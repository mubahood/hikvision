using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;

namespace EHRMSBridgeApp;

public class App : Application
{
    public override void Initialize()
    {
        try
        {
            AvaloniaXamlLoader.Load(this);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"XAML load error: {ex.Message}");
            throw;
        }
    }

    public override void OnFrameworkInitializationCompleted()
    {
        try
        {
            if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
                desktop.MainWindow = new MainWindow();
            base.OnFrameworkInitializationCompleted();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Framework init error: {ex.Message}");
            throw;
        }
    }
}
