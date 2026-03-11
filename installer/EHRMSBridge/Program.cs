using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://localhost:5199");
builder.Logging.SetMinimumLevel(LogLevel.Warning);

var app = builder.Build();
app.UseDefaultFiles();
app.UseStaticFiles();

// ─── Resolve project root (parent of installer/) ───
var projectRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", ".."));
if (!File.Exists(Path.Combine(projectRoot, "hikvision_bridge.py")))
{
    // Fallback: check if we're running from publish output or dev
    projectRoot = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), ".."));
    if (!File.Exists(Path.Combine(projectRoot, "hikvision_bridge.py")))
    {
        // Last resort: prompt-style search upward
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "hikvision_bridge.py")))
            {
                projectRoot = dir.FullName;
                break;
            }
            dir = dir.Parent;
        }
    }
}

var envFile = Path.Combine(projectRoot, ".env");
var envExample = Path.Combine(projectRoot, ".env.example");
var bridgeScript = Path.Combine(projectRoot, "hikvision_bridge.py");
var dashboardScript = Path.Combine(projectRoot, "dashboard.py");
var requirementsFile = Path.Combine(projectRoot, "requirements.txt");
var bridgePidFile = Path.Combine(projectRoot, "bridge.pid");
var dashboardPidFile = Path.Combine(projectRoot, "dashboard.pid");
var bridgeLog = Path.Combine(projectRoot, "hikvision_bridge.log");
var bridgeOutputLog = Path.Combine(projectRoot, "bridge_output.log");
var dashboardLog = Path.Combine(projectRoot, "dashboard.log");

string FindPython()
{
    var candidates = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
        ? new[] { "python", "python3", "py" }
        : new[] { "python3", "python" };
    foreach (var cmd in candidates)
    {
        try
        {
            var p = Process.Start(new ProcessStartInfo(cmd, "--version")
            { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true });
            p?.WaitForExit(5000);
            if (p?.ExitCode == 0) return cmd;
        }
        catch { }
    }
    return "";
}

string GetVenvPython()
{
    var venvDir = Path.Combine(projectRoot, ".venv");
    if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        return Path.Combine(venvDir, "Scripts", "python.exe");
    return Path.Combine(venvDir, "bin", "python3");
}

(int code, string output) RunCommand(string command, string args, string? workDir = null, int timeout = 60000)
{
    try
    {
        var psi = new ProcessStartInfo(command, args)
        {
            WorkingDirectory = workDir ?? projectRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        var proc = Process.Start(psi)!;
        var stdout = proc.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit(timeout);
        return (proc.ExitCode, stdout + stderr);
    }
    catch (Exception ex)
    {
        return (-1, ex.Message);
    }
}

bool IsProcessRunning(string pidFile)
{
    if (!File.Exists(pidFile)) return false;
    if (int.TryParse(File.ReadAllText(pidFile).Trim(), out int pid))
    {
        try { Process.GetProcessById(pid); return true; } catch { }
    }
    return false;
}

Dictionary<string, string> ReadEnvFile()
{
    var dict = new Dictionary<string, string>();
    var path = File.Exists(envFile) ? envFile : envExample;
    if (!File.Exists(path)) return dict;
    foreach (var line in File.ReadAllLines(path))
    {
        var trimmed = line.Trim();
        if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith('#')) continue;
        var eq = trimmed.IndexOf('=');
        if (eq > 0)
            dict[trimmed[..eq].Trim()] = trimmed[(eq + 1)..].Trim();
    }
    return dict;
}

void WriteEnvFile(Dictionary<string, string> values)
{
    // Preserve comments and structure from existing file or example
    var sourcePath = File.Exists(envFile) ? envFile : envExample;
    var lines = File.Exists(sourcePath) ? File.ReadAllLines(sourcePath).ToList() : new List<string>();
    var written = new HashSet<string>();
    for (int i = 0; i < lines.Count; i++)
    {
        var trimmed = lines[i].Trim();
        if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith('#')) continue;
        var eq = trimmed.IndexOf('=');
        if (eq > 0)
        {
            var key = trimmed[..eq].Trim();
            if (values.ContainsKey(key))
            {
                lines[i] = $"{key}={values[key]}";
                written.Add(key);
            }
        }
    }
    // Append any new keys
    foreach (var kv in values.Where(kv => !written.Contains(kv.Key)))
        lines.Add($"{kv.Key}={kv.Value}");
    File.WriteAllLines(envFile, lines);
}

