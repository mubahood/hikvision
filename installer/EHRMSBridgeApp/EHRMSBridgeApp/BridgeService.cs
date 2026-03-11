using System.Diagnostics;
using System.Runtime.InteropServices;

namespace EHRMSBridgeApp;

/// <summary>
/// Manages the Hikvision bridge project — config, processes, diagnostics.
/// All methods are hardened with try/catch to prevent unhandled exceptions.
/// </summary>
public class BridgeService
{
    public string ProjectRoot { get; private set; } = "";
    public string LastError { get; private set; } = "";

    public BridgeService()
    {
        try
        {
            ProjectRoot = FindProjectRoot();
        }
        catch (Exception ex)
        {
            LastError = $"Failed to find project root: {ex.Message}";
            ProjectRoot = Directory.GetCurrentDirectory();
        }
    }

    // ─── Path helpers ───

    string Env => Path.Combine(ProjectRoot, ".env");
    string EnvExample => Path.Combine(ProjectRoot, ".env.example");
    string BridgeScript => Path.Combine(ProjectRoot, "hikvision_bridge.py");
    string DashboardScript => Path.Combine(ProjectRoot, "dashboard.py");
    string Requirements => Path.Combine(ProjectRoot, "requirements.txt");
    string BridgePid => Path.Combine(ProjectRoot, "bridge.pid");
    string DashboardPid => Path.Combine(ProjectRoot, "dashboard.pid");
    string BridgeLog => Path.Combine(ProjectRoot, "hikvision_bridge.log");
    string BridgeOutputLog => Path.Combine(ProjectRoot, "bridge_output.log");
    string DashboardLog => Path.Combine(ProjectRoot, "dashboard.log");

    public bool ProjectFound
    {
        get
        {
            try { return File.Exists(BridgeScript); }
            catch { return false; }
        }
    }

    // ─── Find project root ───

