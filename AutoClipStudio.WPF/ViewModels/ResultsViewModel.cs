using System;
using System.Collections.ObjectModel;
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
/// Results window view model - clip cards with preview, review, export.
/// </summary>
public partial class ResultsViewModel : ObservableObject
{
    private readonly IPythonBackendService _backend;
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialog;
    private readonly ILogger<ResultsViewModel> _logger;

    [ObservableProperty]
    private ObservableCollection<ClipViewModel> _clips = new();

    [ObservableProperty]
    private ClipViewModel? _selectedClip;

    [ObservableProperty]
    private string _sourceVideoPath = "";

    [ObservableProperty]
    private bool _isProcessing = false;

    [ObservableProperty]
    private string _currentStage = "";

    [ObservableProperty]
    private double _progressPercent = 0;

    [ObservableProperty]
    private string _progressMessage = "";

    public ICommand PlayClipCommand { get; }
    public ICommand CopySocialCopyCommand { get; }
    public ICommand ReviewSubtitlesCommand { get; }
    public ICommand ExportClipCommand { get; }
    public ICommand OpenOutputFolderCommand { get; }
    public ICommand NewProjectCommand { get; }

    public ResultsViewModel(
        IPythonBackendService backend,
        ISettingsService settings,
        IDialogService dialog,
        ILogger<ResultsViewModel> logger)
    {
        _backend = backend;
        _settings = settings;
        _dialog = dialog;
        _logger = logger;

        PlayClipCommand = new RelayCommand<ClipViewModel>(PlayClip);
        CopySocialCopyCommand = new AsyncRelayCommand<ClipViewModel>(CopySocialCopyAsync);
        ReviewSubtitlesCommand = new AsyncRelayCommand<ClipViewModel>(ReviewSubtitlesAsync);
        ExportClipCommand = new AsyncRelayCommand<ClipViewModel>(ExportClipAsync);
        OpenOutputFolderCommand = new RelayCommand(OpenOutputFolder);
        NewProjectCommand = new RelayCommand(NewProject);
    }

    public void LoadClips(List<Clip> clips, string sourceVideoPath, TranscriptionResult transcription)
    {
        SourceVideoPath = sourceVideoPath;
        Clips.Clear();

        foreach (var clip in clips)
        {
            var clipVm = new ClipViewModel(clip, _backend, _settings, _dialog, _logger);
            Clips.Add(clipVm);
        }

        SelectedClip = Clips.FirstOrDefault();
    }

    private void PlayClip(ClipViewModel? clipVm)
    {
        if (clipVm == null) return;
        clipVm.TogglePlay();
    }