// ─── API ENDPOINTS ───

// Status overview
app.MapGet("/api/status", () =>
{
    var python = FindPython();
    var pythonVersion = "";
    if (!string.IsNullOrEmpty(python))
    {
        var (_, ver) = RunCommand(python, "--version");
        pythonVersion = ver.Trim();
    }
    var venvExists = Directory.Exists(Path.Combine(projectRoot, ".venv"));
    var envExists = File.Exists(envFile);
    var bridgeRunning = IsProcessRunning(bridgePidFile);
    var dashboardRunning = IsProcessRunning(dashboardPidFile);
    var projectFound = File.Exists(bridgeScript);

    return Results.Json(new
    {
        projectRoot,
        projectFound,
        pythonInstalled = !string.IsNullOrEmpty(python),
        pythonCommand = python,
        pythonVersion,
        venvExists,
        envConfigured = envExists,
        bridgeRunning,
        dashboardRunning,
        platform = RuntimeInformation.OSDescription
    });
});

// ─── SETUP ENDPOINTS ───

app.MapPost("/api/setup/check-python", () =>
{
    var python = FindPython();
    if (string.IsNullOrEmpty(python))
        return Results.Json(new { success = false, message = "Python not found. Please install Python 3.10+ from python.org" });
    var (_, ver) = RunCommand(python, "--version");
    return Results.Json(new { success = true, message = ver.Trim(), command = python });
});

app.MapPost("/api/setup/create-venv", () =>
{
    var python = FindPython();
    if (string.IsNullOrEmpty(python))
        return Results.Json(new { success = false, message = "Python not found" });
    var venvPath = Path.Combine(projectRoot, ".venv");
    if (Directory.Exists(venvPath))
        return Results.Json(new { success = true, message = "Virtual environment already exists" });
    var (code, output) = RunCommand(python, $"-m venv \"{venvPath}\"", projectRoot, 120000);
    return Results.Json(new { success = code == 0, message = code == 0 ? "Virtual environment created" : output });
});

app.MapPost("/api/setup/install-deps", () =>
{
    var venvPython = GetVenvPython();
    if (!File.Exists(venvPython))
        return Results.Json(new { success = false, message = "Virtual environment not found. Create it first." });
    var (code, output) = RunCommand(venvPython, $"-m pip install -r \"{requirementsFile}\"", projectRoot, 300000);
    return Results.Json(new { success = code == 0, message = code == 0 ? "Dependencies installed successfully" : output });
});

app.MapPost("/api/setup/check-deps", () =>
{
    var venvPython = GetVenvPython();
    if (!File.Exists(venvPython))
        return Results.Json(new { success = false, message = "Virtual environment not found" });
    var (code, output) = RunCommand(venvPython, "-m pip list --format=columns", projectRoot, 30000);
    return Results.Json(new { success = code == 0, packages = output });
});

app.MapPost("/api/setup/test-db", () =>
{
    var venvPython = GetVenvPython();
    if (!File.Exists(venvPython))
        return Results.Json(new { success = false, message = "Virtual environment not found" });
    var script = "import mysql.connector; from dotenv import load_dotenv; import os; load_dotenv(); " +
                 "c=mysql.connector.connect(host=os.getenv('DB_HOST','localhost'),port=int(os.getenv('DB_PORT','3306'))," +
                 "user=os.getenv('DB_USER','root'),password=os.getenv('DB_PASS','root')," +
                 "database=os.getenv('DB_NAME','hikvision')); print('Connected: '+c.get_server_info()); c.close()";
    var (code, output) = RunCommand(venvPython, $"-c \"{script}\"", projectRoot, 15000);
    return Results.Json(new { success = code == 0, message = code == 0 ? output.Trim() : $"Database connection failed: {output}" });
});

