using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
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
/// View model for the subtitle editor window.
/// </summary>
public partial class SubtitleEditorViewModel : ObservableObject
{
    private readonly IPythonBackendService _backend;
    private readonly ISettingsService _settings;
    private readonly IDialogService _dialog;
    private readonly ILogger<SubtitleEditorViewModel> _logger;

    public Clip Clip { get; }

    [ObservableProperty]
    private ObservableCollection<SubtitleLineViewModel> _subtitleLines = new();

    [ObservableProperty]
    private string _videoPath = "";

    [ObservableProperty]
    private double _videoDuration = 0;

    [ObservableProperty]
    private double _videoPosition = 0;

    [ObservableProperty]
    private bool _isPlaying = false;

    [ObservableProperty]
    private SubtitleWordViewModel? _selectedWord;

    public ICommand PlayVideoCommand { get; }
    public ICommand VideoSeekBackCommand { get; }
    public ICommand VideoPlayPauseCommand { get; }
    public ICommand VideoSeekForwardCommand { get; }
    public ICommand PlayFromSelectionCommand { get; }
    public ICommand UndoCommand { get; }
    public ICommand ApplyCorrectionsCommand { get; }
    public ICommand ExportSrtCommand { get; }
    public ICommand SaveAndCloseCommand { get; }

    public SubtitleEditorViewModel(
        Clip clip,
        IPythonBackendService backend,
        ISettingsService settings,
        IDialogService dialog,
        ILogger<SubtitleEditorViewModel> logger)
    {
        Clip = clip;
        _backend = backend;
        _settings = settings;
        _dialog = dialog;
        _logger = logger;

        VideoPath = clip.VideoPath ?? "";
        VideoDuration = clip.Duration;

        PlayVideoCommand = new RelayCommand(PlayVideo);
        VideoSeekBackCommand = new RelayCommand(SeekBack);
        VideoPlayPauseCommand = new RelayCommand(TogglePlayPause);
        VideoSeekForwardCommand = new RelayCommand(SeekForward);
        PlayFromSelectionCommand = new AsyncRelayCommand(PlayFromSelectionAsync);
        UndoCommand = new RelayCommand(Undo);
        ApplyCorrectionsCommand = new AsyncRelayCommand(ApplyCorrectionsAsync);
        ExportSrtCommand = new AsyncRelayCommand(ExportSrtAsync);
        SaveAndCloseCommand = new AsyncRelayCommand(SaveAndCloseAsync);

        LoadSubtitles();
    }

    private void LoadSubtitles()
    {
        SubtitleLines.Clear();

        if (Clip.TranscriptionWords == null || Clip.TranscriptionWords.Count == 0) return;

        // Filter words to clip range
        var clipWords = Clip.TranscriptionWords
            .Where(w => w.Start >= Clip.Start && w.Start < Clip.End)
            .OrderBy(w => w.Start)
            .ToList();

        // Group into lines (same adaptive logic as backend)
        var lines = new List<List<TranscriptionWord>>();
        var currentLine = new List<TranscriptionWord>();
        double lineStart = 0;
        const double MAX_CPS = 19;
        const double MIN_LINE_DURATION = 0.8;
        const double MAX_LINE_DURATION = 7.0;
        const int MAX_WORDS_PER_LINE = 10;
        const int MAX_CHARS_PER_LINE = 42;

        foreach (var word in clipWords)
        {
            if (currentLine.Count == 0)
            {
                lineStart = word.Start;
                currentLine.Add(word);
                continue;
            }

            var currentText = string.Join(" ", currentLine.Select(w => w.Word));
            var currentChars = currentText.Length;
            var currentDuration = word.Start - lineStart;
            var projectedDuration = word.End - lineStart;
            var projectedCps = (currentChars + word.Word.Length + 1) / Math.Max(projectedDuration, 0.001);
            var gap = word.Start - currentLine.Last().End;

            var shouldBreak = currentLine.Count >= MAX_WORDS_PER_LINE ||
                             currentChars + word.Word.Length + 1 > MAX_CHARS_PER_LINE ||
                             projectedCps > MAX_CPS ||
                             (currentLine.Count >= 4 && gap > 0.4) ||
                             (gap > 0.8);

            if (shouldBreak && currentDuration < MIN_LINE_DURATION && currentLine.Count > 1)
                shouldBreak = false;

            if (!shouldBreak && projectedDuration > MAX_LINE_DURATION)
                shouldBreak = true;

            if (shouldBreak)
            {
                var lineEnd = currentLine.Last().end + 0.15;
                lines.Add(currentLine);
                currentLine = new List<TranscriptionWord> { word };
                lineStart = word.Start;
            }
            else
            {
                currentLine.Add(word);
            }
        }

        if (currentLine.Count > 0)
            lines.Add(currentLine);

        // Limit lines
        if (lines.Count > _settings.Settings.MaxLines)
        {
            var excess = lines.Skip(_settings.Settings.MaxLines - 1).ToList();
            lines = lines.Take(_settings.Settings.MaxLines - 1).ToList();
            if (excess.Any())
            {
                lines.Last().AddRange(excess.SelectMany(l => l));
            }
        }

        // Create view models
        for (int i = 0; i < lines.Count; i++)
        {
            var lineVm = new SubtitleLineViewModel
            {
                Index = i,
                Start = lines[i].First().Start,
                End = lines[i].Last().End + 0.15,
                Text = string.Join(" ", lines[i].Select(w => w.Word)),
                Words = new ObservableCollection<SubtitleWordViewModel>()
            };

            for (int j = 0; j < lines[i].Count; j++)
            {
                var word = lines[i][j];
                lineVm.Words.Add(new SubtitleWordViewModel
                {
                    WordText = word.Word,
                    OriginalWord = word.IsCorrected ? word.CorrectedText ?? word.Word : null,
                    Start = word.Start,
                    End = word.End,
                    Confidence = word.Confidence,
                    IsCorrected = word.IsCorrected,
                    State = word.IsCorrected ? SubtitleWordState.Corrected :
                           word.Confidence < 0.65 ? SubtitleWordState.LowConfidence :
                           SubtitleWordState.Pending,
                    Index = Clip.TranscriptionWords.IndexOf(word),
                    LineIndex = i
                });
            }

            SubtitleLines.Add(lineVm);
        }
    }

