using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using AutoClipStudio.Core.Models;
using AutoClipStudio.WPF.Services;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace AutoClipStudio.WPF.Services;

/// <summary>
/// JSON-RPC client for Python backend communication.
/// </summary>
public class PythonBackendService : IPythonBackendService, IDisposable
{
    private readonly ILogger<PythonBackendService> _logger;
    private readonly PythonBackendOptions _options;
    private Process? _pythonProcess;
    private StreamWriter? _stdin;
    private StreamReader? _stdout;
    private readonly Dictionary<string, TaskCompletionSource<JsonElement>> _pendingRequests = new();
    private readonly JsonSerializerOptions _jsonOptions;
    private long _requestId = 0;

    public event EventHandler<ProgressNotification>? ProgressChanged;
    public event EventHandler<string>? ErrorOccurred;
    public event EventHandler? BackendStarted;
    public event EventHandler? BackendStopped;

    public bool IsRunning => _pythonProcess != null && !_pythonProcess.HasExited;

    public PythonBackendService(
        ILogger<PythonBackendService> logger,
        IOptions<PythonBackendOptions> options)
    {
        _logger = logger;
        _options = options.Value;
        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        };
    }

    public async Task StartAsync()
    {
        if (IsRunning) return;

        _logger.LogInformation("Starting Python backend...");

        var pythonExe = FindPythonExecutable();
        if (string.IsNullOrEmpty(pythonExe))
        {
            throw new InvalidOperationException("Python executable not found. Please ensure Python 3.11+ is installed or bundled.");
        }

        var scriptPath = FindBackendScript();
        if (string.IsNullOrEmpty(scriptPath))
        {
            throw new InvalidOperationException("Python backend script not found.");
        }

        var startInfo = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = $"\"{scriptPath}\"",
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
            WorkingDirectory = Path.GetDirectoryName(scriptPath)
        };

        _pythonProcess = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
        _pythonProcess.ErrorDataReceived += (s, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
            {
                _logger.LogError("[Python] {Error}", e.Data);
            }
        };
        _pythonProcess.Exited += (s, e) =>
        {
            _logger.LogWarning("Python backend exited with code {Code}", _pythonProcess.ExitCode);
            BackendStopped?.Invoke(this, EventArgs.Empty);
        };

        _pythonProcess.Start();
        _pythonProcess.BeginErrorReadLine();

        _stdin = _pythonProcess.StandardInput;
        _stdout = _pythonProcess.StandardOutput;

        // Start reading responses
        _ = Task.Run(ReadResponsesAsync);

        // Wait for backend to be ready
        await Task.Delay(1000);

        BackendStarted?.Invoke(this, EventArgs.Empty);
        _logger.LogInformation("Python backend started successfully");
    }

    public async Task StopAsync()
    {
        if (_pythonProcess != null && !_pythonProcess.HasExited)
        {
            _logger.LogInformation("Stopping Python backend...");
            _pythonProcess.Kill(true);
            await _pythonProcess.WaitForExitAsync();
            _pythonProcess.Dispose();
            _pythonProcess = null;
        }

        _stdin?.Dispose();
        _stdout?.Dispose();
        _stdin = null;
        _stdout = null;
    }

    private string? FindPythonExecutable()
    {
        // Check bundled Python first
        var bundledPython = Path.Combine(
            AppDomain.CurrentDomain.BaseDirectory,
            "Python", "python.exe");
        if (File.Exists(bundledPython)) return bundledPython;

        // Check PATH
        var paths = Environment.GetEnvironmentVariable("PATH")?.Split(';') ?? [];
        foreach (var path in paths)
        {
            var python = Path.Combine(path, "python.exe");
            if (File.Exists(python)) return python;

            var python3 = Path.Combine(path, "python3.exe");
            if (File.Exists(python3)) return python3;
        }

        return null;
    }

    private string? FindBackendScript()
    {
        // Check relative to app directory
        var baseDir = AppDomain.CurrentDomain.BaseDirectory;
        var candidates = new[]
        {
            Path.Combine(baseDir, "Python", "auto_clip_studio", "main.py"),
            Path.Combine(baseDir, "..", "..", "src", "AutoClipStudio.Python", "auto_clip_studio", "main.py"),
            Path.Combine(baseDir, "auto_clip_studio", "main.py")
        };

        foreach (var candidate in candidates)
        {
            var fullPath = Path.GetFullPath(candidate);
            if (File.Exists(fullPath)) return fullPath;
        }

        return null;
    }

    private async Task ReadResponsesAsync()
    {
        try
        {
            while (_stdout != null && !_stdout.EndOfStream)
            {
                var line = await _stdout.ReadLineAsync();
                if (string.IsNullOrWhiteSpace(line)) continue;

                try
                {
                    var doc = JsonDocument.Parse(line);
                    var root = doc.RootElement;

                    if (root.TryGetProperty("method", out var methodProp) &&
                        methodProp.GetString() == "progress")
                    {
                        // Progress notification
                        if (root.TryGetProperty("params", out var paramsElem))
                        {
                            var progress = JsonSerializer.Deserialize<ProgressNotification>(paramsElem.GetRawText(), _jsonOptions);
                            if (progress != null)
                            {
                                ProgressChanged?.Invoke(this, progress);
                            }
                        }
                    }
                    else if (root.TryGetProperty("id", out var idProp))
                    {
                        // Response to request
                        var id = idProp.GetString() ?? "";
                        if (_pendingRequests.TryGetValue(id, out var tcs))
                        {
                            _pendingRequests.Remove(id);
                            if (root.TryGetProperty("error", out var errorElem))
                            {
                                var error = JsonSerializer.Deserialize<PythonError>(errorElem.GetRawText(), _jsonOptions);
                                tcs.SetException(new PythonBackendException(error?.Message ?? "Unknown error"));
                            }
                            else if (root.TryGetProperty("result", out var resultElem))
                            {
                                tcs.SetResult(resultElem);
                            }
                        }
                    }
                }
                catch (JsonException ex)
                {
                    _logger.LogWarning("Failed to parse JSON-RPC message: {Ex}", ex.Message);
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error reading Python backend responses");
        }
    }

    private async Task<T> SendRequestAsync<T>(string method, object? @params = null)
    {
        if (!IsRunning)
        {
            throw new InvalidOperationException("Python backend is not running");
        }

        var id = Interlocked.Increment(ref _requestId).ToString();
        var request = new
        {
            jsonrpc = "2.0",
            method,
            @params,
            id
        };

        var tcs = new TaskCompletionSource<JsonElement>();
        _pendingRequests[id] = tcs;

        var json = JsonSerializer.Serialize(request, _jsonOptions);
        await _stdin!.WriteLineAsync(json);
        await _stdin.FlushAsync();

        // Wait for response with timeout
        var completedTask = await Task.WhenAny(tcs.Task, Task.Delay(TimeSpan.FromMinutes(5)));
        if (completedTask == tcs.Task)
        {
            var result = await tcs.Task;
            return JsonSerializer.Deserialize<T>(result.GetRawText(), _jsonOptions)!;
        }
        else
        {
            _pendingRequests.Remove(id);
            throw new TimeoutException($"Request {method} timed out");
        }
    }

    public async Task<UrlValidationResult> ValidateUrlAsync(string url)
    {
        var result = await SendRequestAsync<JsonElement>("validate_url", new { url });
        return JsonSerializer.Deserialize<UrlValidationResult>(result.GetRawText(), _jsonOptions)!;
    }

    public async Task<DownloadResult> DownloadVideoAsync(string url, string outputDir, string? topic = null)
    {
        var result = await SendRequestAsync<JsonElement>("download_video", new { url, output_dir = outputDir, topic });
        return JsonSerializer.Deserialize<DownloadResult>(result.GetRawText(), _jsonOptions)!;
    }

    public async Task<TranscriptionResult> TranscribeAsync(string audioPath, string language = "es", string modelSize = "large-v3")
    {
        var result = await SendRequestAsync<JsonElement>("transcribe", new { audio_path = audioPath, language, model_size = modelSize });
        return JsonSerializer.Deserialize<TranscriptionResult>(result.GetRawText(), _jsonOptions)!;
    }

    public async Task<List<Clip>> SelectClipsAsync(TranscriptionResult transcription, double videoDuration, string? topic = null, int maxClips = 3, int maxDuration = 75)
    {
        var transcriptionData = new
        {
            segments = transcription.Segments?.Select(s => new { s.Id, s.Start, s.End, s.Text, s.Words, s.SpeakerId, s.Confidence }),
            words = transcription.Words?.Select(w => new { w.Word, w.Start, w.End, w.Confidence, w.SpeakerId, w.IsCorrected, w.CorrectedText, w.TimeOffset }),
            language = transcription.Language
        };

        var result = await SendRequestAsync<JsonElement>("select_clips", new
        {
            transcription = transcriptionData,
            video_duration = videoDuration,
            topic,
            max_clips = maxClips,
            max_duration = maxDuration
        });

        var clipsData = result.GetProperty("clips");
        return JsonSerializer.Deserialize<List<Clip>>(clipsData.GetRawText(), _jsonOptions)!;
    }

    public async Task<List<Clip>> RenderClipsAsync(List<Clip> clips, string sourceVideoPath, string layout, string? backgroundPath, string outputDir)
    {
        var result = await SendRequestAsync<JsonElement>("render_clips", new
        {
            clips = clips.Select(c => new { c.Id, c.Start, c.End, c.Duration, c.Hook, c.Development, c.Closing, c.Score, c.Layout, c.BackgroundAsset }),
            video_path = sourceVideoPath,
            layout,
            background_path = backgroundPath,
            output_dir = outputDir
        });

        var clipsData = result.GetProperty("rendered_clips");
        return JsonSerializer.Deserialize<List<Clip>>(clipsData.GetRawText(), _jsonOptions)!;
    }

    public async Task<SubtitleResult> GenerateSubtitlesAsync(Clip clip, List<TranscriptionWord> words, string style = "karaoke")
    {
        var result = await SendRequestAsync<JsonElement>("generate_subtitles", new
        {
            clip = new { clip.Id, clip.Start, clip.End },
            words = words.Select(w => new { w.Word, w.Start, w.End, w.Confidence, w.SpeakerId, w.IsCorrected, w.CorrectedText, w.TimeOffset }),
            style
        });

        return JsonSerializer.Deserialize<SubtitleResult>(result.GetRawText(), _jsonOptions)!;
    }

    public async Task<LayoutPreviewResult> PreviewLayoutAsync(string layout, Clip? clip = null)
    {
        var result = await SendRequestAsync<JsonElement>("preview_layout", new
        {
            layout,
            clip = clip != null ? new { clip.Id, clip.Start, clip.End } : null
        });

        return JsonSerializer.Deserialize<LayoutPreviewResult>(result.GetRawText(), _jsonOptions)!;
    }

    public async Task<List<LayoutInfo>> GetAvailableLayoutsAsync()
    {
        var result = await SendRequestAsync<JsonElement>("get_available_layouts", new { });
        var layoutsData = result.GetProperty("layouts");
        return JsonSerializer.Deserialize<List<LayoutInfo>>(layoutsData.GetRawText(), _jsonOptions)!;
    }

    public async Task<CorrectionResult> CorrectSubtitleAsync(string clipId, int wordIndex, string correctedText, double timeOffset = 0)
    {
        var result = await SendRequestAsync<JsonElement>("correct_subtitle", new
        {
            clip_id = clipId,
            word_index = wordIndex,
            corrected_text = correctedText,
            time_offset = timeOffset
        });

        return JsonSerializer.Deserialize<CorrectionResult>(result.GetRawText(), _jsonOptions)!;
    }

    public async Task<ExportResult> ExportClipAsync(Clip clip, string outputPath, string? subtitlesPath = null)
    {
        var result = await SendRequestAsync<JsonElement>("export_clip", new
        {
            clip = new { clip.Id, clip.Start, clip.End, clip.Duration, clip.VideoPath, clip.SubtitlePath },
            output_path = outputPath,
            subtitles_path = subtitlesPath
        });

        return JsonSerializer.Deserialize<ExportResult>(result.GetRawText(), _jsonOptions)!;
    }

    public void Dispose()
    {
        StopAsync().GetAwaiter().GetResult();
        GC.SuppressFinalize(this);
    }
}

public class PythonBackendOptions
{
    public string? PythonPath { get; set; }
    public string? ScriptPath { get; set; }
    public int StartupTimeoutSeconds { get; set; } = 30;
}

public class PythonError
{
    public int Code { get; set; }
    public string Message { get; set; } = "";
    public object? Data { get; set; }
}

public class PythonBackendException : Exception
{
    public PythonBackendException(string message) : base(message) { }
}