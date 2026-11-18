namespace AutoClipStudio.Core.Models;

/// <summary>
/// Job status enumeration.
/// </summary>
public enum JobStatus
{
    Idle,
    Downloading,
    Downloaded,
    Transcribing,
    Transcribed,
    Selecting,
    Selected,
    Rendering,
    Rendered,
    Exporting,
    Exported,
    Error,
    Cancelled
}

/// <summary>
/// Job type enumeration.
/// </summary>
public enum JobType
{
    Download,
    Transcription,
    Selection,
    Render,
    Export
}

/// <summary>
/// Progress information for a job.
/// </summary>
public class JobProgress
{
    public string Stage { get; set; } = "";
    public double Percent { get; set; }
    public string Message { get; set; } = "";
    public int CurrentItem { get; set; }
    public int TotalItems { get; set; }
    public double? EtaSeconds { get; set; }
}

/// <summary>
/// Transcription word with timing.
/// </summary>
public class TranscriptionWord
{
    public string Word { get; set; } = "";
    public double Start { get; set; }
    public double End { get; set; }
    public double Confidence { get; set; }
    public int? SpeakerId { get; set; }
    public bool IsCorrected { get; set; }
    public string? CorrectedText { get; set; }
    public double TimeOffset { get; set; }
}

/// <summary>
/// Transcription segment (sentence/phrase).
/// </summary>
public class TranscriptionSegment
{
    public int Id { get; set; }
    public double Start { get; set; }
    public double End { get; set; }
    public string Text { get; set; } = "";
    public List<TranscriptionWord> Words { get; set; } = new();
    public int? SpeakerId { get; set; }
    public double Confidence { get; set; } = 1.0;
}

/// <summary>
/// A selected clip with metadata.
/// </summary>
public class Clip
{
    public string Id { get; set; } = Guid.NewGuid().ToString()[..8];
    public double Start { get; set; }
    public double End { get; set; }
    public double Duration { get; set; }
    public string StartTimecode => FormatTime(Start);
    public string EndTimecode => FormatTime(End);
    public string Hook { get; set; } = "";
    public string Development { get; set; } = "";
    public string Closing { get; set; } = "";
    public double Score { get; set; }
    public Dictionary<string, double> ScoreBreakdown { get; set; } = new();
    public string ScoreExplanation { get; set; } = "";
    public string SocialCopy { get; set; } = "";
    public List<string> Hashtags { get; set; } = new();
    public string Layout { get; set; } = "solo_podcast";
    public string? BackgroundAsset { get; set; }
    public string? SubtitlePath { get; set; }
    public string? VideoPath { get; set; }
    public string? PreviewPath { get; set; }
    public string SourceVideoPath { get; set; } = "";
    public List<TranscriptionSegment> TranscriptionSegments { get; set; } = new();
    public List<TranscriptionWord> TranscriptionWords { get; set; } = new();
    public List<(double Start, double End)> ExcludedRanges { get; set; } = new();
    public bool IsReviewed { get; set; }

    private static string FormatTime(double seconds)
    {
        var hours = (int)(seconds / 3600);
        var minutes = (int)((seconds % 3600) / 60);
        var secs = (int)(seconds % 60);
        return hours > 0 ? $"{hours:00}:{minutes:00}:{secs:00}" : $"{minutes:00}:{secs:00}";
    }
}

/// <summary>
/// Layout type enumeration.
/// </summary>
public enum LayoutType
{
    SoloPodcast,
    BallsHoops,
    BlockParkour,
    MyGameplay
}

/// <summary>
/// Layout configuration.
/// </summary>
public class Layout
{
    public LayoutType Type { get; set; }
    public string Name { get; set; } = "";
    public string DisplayName { get; set; } = "";
    public string Description { get; set; } = "";
    public bool IsSplitScreen { get; set; }
    public BackgroundAsset? BackgroundAsset { get; set; }
    public Dictionary<string, double> PodcastArea { get; set; } = new();
    public Dictionary<string, double> BackgroundArea { get; set; } = new();
    public Dictionary<string, double> SubtitleArea { get; set; } = new();
    public bool ZoomEnabled { get; set; } = true;
    public bool FramingEnabled { get; set; } = true;
    public bool VoiceLeveling { get; set; } = true;
}

/// <summary>
/// Background asset for split-screen layouts.
/// </summary>
public class BackgroundAsset
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string DisplayName { get; set; } = "";
    public LayoutType Type { get; set; }
    public string VideoPath { get; set; } = "";
    public string? ThumbnailPath { get; set; }
    public double Duration { get; set; }
    public bool IsBundled { get; set; }
    public bool Loopable { get; set; }
    public int Fps { get; set; } = 30;
    public (int Width, int Height) Resolution { get; set; } = (1080, 1920);
}

/// <summary>
/// Main job container.
/// </summary>
public class Job
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public JobType Type { get; set; }
    public JobStatus Status { get; set; } = JobStatus.Idle
    public JobProgress Progress { get; set; } = new();
    public DateTime CreatedAt { get; set; } = DateTime.Now;
    public DateTime UpdatedAt { get; set; } = DateTime.Now;
    public string? Error { get; set; }
    public bool Cancelled { get; set; }

    // Job-specific data
    public string? Url { get; set; }
    public string? Topic { get; set; }
    public string? VideoPath { get; set; }
    public string? AudioPath { get; set; }
    public Dictionary<string, object> Metadata { get; set; } = new();
    public double Duration { get; set; }
    public List<TranscriptionSegment> TranscriptionSegments { get; set; } = new();
    public List<TranscriptionWord> TranscriptionWords { get; set; } = new();
    public string DetectedLanguage { get; set; } = "es";
    public List<Clip> SelectedClips { get; set; } = new();
    public List<Clip> RenderedClips { get; set; } = new();

    // Settings
    public int MaxClips { get; set; } = 3;
    public int MaxDuration { get; set; } = 75;
    public string Layout { get; set; } = "solo_podcast";
    public string? BackgroundPath { get; set; }
    public string? OutputDir { get; set; }
    public string ModelSize { get; set; } = "large-v3";
    public string Language { get; set; } = "es";
}