    private void PlayVideo()
    {
        if (string.IsNullOrEmpty(VideoPath) || !File.Exists(VideoPath)) return;
        try { Process.Start(new ProcessStartInfo(VideoPath) { UseShellExecute = true }); }
        catch (Exception ex) { _logger.LogError(ex, "Failed to play video"); }
    }

    private void SeekBack() => VideoPosition = Math.Max(0, VideoPosition - 5);
    private void SeekForward() => VideoPosition = Math.Min(VideoDuration, VideoPosition + 5);

    private void TogglePlayPause()
    {
        IsPlaying = !IsPlaying;
    }

    private async Task PlayFromSelectionAsync()
    {
        if (SelectedWord == null) return;
        VideoPosition = Math.Max(0, SelectedWord.Start - 0.5);
        IsPlaying = true;
        await Task.Delay(100);
    }

    private void Undo()
    {
        foreach (var line in SubtitleLines.Reverse())
        {
            var corrected = line.Words.LastOrDefault(w => w.State == SubtitleWordState.Corrected);
            if (corrected != null)
            {
                corrected.State = corrected.Confidence < 0.65 ? SubtitleWordState.LowConfidence : SubtitleWordState.Pending;
                corrected.WordText = corrected.OriginalWord ?? corrected.WordText;
                corrected.IsCorrected = false;
                SelectedWord = corrected;
                return;
            }
        }
    }

