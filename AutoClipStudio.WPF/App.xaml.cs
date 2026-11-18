using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using AutoClipStudio.WPF.Services;
using AutoClipStudio.WPF.ViewModels;
using AutoClipStudio.WPF.Views;

namespace AutoClipStudio.WPF;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    private IHost? _host;

    protected override async void OnStartup(StartupEventArgs e)
    {
        _host = Host.CreateDefaultBuilder()
            .ConfigureServices((context, services) =>
            {
                // Services
                services.AddSingleton<IPythonBackendService, PythonBackendService>();
                services.AddSingleton<ISettingsService, SettingsService>();
                services.AddSingleton<IDialogService, DialogService>();

                // ViewModels
                services.AddTransient<MainViewModel>();
                services.AddTransient<ResultsViewModel>();
                services.AddTransient<SettingsViewModel>();

                // Views
                services.AddTransient<MainWindow>();
                services.AddTransient<ResultsWindow>();
                services.AddTransient<SettingsWindow>();
            })
            .Build();

        await _host.StartAsync();

        var mainWindow = _host.Services.GetRequiredService<MainWindow>();
        mainWindow.Show();

        base.OnStartup(e);
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        if (_host != null)
        {
            await _host.StopAsync();
            _host.Dispose();
        }
        base.OnExit(e);
    }
}