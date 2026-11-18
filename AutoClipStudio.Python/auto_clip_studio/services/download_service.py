"""
AutoClip Studio - Download Service
Handles video downloading from YouTube and other sources using yt-dlp.
"""

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
import yt_dlp

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import JobProgress

logger = get_logger(__name__)


class DownloadService:
    """Service for downloading videos from various sources."""

    def __init__(self, config: Config):
        self.config = config

    async def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL and extract basic info without downloading."""
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
            }

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, self._extract_info, url, ydl_opts
            )

            return {
                "valid": True,
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Unknown"),
                "thumbnail": info.get("thumbnail"),
                "is_live": info.get("is_live", False),
                "platform": info.get("extractor_key", "Unknown"),
                "formats_available": len(info.get("formats", []))
            }
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }

    def _extract_info(self, url: str, ydl_opts: Dict) -> Dict:
        """Extract info using yt-dlp (sync)."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download(
        self,
        url: str,
        output_dir: Path,
        topic: Optional[str] = None
    ) -> AsyncGenerator[JobProgress, Dict[str, Any]]:
        """
        Download video and extract audio.
        Yields progress updates, returns final result.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_title = "video"
        video_path = output_dir / f"{safe_title}.%(ext)s"
        audio_path = output_dir / f"{safe_title}.wav"

        # Progress hook for yt-dlp
        progress_data = {"percent": 0.0, "stage": "downloading"}

        def progress_hook(d):
            if d["status"] == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                if total > 0:
                    progress_data["percent"] = (downloaded / total) * 100
                progress_data["stage"] = "downloading"
                progress_data["message"] = f"Descargando: {d.get('_percent_str', '').strip()}"
            elif d["status"] == "finished":
                progress_data["percent"] = 100
                progress_data["stage"] = "post_processing"
                progress_data["message"] = "Procesando vídeo..."

        ydl_opts = {
            "format": self.config.ytdlp_format,
            "outtmpl": str(video_path),
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": False,
            "max_filesize": self.config.ytdlp_max_filesize,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
            "postprocessor_args": {
                "FFmpegExtractAudio": ["-ar", "16000", "-ac", "1"]
            },
            "keepvideo": True,
        }

        # Start download
        yield JobProgress(stage="downloading", percent=0, message="Iniciando descarga...")

        loop = asyncio.get_event_loop()
        try:
            info = await loop.run_in_executor(
                None, self._download_with_ytdlp, url, ydl_opts
            )

            # Find actual downloaded files
            video_files = list(output_dir.glob(f"{safe_title}.*"))
            video_file = next((f for f in video_files if f.suffix in [".mp4", ".mkv", ".webm", ".mov"]), None)
            audio_file = output_dir / f"{safe_title}.wav"

            if not video_file or not video_file.exists():
                # Try to find by actual title
                actual_title = info.get("title", "video").replace("/", "_").replace("\\", "_")
                video_files = list(output_dir.glob(f"{actual_title}.*"))
                video_file = next((f for f in video_files if f.suffix in [".mp4", ".mkv", ".webm", ".mov"]), None)
                audio_file = output_dir / f"{actual_title}.wav"

            if not video_file or not video_file.exists():
                raise FileNotFoundError("Video file not found after download")

            # Get video duration
            duration = await self._get_video_duration(video_file)

            yield JobProgress(
                stage="completed",
                percent=100,
                message="Descarga completada",
                current_item=1,
                total_items=1
            )

            return {
                "video_path": video_file,
                "audio_path": audio_file if audio_file.exists() else None,
                "metadata": {
                    "title": info.get("title"),
                    "uploader": info.get("uploader"),
                    "duration": duration,
                    "description": info.get("description"),
                    "tags": info.get("tags", []),
                    "upload_date": info.get("upload_date"),
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                },
                "duration": duration
            }

        except Exception as e:
            logger.exception("Download failed")
            yield JobProgress(stage="error", percent=0, message=f"Error: {str(e)}")
            raise

    def _download_with_ytdlp(self, url: str, ydl_opts: Dict) -> Dict:
        """Download using yt-dlp (sync)."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    async def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return float(stdout.decode().strip())
        except Exception:
            return 0.0