    private async Task ApplyCorrectionsAsync()
    {
        var corrections = new List<(int index, string text, double offset)>();

        foreach (var line in SubtitleLines)
        {
            foreach (var word in line.Words)
            {
                if (word.State == SubtitleWordState.Corrected || word.IsCorrected)
                {
                    corrections.Add((word.Index, word.WordText, 0.0));
                }
            }
        }

        if (corrections.Count == 0)
        {
            await _dialog.ShowMessageAsync("No hay correcciones para aplicar", "Información", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        foreach (var (index, text, offset) in corrections)
        {
            await _backend.CorrectSubtitleAsync(Clip.Id, index, text, offset);
        }

        await _dialog.ShowMessageAsync($"{corrections.Count} corrección(es) aplicada(s). Los subtítulos se regenerarán al exportar.", "Éxito", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private async Task ExportSrtAsync()
    {
        var defaultName = $"{Clip.Id}_subtitles.srt";
        var path = await _dialog.SaveFileDialogAsync(
            "Exportar subtítulos",
            "SubRip (*.srt)|*.srt|Advanced SubStation Alpha (*.ass)|*.ass",
            defaultName,
            _settings.Settings.OutputDirectory);

        if (string.IsNullOrEmpty(path)) return;

        try
        {
            var srtContent = GenerateSrtContent();
            await File.WriteAllTextAsync(path, srtContent);
            await _dialog.ShowMessageAsync($"Subtítulos exportados a:\n{path}", "Exportación completada", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to export subtitles");
            await _dialog.ShowMessageAsync(ex.Message, "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private string GenerateSrtContent()
    {
        var lines = new List<string>();
        int index = 1;

        foreach (var lineVm in SubtitleLines)
        {
            lines.Add(index.ToString());
            lines.Add($"{FormatSrtTime(lineVm.Start)} --> {FormatSrtTime(lineVm.End)}");
            lines.Add(lineVm.Text);
            lines.Add("");
            index++;
        }

        return string.Join(Environment.NewLine, lines);
    }

    private string FormatSrtTime(double seconds)
    {
        var ts = TimeSpan.FromSeconds(seconds);
        return $"{ts.Hours:00}:{ts.Minutes:00}:{ts.Seconds:00},{ts.Milliseconds:000}";
    }

    private async Task SaveAndCloseAsync()
    {
        var hasCorrections = SubtitleLines.Any(l => l.Words.Any(w => w.State == SubtitleWordState.Corrected));
        if (hasCorrections)
        {
            await ApplyCorrectionsAsync();
        }
        Application.Current.Windows.OfType<Views.SubtitleEditorWindow>().FirstOrDefault()?.Close();
    }
}

/// <summary>
/// View model for a subtitle line in the editor.
/// </summary>
public partial class SubtitleLineViewModel : ObservableObject
{
    public int Index { get; set; }
    public double Start { get; set; }
    public double End { get; set; }
    public string Text { get; set; } = "";
    public ObservableCollection<SubtitleWordViewModel> Words { get; set; } = new();

    public string TimecodeRange => $"{FormatTime(Start)} - {FormatTime(End)}";

    private static string FormatTime(double seconds)
    {
        var ts = TimeSpan.FromSeconds(seconds);
        return ts.Hours > 0 ? $"{ts.Hours:00}:{ts.Minutes:00}:{ts.Seconds:00}" : $"{ts.Minutes:00}:{ts.Seconds:00}";
    }
}

/// <summary>
/// View model for a subtitle word in the editor.
/// </summary>
public partial class SubtitleWordViewModel : ObservableObject
{
    [ObservableProperty]
    private string _wordText = "";

    [ObservableProperty]
    private string? _originalWord;

    [ObservableProperty]
    private double _start;

    [ObservableProperty]
    private double _end;

    [ObservableProperty]
    private double _confidence = 1.0;

    [ObservableProperty]
    private bool _isCorrected = false;

    [ObservableProperty]
    private SubtitleWordState _state = SubtitleWordState.Pending;

    public int Index { get; set; }
    public int LineIndex { get; set; }

    public string TimecodeRange => $"{FormatTime(Start)} - {FormatTime(End)}";

    // Computed UI properties
    public Brush StateForeground => State switch
    {
        SubtitleWordState.Pending => Brushes.White,
        SubtitleWordState.Active => (Brush)Application.Current.Resources["SubtitleActiveBrush"],
        SubtitleWordState.Done => (Brush)Application.Current.Resources["SubtitleDoneBrush"],
        SubtitleWordState.Corrected => (Brush)Application.Current.Resources["SubtitleCorrectedBrush"],
        SubtitleWordState.LowConfidence => (Brush)Application.Current.Resources["SubtitleLowConfBrush"],
        _ => Brushes.White
    };

    public Brush StateBackground => State switch
    {
        SubtitleWordState.Active => new SolidColorBrush(Color.FromArgb(0x30, 0xFF, 0xD7, 0x00)),
        SubtitleWordState.Corrected => new SolidColorBrush(Color.FromArgb(0x30, 0xE9, 0x45, 0x60)),
        SubtitleWordState.LowConfidence => new SolidColorBrush(Color.FromArgb(0x30, 0x00, 0xFF, 0xFF)),
        _ => Brushes.Transparent
    };

    public Brush StateBorder => State switch
    {
        SubtitleWordState.Active => (Brush)Application.Current.Resources["SubtitleActiveBrush"],
        SubtitleWordState.Corrected => (Brush)Application.Current.Resources["SubtitleCorrectedBrush"],
        SubtitleWordState.LowConfidence => (Brush)Application.Current.Resources["SubtitleLowConfBrush"],
        _ => Brushes.Transparent
    };

    public Thickness StateBorderThickness => State switch
    {
        SubtitleWordState.Corrected => new Thickness(2),
        SubtitleWordState.LowConfidence => new Thickness(2),
        SubtitleWordState.Active => new Thickness(1),
        _ => new Thickness(0)
    };

    private static string FormatTime(double seconds)
    {
        var ts = TimeSpan.FromSeconds(seconds);
        return ts.Hours > 0 ? $"{ts.Hours:00}:{ts.Minutes:00}:{ts.Seconds:00}" : $"{ts.Minutes:00}:{ts.Seconds:00}";
    }

    partial void OnStateChanged(SubtitleWordState value)
    {
        IsCorrected = value == SubtitleWordState.Corrected;
        OnPropertyChanged(nameof(StateForeground));
        OnPropertyChanged(nameof(StateBackground));
        OnPropertyChanged(nameof(StateBorder));
        OnPropertyChanged(nameof(StateBorderThickness));
    }
}

public enum SubtitleWordState
{
    Pending,
    Active,
    Done,
    Corrected,
    LowConfidence
}