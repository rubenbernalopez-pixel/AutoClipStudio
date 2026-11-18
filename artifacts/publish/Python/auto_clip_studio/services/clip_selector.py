"""
AutoClip Studio - Clip Selector
Intelligent selection of podcast clips based on conversation analysis.
Implements the selection criteria from the requirements:
- Concrete questions with answers, confessions, contradictions, decisions with consequences, anecdotes with punchlines
- Proper boundaries: start understood from feed entry, end after answer/punchline before next topic/promo
- Avoid near-duplicates, prefer quality over quantity
"""

import asyncio
import re
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import JobProgress, Clip, TranscriptionSegment, TranscriptionWord

logger = get_logger(__name__)


@dataclass
class ConversationUnit:
    """A coherent unit of conversation (question-answer, anecdote, etc.)."""
    start: float
    end: float
    segments: List[TranscriptionSegment]
    words: List[TranscriptionWord]
    unit_type: str  # "qa", "anecdote", "opinion", "confession", "contradiction", "decision"
    hook_text: str
    development_text: str
    closing_text: str
    speakers: List[int]
    confidence: float
    has_question: bool = False
    has_answer: bool = False
    is_promo: bool = False
    promo_score: float = 0.0


class ClipSelector:
    """Intelligent clip selection based on conversation analysis."""

    def __init__(self, config: Config):
        self.config = config
        self.promo_patterns = self._load_promo_patterns()
        self.question_patterns = self._load_question_patterns()
        self.hook_patterns = self._load_hook_patterns()
        self.closing_patterns = self._load_closing_patterns()

    def _load_promo_patterns(self) -> List[re.Pattern]:
        """Patterns that indicate promotional/sponsored content."""
        patterns = [
            r"(gracias a|patrocinad[oa]|sponsor|colaborad[oa])",
            r"(suscr[íi]bete|sígueme|follow|dale al like)",
            r"(c[oó]digo|descuento|oferta|promoci[oó]n)",
            r"(enlace en la descripci[oó]n|link en bio)",
            r"(nuestro patrocinador|gracias a nuestro)",
            r"(antes de seguir|para terminar|para cerrar).*?(patrocin|sponsor)",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _load_question_patterns(self) -> List[re.Pattern]:
        """Patterns that indicate questions."""
        patterns = [
            r"^\s*[¿?].*[?¿]\s*$",
            r"^(por qu[ée]|c[oó]mo|qu[ée]|cu[aá]ndo|d[oó]nde|qui[ée]n|cu[aá]l)\b",
            r"\?$",
            r"^.*\?\s*$",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _load_hook_patterns(self) -> List[re.Pattern]:
        """Patterns that indicate strong hooks (opening lines)."""
        patterns = [
            r"^(nunca|jamás|siempre|todo el mundo|nadie)\b",
            r"^(la verdad|honestamente|sinceramente|te voy a contar)",
            r"^(lo que pasa es que|el problema es que|la clave est[áa] en)",
            r"^(me arrepiento|me equivoqué|fue un error|no deber[íi]a)",
            r"^(cerré|abandoné|deje|perdí|gané|cambió todo)",
            r"^(¿por qu[ée]|por qu[ée]).*(cerrar|dejar|abandonar|fallar|perder)",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _load_closing_patterns(self) -> List[re.Pattern]:
        """Patterns that indicate good closing lines."""
        patterns = [
            r"(y as[íi] (fue|cambi[oó]|termin[oó]|pas[oó])|.+y ya est[áa]|.+y punto\.?$)",
            r"(al final|al final de cuentas|la moraleja|la lecci[oó]n|lo importante)",
            r"(y ahora|ahora bien|as[íi] que|por eso|en definitiva)",
            r"(\.\.\.\s*$|y entonces\s*$|y despu[eé]s\s*$)",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    async def select_clips(
        self,
        transcription: Dict[str, Any],
        video_duration: float,
        topic: Optional[str] = None,
        max_clips: int = 3,
        max_duration: int = 75
    ) -> AsyncGenerator[JobProgress, List[Clip]]:
        """
        Select best clips from transcription.
        Yields progress, returns selected clips.
        """
        segments = transcription.get("segments", [])
        words = transcription.get("words", [])

        if not segments:
            yield JobProgress(stage="completed", percent=100, message="Sin contenido para analizar")
            return []

        yield JobProgress(stage="analyzing", percent=10, message="Analizando conversación...")

        # Convert to model objects
        trans_segments = [TranscriptionSegment.from_dict(s) for s in segments]
        trans_words = [TranscriptionWord.from_dict(w) for w in words]

        # Step 1: Detect conversation units
        units = await self._detect_conversation_units(trans_segments, trans_words, video_duration)

        yield JobProgress(stage="scoring", percent=40, message="Evaluando unidades...")

        # Step 2: Score each unit
        scored_units = await self._score_units(units, topic, trans_words)

        yield JobProgress(stage="filtering", percent=60, message="Filtrando mejores opciones...")

        # Step 3: Filter and select best clips
        selected_clips = await self._select_best_clips(scored_units, max_clips, max_duration, trans_words)

        yield JobProgress(stage="refining", percent=80, message="Refinando cortes...")

        # Step 4: Refine boundaries and generate metadata
        final_clips = await self._refine_clips(selected_clips, trans_segments, trans_words, video_duration)

        yield JobProgress(
            stage="completed",
            percent=100,
            message=f"{len(final_clips)} clips seleccionados",
            current_item=len(final_clips),
            total_items=max_clips
        )

        return final_clips

    async def _detect_conversation_units(
        self,
        segments: List[TranscriptionSegment],
        words: List[TranscriptionWord],
        video_duration: float
    ) -> List[ConversationUnit]:
        """Detect coherent conversation units from transcription."""
        units = []
        current_unit_segments = []
        current_unit_words = []
        unit_start = 0.0

        for i, segment in enumerate(segments):
            current_unit_segments.append(segment)
            current_unit_words.extend(segment.words)

            # Check if this segment ends a conversation unit
            is_unit_end = self._is_unit_boundary(segment, segments, i)

            # Also check for promo content
            is_promo = self._is_promo_segment(segment)

            if is_unit_end or is_promo or i == len(segments) - 1:
                unit_end = segment.end

                if current_unit_segments:
                    unit = self._create_conversation_unit(
                        current_unit_segments, current_unit_words,
                        unit_start, unit_end, is_promo
                    )
                    if unit and unit.duration >= self.config.min_clip_duration:
                        units.append(unit)

                # Start new unit
                current_unit_segments = []
                current_unit_words = []
                unit_start = unit_end

        return units

    def _is_unit_boundary(
        self,
        segment: TranscriptionSegment,
        all_segments: List[TranscriptionSegment],
        index: int
    ) -> bool:
        """Determine if a segment ends a conversation unit."""
        text = segment.text.strip().lower()

        # Long pause after segment (check next segment start)
        if index + 1 < len(all_segments):
            pause = all_segments[index + 1].start - segment.end
            if pause > 2.0:  # 2+ second pause
                return True

        # Closing patterns
        for pattern in self.closing_patterns:
            if pattern.search(text):
                return True

        # Segment is very long (likely end of thought)
        if segment.end - segment.start > 15.0:
            return True

        return False

    def _is_promo_segment(self, segment: TranscriptionSegment) -> bool:
        """Check if segment is promotional content."""
        text = segment.text.lower()
        for pattern in self.promo_patterns:
            if pattern.search(text):
                return True
        return False

    def _create_conversation_unit(
        self,
        segments: List[TranscriptionSegment],
        words: List[TranscriptionWord],
        start: float,
        end: float,
        is_promo: bool
    ) -> Optional[ConversationUnit]:
        """Create a conversation unit from segments."""
        if not segments:
            return None

        full_text = " ".join(s.text for s in segments).strip()
        if len(full_text) < 20:  # Too short
            return None

        # Detect unit type
        unit_type, hook, development, closing = self._classify_unit(segments)

        # Get speakers
        speakers = list(set(w.speaker_id for w in words if w.speaker_id is not None))

        # Calculate confidence
        confidence = sum(s.confidence for s in segments) / len(segments)

        return ConversationUnit(
            start=start,
            end=end,
            segments=segments,
            words=words,
            unit_type=unit_type,
            hook_text=hook,
            development_text=development,
            closing_text=closing,
            speakers=speakers,
            confidence=confidence,
            has_question=self._has_question(segments),
            has_answer=self._has_answer(segments),
            is_promo=is_promo,
            promo_score=1.0 if is_promo else 0.0
        )

    def _classify_unit(
        self,
        segments: List[TranscriptionSegment]
    ) -> Tuple[str, str, str, str]:
        """Classify conversation unit type and extract hook/development/closing."""
        full_text = " ".join(s.text for s in segments)
        first_segment = segments[0].text if segments else ""
        last_segment = segments[-1].text if segments else ""

        # Check for question-answer pattern
        has_question = self._has_question(segments)
        has_answer = self._has_answer(segments)

        if has_question and has_answer:
            unit_type = "qa"
            # Find question and answer
            q_idx = next((i for i, s in enumerate(segments) if self._is_question(s.text)), 0)
            hook = segments[q_idx].text if q_idx < len(segments) else first_segment
            development = " ".join(s.text for s in segments[q_idx+1:-1]) if len(segments) > q_idx+2 else ""
            closing = last_segment
        elif self._is_anecdote(segments):
            unit_type = "anecdote"
            hook = first_segment
            development = " ".join(s.text for s in segments[1:-1]) if len(segments) > 2 else ""
            closing = last_segment
        elif self._is_confession(segments):
            unit_type = "confession"
            hook = first_segment
            development = " ".join(s.text for s in segments[1:-1]) if len(segments) > 2 else ""
            closing = last_segment
        elif self._is_contradiction(segments):
            unit_type = "contradiction"
            hook = first_segment
            development = " ".join(s.text for s in segments[1:-1]) if len(segments) > 2 else ""
            closing = last_segment
        elif self._is_decision(segments):
            unit_type = "decision"
            hook = first_segment
            development = " ".join(s.text for s in segments[1:-1]) if len(segments) > 2 else ""
            closing = last_segment
        else:
            unit_type = "opinion"
            hook = first_segment
            development = " ".join(s.text for s in segments[1:-1]) if len(segments) > 2 else ""
            closing = last_segment

        return unit_type, hook.strip(), development.strip(), closing.strip()

    def _has_question(self, segments: List[TranscriptionSegment]) -> bool:
        return any(self._is_question(s.text) for s in segments)

    def _has_answer(self, segments: List[TranscriptionSegment]) -> bool:
        # Answer typically follows a question, longer, more explanatory
        for i, s in enumerate(segments):
            if self._is_question(s.text) and i + 1 < len(segments):
                next_seg = segments[i + 1]
                if len(next_seg.text) > len(s.text) * 1.5:
                    return True
        return False

    def _is_question(self, text: str) -> bool:
        text = text.strip()
        for pattern in self.question_patterns:
            if pattern.search(text):
                return True
        return False

    def _is_anecdote(self, segments: List[TranscriptionSegment]) -> bool:
        text = " ".join(s.text for s in segments).lower()
        anecdote_markers = [
            "me acuerdo", "recuerdo", "una vez", "había una vez",
            "me pasó", "me sucedió", "anécdota", "historia"
        ]
        return any(m in text for m in anecdote_markers)

    def _is_confession(self, segments: List[TranscriptionSegment]) -> bool:
        text = " ".join(s.text for s in segments).lower()
        confession_markers = [
            "me arrepiento", "fue un error", "me equivoqué",
            "no debería", "debí haber", "lo peor fue"
        ]
        return any(m in text for m in confession_markers)

    def _is_contradiction(self, segments: List[TranscriptionSegment]) -> bool:
        text = " ".join(s.text for s in segments).lower()
        contradiction_markers = [
            "pero en realidad", "la verdad es que", "en realidad",
            "contradice", "lo contrario", "no es así"
        ]
        return any(m in text for m in contradiction_markers)

    def _is_decision(self, segments: List[TranscriptionSegment]) -> bool:
        text = " ".join(s.text for s in segments).lower()
        decision_markers = [
            "decidí", "decidimos", "elegí", "opté por", "me lancé",
            "cerré", "abandoné", "dejé", "cambié de"
        ]
        return any(m in text for m in decision_markers)

    async def _score_units(
        self,
        units: List[ConversationUnit],
        topic: Optional[str],
        all_words: List[TranscriptionWord]
    ) -> List[Tuple[ConversationUnit, float, Dict[str, float]]]:
        """Score each conversation unit for clip potential."""
        scored = []

        for unit in units:
            if unit.is_promo:
                continue

            # Calculate component scores
            hook_score = self._score_hook(unit)
            development_score = self._score_development(unit)
            closing_score = self._score_closing(unit)
            clarity_score = self._score_clarity(unit, all_words)

            # Topic relevance bonus
            topic_bonus = 0.0
            if topic:
                topic_bonus = self._calculate_topic_relevance(unit, topic)

            # Weighted total
            total_score = (
                hook_score * self.config.hook_weight +
                development_score * self.config.development_weight +
                closing_score * self.config.closing_weight +
                clarity_score * self.config.clarity_weight +
                topic_bonus * 0.1  # Small bonus
            )

            breakdown = {
                "hook": hook_score,
                "development": development_score,
                "closing": closing_score,
                "clarity": clarity_score,
                "topic_relevance": topic_bonus
            }

            scored.append((unit, total_score, breakdown))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _score_hook(self, unit: ConversationUnit) -> float:
        """Score the hook (opening) strength."""
        score = 0.5  # Base

        text = unit.hook_text.lower()

        # Strong opening patterns
        for pattern in self.hook_patterns:
            if pattern.search(text):
                score += 0.3
                break

        # Question as hook
        if unit.has_question:
            score += 0.2

        # Specific names/entities mentioned early
        if re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b", unit.hook_text):
            score += 0.1

        # Length check - not too short, not too long
        hook_words = len(unit.hook_text.split())
        if 5 <= hook_words <= 25:
            score += 0.1

        return min(score, 1.0)

    def _score_development(self, unit: ConversationUnit) -> float:
        """Score the development (middle) quality."""
        if not unit.development_text:
            return 0.3

        score = 0.5
        text = unit.development_text.lower()
        words = text.split()

        # Good length
        if 30 <= len(words) <= 150:
            score += 0.2
        elif len(words) > 150:
            score += 0.1

        # Explanatory language
        explanatory = ["porque", "ya que", "puesto que", "la razón", "el motivo",
                       "explico", "te cuento", "pasó que", "sucedió que"]
        if any(e in text for e in explanatory):
            score += 0.15

        # Concrete details (numbers, names, specific events)
        if re.search(r"\b\d+\b", text):  # Numbers
            score += 0.1
        if re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b", text):  # Proper names
            score += 0.1

        return min(score, 1.0)

    def _score_closing(self, unit: ConversationUnit) -> float:
        """Score the closing (ending) strength."""
        if not unit.closing_text:
            return 0.2

        score = 0.5
        text = unit.closing_text.lower()

        # Strong closing patterns
        for pattern in self.closing_patterns:
            if pattern.search(text):
                score += 0.3
                break

        # Conclusive language
        conclusive = ["así que", "por eso", "en definitiva", "al final",
                      "la conclusión", "moraleja", "lección"]
        if any(c in text for c in conclusive):
            score += 0.15

        # Not trailing off
        if not text.endswith(("...", "y entonces", "y después", "bueno,")):
            score += 0.1

        return min(score, 1.0)

    def _score_clarity(self, unit: ConversationUnit, all_words: List[TranscriptionWord]) -> float:
        """Score clarity based on transcription confidence and speaker separation."""
        if not unit.words:
            return 0.5

        # Average confidence of words in this unit
        word_confidences = [w.confidence for w in unit.words if w.confidence > 0]
        if not word_confidences:
            return 0.5

        avg_confidence = sum(word_confidences) / len(word_confidences)

        # Penalize low confidence words
        low_conf_count = sum(1 for c in word_confidences if c < 0.7)
        low_conf_ratio = low_conf_count / len(word_confidences)

        # Speaker separation (prefer single speaker or clear alternation)
        speaker_changes = 0
        prev_speaker = None
        for w in unit.words:
            if w.speaker_id is not None and w.speaker_id != prev_speaker:
                speaker_changes += 1
                prev_speaker = w.speaker_id

        # Good if 1-2 speakers with clear turns
        speaker_score = 1.0
        if speaker_changes > 10:  # Too fragmented
            speaker_score = 0.7
        elif speaker_changes == 0:  # Single speaker
            speaker_score = 1.0

        clarity = avg_confidence * 0.7 + (1 - low_conf_ratio) * 0.2 + speaker_score * 0.1
        return min(clarity, 1.0)

    def _calculate_topic_relevance(self, unit: ConversationUnit, topic: str) -> float:
        """Calculate relevance to user-specified topic."""
        topic_lower = topic.lower()
        unit_text = (unit.hook_text + " " + unit.development_text + " " + unit.closing_text).lower()

        # Simple keyword matching
        topic_words = set(topic_lower.split())
        unit_words = set(unit_text.split())

        overlap = len(topic_words & unit_words)
        if not topic_words:
            return 0.0

        return min(overlap / len(topic_words), 1.0)

    async def _select_best_clips(
        self,
        scored_units: List[Tuple[ConversationUnit, float, Dict[str, float]]],
        max_clips: int,
        max_duration: int,
        all_words: List[TranscriptionWord]
    ) -> List[Clip]:
        """Select best non-overlapping clips."""
        selected = []
        used_ranges = []  # (start, end) of selected clips

        for unit, score, breakdown in scored_units:
            if len(selected) >= max_clips:
                break

            if score < self.config.min_score_threshold:
                continue

            # Check overlap with already selected
            overlaps = False
            for used_start, used_end in used_ranges:
                overlap_start = max(unit.start, used_start)
                overlap_end = min(unit.end, used_end)
                if overlap_end - overlap_start > 5.0:  # More than 5s overlap
                    overlaps = True
                    break

            if overlaps:
                continue

            # Check duration
            duration = unit.end - unit.start
            if duration < self.config.min_clip_duration:
                continue
            if duration > max_duration:
                # Try to trim to max_duration keeping best parts
                unit = self._trim_unit(unit, max_duration)
                duration = unit.end - unit.start

            # Create clip
            clip = Clip(
                start=unit.start,
                end=unit.end,
                duration=duration,
                hook=unit.hook_text[:200],
                development=unit.development_text[:500],
                closing=unit.closing_text[:200],
                score=score,
                score_breakdown=breakdown,
                score_explanation=self._generate_score_explanation(breakdown, unit),
                transcription_segments=unit.segments,
                transcription_words=unit.words
            )

            # Generate social copy and hashtags
            clip.social_copy = self._generate_social_copy(clip, unit)
            clip.hashtags = self._generate_hashtags(clip, unit)

            selected.append(clip)
            used_ranges.append((unit.start, unit.end))

        return selected

    def _trim_unit(self, unit: ConversationUnit, max_duration: float) -> ConversationUnit:
        """Trim unit to max_duration keeping the best parts."""
        # Prefer keeping hook and closing, trim development
        current_duration = unit.end - unit.start
        if current_duration <= max_duration:
            return unit

        excess = current_duration - max_duration
        # Trim from development proportionally
        dev_duration = sum(s.end - s.start for s in unit.segments[1:-1]) if len(unit.segments) > 2 else 0
        if dev_duration > excess:
            # We can trim development
            # For simplicity, just reduce end time
            new_end = unit.end - excess
            # Adjust segments
            new_segments = []
            new_words = []
            for seg in unit.segments:
                if seg.start >= new_end:
                    break
                new_seg = seg
                if seg.end > new_end:
                    # Truncate segment
                    from auto_clip_studio.models.job import TranscriptionSegment
                    new_seg = TranscriptionSegment(
                        id=seg.id,
                        start=seg.start,
                        end=new_end,
                        text=seg.text,
                        words=[w for w in seg.words if w.start < new_end],
                        speaker_id=seg.speaker_id,
                        confidence=seg.confidence
                    )
                new_segments.append(new_seg)
                new_words.extend(new_seg.words)

            unit.segments = new_segments
            unit.words = new_words
            unit.end = new_end
            # Recalculate development text
            unit.development_text = " ".join(s.text for s in unit.segments[1:-1]) if len(unit.segments) > 2 else ""

        return unit

    def _generate_score_explanation(
        self,
        breakdown: Dict[str, float],
        unit: ConversationUnit
    ) -> str:
        """Generate human-readable score explanation."""
        parts = []
        if breakdown["hook"] > 0.7:
            parts.append("gancho muy fuerte")
        elif breakdown["hook"] > 0.5:
            parts.append("buen gancho")

        if breakdown["development"] > 0.7:
            parts.append("desarrollo rico en detalles")
        elif breakdown["development"] > 0.5:
            parts.append("desarrollo adecuado")

        if breakdown["closing"] > 0.7:
            parts.append("cierre contundente")
        elif breakdown["closing"] > 0.5:
            parts.append("cierre claro")

        if breakdown["clarity"] < 0.6:
            parts.append("algunas palabras con baja confianza")

        if breakdown.get("topic_relevance", 0) > 0.5:
            parts.append("muy relevante al tema pedido")

        if not parts:
            return "Clip con potencial editorial moderado"

        return "Clip seleccionado por: " + ", ".join(parts) + "."

    def _generate_social_copy(self, clip: Clip, unit: ConversationUnit) -> str:
        """Generate social media copy for the clip."""
        # Use hook as the main text, add context
        hook = clip.hook.strip()
        if len(hook) > 100:
            hook = hook[:97] + "..."

        copy = f"{hook}\n\n"
        copy += f"🎙️ Del episodio: {unit.segments[0].text[:80]}..." if unit.segments else ""
        copy += f"\n\n#PodcastEnClips #Shorts #Reels #TikTok"

        return copy

    def _generate_hashtags(self, clip: Clip, unit: ConversationUnit) -> List[str]:
        """Generate relevant hashtags."""
        tags = ["#PodcastClips", "#Shorts", "#Reels", "#TikTok"]

        # Extract key topics from clip text
        full_text = (clip.hook + " " + clip.development + " " + clip.closing).lower()

        topic_tags = {
            "emprendimiento": ["negocio", "empresa", "startup", "emprender", "cerrar", "tienda"],
            "dinero": ["dinero", "proveedor", "cliente", "rentable", "pagar", "cobrar"],
            "decisiones": ["decidí", "elegí", "cambié", "me lancé", "arrepiento"],
            "historias": ["recuerdo", "anécdota", "me pasó", "historia"],
            "consejos": ["consejo", "recomiendo", "clave", "truco", "aprendí"],
        }

        for tag, keywords in topic_tags.items():
            if any(kw in full_text for kw in keywords):
                tags.append(f"#{tag.capitalize()}")

        # Add speaker names if detectable (capitalized words)
        names = set(re.findall(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b", full_text))
        for name in list(names)[:2]:
            if len(name) > 3:
                tags.append(f"#{name}")

        return tags[:10]  # Limit hashtags

    async def _refine_clips(
        self,
        clips: List[Clip],
        all_segments: List[TranscriptionSegment],
        all_words: List[TranscriptionWord],
        video_duration: float
    ) -> List[Clip]:
        """Refine clip boundaries and add preview markers."""
        refined = []

        for clip in clips:
            # Add "listen to start" and "watch last 5s" markers
            clip.hook = f"[🔊 Escuchar inicio] {clip.hook}"
            clip.closing = f"{clip.closing} [▶ Ver últimos 5s]"

            # Ensure we have word-level data for subtitle generation
            clip.transcription_words = [
                w for w in all_words
                if clip.start <= w.start < clip.end
            ]

            # Ensure segment data
            clip.transcription_segments = [
                s for s in all_segments
                if not (s.end <= clip.start or s.start >= clip.end)
            ]

            refined.append(clip)

        return refined