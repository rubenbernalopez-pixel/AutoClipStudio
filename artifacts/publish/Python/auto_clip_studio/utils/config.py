"""
AutoClip Studio - Configuration
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):
    """Application configuration."""

    # Paths
    app_data_dir: Path = Field(
        default_factory=lambda: Path(os.environ.get("LOCALAPPDATA", "")) / "AutoClipStudio"
    )
    temp_dir: Path = Field(default_factory=lambda: Path(os.environ.get("TEMP", "")) / "AutoClipStudio")
    output_dir: Path = Field(
        default_factory=lambda: Path.home() / "Documents" / "AutoClipStudio" / "Clips"
    )
    assets_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent.parent / "assets"
    )
    whisper_models_dir: Path = Field(
        default_factory=lambda: Path(os.environ.get("LOCALAPPDATA", "")) / "AutoClipStudio" / "whisper_models"
    )

    # Whisper settings
    default_model_size: str = "large-v3"
    default_language: str = "es"
    whisper_device: str = "auto"  # auto, cpu, cuda
    whisper_compute_type: str = "float16"  # float16, int8, float32

    # Video settings
    default_width: int = 1080
    default_height: int = 1920
    default_fps: int = 30
    default_max_clips: int = 3
    default_max_duration: int = 75  # seconds
    video_codec: str = "libx264"
    video_preset: str = "medium"
    video_crf: int = 20
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"

    # yt-dlp settings
    ytdlp_format: str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    ytdlp_max_filesize: str = "2G"

    # Clip selection
    min_clip_duration: int = 15  # seconds
    max_clip_duration: int = 75  # seconds
    hook_weight: float = 0.3
    development_weight: float = 0.3
    closing_weight: float = 0.2
    clarity_weight: float = 0.2
    min_score_threshold: float = 0.4

    # Subtitle settings
    subtitle_font_size: int = 48
    subtitle_font_family: str = "Inter"
    subtitle_color_active: str = "#FFD700"  # Gold
    subtitle_color_done: str = "#00FF7F"  # Spring green
    subtitle_color_pending: str = "#FFFFFF80"  # White with transparency
    subtitle_outline_color: str = "#000000"
    subtitle_outline_width: int = 3
    subtitle_line_duration: float = 0.45  # seconds per line
    max_words_per_line: int = 8
    max_lines: int = 2

    # Layout settings
    podcast_area_ratio: float = 0.55  # Top portion for podcast in split screen
    background_area_ratio: float = 0.45  # Bottom portion for background
    subtitle_safe_top: float = 0.10
    subtitle_safe_bottom: float = 0.15
    subtitle_safe_sides: float = 0.05

    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    # First run
    first_run_completed: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.whisper_models_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls) -> "Config":
        """Load config from file or create default."""
        config_path = cls().app_data_dir / "config.json"
        if config_path.exists():
            import json
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        return cls()

    def save(self):
        """Save config to file."""
        config_path = self.app_data_dir / "config.json"
        import json
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, default=str)

    def get_whisper_model_path(self, model_size: str) -> Path:
        """Get path to whisper model."""
        return self.whisper_models_dir / f"{model_size}.pt"

    def is_model_downloaded(self, model_size: str) -> bool:
        """Check if whisper model is downloaded."""
        return self.get_whisper_model_path(model_size).exists()