app.MapPost("/api/setup/test-device", () =>
{
    var venvPython = GetVenvPython();
    if (!File.Exists(venvPython))
        return Results.Json(new { success = false, message = "Virtual environment not found" });
    var script = "from dotenv import load_dotenv; import os, requests; from requests.auth import HTTPDigestAuth; load_dotenv(); " +
                 "ip=os.getenv('DEVICE_IP',''); u=os.getenv('DEVICE_USER','admin'); p=os.getenv('DEVICE_PASS',''); " +
                 "r=requests.get(f'http://{ip}/ISAPI/System/deviceInfo',auth=HTTPDigestAuth(u,p),timeout=10); " +
                 "print('Connected' if r.status_code==200 else f'Failed: {r.status_code}')";
    var (code, output) = RunCommand(venvPython, $"-c \"{script}\"", projectRoot, 20000);
    return Results.Json(new { success = code == 0 && output.Contains("Connected"), message = output.Trim() });
});

// ─── CONFIG ENDPOINTS ───

app.MapGet("/api/config", () => Results.Json(ReadEnvFile()));

app.MapPost("/api/config", async (HttpRequest req) =>
{
    var body = await JsonSerializer.DeserializeAsync<Dictionary<string, string>>(req.Body);
    if (body == null) return Results.BadRequest("Invalid JSON");
    // Validate keys - only allow known config keys
    var allowedKeys = new HashSet<string> {
        "DEVICE_IP","DEVICE_USER","DEVICE_PASS","DEVICE_ID",
        "DB_HOST","DB_PORT","DB_NAME","DB_USER","DB_PASS","DB_SOCKET",
        "WEBHOOK_URL","WEBHOOK_API_KEY","BATCH_UPLOAD_SIZE",
        "POLL_INTERVAL","LOG_LEVEL","LOG_FILE",
        "DATA_RETENTION_DAYS","AUTO_BACKUP_ENABLED"
    };
    var filtered = body.Where(kv => allowedKeys.Contains(kv.Key)).ToDictionary(kv => kv.Key, kv => kv.Value);
    WriteEnvFile(filtered);
    return Results.Json(new { success = true, message = "Configuration saved" });
});

// ─── SERVICE MANAGEMENT ───

