"""
AutoClip Studio - Subtitle Generator
Generates karaoke-style ASS subtitles with word-level highlighting (gold→green).
Supports correction workflow with audio playback for verification.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import Clip, TranscriptionWord, TranscriptionSegment

logger = get_logger(__name__)


@dataclass
class SubtitleLine:
    """A single subtitle line with word-level timing."""
    start: float
    end: float
    words: List[TranscriptionWord]
    text: str
    layer: int = 0
    style: str = "Default"


class SubtitleGenerator:
    """Generates and manages karaoke-style subtitles."""

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
        Generate karaoke-style ASS subtitles for a clip.
        Returns subtitle file path and metadata.
        """
        # Filter words to clip time range
        clip_words = [
            w for w in words
            if clip.start <= w.start < clip.end
        ]

        if not clip_words:
            logger.warning(f"No words in clip time range for {clip.id}")
            return {"path": None, "lines": []}

        # Apply corrections
        clip_words = self._apply_corrections(clip.id, clip_words)

        # Group words into lines
        lines = self._group_words_into_lines(clip_words)

        # Generate ASS file
        ass_path = await self._write_ass_file(clip, lines)

        # Generate preview data for UI
        preview_data = self._generate_preview_data(lines)

        return {
            "path": str(ass_path),
            "lines": preview_data,
            "format": "ass",
            "style": style
        }

    def _apply_corrections(
        self,
        clip_id: str,
        words: List[TranscriptionWord]
    ) -> List[TranscriptionWord]:
        """Apply user corrections to words."""
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

    def _group_words_into_lines(
        self,
        words: List[TranscriptionWord]
    ) -> List[SubtitleLine]:
        """Group words into subtitle lines based on timing and count."""
        lines = []
        current_line_words = []
        line_start = None

        for word in words:
            if not current_line_words:
                line_start = word.start
                current_line_words.append(word)
                continue

            # Check if we should break line
            time_gap = word.start - current_line_words[-1].end
            word_count = len(current_line_words)

            should_break = (
                word_count >= self.config.max_words_per_line or
                time_gap > self.config.subtitle_line_duration or
                (word_count >= 3 and time_gap > 0.3)
            )

            if should_break:
                # Finalize current line
                line_end = current_line_words[-1].end
                lines.append(SubtitleLine(
                    start=line_start,
                    end=line_end + 0.15,  # Slightly longer for readability
                    words=current_line_words,
                    text=" ".join(w.word for w in current_line_words)
                ))
                current_line_words = [word]
                line_start = word.start
            else:
                current_line_words.append(word)

        # Don't forget last line
        if current_line_words:
            line_end = current_line_words[-1].end
            lines.append(SubtitleLine(
                start=line_start,
                end=line_end + 0.15,
                words=current_line_words,
                text=" ".join(w.word for w in current_line_words)
            ))

        # Limit to max_lines
        if len(lines) > self.config.max_lines:
            # Merge excess lines into the last one
            excess = lines[self.config.max_lines - 1:]
            lines = lines[:self.config.max_lines - 1]
            if excess:
                last_line = lines[-1]
                all_excess_words = []
                for ex in excess:
                    all_excess_words.extend(ex.words)
                last_line.words.extend(all_excess_words)
                last_line.text = " ".join(w.word for w in last_line.words)
                last_line.end = all_excess_words[-1].end + 0.15

        return lines

    async def _write_ass_file(self, clip: Clip, lines: List[SubtitleLine]) -> Path:
        """Write ASS subtitle file with karaoke styling."""
        output_dir = self.config.output_dir / "subtitles"
        output_dir.mkdir(parents=True, exist_ok=True)

        ass_path = output_dir / f"{clip.id}.ass"

        # ASS header
        ass_content = self._build_ass_header()

        # Styles
        ass_content += self._build_ass_styles()

        # Events
        ass_content += "[Events]\n"
        ass_content += "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

        for i, line in enumerate(lines):
            ass_line = self._build_ass_dialogue(line, i)
            ass_content += ass_line + "\n"

        # Write file
        with open(ass_path, "w", encoding="utf-8-sig") as f:
            f.write(ass_content)

        logger.info(f"Generated ASS subtitles: {ass_path} ({len(lines)} lines)")
        return ass_path

    def _build_ass_header(self) -> str:
        """Build ASS file header."""
        return """[Script Info]
Title: AutoClip Studio Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

"""

    def _build_ass_styles(self) -> str:
        """Build ASS styles for karaoke subtitles."""
        # Color format in ASS: {\\c&HBBGGRR&} (Blue-Green-Red in hex)
        # Gold: #FFD700 -> &H00D7FF
        # Green: #00FF7F -> &H7FFF00
        # White: #FFFFFF -> &HFFFFFF
        # Black outline: #000000 -> &H000000

        return f"""[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Inter,{self.config.subtitle_font_size},&H00D7FF,&H00D7FF,&H000000,&H80000000,0,0,0,0,100,100,0,0,1,{self.config.subtitle_outline_width},2,2,{int(self.config.subtitle_safe_sides*1080)},{int(self.config.subtitle_safe_sides*1080)},{int(self.config.subtitle_safe_bottom*1920)},1
Style: Karaoke,Inter,{self.config.subtitle_font_size},&H7FFF00,&H7FFF00,&H000000,&H80000000,0,0,0,0,100,100,0,0,1,{self.config.subtitle_outline_width},2,2,{int(self.config.subtitle_safe_sides*1080)},{int(self.config.subtitle_safe_sides*1080)},{int(self.config.subtitle_safe_bottom*1920)},1
Style: Pending,Inter,{self.config.subtitle_font_size},&HFFFFFF80,&HFFFFFF80,&H000000,&H80000000,0,0,0,0,100,100,0,0,1,{self.config.subtitle_outline_width},2,2,{int(self.config.subtitle_safe_sides*1080)},{int(self.config.subtitle_safe_sides*1080)},{int(self.config.subtitle_safe_bottom*1920)},1

"""

    def _build_ass_dialogue(self, line: SubtitleLine, line_index: int) -> str:
        """Build a single ASS dialogue line with karaoke timing."""
        # Convert time to ASS format (H:MM:SS.cc)
        start_ass = self._time_to_ass(line.start)
        end_ass = self._time_to_ass(line.end)

        # Build karaoke text with inline timing
        karaoke_text = self._build_karaoke_text(line.words, line.start)

        return f"Dialogue: {line.layer},{start_ass},{end_ass},Default,,0,0,0,,{karaoke_text}"

    def _time_to_ass(self, seconds: float) -> str:
        """Convert seconds to ASS time format H:MM:SS.cc"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        centiseconds = int((secs - int(secs)) * 100)
        return f"{hours}:{minutes:02d}:{int(secs):02d}.{centiseconds:02d}"

    def _build_karaoke_text(self, words: List[TranscriptionWord], line_start: float) -> str:
        """Build karaoke text with word-level timing."""
        parts = []

        for i, word in enumerate(words):
            word_text = word.corrected_text if word.is_corrected and word.corrected_text else word.word
            word_text = self._escape_ass_text(word_text)

            # Calculate relative timing within line
            rel_start = max(0, word.start - line_start)
            rel_end = max(0, word.end - line_start)
            duration_cs = int((rel_end - rel_start) * 100)  # centiseconds

            if duration_cs < 1:
                duration_cs = 1

            # Karaoke tag: {\kf<duration>} for fill effect
            # Gold color for active word, green for done
            parts.append(f"{{\\kf{duration_cs}\\1c&H00D7FF&}}{word_text}{{\\1c&H7FFF00&}}")

        # Add remaining time as pending (transparent white)
        # This is handled by the line duration extending beyond last word

        return "".join(parts)

    def _escape_ass_text(self, text: str) -> str:
        """Escape special characters for ASS format."""
        return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

    def _generate_preview_data(self, lines: List[SubtitleLine]) -> List[Dict[str, Any]]:
        """Generate preview data for UI."""
        return [
            {
                "index": i,
                "start": line.start,
                "end": line.end,
                "text": line.text,
                "words": [
                    {
                        "word": w.corrected_text if w.is_corrected and w.corrected_text else w.word,
                        "start": w.start,
                        "end": w.end,
                        "confidence": w.confidence,
                        "is_corrected": w.is_corrected,
                        "original_word": w.word if w.is_corrected else None
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
        """Record a word correction."""
        if clip_id not in self.corrections:
            self.corrections[clip_id] = {}

        self.corrections[clip_id][word_index] = {
            "corrected_text": corrected_text,
            "time_offset": time_offset,
            "original_index": word_index
        }

        logger.info(f"Correction recorded for clip {clip_id}, word {word_index}: '{corrected_text}' (offset: {time_offset}s)")

        return {
            "success": True,
            "clip_id": clip_id,
            "word_index": word_index,
            "corrected_text": corrected_text,
            "time_offset": time_offset
        }

    def get_corrections(self, clip_id: str) -> Dict[int, Dict]:
        """Get all corrections for a clip."""
        return self.corrections.get(clip_id, {})

    def clear_corrections(self, clip_id: str):
        """Clear corrections for a clip."""
        if clip_id in self.corrections:
            del self.corrections[clip_id]

    async def export_corrected_subtitles(
        self,
        clip: Clip,
        words: List[TranscriptionWord],
        output_path: Path
    ) -> Path:
        """Export corrected subtitles to a new file (preserving original)."""
        # Generate with corrections applied
        result = await self.generate(clip, words)

        if result["path"]:
            # Copy to new location
            import shutil
            shutil.copy2(result["path"], output_path)
            logger.info(f"Exported corrected subtitles to {output_path}")

        return output_path

    async def generate_srt_fallback(
        self,
        clip: Clip,
        words: List[TranscriptionWord]
    ) -> Path:
        """Generate SRT format as fallback."""
        output_dir = self.config.output_dir / "subtitles"
        output_dir.mkdir(parents=True, exist_ok=True)

        srt_path = output_dir / f"{clip.id}.srt"

        clip_words = [w for w in words if clip.start <= w.start < clip.end]
        clip_words = self._apply_corrections(clip.id, clip_words)
        lines = self._group_words_into_lines(clip_words)

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, line in enumerate(lines):
                f.write(f"{i+1}\n")
                f.write(f"{self._time_to_srt(line.start)} --> {self._time_to_srt(line.end)}\n")
                f.write(f"{line.text}\n\n")

        return srt_path

    def _time_to_srt(self, seconds: float) -> str:
        """Convert seconds to SRT time format HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"