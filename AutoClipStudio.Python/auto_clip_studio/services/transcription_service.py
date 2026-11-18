"""
AutoClip Studio - Transcription Service (MEJORADO)
Usa faster-whisper large-v3 con VAD, corrección de alineación y timestamps por palabra ultra-precisos.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple
import numpy as np
import torch

from faster_whisper import WhisperModel
from faster_whisper.vad import VadOptions

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import JobProgress, TranscriptionSegment, TranscriptionWord

logger = get_logger(__name__)


class TranscriptionService:
    """Servicio de transcripción con Whisper large-v3 optimizado para español."""

    def __init__(self, config: Config):
        self.config = config
        self._model: Optional[WhisperModel] = None
        self._model_size: Optional[str] = None
        self._device: Optional[str] = None

    def _get_model(self, model_size: str, device: str = "auto", compute_type: str = "float16") -> WhisperModel:
        """Carga o reutiliza el modelo Whisper con configuración óptima."""
        if self._model is not None and self._model_size == model_size and self._device == device:
            return self._model

        # Determinar dispositivo automáticamente
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"
                # Verificar VRAM disponible
                try:
                    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    if vram_gb < 6:
                        compute_type = "int8_float16"  # Híbrido para VRAM limitada
                        logger.info(f"VRAM limitada ({vram_gb:.1f}GB), usando int8_float16")
                except Exception:
                    pass
            else:
                device = "cpu"
                compute_type = "int8"
                logger.info("CUDA no disponible, usando CPU con int8")

        logger.info(f"Cargando Whisper {model_size} en {device} ({compute_type})")

        model_path = self.config.get_whisper_model_path(model_size)
        download_root = str(self.config.whisper_models_dir)

        # Configuración VAD optimizada para podcasts (habla continua, pocos silencios)
        vad_options = VadOptions(
            threshold=0.35,           # Más sensible para detectar habla suave
            min_speech_duration_ms=100,  # Mínimo 100ms de habla
            max_speech_duration_s=30,    # Máx 30s por segmento
            min_silence_duration_ms=300, # Silencio mínimo para separar
            speech_pad_ms=200           # Padding alrededor de habla
        )

        if model_path.exists():
            logger.info(f"Usando modelo local: {model_path}")
            self._model = WhisperModel(
                str(model_path),
                device=device,
                compute_type=compute_type,
                local_files_only=True,
                cpu_threads=os.cpu_count() or 4,
                num_workers=1
            )
        else:
            logger.info(f"Descargando modelo {model_size}...")
            self._model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
                cpu_threads=os.cpu_count() or 4,
                num_workers=1
            )

        self._model_size = model_size
        self._device = device
        return self._model

    async def transcribe(
        self,
        audio_path: Path,
        language: str = "es",
        model_size: str = "large-v3",
        prompt: Optional[str] = None
    ) -> AsyncGenerator[JobProgress, Dict[str, Any]]:
        """
        Transcribe audio con timestamps por palabra y corrección de alineación.
        Yields progress, returns transcription result.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio no encontrado: {audio_path}")

        yield JobProgress(stage="loading_model", percent=5, message="Cargando modelo Whisper large-v3...")

        model = self._get_model(model_size, self.config.whisper_device, self.config.whisper_compute_type)

        yield JobProgress(stage="transcribing", percent=10, message="Transcribiendo con VAD y timestamps por palabra...")

        # Ejecutar transcripción en executor (bloqueante)
        loop = asyncio.get_event_loop()

        # Prompt contextual para mejorar precisión en español
        initial_prompt = prompt or (
            "Este es un podcast en español. Los hablantes usan lenguaje natural, "
            "pueden interrumpirse, reírse, usar muletillas. Nombres propios, cifras y "
            "negaciones deben transcribirse exactamente."
        )

        try:
            segments, info = await loop.run_in_executor(
                None,
                lambda: list(model.transcribe(
                    str(audio_path),
                    language=language if language != "auto" else None,
                    task="transcribe",
                    beam_size=5,
                    best_of=5,
                    patience=1.0,
                    length_penalty=1.0,
                    repetition_penalty=1.02,
                    no_repeat_ngram_size=0,
                    temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                    compression_ratio_threshold=2.4,
                    log_prob_threshold=-1.0,
                    no_speech_threshold=0.4,
                    condition_on_previous_text=True,
                    prompt_reset_on_temperature=0.5,
                    initial_prompt=initial_prompt,
                    word_timestamps=True,
                    prepend_punctuations="\"'¿¡([{-",
                    append_punctuations="\"'.。,，!！?？:：\")]}、",
                    vad_filter=True,
                    vad_parameters=dict(
                        threshold=0.35,
                        min_speech_duration_ms=100,
                        max_speech_duration_s=30,
                        min_silence_duration_ms=300,
                        speech_pad_ms=200
                    )
                ))
            )
        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            # Fallback sin VAD
            logger.warning("Reintentando sin VAD...")
            segments, info = await loop.run_in_executor(
                None,
                lambda: list(model.transcribe(
                    str(audio_path),
                    language=language if language != "auto" else None,
                    task="transcribe",
                    beam_size=5,
                    word_timestamps=True,
                    temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                    vad_filter=False
                ))
            )

        yield JobProgress(stage="processing", percent=70, message="Procesando segmentos y corrigiendo alineación...")

        # Procesar segmentos y palabras con corrección de alineación
        transcription_segments = []
        transcription_words = []
        total_segments = len(segments)

        for i, segment in enumerate(segments):
            words = []
            if segment.words:
                for j, word in enumerate(segment.words):
                    # Limpiar palabra
                    clean_word = word.word.strip()
                    if not clean_word:
                        continue

                    tw = TranscriptionWord(
                        word=clean_word,
                        start=word.start,
                        end=word.end,
                        confidence=word.probability,
                        speaker_id=None
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

            # Progreso
            percent = 70 + (i / max(total_segments, 1)) * 25
            yield JobProgress(
                stage="transcribing",
                percent=percent,
                message=f"Segmento {i+1}/{total_segments}",
                current_item=i+1,
                total_items=total_segments
            )

        # Corrección de alineación post-proceso
        yield JobProgress(stage="aligning", percent=95, message="Corrigiendo alineación temporal...")
        transcription_words = await self._correct_alignment(transcription_words, audio_path)

        detected_language = info.language if hasattr(info, 'language') else language
        language_prob = info.language_probability if hasattr(info, 'language_probability') else 1.0

        logger.info(f"Transcripción completa: {len(transcription_segments)} segmentos, "
                    f"{len(transcription_words)} palabras, idioma: {detected_language} ({language_prob:.2f})")

        yield JobProgress(
            stage="completed",
            percent=100,
            message="Transcripción completada con alineación corregida",
            current_item=total_segments,
            total_items=total_segments
        )

        return {
            "segments": transcription_segments,
            "words": transcription_words,
            "language": detected_language,
            "language_probability": language_prob
        }

    async def _correct_alignment(
        self,
        words: List[TranscriptionWord],
        audio_path: Path
    ) -> List[TranscriptionWord]:
        """
        Corrige alineación temporal usando análisis de energía de audio.
        Detecta y corrige desplazamientos sistemáticos.
        """
        if len(words) < 10:
            return words

        try:
            # Extraer audio completo para análisis
            import librosa
            y, sr = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: librosa.load(str(audio_path), sr=16000, mono=True)
            )

            # Calcular energía por frame
            frame_length = 512
            hop_length = 160
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

            # Detectar onsets (inicios de fonemas)
            onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length, units='time')

            # Corregir palabras con baja confianza usando onsets cercanos
            corrected = []
            for word in words:
                if word.confidence >= 0.85:
                    corrected.append(word)
                    continue

                # Buscar onset más cercano al inicio de la palabra
                word_start = word.start
                nearby_onsets = onsets[np.abs(onsets - word_start) < 0.3]

                if len(nearby_onsets) > 0:
                    # Usar onset más cercano como referencia real
                    best_onset = nearby_onsets[np.argmin(np.abs(nearby_onsets - word_start))]
                    offset = best_onset - word_start

                    # Solo corregir si el offset es pequeño (< 200ms) y mejora confianza
                    if abs(offset) < 0.2:
                        corrected.append(TranscriptionWord(
                            word=word.word,
                            start=word.start + offset,
                            end=word.end + offset,
                            confidence=min(word.confidence + 0.1, 1.0),
                            speaker_id=word.speaker_id,
                            is_corrected=True,
                            corrected_text=word.word,
                            time_offset=offset
                        ))
                        continue

                corrected.append(word)

            logger.info(f"Alineación corregida: {sum(1 for w in corrected if w.is_corrected)} palabras ajustadas")
            return corrected

        except Exception as e:
            logger.warning(f"No se pudo corregir alineación (librosa no disponible): {e}")
            return words

    async def verify_segment(
        self,
        audio_path: Path,
        reference_text: str,
        start_time: float,
        end_time: float
    ) -> Dict[str, Any]:
        """Verifica un segmento contra texto de referencia."""
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

        transcribed = " ".join(s.text.strip() for s in segments)

        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, transcribed.lower(), reference_text.lower()).ratio()

        return {
            "transcribed": transcribed,
            "reference": reference_text,
            "similarity": similarity,
            "match": similarity > 0.8,
            "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
        }

    def unload_model(self):
        """Libera memoria del modelo."""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_size = None
            self._device = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()