    private async Task CopySocialCopyAsync(ClipViewModel? clipVm)
    {
        if (clipVm == null) return;

        try
        {
            Clipboard.SetText(clipVm.SocialCopy);
            await _dialog.ShowMessageAsync("Publicación copiada al portapapeles", "Copiado", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to copy to clipboard");
        }
    }

    private async Task ReviewSubtitlesAsync(ClipViewModel? clipVm)
    {
        if (clipVm == null) return;
        await clipVm.OpenSubtitleEditorAsync();
    }

    private async Task ExportClipAsync(ClipViewModel? clipVm)
    {
        if (clipVm == null) return;

        var defaultName = $"{clipVm.Id}_{DateTime.Now:yyyyMMdd_HHmmss}.mp4";
        var path = await _dialog.SaveFileDialogAsync(
            "Exportar clip",
            "Vídeo MP4 (*.mp4)|*.mp4",
            defaultName,
            _settings.Settings.OutputDirectory);

        if (string.IsNullOrEmpty(path)) return;

        IsProcessing = true;
        CurrentStage = "Exportando";
        ProgressMessage = "Exportando clip final con subtítulos...";

        try
        {
            var result = await _backend.ExportClipAsync(clipVm.Clip, path, clipVm.Clip.SubtitlePath);
            if (result.Success)
            {
                await _dialog.ShowMessageAsync($"Clip exportado a:\n{path}", "Exportación completada", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            else
            {
                await _dialog.ShowMessageAsync(result.Error ?? "Error desconocido", "Error en exportación", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Export failed");
            await _dialog.ShowMessageAsync(ex.Message, "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            IsProcessing = false;
        }
    }

    private void OpenOutputFolder()
    {
        try
        {
            var dir = _settings.Settings.OutputDirectory;
            if (Directory.Exists(dir))
            {
                Process.Start(new ProcessStartInfo(dir) { UseShellExecute = true });
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to open output folder");
        }
    }

    private void NewProject()
    {
        var mainWindow = App.Current.Windows.OfType<MainWindow>().FirstOrDefault();
        if (mainWindow != null)
        {
            mainWindow.Activate();
            mainWindow.Focus();
        }

        // Close results window
        Application.Current.Windows.OfType<ResultsWindow>().FirstOrDefault()?.Close();
    }
}

/// <summary>
/// View model for individual clip card.
/// </summary>
public partial class ClipViewModel : ObservableObject
{
    private readonly IPythonBackendService _backend;
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialog;
    private readonly ILogger<ResultsViewModel> _logger;

    public Clip Clip { get; }

    [ObservableProperty]
    private bool _isPlaying = false;

    [ObservableProperty]
    private string? _previewImage;

    [ObservableProperty]
    private bool _showPlayButton = true;

    public ClipViewModel(Clip clip, IPythonBackendService backend, ISettingsService settings, IDialogService dialog, ILogger<ResultsViewModel> logger)
    {
        Clip = clip;
        _backend = backend;
        _settings = settings;
        _dialog = dialog;
        _logger = logger;

        // Generate preview image path
        PreviewImage = GeneratePreviewPath();
        HasPreview = File.Exists(PreviewImage);
        HasVideo = File.Exists(Clip.VideoPath);
        ShowPlayButton = HasVideo;
    }

    public string Id => Clip.Id;
    public string Hook => Clip.Hook;
    public string Development => Clip.Development;
    public string Closing => Clip.Closing;
    public double Score => Clip.Score;
    public Dictionary<string, double> ScoreBreakdown => Clip.ScoreBreakdown;
    public string ScoreExplanation => Clip.ScoreExplanation;
    public string SocialCopy => Clip.SocialCopy;
    public List<string> Hashtags => Clip.Hashtags;
    public string Layout => Clip.Layout;
    public string? BackgroundAsset => Clip.BackgroundAsset;
    public string? SubtitlePath => Clip.SubtitlePath;
    public string? VideoPath => Clip.VideoPath;
    public string DurationText => FormatDuration(Clip.Duration);
    public string TimecodeRange => $"{Clip.StartTimecode} - {Clip.EndTimecode}";
    public string LayoutDisplayName => GetLayoutDisplayName(Clip.Layout);
    public string ScorePercent => $"{(int)(Clip.Score * 100)}%";
    public Brush ScoreColor => GetScoreColor(Clip.Score);

    public bool HasPreview { get; }
    public bool HasVideo { get; }

    public ICommand PlayCommand => new RelayCommand(TogglePlay);
    public ICommand CopySocialCopyCommand => new AsyncRelayCommand(CopySocialCopyAsync);
    public ICommand ReviewSubtitlesCommand => new AsyncRelayCommand(OpenSubtitleEditorAsync);
    public ICommand ExportCommand => new AsyncRelayCommand(ExportAsync);
    public ICommand ShowScoreDetailsCommand => new RelayCommand(ShowScoreDetails);

    private string GeneratePreviewPath()
    {
        var dir = Path.GetDirectoryName(Clip.VideoPath ?? "") ?? _settings.Settings.TempDirectory;
        return Path.Combine(dir, $"{Clip.Id}_thumb.jpg");
    }

    private string FormatDuration(double seconds)
    {
        var ts = TimeSpan.FromSeconds(seconds);
        return ts.Minutes > 0 ? $"{ts.Minutes}:{ts.Seconds:00}" : $"{ts.Seconds}s";
    }

    private string GetLayoutDisplayName(string layout)
    {
        return layout switch
        {
            "solo_podcast" => "Solo pódcast",
            "balls_hoops" => "Pelotas y aros",
            "block_parkour" => "Parkour de bloques",
            "my_gameplay" => "Mi gameplay",
            _ => layout
        };
    }

    private Brush GetScoreColor(double score)
    {
        return score switch
        {
            >= 0.8 => Brushes.LimeGreen,
            >= 0.6 => Brushes.Gold,
            >= 0.4 => Brushes.DodgerBlue,
            _ => Brushes.IndianRed
        };
    }

    private void TogglePlay()
    {
        if (string.IsNullOrEmpty(Clip.VideoPath) || !File.Exists(Clip.VideoPath)) return;

        try
        {
            if (IsPlaying)
            {
                // Stop - in real app, control MediaElement
                IsPlaying = false;
                ShowPlayButton = true;
            }
            else
            {
                // Play - open in default player or embedded
                Process.Start(new ProcessStartInfo(Clip.VideoPath) { UseShellExecute = true });
                IsPlaying = true;
                ShowPlayButton = false;
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to play video");
        }
    }

    private async Task CopySocialCopyAsync()
    {
        try
        {
            Clipboard.SetText(SocialCopy);
            await _dialog.ShowMessageAsync("Publicación copiada al portapapeles", "Copiado", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to copy");
        }
    }

    private async Task OpenSubtitleEditorAsync()
    {
        // Open subtitle editor window
        var editorWindow = new SubtitleEditorWindow(Clip, _backend, _settings, _dialog, _logger);
        editorWindow.ShowDialog();
    }

    private async Task ExportAsync()
    {
        var defaultName = $"{Clip.Id}_{DateTime.Now:yyyyMMdd_HHmmss}.mp4";
        var path = await _dialog.SaveFileDialogAsync(
            "Exportar clip",
            "Vídeo MP4 (*.mp4)|*.mp4",
            defaultName,
            _settings.Settings.OutputDirectory);

        if (string.IsNullOrEmpty(path)) return;

        try
        {
            var result = await _backend.ExportClipAsync(Clip, path, Clip.SubtitlePath);
            if (result.Success)
            {
                await _dialog.ShowMessageAsync($"Clip exportado a:\n{path}", "Exportación completada", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            else
            {
                await _dialog.ShowMessageAsync(result.Error ?? "Error desconocido", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Export failed");
            await _dialog.ShowMessageAsync(ex.Message, "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void ShowScoreDetails()
    {
        var details = "Desglose de puntuación:\n\n";
        foreach (var kvp in ScoreBreakdown)
        {
            details += $"• {kvp.Key}: {(int)(kvp.Value * 100)}%\n";
        }
        details += $"\n{ScoreExplanation}";

        MessageBox.Show(details, $"Puntuación: {ScorePercent}", MessageBoxButton.OK, MessageBoxImage.Information);
    }
}