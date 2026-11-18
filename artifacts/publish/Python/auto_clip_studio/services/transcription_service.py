"""
AutoClip Studio - Transcription Service
Uses faster-whisper for high-quality Spanish transcription with word-level timestamps.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
import torch

from faster_whisper import WhisperModel

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import JobProgress, TranscriptionSegment, TranscriptionWord

logger = get_logger(__name__)


class TranscriptionService:
    """Service for audio transcription using faster-whisper."""

    def __init__(self, config: Config):
        self.config = config
        self._model: Optional[WhisperModel] = None
        self._model_size: Optional[str] = None

    def _get_model(self, model_size: str, device: str = "auto", compute_type: str = "float16") -> WhisperModel:
        """Get or load the Whisper model."""
        if self._model is not None and self._model_size == model_size:
            return self._model

        # Determine device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda":
                compute_type = "float16"
            else:
                compute_type = "int8"

        logger.info(f"Loading Whisper model: {model_size} on {device} with {compute_type}")

        model_path = self.config.get_whisper_model_path(model_size)
        if model_path.exists():
            logger.info(f"Using local model: {model_path}")
            self._model = WhisperModel(
                str(model_path),
                device=device,
                compute_type=compute_type,
                local_files_only=True
            )
        else:
            logger.info(f"Downloading model: {model_size}")
            self._model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=str(self.config.whisper_models_dir)
            )

        self._model_size = model_size
        return self._model

    async def transcribe(
        self,
        audio_path: Path,
        language: str = "es",
        model_size: str = "large-v3"
    ) -> AsyncGenerator[JobProgress, Dict[str, Any]]:
        """
        Transcribe audio file with word-level timestamps.
        Yields progress updates, returns transcription result.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        yield JobProgress(stage="loading_model", percent=5, message="Cargando modelo de transcripción...")

        model = self._get_model(model_size, self.config.whisper_device, self.config.whisper_compute_type)

        yield JobProgress(stage="transcribing", percent=10, message="Transcribiendo audio...")

        # Run transcription in executor to avoid blocking
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: list(model.transcribe(
                str(audio_path),
                language=language if language != "auto" else None,
                task="transcribe",
                beam_size=5,
                word_timestamps=True,
                condition_on_previous_text=True,
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            ))
        )

        yield JobProgress(stage="processing", percent=70, message="Procesando segmentos...")

        # Process segments and words
        transcription_segments = []
        transcription_words = []

        total_segments = len(segments)
        for i, segment in enumerate(segments):
            # Create words list
            words = []
            if segment.words:
                for j, word in enumerate(segment.words):
                    tw = TranscriptionWord(
                        word=word.word.strip(),
                        start=word.start,
                        end=word.end,
                        confidence=word.probability,
                        speaker_id=None  # Will be filled by diarization if available
                    )
                    words.append(tw)
                    transcription_words.append(tw)

            ts = TranscriptionSegment(
                id=i,
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
                words=words,
                confidence=segment.avg_logprob if hasattr(segment, 'avg_logprob') else 1.0
            )
            transcription_segments.append(ts)

            # Yield progress
            percent = 70 + (i / total_segments) * 25
            yield JobProgress(
                stage="transcribing",
                percent=percent,
                message=f"Segmento {i+1}/{total_segments}",
                current_item=i+1,
                total_items=total_segments
            )

        # Detect language
        detected_language = info.language if hasattr(info, 'language') else language
        language_prob = info.language_probability if hasattr(info, 'language_probability') else 1.0

        logger.info(f"Transcription complete: {len(transcription_segments)} segments, "
                    f"{len(transcription_words)} words, language: {detected_language} ({language_prob:.2f})")

        yield JobProgress(
            stage="completed",
            percent=100,
            message="Transcripción completada",
            current_item=total_segments,
            total_items=total_segments
        )

        return {
            "segments": transcription_segments,
            "words": transcription_words,
            "language": detected_language,
            "language_probability": language_prob
        }

    async def verify_transcription_sync(
        self,
        audio_path: Path,
        reference_text: str,
        start_time: float,
        end_time: float
    ) -> Dict[str, Any]:
        """
        Verify transcription against reference text for a specific time range.
        Used for subtitle validation.
        """
        model = self._get_model(self.config.default_model_size)

        loop = asyncio.get_event_loop()
        segments, _ = await loop.run_in_executor(
            None,
            lambda: list(model.transcribe(
                str(audio_path),
                language="es",
                task="transcribe",
                beam_size=5,
                word_timestamps=True,
                clip_timestamps=f"{start_time},{end_time}"
            ))
        )

        transcribed_text = " ".join(s.text.strip() for s in segments)

        # Simple similarity check
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, transcribed_text.lower(), reference_text.lower()).ratio()

        return {
            "transcribed": transcribed_text,
            "reference": reference_text,
            "similarity": similarity,
            "match": similarity > 0.8,
            "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
        }

    def unload_model(self):
        """Unload model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_size = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()