app.MapPost("/api/bridge/start", () =>
{
    if (IsProcessRunning(bridgePidFile))
        return Results.Json(new { success = false, message = "Bridge is already running" });
    var venvPython = GetVenvPython();
    if (!File.Exists(venvPython))
        return Results.Json(new { success = false, message = "Virtual environment not found. Run setup first." });
    try
    {
        var psi = new ProcessStartInfo(venvPython, $"\"{bridgeScript}\"")
        {
            WorkingDirectory = projectRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        var proc = Process.Start(psi)!;
        File.WriteAllText(bridgePidFile, proc.Id.ToString());
        Thread.Sleep(2000);
        if (!proc.HasExited)
            return Results.Json(new { success = true, message = $"Bridge started (PID: {proc.Id})" });
        var err = proc.StandardError.ReadToEnd();
        return Results.Json(new { success = false, message = $"Bridge exited immediately: {err}" });
    }
    catch (Exception ex)
    {
        return Results.Json(new { success = false, message = ex.Message });
    }
});

app.MapPost("/api/bridge/stop", () =>
{
    if (!File.Exists(bridgePidFile))
        return Results.Json(new { success = false, message = "Bridge is not running" });
    try
    {
        var pid = int.Parse(File.ReadAllText(bridgePidFile).Trim());
        var proc = Process.GetProcessById(pid);
        proc.Kill(true);
        proc.WaitForExit(5000);
        File.Delete(bridgePidFile);
        return Results.Json(new { success = true, message = "Bridge stopped" });
    }
    catch
    {
        if (File.Exists(bridgePidFile)) File.Delete(bridgePidFile);
        return Results.Json(new { success = true, message = "Bridge stopped (process already ended)" });
    }
});

app.MapPost("/api/dashboard/start", () =>
{
    if (IsProcessRunning(dashboardPidFile))
        return Results.Json(new { success = false, message = "Dashboard is already running" });
    var venvPython = GetVenvPython();
    if (!File.Exists(venvPython))
        return Results.Json(new { success = false, message = "Virtual environment not found" });
    try
    {
        var streamlit = Path.Combine(Path.GetDirectoryName(venvPython)!, "streamlit");
        if (!File.Exists(streamlit) && RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            streamlit = Path.Combine(Path.GetDirectoryName(venvPython)!, "streamlit.exe");
        var psi = new ProcessStartInfo(streamlit, $"run \"{dashboardScript}\" --server.port 8502 --server.headless true")
        {
            WorkingDirectory = projectRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        var proc = Process.Start(psi)!;
        File.WriteAllText(dashboardPidFile, proc.Id.ToString());
        Thread.Sleep(3000);
        if (!proc.HasExited)
            return Results.Json(new { success = true, message = $"Dashboard started on port 8502 (PID: {proc.Id})" });
        return Results.Json(new { success = false, message = "Dashboard exited immediately" });
    }
    catch (Exception ex)
    {
        return Results.Json(new { success = false, message = ex.Message });
    }
});

app.MapPost("/api/dashboard/stop", () =>
{
    if (!File.Exists(dashboardPidFile))
        return Results.Json(new { success = false, message = "Dashboard is not running" });
    try
    {
        var pid = int.Parse(File.ReadAllText(dashboardPidFile).Trim());
        var proc = Process.GetProcessById(pid);
        proc.Kill(true);
        proc.WaitForExit(5000);
        File.Delete(dashboardPidFile);
        return Results.Json(new { success = true, message = "Dashboard stopped" });
    }
    catch
    {
        if (File.Exists(dashboardPidFile)) File.Delete(dashboardPidFile);
        return Results.Json(new { success = true, message = "Dashboard stopped" });
    }
});

// ─── DIAGNOSTICS ───

app.MapGet("/api/diagnostics", () =>
{
    var checks = new List<object>();

    // 1. Project files
    checks.Add(new { name = "Project Files", ok = File.Exists(bridgeScript), detail = File.Exists(bridgeScript) ? "All core files found" : "hikvision_bridge.py not found" });

    // 2. Python
    var py = FindPython();
    checks.Add(new { name = "Python", ok = !string.IsNullOrEmpty(py), detail = string.IsNullOrEmpty(py) ? "Not installed" : RunCommand(py, "--version").output.Trim() });

    // 3. Virtual env
    var venvExists = Directory.Exists(Path.Combine(projectRoot, ".venv"));
    checks.Add(new { name = "Virtual Environment", ok = venvExists, detail = venvExists ? ".venv directory exists" : "Not created" });

    // 4. .env config
    var envOk = File.Exists(envFile);
    checks.Add(new { name = "Environment Config", ok = envOk, detail = envOk ? ".env file configured" : ".env file missing" });

    // 5. Bridge status
    var bridgeUp = IsProcessRunning(bridgePidFile);
    checks.Add(new { name = "Bridge Service", ok = bridgeUp, detail = bridgeUp ? "Running" : "Stopped" });

    // 6. Dashboard status
    var dashUp = IsProcessRunning(dashboardPidFile);
    checks.Add(new { name = "Dashboard", ok = dashUp, detail = dashUp ? "Running on port 8502" : "Stopped" });

    // 7. Log file
    var logExists = File.Exists(bridgeLog);
    var logSize = logExists ? new FileInfo(bridgeLog).Length : 0;
    checks.Add(new { name = "Bridge Log", ok = logExists, detail = logExists ? $"Size: {logSize / 1024} KB" : "No log file yet" });

    return Results.Json(checks);
});

app.MapGet("/api/logs/{service}", (string service) =>
{
    var logFile = service switch
    {
        "bridge" => File.Exists(bridgeLog) ? bridgeLog : bridgeOutputLog,
        "dashboard" => dashboardLog,
        _ => ""
    };
    if (string.IsNullOrEmpty(logFile) || !File.Exists(logFile))
        return Results.Json(new { lines = Array.Empty<string>() });
    var lines = File.ReadAllLines(logFile);
    var tail = lines.Skip(Math.Max(0, lines.Length - 200)).ToArray();
    return Results.Json(new { lines = tail });
});

// ─── OPEN BROWSER + RUN ───

app.Lifetime.ApplicationStarted.Register(() =>
{
    var url = "http://localhost:5199";
    Console.WriteLine($"\n  EHRMS Device Bridge Manager");
    Console.WriteLine($"  Open: {url}\n");
    try
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            Process.Start(new ProcessStartInfo("cmd", $"/c start {url}") { CreateNoWindow = true });
        else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            Process.Start("open", url);
        else
            Process.Start("xdg-open", url);
    }
    catch { }
});

app.Run();
