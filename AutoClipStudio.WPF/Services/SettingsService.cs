using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using AutoClipStudio.WPF.Services;
using Microsoft.Extensions.Logging;

namespace AutoClipStudio.WPF.Services;

/// <summary>
/// Application settings persistence.
/// </summary>
public interface ISettingsService
{
    AppSettings Settings { get; }
    Task LoadAsync();
    Task SaveAsync();
    void ResetToDefaults();
}

public class SettingsService : ISettingsService
{
    private readonly ILogger<SettingsService> _logger;
    private readonly string _settingsPath;
    public AppSettings Settings { get; private set; } = new();

    public SettingsService(ILogger<SettingsService> logger)
    {
        _logger = logger;
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var dir = Path.Combine(appData, "AutoClipStudio");
        Directory.CreateDirectory(dir);
        _settingsPath = Path.Combine(dir, "settings.json");
    }

    public async Task LoadAsync()
    {
        try
        {
            if (File.Exists(_settingsPath))
            {
                var json = await File.ReadAllTextAsync(_settingsPath);
                var loaded = JsonSerializer.Deserialize<AppSettings>(json);
                if (loaded != null)
                {
                    Settings = loaded;
                    _logger.LogInformation("Settings loaded from {Path}", _settingsPath);
                }
            }
            else
            {
                Settings = new AppSettings();
                await SaveAsync();
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load settings, using defaults");
            Settings = new AppSettings();
        }
    }

    public async Task SaveAsync()
    {
        try
        {
            var json = JsonSerializer.Serialize(Settings, new JsonSerializerOptions
            {
                WriteIndented = true
            });
            await File.WriteAllTextAsync(_settingsPath, json);
            _logger.LogInformation("Settings saved to {Path}", _settingsPath);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to save settings");
        }
    }

    public void ResetToDefaults()
    {
        Settings = new AppSettings();
    }
}

public class AppSettings
{
    // General
    public string Language { get; set; } = "es-ES";
    public string Theme { get; set; } = "Dark";
    public bool AutoCheckUpdates { get; set; } = true;
    public bool StartMinimized { get; set; } = false;

    // Paths
    public string OutputDirectory { get; set; } = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
        "AutoClipStudio", "Clips");
    public string TempDirectory { get; set; } = Path.Combine(
        Environment.GetEnvironmentVariable("TEMP") ?? Path.GetTempPath(),
        "AutoClipStudio");

    // Video defaults
    public int DefaultWidth { get; set; } = 1080;
    public int DefaultHeight { get; set; } = 1920;
    public int DefaultFps { get; set; } = 30;
    public int DefaultMaxClips { get; set; } = 3;
    public int DefaultMaxDuration { get; set; } = 75;
    public string DefaultLayout { get; set; } = "solo_podcast";

    // Whisper settings
    public string DefaultModelSize { get; set; } = "large-v3";
    public string DefaultLanguage { get; set; } = "es";
    public string WhisperDevice { get; set; } = "auto";
    public string WhisperComputeType { get; set; } = "float16";

    // Subtitle settings
    public int SubtitleFontSize { get; set; } = 48;
    public string SubtitleFontFamily { get; set; } = "Inter";
    public double SubtitleLineDuration { get; set; } = 0.45;
    public int MaxWordsPerLine { get; set; } = 8;
    public int MaxLines { get; set; } = 2;

    // Advanced
    public bool EnableGpuAcceleration { get; set; } = true;
    public int MaxConcurrentJobs { get; set; } = 1;
    public bool KeepTempFiles { get; set; } = false;
    public string LogLevel { get; set; } = "INFO";
}