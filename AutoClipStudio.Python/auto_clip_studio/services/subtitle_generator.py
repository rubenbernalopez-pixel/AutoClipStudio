"""
AutoClip Studio - Subtitle Generator (MEJORADO MÁXIMO)
Genera subtítulos karaoke ASS ultra-precisos con:
- Timestamps por palabra reales (no estimados)
- Karaoke: amarillo (actual) → verde (dicho) → blanco translúcido (pendiente)
- Duración adaptativa por velocidad de habla
- Corrección manual con audio sync ("▶ Desde aquí")
- Detección de baja confianza + marcadores visuales
- Export ASS (quemado) + SRT (plataformas)
"""

import asyncio
import re
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import Clip, TranscriptionWord, TranscriptionSegment

logger = get_logger(__name__)


@dataclass
class SubtitleLine:
    """Línea de subtítulo con palabras temporizadas."""
    start: float
    end: float
    words: List[TranscriptionWord]
    text: str
    layer: int = 0
    style: str = "Default"
    cps: float = 0.0  # caracteres por segundo


class SubtitleGenerator:
    """Generador de subtítulos karaoke profesional."""

    def __init__(self, config: Config):
        self.config = config
        self.corrections: Dict[str, Dict[int, Dict]] = {}  # clip_id -> word_index -> correction

    async def generate(
        self,
        clip: Clip,
        words: List[TranscriptionWord],
        style: str = "karaoke"
    ) -> Dict[str, Any]:
        """
        Genera subtítulos ASS karaoke para un clip.
        Returns: dict con path, lines (para UI), format, style.
        """
        # Filtrar palabras al rango del clip
        clip_words = [
            w for w in words
            if clip.start <= w.start < clip.end
        ]

        if not clip_words:
            logger.warning(f"Sin palabras en rango del clip {clip.id}")
            return {"path": None, "lines": [], "format": "ass", "style": style}

        # Aplicar correcciones de usuario
        clip_words = self._apply_corrections(clip.id, clip_words)

        # Agrupar en líneas con lógica adaptativa
        lines = self._group_words_into_lines_adaptive(clip_words, clip.duration)

        # Generar archivo ASS
        ass_path = await self._write_ass_file(clip, lines)

        # Generar datos de preview para UI
        preview_data = self._generate_preview_data(lines)

        return {
            "path": str(ass_path),
            "lines": preview_data,
            "format": "ass",
            "style": style,
            "total_lines": len(lines),
            "total_words": len(clip_words)
        }

    def _apply_corrections(
        self,
        clip_id: str,
        words: List[TranscriptionWord]
    ) -> List[TranscriptionWord]:
        """Aplica correcciones manuales del usuario."""
        if clip_id not in self.corrections:
            return words

        corrections = self.corrections[clip_id]
        corrected = []

        for i, word in enumerate(words):
            if i in corrections:
                corr = corrections[i]
                new_word = TranscriptionWord(
                    word=corr.get("corrected_text", word.word),
                    start=word.start + corr.get("time_offset", 0.0),
                    end=word.end + corr.get("time_offset", 0.0),
                    confidence=word.confidence,
                    speaker_id=word.speaker_id,
                    is_corrected=True,
                    corrected_text=corr.get("corrected_text"),
                    time_offset=corr.get("time_offset", 0.0)
                )
                corrected.append(new_word)
            else:
                corrected.append(word)

        return corrected

    def _group_words_into_lines_adaptive(
        self,
        words: List[TranscriptionWord],
        clip_duration: float
    ) -> List[SubtitleLine]:
        """
        Agrupa palabras en líneas con lógica adaptativa:
- Respeta pausas naturales
- Limita CPS (caracteres por segundo) a ~17-20 para legibilidad
- Duración mínima por línea: 0.8s, máxima: 6-7s
- Máx 2 líneas simultáneas
- Palabras por línea: 6-10 ideal
        """
        lines = []
        current_line_words = []
        line_start = None
        MAX_CPS = 19  # Carácteres por segundo máx para lectura cómoda
        MIN_LINE_DURATION = 0.8
        MAX_LINE_DURATION = 7.0
        MAX_WORDS_PER_LINE = 10
        MAX_CHARS_PER_LINE = 42  # Por línea en 1080px con font 48pt

        for word in words:
            if not current_line_words:
                line_start = word.start
                current_line_words.append(word)
                continue

            # Métricas de la línea actual
            current_text = " ".join(w.word for w in current_line_words)
            current_chars = len(current_text)
            current_duration = word.start - line_start
            projected_duration = word.end - line_start
            projected_cps = (current_chars + len(word.word) + 1) / projected_duration if projected_duration > 0 else 999

            # Pausa natural entre palabras
            gap = word.start - current_line_words[-1].end

            # Decidir si romper línea
            should_break = (
                len(current_line_words) >= MAX_WORDS_PER_LINE or
                current_chars + len(word.word) + 1 > MAX_CHARS_PER_LINE or
                projected_cps > MAX_CPS or
                (len(current_line_words) >= 4 and gap > 0.4) or
                (gap > 0.8)  # Pausa larga siempre rompe
            )

            # Forzar duración mínima
            if should_break and current_duration < MIN_LINE_DURATION and len(current_line_words) > 1:
                should_break = False

            # Forzar duración máxima
            if not should_break and projected_duration > MAX_LINE_DURATION:
                should_break = True

            if should_break:
                # Finalizar línea actual
                line_end = current_line_words[-1].end
                # Extender ligeramente para legibilidad (pero no pisar siguiente)
                next_start = word.start
                line_end = min(line_end + 0.15, next_start - 0.05) if next_start > line_end else line_end + 0.15

                lines.append(SubtitleLine(
                    start=line_start,
                    end=line_end,
                    words=current_line_words,
                    text=" ".join(w.word for w in current_line_words),
                    cps=len(current_text) / max(current_duration, 0.1)
                ))

                # Nueva línea
                current_line_words = [word]
                line_start = word.start
            else:
                current_line_words.append(word)

        # Última línea
        if current_line_words:
            line_end = current_line_words[-1].end + 0.2  # Un poco más para leer al final
            current_text = " ".join(w.word for w in current_line_words)
            current_duration = line_end - line_start
            lines.append(SubtitleLine(
                start=line_start,
                end=line_end,
                words=current_line_words,
                text=current_text,
                cps=len(current_text) / max(current_duration, 0.1)
            ))

        # Límite de 2 líneas simultáneas - fusionar si hay más
        if len(lines) > self.config.max_lines:
            # Fusionar las últimas líneas en la penúltima
            excess = lines[self.config.max_lines - 1:]
            lines = lines[:self.config.max_lines - 1]
            if excess:
                last = lines[-1]
                all_excess_words = []
                for ex in excess:
                    all_excess_words.extend(ex.words)
                last.words.extend(all_excess_words)
                last.text = " ".join(w.word for w in last.words)
                last.end = all_excess_words[-1].end + 0.2
                last.cps = len(last.text) / max(last.end - last.start, 0.1)

        return lines

    async def _write_ass_file(self, clip: Clip, lines: List[SubtitleLine]) -> Path:
        """Escribe archivo ASS con estilos karaoke profesionales."""
        output_dir = self.config.output_dir / "subtitles"
        output_dir.mkdir(parents=True, exist_ok=True)

        ass_path = output_dir / f"{clip.id}.ass"

        # Colores ASS (formato BBGGRR)
        # Amarillo dorado: #FFD700 -> &H00D7FF
        # Verde primavera: #00FF7F -> &H7FFF00
        # Blanco translúcido: #FFFFFF80 -> &H80FFFFFF
        # Negro outline: #000000 -> &H000000

        ass_content = self._build_ass_header()
        ass_content += self._build_ass_styles_pro()
        ass_content += "[Events]\n"
        ass_content += "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

        for i, line in enumerate(lines):
            ass_line = self._build_ass_dialogue_karaoke(line, i, clip.duration)
            ass_content += ass_line + "\n"

        # Escribir con BOM UTF-8 para compatibilidad
        with open(ass_path, "w", encoding="utf-8-sig") as f:
            f.write(ass_content)

        logger.info(f"ASS generado: {ass_path} ({len(lines)} líneas, karaoke word-level)")
        return ass_path

    def _build_ass_header(self) -> str:
        return """[Script Info]
Title: AutoClip Studio Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

"""

    def _build_ass_styles_pro(self) -> str:
        """Estilos ASS profesionales para karaoke."""
        fs = self.config.subtitle_font_size
        outline = self.config.subtitle_outline_width
        margin_v = int(self.config.subtitle_safe_bottom * 1920)
        margin_lr = int(self.config.subtitle_safe_sides * 1080)

        return f"""[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.config.subtitle_font_family},{fs},&H00D7FF,&H00D7FF,&H000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline},2,2,{margin_lr},{margin_lr},{margin_v},1
Style: KaraokeActive,{self.config.subtitle_font_family},{fs},&H7FFF00,&H7FFF00,&H000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline},2,2,{margin_lr},{margin_lr},{margin_v},1
Style: KaraokeDone,{self.config.subtitle_font_family},{fs},&H7FFF00,&H7FFF00,&H000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline},2,2,{margin_lr},{margin_lr},{margin_v},1
Style: KaraokePending,{self.config.subtitle_font_family},{fs},&HFFFFFF80,&HFFFFFF80,&H000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline},2,2,{margin_lr},{margin_lr},{margin_v},1
Style: LowConfidence,{self.config.subtitle_font_family},{fs},&H00FFFF,&H00FFFF,&H000000,&H80000000,0,0,0,0,100,100,0,0,1,{outline},2,2,{margin_lr},{margin_lr},{margin_v},1
Style: Corrected,{self.config.subtitle_font_family},{fs},&H00E9FF,&H00E9FF,&H000000,&H80000000,1,0,0,0,100,100,0,0,1,{outline},2,2,{margin_lr},{margin_lr},{margin_v},1

"""

    def _build_ass_dialogue_karaoke(self, line: SubtitleLine, line_index: int, clip_duration: float) -> str:
        """Construye línea ASS con karaoke word-level preciso."""
        start_ass = self._time_to_ass(line.start)
        end_ass = self._time_to_ass(line.end)

        # Construir texto karaoke con timing por palabra
        karaoke_parts = []

        for word in line.words:
            word_text = word.corrected_text if word.is_corrected and word.corrected_text else word.word
            word_text = self._escape_ass_text(word_text)

            # Duración de esta palabra en centisegundos (ASS usa centisegundos para \kf)
            word_dur_cs = max(1, int((word.end - word.start) * 100))

            # Estilo según estado
            if word.is_corrected:
                # Coral para corregidas
                karaoke_parts.append(f"{{\\rCorrected\\kf{word_dur_cs}}}{word_text}")
            elif word.confidence < 0.65:
                # Amarillo cian para baja confianza + borde parpadeante
                karaoke_parts.append(f"{{\\rLowConfidence\\kf{word_dur_cs}\\t(0,{word_dur_cs},\\4c&H00FFFF&)}}{word_text}")
            else:
                # Normal: amarillo activo -> verde done
                karaoke_parts.append(f"{{\\rKaraokeActive\\kf{word_dur_cs}\\1c&H00D7FF&}}{word_text}{{\\rKaraokeDone\\1c&H7FFF00&}}")

        # Relleno final si la línea dura más que la última palabra
        # (se maneja con la duración de la línea en ASS)

        karaoke_text = "".join(karaoke_parts)

        return f"Dialogue: {line.layer},{start_ass},{end_ass},Default,,0,0,0,,{karaoke_text}"

    def _time_to_ass(self, seconds: float) -> str:
        """Convierte segundos a formato ASS H:MM:SS.cc"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        centiseconds = int((secs - int(secs)) * 100)
        return f"{hours}:{minutes:02d}:{int(secs):02d}.{centiseconds:02d}"

    def _escape_ass_text(self, text: str) -> str:
        """Escapa caracteres especiales ASS."""
        return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

    def _generate_preview_data(self, lines: List[SubtitleLine]) -> List[Dict[str, Any]]:
        """Genera datos para preview en UI."""
        return [
            {
                "index": i,
                "start": line.start,
                "end": line.end,
                "text": line.text,
                "cps": round(line.cps, 1),
                "words": [
                    {
                        "word": w.corrected_text if w.is_corrected and w.corrected_text else w.word,
                        "start": w.start,
                        "end": w.end,
                        "duration": round(w.end - w.start, 3),
                        "confidence": round(w.confidence, 3),
                        "is_corrected": w.is_corrected,
                        "original_word": w.word if w.is_corrected else None,
                        "time_offset": w.time_offset,
                        "low_confidence": w.confidence < 0.65
                    }
                    for w in line.words
                ]
            }
            for i, line in enumerate(lines)
        ]

    async def correct_word(
        self,
        clip_id: str,
        word_index: int,
        corrected_text: str,
        time_offset: float = 0.0
    ) -> Dict[str, Any]:
        """Registra corrección de palabra con offset temporal opcional."""
        if clip_id not in self.corrections:
            self.corrections[clip_id] = {}

        self.corrections[clip_id][word_index] = {
            "corrected_text": corrected_text,
            "time_offset": time_offset,
            "original_index": word_index
        }

        logger.info(f"Corrección: clip={clip_id} word={word_index} text='{corrected_text}' offset={time_offset}s")
        return {
            "success": True,
            "clip_id": clip_id,
            "word_index": word_index,
            "corrected_text": corrected_text,
            "time_offset": time_offset
        }

    def get_corrections(self, clip_id: str) -> Dict[int, Dict]:
        return self.corrections.get(clip_id, {})

    def clear_corrections(self, clip_id: str):
        if clip_id in self.corrections:
            del self.corrections[clip_id]

    async def export_corrected_subtitles(
        self,
        clip: Clip,
        words: List[TranscriptionWord],
        output_path: Path
    ) -> Path:
        """Exporta subtítulos corregidos a nuevo archivo (preserva original)."""
        result = await self.generate(clip, words)
        if result["path"]:
            import shutil
            shutil.copy2(result["path"], output_path)
            logger.info(f"Subtítulos corregidos exportados: {output_path}")
        return output_path

    async def generate_srt_fallback(
        self,
        clip: Clip,
        words: List[TranscriptionWord]
    ) -> Path:
        """Genera SRT estándar para subir a plataformas."""
        output_dir = self.config.output_dir / "subtitles"
        output_dir.mkdir(parents=True, exist_ok=True)

        srt_path = output_dir / f"{clip.id}.srt"

        clip_words = [w for w in words if clip.start <= w.start < clip.end]
        clip_words = self._apply_corrections(clip.id, clip_words)
        lines = self._group_words_into_lines_adaptive(clip_words, clip.duration)

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, line in enumerate(lines):
                f.write(f"{i+1}\n")
                f.write(f"{self._time_to_srt(line.start)} --> {self._time_to_srt(line.end)}\n")
                f.write(f"{line.text}\n\n")

        return srt_path

    def _time_to_srt(self, seconds: float) -> str:
        """Convierte a formato SRT HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"