using Avalonia;

namespace EHRMSBridgeApp;

class Program
{
    [STAThread]
    public static void Main(string[] args)
    {
        try
        {
            // Catch unhandled exceptions from background threads
            AppDomain.CurrentDomain.UnhandledException += (_, e) =>
            {
                var ex = e.ExceptionObject as Exception;
                LogFatalError($"Unhandled exception: {ex?.Message}\n{ex?.StackTrace}");
            };

            // Catch unobserved task exceptions
            TaskScheduler.UnobservedTaskException += (_, e) =>
            {
                e.SetObserved();
                LogFatalError($"Unobserved task exception: {e.Exception?.Message}");
            };

            BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
        }
        catch (Exception ex)
        {
            LogFatalError($"Fatal startup error: {ex.Message}\n{ex.StackTrace}");
        }
    }

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .LogToTrace();

    static void LogFatalError(string message)
    {
        try
        {
            var logPath = Path.Combine(AppContext.BaseDirectory, "crash.log");
            File.AppendAllText(logPath, $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}\n\n");
        }
        catch { }
    }
}
