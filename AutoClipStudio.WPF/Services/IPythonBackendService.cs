using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AutoClipStudio.Core.Models;

namespace AutoClipStudio.WPF.Services;

/// <summary>
/// Interface for communicating with Python backend via JSON-RPC.
/// </summary>
public interface IPythonBackendService
{
    event EventHandler<ProgressNotification>? ProgressChanged;
    event EventHandler<string>? ErrorOccurred;
    event EventHandler? BackendStarted;
    event EventHandler? BackendStopped;

    bool IsRunning { get; }

    Task StartAsync();
    Task StopAsync();

    Task<UrlValidationResult> ValidateUrlAsync(string url);
    Task<DownloadResult> DownloadVideoAsync(string url, string outputDir, string? topic = null);
    Task<TranscriptionResult> TranscribeAsync(string audioPath, string language = "es", string modelSize = "large-v3");
    Task<List<Clip>> SelectClipsAsync(TranscriptionResult transcription, double videoDuration, string? topic = null, int maxClips = 3, int maxDuration = 75);
    Task<List<Clip>> RenderClipsAsync(List<Clip> clips, string sourceVideoPath, string layout, string? backgroundPath, string outputDir);
    Task<SubtitleResult> GenerateSubtitlesAsync(Clip clip, List<TranscriptionWord> words, string style = "karaoke");
    Task<LayoutPreviewResult> PreviewLayoutAsync(string layout, Clip? clip = null);
    Task<CorrectionResult> CorrectSubtitleAsync(string clipId, int wordIndex, string correctedText, double timeOffset = 0);
    Task<ExportResult> ExportClipAsync(Clip clip, string outputPath, string? subtitlesPath = null);
    Task<List<LayoutInfo>> GetAvailableLayoutsAsync();
}

public record UrlValidationResult(
    bool Valid,
    string? Title = null,
    double Duration = 0,
    string? Uploader = null,
    string? Thumbnail = null,
    bool IsLive = false,
    string? Platform = null,
    string? Error = null
);

public record DownloadResult(
    bool Success,
    string? VideoPath = null,
    string? AudioPath = null,
    Dictionary<string, object>? Metadata = null,
    double Duration = 0,
    string? Error = null
);

public record TranscriptionResult(
    bool Success,
    List<TranscriptionSegment>? Segments = null,
    List<TranscriptionWord>? Words = null,
    string? Language = null,
    double LanguageProbability = 1.0,
    string? Error = null
);

public record SubtitleResult(
    bool Success,
    string? SubtitlePath = null,
    List<SubtitleLine>? Lines = null,
    string? Error = null
);

public record SubtitleLine(
    int Index,
    double Start,
    double End,
    string Text,
    List<SubtitleWord> Words
);

public record SubtitleWord(
    string Word,
    double Start,
    double End,
    double Confidence,
    bool IsCorrected,
    string? OriginalWord = null
);

public record LayoutPreviewResult(
    bool Success,
    string? PreviewPath = null,
    string? Error = null
);

public record CorrectionResult(
    bool Success,
    string? Error = null
);

public record ExportResult(
    bool Success,
    string? OutputPath = null,
    string? Error = null
);

public record LayoutInfo(
    string Type,
    string Name,
    string DisplayName,
    string Description,
    bool IsSplitScreen,
    List<BackgroundAssetInfo>? AvailableBackgrounds = null
);

public record BackgroundAssetInfo(
    string Id,
    string Name,
    string DisplayName,
    string Type,
    string VideoPath,
    string? ThumbnailPath,
    double Duration,
    bool IsBundled,
    bool Loopable
);

public record ProgressNotification(
    string Stage,
    double Percent,
    string Message,
    int CurrentItem,
    int TotalItems,
    double? EtaSeconds
);