    static string FindProjectRoot()
    {
        try
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null)
            {
                if (File.Exists(Path.Combine(dir.FullName, "hikvision_bridge.py")))
                    return dir.FullName;
                dir = dir.Parent;
            }
        }
        catch { /* permission or access errors — fall through */ }

        try
        {
            var cwd = Directory.GetCurrentDirectory();
            var dir = new DirectoryInfo(cwd);
            while (dir != null)
            {
                if (File.Exists(Path.Combine(dir.FullName, "hikvision_bridge.py")))
                    return dir.FullName;
                dir = dir.Parent;
            }
            return cwd;
        }
        catch
        {
            return AppContext.BaseDirectory;
        }
    }

    // ─── Python detection ───

    public string FindPython()
    {
        try
        {
            var cmds = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
                ? new[] { "python", "python3", "py" }
                : new[] { "python3", "python" };
            foreach (var cmd in cmds)
            {
                try
                {
                    var (code, _) = Run(cmd, "--version", timeout: 5000);
                    if (code == 0) return cmd;
                }
                catch { }
            }
        }
        catch { }
        return "";
    }

    public string GetPythonVersion()
    {
        try
        {
            var py = FindPython();
            if (string.IsNullOrEmpty(py)) return "Not installed";
            var (_, output) = Run(py, "--version");
            return string.IsNullOrWhiteSpace(output) ? "Unknown version" : output.Trim();
        }
        catch (Exception ex)
        {
            return $"Error: {ex.Message}";
        }
    }

    public string VenvPython
    {
        get
        {
            try
            {
                var dir = Path.Combine(ProjectRoot, ".venv");
                return RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
                    ? Path.Combine(dir, "Scripts", "python.exe")
                    : Path.Combine(dir, "bin", "python3");
            }
            catch
            {
                return "";
            }
        }
    }

    public bool VenvExists
    {
        get
        {
            try { return Directory.Exists(Path.Combine(ProjectRoot, ".venv")); }
            catch { return false; }
        }
    }

    public bool EnvExists
    {
        get
        {
            try { return File.Exists(Env); }
            catch { return false; }
        }
    }

    // ─── Process runner ───

    public (int code, string output) Run(string command, string args, string? workDir = null, int timeout = 60000)
    {
        try
        {
            var psi = new ProcessStartInfo(command, args)
            {
                WorkingDirectory = workDir ?? ProjectRoot,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            var proc = Process.Start(psi);
            if (proc == null) return (-1, "Failed to start process.");
            var stdout = proc.StandardOutput.ReadToEnd();
            var stderr = proc.StandardError.ReadToEnd();
            if (!proc.WaitForExit(timeout))
            {
                try { proc.Kill(true); } catch { }
                return (-1, $"Process timed out after {timeout / 1000}s.\n{stdout}{stderr}");
            }
            return (proc.ExitCode, stdout + stderr);
        }
        catch (Exception ex)
        {
            return (-1, $"Process error: {ex.Message}");
        }
    }

    // ─── PID management ───

    public bool IsRunning(string pidFile)
    {
        try
        {
            if (!File.Exists(pidFile)) return false;
            var content = File.ReadAllText(pidFile).Trim();
            if (int.TryParse(content, out int pid))
            {
                try { Process.GetProcessById(pid); return true; } catch { }
            }
        }
        catch { }
        return false;
    }

    public bool BridgeRunning => IsRunning(BridgePid);
    public bool DashboardRunning => IsRunning(DashboardPid);

    // ─── Setup steps ───

    public (bool ok, string msg) CheckPython()
    {
        try
        {
            var py = FindPython();
            if (string.IsNullOrEmpty(py))
                return (false, "Python not found. Install Python 3.10+ from python.org");
            var (_, ver) = Run(py, "--version");
            return (true, string.IsNullOrWhiteSpace(ver) ? "Python found" : ver.Trim());
        }
        catch (Exception ex)
        {
            return (false, $"Error checking Python: {ex.Message}");
        }
    }

    public (bool ok, string msg) CreateVenv()
    {
        try
        {
            if (VenvExists) return (true, "Virtual environment already exists.");
            var py = FindPython();
            if (string.IsNullOrEmpty(py)) return (false, "Python not found.");
            var venvPath = Path.Combine(ProjectRoot, ".venv");
            var (code, output) = Run(py, $"-m venv \"{venvPath}\"", timeout: 120000);
            return code == 0
                ? (true, "Virtual environment created successfully.")
                : (false, $"Failed: {output}");
        }
        catch (Exception ex)
        {
            return (false, $"Error creating venv: {ex.Message}");
        }
    }

    public (bool ok, string msg) InstallDeps()
    {
        try
        {
            if (string.IsNullOrEmpty(VenvPython) || !File.Exists(VenvPython))
                return (false, "Virtual environment not found. Create it first.");
            var (code, output) = Run(VenvPython, $"-m pip install -r \"{Requirements}\"", timeout: 300000);
            return code == 0
                ? (true, "All dependencies installed successfully.")
                : (false, $"Failed:\n{output}");
        }
        catch (Exception ex)
        {
            return (false, $"Error installing dependencies: {ex.Message}");
        }
    }

    public (bool ok, string msg) TestDatabase()
    {
        try
        {
            if (string.IsNullOrEmpty(VenvPython) || !File.Exists(VenvPython))
                return (false, "Virtual environment not found.");
            var script = "import mysql.connector; from dotenv import load_dotenv; import os; load_dotenv(); " +
                         "c=mysql.connector.connect(host=os.getenv('DB_HOST','localhost'),port=int(os.getenv('DB_PORT','3306'))," +
                         "user=os.getenv('DB_USER','root'),password=os.getenv('DB_PASS','root')," +
                         "database=os.getenv('DB_NAME','hikvision')); print('Connected: '+c.get_server_info()); c.close()";
            var (code, output) = Run(VenvPython, $"-c \"{script}\"", timeout: 15000);
            return code == 0
                ? (true, string.IsNullOrWhiteSpace(output) ? "Connected" : output.Trim())
                : (false, $"Database connection failed: {output}");
        }
        catch (Exception ex)
        {
            return (false, $"Error testing database: {ex.Message}");
        }
    }

    public (bool ok, string msg) TestDevice()
    {
        try
        {
            if (string.IsNullOrEmpty(VenvPython) || !File.Exists(VenvPython))
                return (false, "Virtual environment not found.");
            var script = "from dotenv import load_dotenv; import os, requests; from requests.auth import HTTPDigestAuth; load_dotenv(); " +
                         "ip=os.getenv('DEVICE_IP',''); u=os.getenv('DEVICE_USER','admin'); p=os.getenv('DEVICE_PASS',''); " +
                         "r=requests.get(f'http://{ip}/ISAPI/System/deviceInfo',auth=HTTPDigestAuth(u,p),timeout=10); " +
                         "print('Connected' if r.status_code==200 else f'Failed: {r.status_code}')";
            var (code, output) = Run(VenvPython, $"-c \"{script}\"", timeout: 20000);
            return (code == 0 && output.Contains("Connected"),
                    string.IsNullOrWhiteSpace(output) ? "No response from device" : output.Trim());
        }
        catch (Exception ex)
        {
            return (false, $"Error testing device: {ex.Message}");
        }
    }

    public (bool ok, string msg) CheckDeps()
    {
        try
        {
            if (string.IsNullOrEmpty(VenvPython) || !File.Exists(VenvPython))
                return (false, "Virtual environment not found.");
            var (code, output) = Run(VenvPython, "-m pip list --format=columns", timeout: 30000);
            return (code == 0, string.IsNullOrWhiteSpace(output) ? "No packages found" : output);
        }
        catch (Exception ex)
        {
            return (false, $"Error checking dependencies: {ex.Message}");
        }
    }

    // ─── Config ───

    public Dictionary<string, string> ReadConfig()
    {
        var dict = new Dictionary<string, string>();
        try
        {
            var path = File.Exists(Env) ? Env : (File.Exists(EnvExample) ? EnvExample : "");
            if (string.IsNullOrEmpty(path)) return dict;
            foreach (var line in File.ReadAllLines(path))
            {
                var t = line.Trim();
                if (string.IsNullOrEmpty(t) || t.StartsWith('#')) continue;
                var eq = t.IndexOf('=');
                if (eq > 0) dict[t[..eq].Trim()] = t[(eq + 1)..].Trim();
            }
        }
        catch (Exception ex)
        {
            LastError = $"Error reading config: {ex.Message}";
        }
        return dict;
    }

    public (bool ok, string msg) SaveConfig(Dictionary<string, string> values)
    {
        try
        {
            if (values == null || values.Count == 0)
                return (false, "No configuration values to save.");

            var src = File.Exists(Env) ? Env : (File.Exists(EnvExample) ? EnvExample : "");
            var lines = !string.IsNullOrEmpty(src) ? File.ReadAllLines(src).ToList() : new List<string>();
            var written = new HashSet<string>();
            for (int i = 0; i < lines.Count; i++)
            {
                var t = lines[i].Trim();
                if (string.IsNullOrEmpty(t) || t.StartsWith('#')) continue;
                var eq = t.IndexOf('=');
                if (eq > 0)
                {
                    var key = t[..eq].Trim();
                    if (values.ContainsKey(key))
                    {
                        lines[i] = $"{key}={values[key]}";
                        written.Add(key);
                    }
                }
            }
            foreach (var kv in values.Where(kv => !written.Contains(kv.Key)))
                lines.Add($"{kv.Key}={kv.Value}");
            File.WriteAllLines(Env, lines);
            return (true, "Configuration saved successfully.");
        }
        catch (Exception ex)
        {
            return (false, $"Error saving config: {ex.Message}");
        }
    }

    // ─── Services ───

    public (bool ok, string msg) StartBridge()
    {
        if (BridgeRunning) return (false, "Bridge is already running.");
        if (string.IsNullOrEmpty(VenvPython) || !File.Exists(VenvPython))
            return (false, "Virtual environment not found. Run setup first.");
        try
        {
            var psi = new ProcessStartInfo(VenvPython, $"\"{BridgeScript}\"")
            {
                WorkingDirectory = ProjectRoot,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            var proc = Process.Start(psi);
            if (proc == null) return (false, "Failed to start bridge process.");
            File.WriteAllText(BridgePid, proc.Id.ToString());
            Thread.Sleep(2000);
            if (!proc.HasExited) return (true, $"Bridge started (PID: {proc.Id})");
            var stderr = "";
            try { stderr = proc.StandardError.ReadToEnd(); } catch { }
            return (false, $"Bridge exited immediately.{(string.IsNullOrEmpty(stderr) ? "" : $" Error: {stderr}")}");
        }
        catch (Exception ex) { return (false, $"Failed to start bridge: {ex.Message}"); }
    }

    public (bool ok, string msg) StopBridge()
    {
        try
        {
            if (!File.Exists(BridgePid)) return (false, "Bridge is not running.");
            var content = File.ReadAllText(BridgePid).Trim();
            if (int.TryParse(content, out int pid))
            {
                try
                {
                    var proc = Process.GetProcessById(pid);
                    proc.Kill(true);
                    proc.WaitForExit(5000);
                }
                catch (ArgumentException) { /* Process already exited */ }
                catch (Exception ex)
                {
                    LastError = $"Warning stopping bridge: {ex.Message}";
                }
            }
            try { File.Delete(BridgePid); } catch { }
            return (true, "Bridge stopped.");
        }
        catch (Exception ex)
        {
            return (false, $"Error stopping bridge: {ex.Message}");
        }
    }

    public (bool ok, string msg) StartDashboard()
    {
        if (DashboardRunning) return (false, "Dashboard is already running.");
        if (string.IsNullOrEmpty(VenvPython) || !File.Exists(VenvPython))
            return (false, "Virtual environment not found.");
        try
        {
            var venvDir = Path.GetDirectoryName(VenvPython);
            if (string.IsNullOrEmpty(venvDir))
                return (false, "Could not determine virtual environment directory.");

            var streamlit = Path.Combine(venvDir, "streamlit");
            if (!File.Exists(streamlit) && RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                streamlit = Path.Combine(venvDir, "streamlit.exe");
            if (!File.Exists(streamlit))
                return (false, $"Streamlit not found at {streamlit}. Run 'Install Dependencies' first.");

            var psi = new ProcessStartInfo(streamlit, $"run \"{DashboardScript}\" --server.port 8502 --server.headless true")
            {
                WorkingDirectory = ProjectRoot,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            var proc = Process.Start(psi);
            if (proc == null) return (false, "Failed to start dashboard process.");
            File.WriteAllText(DashboardPid, proc.Id.ToString());
            Thread.Sleep(3000);
            if (!proc.HasExited) return (true, $"Dashboard started on port 8502 (PID: {proc.Id})");
            return (false, "Dashboard exited immediately. Check that streamlit is installed correctly.");
        }
        catch (Exception ex) { return (false, $"Failed to start dashboard: {ex.Message}"); }
    }

    public (bool ok, string msg) StopDashboard()
    {
        try
        {
            if (!File.Exists(DashboardPid)) return (false, "Dashboard is not running.");
            var content = File.ReadAllText(DashboardPid).Trim();
            if (int.TryParse(content, out int pid))
            {
                try
                {
                    var proc = Process.GetProcessById(pid);
                    proc.Kill(true);
                    proc.WaitForExit(5000);
                }
                catch (ArgumentException) { /* Process already exited */ }
                catch (Exception ex)
                {
                    LastError = $"Warning stopping dashboard: {ex.Message}";
                }
            }
            try { File.Delete(DashboardPid); } catch { }
            return (true, "Dashboard stopped.");
        }
        catch (Exception ex)
        {
            return (false, $"Error stopping dashboard: {ex.Message}");
        }
    }

    // ─── Diagnostics ───

    public List<(string name, bool ok, string detail)> RunDiagnostics()
    {
        var checks = new List<(string, bool, string)>();
        try
        {
            checks.Add(("Project Files", ProjectFound, ProjectFound ? "All core files found" : "hikvision_bridge.py not found"));

            var py = FindPython();
            checks.Add(("Python", !string.IsNullOrEmpty(py), string.IsNullOrEmpty(py) ? "Not installed" : GetPythonVersion()));
            checks.Add(("Virtual Environment", VenvExists, VenvExists ? ".venv ready" : "Not created"));
            checks.Add(("Configuration (.env)", EnvExists, EnvExists ? "Configured" : "Missing"));
            checks.Add(("Bridge Service", BridgeRunning, BridgeRunning ? "Running" : "Stopped"));
            checks.Add(("Dashboard", DashboardRunning, DashboardRunning ? "Running on port 8502" : "Stopped"));

            try
            {
                var logExists = File.Exists(BridgeLog);
                long logSize = 0;
                if (logExists) logSize = new FileInfo(BridgeLog).Length / 1024;
                checks.Add(("Bridge Log", logExists, logExists ? $"Size: {logSize} KB" : "No log file yet"));
            }
            catch
            {
                checks.Add(("Bridge Log", false, "Could not check log file"));
            }
        }
        catch (Exception ex)
        {
            checks.Add(("Diagnostics Error", false, ex.Message));
        }
        return checks;
    }

    // ─── Logs ───

    public string[] GetLogs(string service, int maxLines = 200)
    {
        try
        {
            var logFile = service == "bridge"
                ? (File.Exists(BridgeLog) ? BridgeLog : BridgeOutputLog)
                : DashboardLog;
            if (!File.Exists(logFile)) return Array.Empty<string>();
            var lines = File.ReadAllLines(logFile);
            return lines.Skip(Math.Max(0, lines.Length - maxLines)).ToArray();
        }
        catch (Exception ex)
        {
            return new[] { $"Error reading logs: {ex.Message}" };
        }
    }
}
