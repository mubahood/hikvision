using System.Diagnostics;
using System.Runtime.InteropServices;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Layout;
using Avalonia.Media;
using Avalonia.Threading;

namespace EHRMSBridgeApp;

public partial class MainWindow : Window
{
    readonly BridgeService _svc;
    readonly Dictionary<string, TextBox> _cfgInputs = new();
    int _setupStep = 1;
    string _currentLogService = "bridge";

    // Brand colours
    static readonly IBrush BrandBrush = new SolidColorBrush(Color.Parse("#790D0B"));
    static readonly IBrush GreenBrush = new SolidColorBrush(Color.Parse("#34C759"));
    static readonly IBrush RedBrush = new SolidColorBrush(Color.Parse("#FF3B30"));
    static readonly IBrush GrayBrush = new SolidColorBrush(Color.Parse("#6E6E73"));
    static readonly IBrush DarkBrush = new SolidColorBrush(Color.Parse("#1D1D1F"));
    static readonly IBrush WhiteBrush = Brushes.White;
    static readonly IBrush OkBg = new SolidColorBrush(Color.Parse("#E8F9EE"));
    static readonly IBrush ErrBg = new SolidColorBrush(Color.Parse("#FFECEA"));
    static readonly IBrush LightBg = new SolidColorBrush(Color.Parse("#F5F5F7"));

    // All pages for navigation
    readonly string[] _pages = ["Home", "Setup", "Settings", "Run", "Diagnostics", "Logs", "Docs"];

    // Settings schema
    static readonly (string section, string key, string label, string placeholder, bool wide)[] ConfigFields =
    [
        ("Device", "DEVICE_IP", "Device IP", "192.168.1.128", false),
        ("Device", "DEVICE_USER", "Username", "admin", false),
        ("Device", "DEVICE_PASS", "Password", "password", false),
        ("Device", "DEVICE_ID", "Device ID", "door1", false),
        ("Db", "DB_HOST", "Host", "localhost", false),
        ("Db", "DB_PORT", "Port", "3306", false),
        ("Db", "DB_NAME", "Database", "hikvision", false),
        ("Db", "DB_USER", "Username", "root", false),
        ("Db", "DB_PASS", "Password", "root", false),
        ("Db", "DB_SOCKET", "Unix Socket (optional)", "/tmp/mysql.sock", true),
        ("Webhook", "WEBHOOK_URL", "Webhook URL", "http://...", true),
        ("Webhook", "WEBHOOK_API_KEY", "API Key", "your_api_key", false),
        ("Webhook", "BATCH_UPLOAD_SIZE", "Batch Size", "10", false),
        ("Bridge", "POLL_INTERVAL", "Poll Interval (sec)", "2", false),
        ("Bridge", "LOG_LEVEL", "Log Level", "INFO", false),
        ("Bridge", "LOG_FILE", "Log File", "hikvision_bridge.log", false),
        ("Bridge", "DATA_RETENTION_DAYS", "Data Retention (days)", "90", false),
    ];

    // Setup wizard steps
    static readonly (string title, string desc, string action)[] SetupSteps =
    [
        ("Check Python Installation", "We need Python 3.10 or higher to run the bridge.", "Check Python"),
        ("Create Virtual Environment", "An isolated Python environment keeps your dependencies clean.", "Create .venv"),
        ("Install Dependencies", "Install all required Python packages from requirements.txt.", "Install Packages"),
        ("Configure Environment", "Set your device IP, database credentials, and webhook URL.", "Open Settings"),
        ("Test Database Connection", "Verify MySQL is running and the hikvision database exists.", "Test Database"),
        ("Test Device Connection", "Check connectivity to your Hikvision terminal.", "Test Device"),
    ];

    public MainWindow()
    {
        try
        {
            _svc = new BridgeService();
            InitializeComponent();
            LoadHomePage();
            RenderSetupStep();
        }
        catch (Exception ex)
        {
            _svc ??= new BridgeService();
            try { InitializeComponent(); } catch { }
            ShowGlobalError($"Initialization error: {ex.Message}");
        }
    }

    void ShowGlobalError(string message)
    {
        try
        {
            var svcMsg = this.FindControl<TextBlock>("ServiceMsg");
            if (svcMsg != null)
            {
                svcMsg.Text = message;
                svcMsg.Foreground = RedBrush;
            }
        }
        catch { }
    }

    // ═══ NAVIGATION ═══

