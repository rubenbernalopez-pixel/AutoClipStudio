"""
AutoClip Studio - Job Models
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid


class JobStatus(str, Enum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    SELECTING = "selecting"
    SELECTED = "selected"
    RENDERING = "rendering"
    RENDERED = "rendered"
    EXPORTING = "exporting"
    EXPORTED = "exported"
    ERROR = "error"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    DOWNLOAD = "download"
    TRANSCRIPTION = "transcription"
    SELECTION = "selection"
    RENDER = "render"
    EXPORT = "export"


@dataclass
class JobProgress:
    """Progress information for a job."""
    stage: str = ""
    percent: float = 0.0
    message: str = ""
    current_item: int = 0
    total_items: int = 0
    eta_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "percent": self.percent,
            "message": self.message,
            "current_item": self.current_item,
            "total_items": self.total_items,
            "eta_seconds": self.eta_seconds
        }


@dataclass
class TranscriptionWord:
    """A single word with timing information."""
    word: str
    start: float
    end: float
    confidence: float
    speaker_id: Optional[int] = None
    is_corrected: bool = False
    corrected_text: Optional[str] = None
    time_offset: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "word": self.word,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "speaker_id": self.speaker_id,
            "is_corrected": self.is_corrected,
            "corrected_text": self.corrected_text,
            "time_offset": self.time_offset
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionWord":
        return cls(
            word=data["word"],
            start=data["start"],
            end=data["end"],
            confidence=data["confidence"],
            speaker_id=data.get("speaker_id"),
            is_corrected=data.get("is_corrected", False),
            corrected_text=data.get("corrected_text"),
            time_offset=data.get("time_offset", 0.0)
        )


@dataclass
class TranscriptionSegment:
    """A transcription segment (sentence/phrase)."""
    id: int
    start: float
    end: float
    text: str
    words: List[TranscriptionWord] = field(default_factory=list)
    speaker_id: Optional[int] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
            "speaker_id": self.speaker_id,
            "confidence": self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionSegment":
        return cls(
            id=data["id"],
            start=data["start"],
            end=data["end"],
            text=data["text"],
            words=[TranscriptionWord.from_dict(w) for w in data.get("words", [])],
            speaker_id=data.get("speaker_id"),
            confidence=data.get("confidence", 1.0)
        )


@dataclass
class Clip:
    """A selected clip with metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start: float = 0.0
    end: float = 0.0
    duration: float = 0.0
    hook: str = ""
    development: str = ""
    closing: str = ""
    score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    score_explanation: str = ""
    social_copy: str = ""
    hashtags: List[str] = field(default_factory=list)
    layout: str = "solo_podcast"
    background_asset: Optional[str] = None
    subtitle_path: Optional[str] = None
    video_path: Optional[str] = None
    preview_path: Optional[str] = None
    source_video_path: str = ""
    transcription_segments: List[TranscriptionSegment] = field(default_factory=list)
    transcription_words: List[TranscriptionWord] = field(default_factory=list)
    excluded_ranges: List[tuple] = field(default_factory=list)  # (start, end) to exclude
    is_reviewed: bool = False

    @property
    def start_timecode(self) -> str:
        return self._format_time(self.start)

    @property
    def end_timecode(self) -> str:
        return self._format_time(self.end)

    def _format_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "start_timecode": self.start_timecode,
            "end_timecode": self.end_timecode,
            "hook": self.hook,
            "development": self.development,
            "closing": self.closing,
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "score_explanation": self.score_explanation,
            "social_copy": self.social_copy,
            "hashtags": self.hashtags,
            "layout": self.layout,
            "background_asset": self.background_asset,
            "subtitle_path": self.subtitle_path,
            "video_path": self.video_path,
            "preview_path": self.preview_path,
            "source_video_path": self.source_video_path,
            "transcription_segments": [s.to_dict() for s in self.transcription_segments],
            "transcription_words": [w.to_dict() for w in self.transcription_words],
            "excluded_ranges": self.excluded_ranges,
            "is_reviewed": self.is_reviewed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Clip":
        clip = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            start=data["start"],
            end=data["end"],
            duration=data["duration"],
            hook=data.get("hook", ""),
            development=data.get("development", ""),
            closing=data.get("closing", ""),
            score=data.get("score", 0.0),
            score_breakdown=data.get("score_breakdown", {}),
            score_explanation=data.get("score_explanation", ""),
            social_copy=data.get("social_copy", ""),
            hashtags=data.get("hashtags", []),
            layout=data.get("layout", "solo_podcast"),
            background_asset=data.get("background_asset"),
            subtitle_path=data.get("subtitle_path"),
            video_path=data.get("video_path"),
            preview_path=data.get("preview_path"),
            source_video_path=data.get("source_video_path", ""),
            excluded_ranges=data.get("excluded_ranges", []),
            is_reviewed=data.get("is_reviewed", False)
        )
        clip.transcription_segments = [
            TranscriptionSegment.from_dict(s) for s in data.get("transcription_segments", [])
        ]
        clip.transcription_words = [
            TranscriptionWord.from_dict(w) for w in data.get("transcription_words", [])
        ]
        return clip


