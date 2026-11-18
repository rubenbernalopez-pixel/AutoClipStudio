using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using AutoClipStudio.Core.Models;
using AutoClipStudio.WPF.Commands;
using AutoClipStudio.WPF.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.Logging;

namespace AutoClipStudio.WPF.ViewModels;

/// <summary>
/// Main window view model - URL input and processing pipeline.
/// </summary>
public partial class MainViewModel : ObservableObject
{
    private readonly IPythonBackendService _backend;
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialog;
    private readonly ILogger<MainViewModel> _logger;

    [ObservableProperty]
    private string _url = "";

    [ObservableProperty]
    private string _topic = "";

    [ObservableProperty]
    private bool _isProcessing = false;

    [ObservableProperty]
    private string _currentStage = "Listo";

    [ObservableProperty]
    private double _progressPercent = 0;

    [ObservableProperty]
    private string _progressMessage = "";

    [ObservableProperty]
    private int _currentItem = 0;

    [ObservableProperty]
    private int _totalItems = 0;

    [ObservableProperty]
    private bool _showAdvancedSettings = false;

    [ObservableProperty]
    private int _maxClips = 3;

    [ObservableProperty]
    private int _maxDuration = 75;

    [ObservableProperty]
    private string _selectedLayout = "solo_podcast";

    [ObservableProperty]
    private string _selectedBackground = "";

    [ObservableProperty]
    private string _modelSize = "large-v3";

    [ObservableProperty]
    private ObservableCollection<LayoutInfo> _availableLayouts = new();

    [ObservableProperty]
    private LayoutInfo? _selectedLayoutInfo;

    [ObservableProperty]
    private bool _hasError = false;

    [ObservableProperty]
    private string _errorMessage = "";

    public ICommand GenerateClipsCommand { get; }
    public ICommand ValidateUrlCommand { get; }
    public ICommand OpenSettingsCommand { get; }
    public ICommand ToggleAdvancedCommand { get; }
    public ICommand RetryCommand { get; }
    public ICommand CancelCommand { get; }

    public MainViewModel(
        IPythonBackendService backend,
        ISettingsService settings,
        IDialogService dialog,
        ILogger<MainViewModel> logger)
    {
        _backend = backend;
        _settings = settings;
        _dialog = dialog;
        _logger = logger;

        GenerateClipsCommand = new AsyncRelayCommand(GenerateClipsAsync, () => !IsProcessing && !string.IsNullOrWhiteSpace(Url));
        ValidateUrlCommand = new AsyncRelayCommand(ValidateUrlAsync, () => !IsProcessing && !string.IsNullOrWhiteSpace(Url));
        OpenSettingsCommand = new RelayCommand(OpenSettings);
        ToggleAdvancedCommand = new RelayCommand(() => ShowAdvancedSettings = !ShowAdvancedSettings);
        RetryCommand = new AsyncRelayCommand(RetryLastStepAsync, () => HasError && !IsProcessing);
        CancelCommand = new RelayCommand(CancelProcessing, () => IsProcessing);

        _backend.ProgressChanged += OnProgressChanged;
        _backend.ErrorOccurred += OnErrorOccurred;
        _backend.BackendStarted += OnBackendStarted;
        _backend.BackendStopped += OnBackendStopped;

        LoadSettings();
        LoadLayoutsAsync();
    }

    private void LoadSettings()
    {
        MaxClips = _settings.Settings.DefaultMaxClips;
        MaxDuration = _settings.Settings.DefaultMaxDuration;
        SelectedLayout = _settings.Settings.DefaultLayout;
        ModelSize = _settings.Settings.DefaultModelSize;
    }

    private async void LoadLayoutsAsync()
    {
        try
        {
            var layouts = await _backend.GetAvailableLayoutsAsync();
            AvailableLayouts.Clear();
            foreach (var layout in layouts)
            {
                AvailableLayouts.Add(layout);
            }
            SelectedLayoutInfo = AvailableLayouts.FirstOrDefault(l => l.Type == SelectedLayout)
                ?? AvailableLayouts.FirstOrDefault();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load layouts");
        }
    }

    private async Task ValidateUrlAsync()
    {
        if (string.IsNullOrWhiteSpace(Url)) return;

        IsProcessing = true;
        CurrentStage = "Validando URL";
        ProgressPercent = 10;
        HasError = false;

        try
        {
            var result = await _backend.ValidateUrlAsync(Url);
            if (result.Valid)
            {
                ProgressMessage = $"✓ {result.Title} ({TimeSpan.FromSeconds(result.Duration):mm\\:ss})";
                ProgressPercent = 100;
            }
            else
            {
                HasError = true;
                ErrorMessage = result.Error ?? "URL no válida";
                ProgressMessage = "✗ URL no válida";
            }
        }
        catch (Exception ex)
        {
            HasError = true;
            ErrorMessage = ex.Message;
            _logger.LogError(ex, "URL validation failed");
        }
        finally
        {
            IsProcessing = false;
        }
    }