    void Nav_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            if (sender is Button btn && btn.Tag is string page)
                NavigateTo(page);
        }
        catch (Exception ex)
        {
            ShowGlobalError($"Navigation error: {ex.Message}");
        }
    }

    void NavigateTo(string page)
    {
        try
        {
            // Hide all pages
            foreach (var p in _pages)
            {
                var panel = this.FindControl<StackPanel>($"Page{p}");
                if (panel != null) panel.IsVisible = false;
            }
            // Show target
            var target = this.FindControl<StackPanel>($"Page{page}");
            if (target != null) target.IsVisible = true;

            // Update nav buttons
            var navNames = new Dictionary<string, string>
            {
                ["Home"] = "NavHome", ["Setup"] = "NavSetup", ["Settings"] = "NavSettings",
                ["Run"] = "NavRun", ["Diagnostics"] = "NavDiag", ["Logs"] = "NavLogs", ["Docs"] = "NavDocs"
            };
            foreach (var (key, name) in navNames)
            {
                var navBtn = this.FindControl<Button>(name);
                if (navBtn == null) continue;
                navBtn.Classes.Clear();
                navBtn.Classes.Add(key == page ? "nav-active" : "nav");
            }

            // Trigger page load
            if (page == "Home") LoadHomePage();
            if (page == "Settings") LoadSettingsPage();
            if (page == "Run") RefreshServices();
            if (page == "Diagnostics") RunDiag_Click(null, null!);
        }
        catch (Exception ex)
        {
            ShowGlobalError($"Navigation error: {ex.Message}");
        }
    }

    // ═══ HOME PAGE ═══

    void LoadHomePage()
    {
        Task.Run(() =>
        {
            try
            {
                var python = _svc.FindPython();
                var pyVer = _svc.GetPythonVersion();
                var venv = _svc.VenvExists;
                var env = _svc.EnvExists;
                var bridge = _svc.BridgeRunning;
                var dash = _svc.DashboardRunning;

                Dispatcher.UIThread.Post(() =>
                {
                    try
                    {
                        HomeCards.Children.Clear();
                        AddStatusCard(HomeCards, "Python", !string.IsNullOrEmpty(python) ? "Installed" : "Missing", !string.IsNullOrEmpty(python));
                        AddStatusCard(HomeCards, "Virtual Env", venv ? "Ready" : "Not Created", venv);
                        AddStatusCard(HomeCards, "Config (.env)", env ? "Configured" : "Missing", env);
                        AddStatusCard(HomeCards, "Bridge", bridge ? "Running" : "Stopped", bridge);
                        AddStatusCard(HomeCards, "Dashboard", dash ? "Running" : "Stopped", dash);

                        HomeInfo.Text = $"Project: {_svc.ProjectRoot}\nPython: {pyVer}\nPlatform: {RuntimeInformation.OSDescription}";
                    }
                    catch (Exception ex)
                    {
                        ShowGlobalError($"Error loading home: {ex.Message}");
                    }
                });
            }
            catch (Exception ex)
            {
                Dispatcher.UIThread.Post(() => ShowGlobalError($"Error loading home: {ex.Message}"));
            }
        });
    }

    void AddStatusCard(WrapPanel parent, string label, string value, bool ok)
    {
        var card = new Border
        {
            Background = WhiteBrush,
            CornerRadius = new CornerRadius(12),
            Padding = new Thickness(20),
            Margin = new Thickness(0, 0, 12, 12),
            MinWidth = 170,
            BoxShadow = BoxShadows.Parse("0 2 10 0 #14000000"),
            Child = new StackPanel
            {
                Children =
                {
                    new TextBlock { Text = label.ToUpper(), FontSize = 11, FontWeight = FontWeight.Bold, Foreground = GrayBrush, LetterSpacing = 0.5 },
                    new TextBlock { Text = value, FontSize = 24, FontWeight = FontWeight.Bold, Foreground = ok ? GreenBrush : RedBrush, Margin = new Thickness(0, 4, 0, 0) }
                }
            }
        };
        parent.Children.Add(card);
    }

    // ═══ SETUP WIZARD ═══

    void RenderSetupStep()
    {
        try
        {
            StepIndicators.Children.Clear();
            for (int i = 0; i < SetupSteps.Length; i++)
            {
                var stepNum = i + 1;
                var isDone = stepNum < _setupStep;
                var isActive = stepNum == _setupStep;

                var circle = new Border
                {
                    Width = 30, Height = 30,
                    CornerRadius = new CornerRadius(15),
                    Background = isDone ? GreenBrush : (isActive ? BrandBrush : new SolidColorBrush(Color.Parse("#D2D2D7"))),
                    Margin = new Thickness(0, 0, 8, 0),
                    Child = new TextBlock
                    {
                        Text = isDone ? "✓" : stepNum.ToString(),
                        Foreground = (isDone || isActive) ? WhiteBrush : GrayBrush,
                        FontSize = 13, FontWeight = FontWeight.Bold,
                        HorizontalAlignment = HorizontalAlignment.Center,
                        VerticalAlignment = VerticalAlignment.Center
                    }
                };
                StepIndicators.Children.Add(circle);
            }

            if (_setupStep < 1 || _setupStep > SetupSteps.Length)
                _setupStep = 1;

            var step = SetupSteps[_setupStep - 1];
            StepTitle.Text = $"Step {_setupStep}: {step.title}";
            StepDesc.Text = step.desc;
            StepAction.Content = step.action;
            StepResult.IsVisible = false;
            StepBack.IsVisible = _setupStep > 1;
            StepNext.Content = _setupStep < SetupSteps.Length ? "Next →" : "Finish → Run Services";
        }
        catch (Exception ex)
        {
            ShowGlobalError($"Error rendering step: {ex.Message}");
        }
    }

    async void StepAction_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            StepAction.IsEnabled = false;
            StepAction.Content = "Working...";

            bool ok = false;
            string msg = "";

            await Task.Run(() =>
            {
                try
                {
                    switch (_setupStep)
                    {
                        case 1: (ok, msg) = _svc.CheckPython(); break;
                        case 2: (ok, msg) = _svc.CreateVenv(); break;
                        case 3: (ok, msg) = _svc.InstallDeps(); break;
                        case 4:
                            ok = true; msg = "Configure your settings, then return to continue.";
                            Dispatcher.UIThread.Post(() => { try { NavigateTo("Settings"); } catch { } });
                            break;
                        case 5: (ok, msg) = _svc.TestDatabase(); break;
                        case 6: (ok, msg) = _svc.TestDevice(); break;
                        default: msg = "Unknown step."; break;
                    }
                }
                catch (Exception ex)
                {
                    ok = false;
                    msg = $"Error: {ex.Message}";
                }
            });

            StepAction.IsEnabled = true;
            if (_setupStep >= 1 && _setupStep <= SetupSteps.Length)
                StepAction.Content = SetupSteps[_setupStep - 1].action;
            StepResult.IsVisible = true;
            StepResult.Background = ok ? OkBg : ErrBg;
            StepResultText.Text = $"{(ok ? "✓" : "✗")} {msg}";
            StepResultText.Foreground = ok ? GreenBrush : RedBrush;
        }
        catch (Exception ex)
        {
            StepAction.IsEnabled = true;
            ShowGlobalError($"Step action error: {ex.Message}");
        }
    }

    void StepBack_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            if (_setupStep > 1) { _setupStep--; RenderSetupStep(); }
        }
        catch (Exception ex)
        {
            ShowGlobalError($"Navigation error: {ex.Message}");
        }
    }

    void StepNext_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            if (_setupStep < SetupSteps.Length)
            {
                _setupStep++;
                RenderSetupStep();
            }
            else
            {
                NavigateTo("Run");
            }
        }
        catch (Exception ex)
        {
            ShowGlobalError($"Navigation error: {ex.Message}");
        }
    }

    // ═══ SETTINGS PAGE ═══

    void LoadSettingsPage()
    {
        try
        {
            var config = _svc.ReadConfig();
            _cfgInputs.Clear();

            var containers = new Dictionary<string, WrapPanel>
            {
                ["Device"] = CfgDevice, ["Db"] = CfgDb, ["Webhook"] = CfgWebhook, ["Bridge"] = CfgBridge
            };
            foreach (var c in containers.Values) c.Children.Clear();

            foreach (var (section, key, label, placeholder, wide) in ConfigFields)
            {
                if (!containers.TryGetValue(section, out var container)) continue;

                config.TryGetValue(key, out var val);
                var input = new TextBox
                {
                    Width = wide ? 440 : 210,
                    Watermark = placeholder,
                    Text = val ?? "",
                    CornerRadius = new CornerRadius(8),
                    Padding = new Thickness(10, 8),
                    FontSize = 13,
                    Margin = new Thickness(0, 0, 12, 0)
                };
                if (key.Contains("PASS", StringComparison.OrdinalIgnoreCase))
                    input.PasswordChar = '•';
                _cfgInputs[key] = input;

                var group = new StackPanel
                {
                    Margin = new Thickness(0, 0, 0, 10),
                    Width = wide ? 460 : 225,
                    Children =
                    {
                        new TextBlock { Text = label.ToUpper(), FontSize = 10.5, FontWeight = FontWeight.Bold, Foreground = GrayBrush, LetterSpacing = 0.3, Margin = new Thickness(0, 0, 0, 4) },
                        input
                    }
                };
                container.Children.Add(group);
            }
        }
        catch (Exception ex)
        {
            ShowGlobalError($"Error loading settings: {ex.Message}");
        }
    }

    async void SaveSettings_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            SaveSettingsBtn.IsEnabled = false;
            SaveSettingsBtn.Content = "Saving...";

            var data = new Dictionary<string, string>();
            foreach (var (key, input) in _cfgInputs)
            {
                if (!string.IsNullOrEmpty(input.Text))
                    data[key] = input.Text;
            }

            var (ok, msg) = (false, "");
            await Task.Run(() => (ok, msg) = _svc.SaveConfig(data));

            SaveSettingsBtn.IsEnabled = true;
            if (ok)
            {
                SaveSettingsBtn.Content = "✓ Saved!";
                await Task.Delay(1500);
                SaveSettingsBtn.Content = "Save Configuration";
            }
            else
            {
                SaveSettingsBtn.Content = $"✗ {msg}";
                await Task.Delay(3000);
                SaveSettingsBtn.Content = "Save Configuration";
            }
        }
        catch (Exception ex)
        {
            SaveSettingsBtn.IsEnabled = true;
            SaveSettingsBtn.Content = "Save Configuration";
            ShowGlobalError($"Error saving settings: {ex.Message}");
        }
    }

    // ═══ RUN SERVICES ═══

    void RefreshServices()
    {
        Task.Run(() =>
        {
            try
            {
                var br = _svc.BridgeRunning;
                var dr = _svc.DashboardRunning;
                Dispatcher.UIThread.Post(() =>
                {
                    try
                    {
                        BridgeStatusText.Text = br ? "Running" : "Stopped";
                        BridgeStatusText.Foreground = br ? GreenBrush : RedBrush;
                        BridgeDot.Classes.Clear();
                        BridgeDot.Classes.Add(br ? "dot-green" : "dot-red");

                        DashStatusText.Text = dr ? "Running" : "Stopped";
                        DashStatusText.Foreground = dr ? GreenBrush : RedBrush;
                        DashDot.Classes.Clear();
                        DashDot.Classes.Add(dr ? "dot-green" : "dot-red");
                    }
                    catch (Exception ex) { ShowGlobalError($"UI refresh error: {ex.Message}"); }
                });
            }
            catch (Exception ex)
            {
                Dispatcher.UIThread.Post(() => ShowGlobalError($"Status check error: {ex.Message}"));
            }
        });
    }

    async void BridgeStart_Click(object? sender, RoutedEventArgs e) => await ServiceAction(() => _svc.StartBridge());
    async void BridgeStop_Click(object? sender, RoutedEventArgs e) => await ServiceAction(() => _svc.StopBridge());
    async void DashStart_Click(object? sender, RoutedEventArgs e) => await ServiceAction(() => _svc.StartDashboard());
    async void DashStop_Click(object? sender, RoutedEventArgs e) => await ServiceAction(() => _svc.StopDashboard());

    async void StartAll_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            await ServiceAction(() => _svc.StartBridge());
            await ServiceAction(() => _svc.StartDashboard());
        }
        catch (Exception ex)
        {
            ShowGlobalError($"Error starting services: {ex.Message}");
        }
    }

    async void StopAll_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            await ServiceAction(() => _svc.StopBridge());
            await ServiceAction(() => _svc.StopDashboard());
        }
        catch (Exception ex)
        {
            ShowGlobalError($"Error stopping services: {ex.Message}");
        }
    }

    void OpenDashboard_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            var url = "http://localhost:8502";
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                Process.Start(new ProcessStartInfo("cmd", $"/c start {url}") { CreateNoWindow = true });
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
                Process.Start("open", url);
            else
                Process.Start("xdg-open", url);
        }
        catch (Exception ex)
        {
            ServiceMsg.Text = $"✗ Could not open browser: {ex.Message}";
            ServiceMsg.Foreground = RedBrush;
        }
    }

    async Task ServiceAction(Func<(bool ok, string msg)> action)
    {
        try
        {
            (bool ok, string msg) result = (false, "");
            await Task.Run(() =>
            {
                try { result = action(); }
                catch (Exception ex) { result = (false, $"Error: {ex.Message}"); }
            });
            ServiceMsg.Text = $"{(result.ok ? "✓" : "✗")} {result.msg}";
            ServiceMsg.Foreground = result.ok ? GreenBrush : RedBrush;
            RefreshServices();
        }
        catch (Exception ex)
        {
            ServiceMsg.Text = $"✗ Unexpected error: {ex.Message}";
            ServiceMsg.Foreground = RedBrush;
        }
    }

    // ═══ DIAGNOSTICS ═══

    async void RunDiag_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            DiagList.Children.Clear();
            DiagList.Children.Add(new TextBlock { Text = "Running checks...", Foreground = GrayBrush, FontSize = 13 });

            List<(string name, bool ok, string detail)> checks = new();
            await Task.Run(() =>
            {
                try { checks = _svc.RunDiagnostics(); }
                catch (Exception ex) { checks.Add(("Error", false, ex.Message)); }
            });

            DiagList.Children.Clear();
            foreach (var (name, ok, detail) in checks)
            {
                var row = new Border
                {
                    Padding = new Thickness(12, 10),
                    Margin = new Thickness(0, 0, 0, 4),
                    CornerRadius = new CornerRadius(8),
                    Background = ok ? OkBg : ErrBg,
                    Child = new StackPanel
                    {
                        Orientation = Orientation.Horizontal,
                        Spacing = 12,
                        Children =
                        {
                            new TextBlock { Text = ok ? "✓" : "✗", FontSize = 16, FontWeight = FontWeight.Bold, Foreground = ok ? GreenBrush : RedBrush, VerticalAlignment = VerticalAlignment.Center },
                            new StackPanel
                            {
                                Children =
                                {
                                    new TextBlock { Text = name, FontSize = 13, FontWeight = FontWeight.SemiBold },
                                    new TextBlock { Text = detail, FontSize = 12, Foreground = GrayBrush }
                                }
                            }
                        }
                    }
                };
                DiagList.Children.Add(row);
            }
        }
        catch (Exception ex)
        {
            DiagList.Children.Clear();
            DiagList.Children.Add(new TextBlock { Text = $"✗ Diagnostics failed: {ex.Message}", Foreground = RedBrush, FontSize = 13 });
        }
    }

    async void TestDb_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            ConnResult.Text = "Testing database...";
            ConnResult.Foreground = GrayBrush;
            var (ok, msg) = (false, "");
            await Task.Run(() =>
            {
                try { (ok, msg) = _svc.TestDatabase(); }
                catch (Exception ex) { msg = $"Error: {ex.Message}"; }
            });
            ConnResult.Text = $"{(ok ? "✓" : "✗")} {msg}";
            ConnResult.Foreground = ok ? GreenBrush : RedBrush;
        }
        catch (Exception ex)
        {
            ConnResult.Text = $"✗ Error: {ex.Message}";
            ConnResult.Foreground = RedBrush;
        }
    }

    async void TestDevice_Click(object? sender, RoutedEventArgs e)
    {
        try
        {
            ConnResult.Text = "Testing device...";
            ConnResult.Foreground = GrayBrush;
            var (ok, msg) = (false, "");
            await Task.Run(() =>
            {
                try { (ok, msg) = _svc.TestDevice(); }
                catch (Exception ex) { msg = $"Error: {ex.Message}"; }
            });
            ConnResult.Text = $"{(ok ? "✓" : "✗")} {msg}";
            ConnResult.Foreground = ok ? GreenBrush : RedBrush;
        }
        catch (Exception ex)
        {
            ConnResult.Text = $"✗ Error: {ex.Message}";
            ConnResult.Foreground = RedBrush;
        }
    }

    // ═══ LOGS ═══

    void LogBridge_Click(object? sender, RoutedEventArgs e) => LoadLogs("bridge");
    void LogDash_Click(object? sender, RoutedEventArgs e) => LoadLogs("dashboard");
    void LogRefresh_Click(object? sender, RoutedEventArgs e) => LoadLogs(_currentLogService);

    async void LoadLogs(string service)
    {
        try
        {
            _currentLogService = service;
            LogBridgeBtn.Classes.Clear();
            LogBridgeBtn.Classes.Add(service == "bridge" ? "brand" : "outline");
            LogDashBtn.Classes.Clear();
            LogDashBtn.Classes.Add(service == "dashboard" ? "brand" : "outline");

            string[] lines = [];
            await Task.Run(() =>
            {
                try { lines = _svc.GetLogs(service); }
                catch (Exception ex) { lines = [$"Error reading logs: {ex.Message}"]; }
            });

            LogOutput.Text = lines.Length > 0
                ? string.Join("\n", lines)
                : "No log entries found.";
        }
        catch (Exception ex)
        {
            LogOutput.Text = $"Error loading logs: {ex.Message}";
        }
    }
}