@dataclass
class Job:
    """Main job container."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: JobType = JobType.DOWNLOAD
    status: JobStatus = JobStatus.IDLE
    progress: JobProgress = field(default_factory=JobProgress)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    cancelled: bool = False

    # Job-specific data
    url: Optional[str] = None
    topic: Optional[str] = None
    video_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    transcription_segments: List[TranscriptionSegment] = field(default_factory=list)
    transcription_words: List[TranscriptionWord] = field(default_factory=list)
    detected_language: str = "es"
    selected_clips: List[Clip] = field(default_factory=list)
    rendered_clips: List[Clip] = field(default_factory=list)

    # Settings
    max_clips: int = 3
    max_duration: int = 75
    layout: str = "solo_podcast"
    background_path: Optional[str] = None
    output_dir: Optional[Path] = None
    model_size: str = "large-v3"
    language: str = "es"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error": self.error,
            "cancelled": self.cancelled,
            "url": self.url,
            "topic": self.topic,
            "video_path": str(self.video_path) if self.video_path else None,
            "audio_path": str(self.audio_path) if self.audio_path else None,
            "metadata": self.metadata,
            "duration": self.duration,
            "transcription_segments": [s.to_dict() for s in self.transcription_segments],
            "transcription_words": [w.to_dict() for w in self.transcription_words],
            "detected_language": self.detected_language,
            "selected_clips": [c.to_dict() for c in self.selected_clips],
            "rendered_clips": [c.to_dict() for c in self.rendered_clips],
            "max_clips": self.max_clips,
            "max_duration": self.max_duration,
            "layout": self.layout,
            "background_path": self.background_path,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "model_size": self.model_size,
            "language": self.language
        }

    def cancel(self):
        self.cancelled = True
        self.status = JobStatus.CANCELLED

    @classmethod
    def create_download_job(
        cls, url: str, output_dir: Path, topic: Optional[str] = None
    ) -> "Job":
        return cls(
            type=JobType.DOWNLOAD,
            url=url,
            topic=topic,
            output_dir=output_dir
        )

    @classmethod
    def create_transcription_job(
        cls, audio_path: Path, language: str, model_size: str
    ) -> "Job":
        return cls(
            type=JobType.TRANSCRIPTION,
            audio_path=audio_path,
            language=language,
            model_size=model_size
        )

    @classmethod
    def create_selection_job(
        cls,
        transcription: Dict[str, Any],
        video_duration: float,
        topic: Optional[str],
        max_clips: int,
        max_duration: int
    ) -> "Job":
        job = cls(
            type=JobType.SELECTION,
            duration=video_duration,
            topic=topic,
            max_clips=max_clips,
            max_duration=max_duration
        )
        job.transcription_segments = [
            TranscriptionSegment.from_dict(s) for s in transcription.get("segments", [])
        ]
        job.transcription_words = [
            TranscriptionWord.from_dict(w) for w in transcription.get("words", [])
        ]
        job.detected_language = transcription.get("language", "es")
        return job

    @classmethod
    def create_render_job(
        cls,
        clips: List[Dict[str, Any]],
        video_path: Path,
        layout: str,
        background_path: Optional[str],
        output_dir: Path
    ) -> "Job":
        return cls(
            type=JobType.RENDER,
            selected_clips=[Clip.from_dict(c) for c in clips],
            video_path=video_path,
            layout=layout,
            background_path=background_path,
            output_dir=output_dir
        )