    private async Task GenerateClipsAsync()
    {
        if (string.IsNullOrWhiteSpace(Url)) return;

        IsProcessing = true;
        HasError = false;
        ProgressPercent = 0;

        try
        {
            // Step 1: Download
            CurrentStage = "Descargando";
            ProgressMessage = "Descargando vídeo y extrayendo audio...";
            var downloadResult = await _backend.DownloadVideoAsync(Url, _settings.Settings.TempDirectory, Topic);

            if (!downloadResult.Success || string.IsNullOrEmpty(downloadResult.VideoPath))
            {
                throw new Exception(downloadResult.Error ?? "Error en la descarga");
            }

            // Step 2: Transcribe
            CurrentStage = "Transcribiendo";
            ProgressMessage = "Transcribiendo audio con Whisper...";
            var transcription = await _backend.TranscribeAsync(
                downloadResult.AudioPath ?? "",
                _settings.Settings.DefaultLanguage,
                ModelSize);

            if (!transcription.Success || transcription.Segments == null || transcription.Segments.Count == 0)
            {
                throw new Exception(transcription.Error ?? "Error en la transcripción");
            }

            // Step 3: Select clips
            CurrentStage = "Seleccionando clips";
            ProgressMessage = "Analizando conversación y seleccionando mejores momentos...";
            var clips = await _backend.SelectClipsAsync(
                transcription,
                downloadResult.Duration,
                Topic,
                MaxClips,
                MaxDuration);

            if (clips.Count == 0)
            {
                throw new Exception("No se encontraron clips aprovechables en este episodio");
            }

            // Step 4: Render clips
            CurrentStage = "Renderizando";
            ProgressMessage = $"Generando {clips.Count} clip(s) con layout {SelectedLayout}...";
            var renderedClips = await _backend.RenderClipsAsync(
                clips,
                downloadResult.VideoPath,
                SelectedLayout,
                string.IsNullOrEmpty(SelectedBackground) ? null : SelectedBackground,
                _settings.Settings.OutputDirectory);

            // Step 5: Generate subtitles for each clip
            CurrentStage = "Generando subtítulos";
            for (int i = 0; i < renderedClips.Count; i++)
            {
                ProgressMessage = $"Subtítulos clip {i + 1}/{renderedClips.Count}...";
                var subtitleResult = await _backend.GenerateSubtitlesAsync(
                    renderedClips[i],
                    transcription.Words ?? new List<TranscriptionWord>());

                if (subtitleResult.Success)
                {
                    renderedClips[i].SubtitlePath = subtitleResult.SubtitlePath;
                }
            }

            // Success - open results window
            var resultsWindow = App.Current.Services.GetRequiredService<ResultsWindow>();
            var resultsVm = App.Current.Services.GetRequiredService<ResultsViewModel>();
            resultsVm.LoadClips(renderedClips, downloadResult.VideoPath, transcription);
            resultsWindow.DataContext = resultsVm;
            resultsWindow.Show();

            // Reset
            CurrentStage = "Completado";
            ProgressMessage = $"{renderedClips.Count} clip(s) generado(s)";
            ProgressPercent = 100;
        }
        catch (Exception ex)
        {
            HasError = true;
            ErrorMessage = ex.Message;
            _logger.LogError(ex, "Clip generation failed");
            CurrentStage = "Error";
            ProgressMessage = $"Error: {ex.Message}";
        }
        finally
        {
            IsProcessing = false;
        }
    }

    private void OnProgressChanged(object? sender, ProgressNotification e)
    {
        Application.Current.Dispatcher.Invoke(() =>
        {
            CurrentStage = e.Stage;
            ProgressPercent = e.Percent;
            ProgressMessage = e.Message;
            CurrentItem = e.CurrentItem;
            TotalItems = e.TotalItems;
        });
    }

    private void OnErrorOccurred(object? sender, string error)
    {
        Application.Current.Dispatcher.Invoke(() =>
        {
            HasError = true;
            ErrorMessage = error;
        });
    }

    private void OnBackendStarted(object? sender, EventArgs e)
    {
        Application.Current.Dispatcher.Invoke(() =>
        {
            CurrentStage = "Backend listo";
            ProgressMessage = "Sistema listo para procesar";
        });
    }

    private void OnBackendStopped(object? sender, EventArgs e)
    {
        Application.Current.Dispatcher.Invoke(() =>
        {
            CurrentStage = "Backend detenido";
            ProgressMessage = "El motor de procesamiento se ha detenido";
        });
    }

    private async Task RetryLastStepAsync()
    {
        HasError = false;
        await GenerateClipsAsync();
    }

    private void CancelProcessing()
    {
        // In a real implementation, send cancel to backend
        IsProcessing = false;
        CurrentStage = "Cancelado";
        ProgressMessage = "Proceso cancelado por el usuario";
    }

    private void OpenSettings()
    {
        var settingsWindow = App.Current.Services.GetRequiredService<SettingsWindow>();
        settingsWindow.ShowDialog();
    }

    partial void OnUrlChanged(string value)
    {
        HasError = false;
        GenerateClipsCommand.NotifyCanExecuteChanged();
        ValidateUrlCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsProcessingChanged(bool value)
    {
        GenerateClipsCommand.NotifyCanExecuteChanged();
        ValidateUrlCommand.NotifyCanExecuteChanged();
        CancelCommand.NotifyCanExecuteChanged();
    }
}