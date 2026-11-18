using System;
using System.ComponentModel;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Input;
using AutoClipStudio.WPF.Commands;
using AutoClipStudio.WPF.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.Logging;

namespace AutoClipStudio.WPF.ViewModels;

/// <summary>
/// Settings window view model.
/// </summary>
public partial class SettingsViewModel : ObservableObject
{
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialog;
    private readonly ILogger<SettingsViewModel> _logger;

    [ObservableProperty]
    private AppSettings _settingsModel;

    [ObservableProperty]
    private bool _isSaving = false;

    [ObservableProperty]
    private string _statusMessage = "";

    public ICommand SaveCommand { get; }
    public ICommand ResetCommand { get; }
    public ICommand BrowseOutputFolderCommand { get; }
    public ICommand BrowseTempFolderCommand { get; }
    public ICommand OpenOutputFolderCommand { get; }
    public ICommand CheckUpdatesCommand { get; }

    public SettingsViewModel(
        ISettingsService settings,
        IDialogService dialog,
        ILogger<SettingsViewModel> logger)
    {
        _settings = settings;
        _dialog = dialog;
        _logger = logger;

        SettingsModel = settings.Settings;

        SaveCommand = new AsyncRelayCommand(SaveAsync);
        ResetCommand = new RelayCommand(Reset);
        BrowseOutputFolderCommand = new AsyncRelayCommand(BrowseOutputFolderAsync);
        BrowseTempFolderCommand = new AsyncRelayCommand(BrowseTempFolderAsync);
        OpenOutputFolderCommand = new RelayCommand(OpenOutputFolder);
        CheckUpdatesCommand = new AsyncRelayCommand(CheckUpdatesAsync);
    }

    private async Task SaveAsync()
    {
        IsSaving = true;
        StatusMessage = "Guardando...";

        try
        {
            await _settings.SaveAsync();
            StatusMessage = "Configuración guardada correctamente";
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to save settings");
            StatusMessage = $"Error: {ex.Message}";
        }
        finally
        {
            IsSaving = false;
        }
    }

    private void Reset()
    {
        _settings.ResetToDefaults();
        SettingsModel = _settings.Settings;
        OnPropertyChanged(nameof(SettingsModel));
        StatusMessage = "Valores por defecto restaurados";
    }

    private async Task BrowseOutputFolderAsync()
    {
        var folder = await _dialog.OpenFolderDialogAsync(
            "Seleccionar carpeta de salida",
            SettingsModel.OutputDirectory);

        if (!string.IsNullOrEmpty(folder))
        {
            SettingsModel.OutputDirectory = folder;
            OnPropertyChanged(nameof(SettingsModel));
        }
    }

    private async Task BrowseTempFolderAsync()
    {
        var folder = await _dialog.OpenFolderDialogAsync(
            "Seleccionar carpeta temporal",
            SettingsModel.TempDirectory);

        if (!string.IsNullOrEmpty(folder))
        {
            SettingsModel.TempDirectory = folder;
            OnPropertyChanged(nameof(SettingsModel));
        }
    }

    private void OpenOutputFolder()
    {
        try
        {
            var dir = SettingsModel.OutputDirectory;
            if (Directory.Exists(dir))
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(dir) { UseShellExecute = true });
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to open output folder");
        }
    }

    private async Task CheckUpdatesAsync()
    {
        StatusMessage = "Comprobando actualizaciones...";
        await Task.Delay(1000); // Simulate check
        StatusMessage = "Estás usando la versión más reciente";
    }
}