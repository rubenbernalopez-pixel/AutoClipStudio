"""
AutoClip Studio - Clip Selector (MEJORADO MÁXIMO)
Selección inteligente tipo OpusClip: análisis semántico completo, detección de promos,
boundaries por significado, anti-duplicados, scoring explicable.
"""

import asyncio
import re
import json
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from difflib import SequenceMatcher

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import JobProgress, Clip, TranscriptionSegment, TranscriptionWord

logger = get_logger(__name__)


@dataclass
class ConversationUnit:
    """Unidad coherente de conversación (pregunta-respuesta, anécdota, etc.)."""
    start: float
    end: float
    segments: List[TranscriptionSegment]
    words: List[TranscriptionWord]
    unit_type: str  # "qa", "anecdote", "confession", "contradiction", "decision", "opinion", "story"
    hook_text: str
    development_text: str
    closing_text: str
    speakers: List[int]
    confidence: float
    has_question: bool = False
    has_answer: bool = False
    is_promo: bool = False
    promo_score: float = 0.0
    entities: List[str] = field(default_factory=list)  # Nombres, lugares, cifras
    emotional_peaks: List[Tuple[float, str]] = field(default_factory=list)  # (time, emotion)
    topic_relevance: float = 0.0


class ClipSelector:
    """Selector inteligente de clips basado en análisis conversacional profundo."""

    def __init__(self, config: Config):
        self.config = config
        self.promo_patterns = self._load_promo_patterns()
        self.question_patterns = self._load_question_patterns()
        self.hook_patterns = self._load_hook_patterns()
        self.closing_patterns = self._load_closing_patterns()
        self.emotion_patterns = self._load_emotion_patterns()
        self.entity_patterns = self._load_entity_patterns()

    def _load_promo_patterns(self) -> List[re.Pattern]:
        """Patrones que indican contenido promocional/patrocinado."""
        patterns = [
            # Patrocinio directo
            r"(gracias a|patrocinad[oa]|sponsor|colaborad[oa])\b",
            r"(nuestro patrocinador|gracias a nuestro|presentado por)",
            # Llamadas a acción
            r"(suscr[íi]bete|sígueme|follow me|dale al like|like y suscr)",
            r"(comenta|deja tu comentario|qué te parece)",
            # Promociones/códigos
            r"(c[oó]digo|descuento|oferta|promoci[oó]n|cup[oó]n)\b",
            r"(\d+%\s*(?:dto|descuento|off))",
            # Enlaces
            r"(enlace en la descripci[oó]n|link en bio|link abajo|en la bio)",
            # Transiciones a promo
            r"(antes de (?:seguir|terminar|cerrar)|para (?:terminar|cerrar)).{0,50}(patrocin|sponsor|colaborad)",
            r"(y ahora.{0,30}(?:gracias|patrocin|sponsor))",
            # Outros genéricos
            r"(nos vemos en el pr[oó]ximo|hasta la pr[oó]xima|hasta luego|adiós amigos)",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _load_question_patterns(self) -> List[re.Pattern]:
        """Patrones que detectan preguntas reales (no retóricas)."""
        patterns = [
            r"^\s*[¿?].*[?¿]\s*$",
            r"^(por qu[ée]|c[oó]mo|qu[ée]|cu[aá]ndo|d[oó]nde|qui[ée]n|cu[aá]l)\b.*\?",
            r"\?\s*$",
            r"^(me puedes|podr[íi]as|quer[íi]a saber|tengo curiosidad).+\?",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _load_hook_patterns(self) -> List[re.Pattern]:
        """Patrones de ganchos fuertes (primeras frases que enganchan)."""
        patterns = [
            # Afirmaciones contundentes
            r"^(nunca|jamás|siempre|todo el mundo|nadie)\b",
            r"^(la verdad|honestamente|sinceramente|te voy a contar|voy a contarte)\b",
            # Problema/conflicto inmediato
            r"^(lo que pasa es que|el problema es que|la clave est[áa] en|el secreto es)\b",
            # Arrepentimiento/error
            r"^(me arrepiento|me equivoqu[ée]|fue un error|no deber[íi]a|deb[íi] haber)\b",
            # Decisión drástica
            r"^(cerré|abandon[ée]|deje|perd[íi]|gan[ée]|cambi[oó] todo|me lanz[ée])\b",
            # Pregunta-gancho con stakes
            r"(?:¿?por qu[ée]?.{0,20})?(cerrar|dejar|abandonar|fallar|perder|arriesgar)\b",
            # Cifra impactante
            r"^\d+.{0,10}(años|euros|d[oó]lares|veces|personas|clientes)\b",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _load_closing_patterns(self) -> List[re.Pattern]:
        """Patrones de cierres satisfactorios (remate, moraleja, conclusión)."""
        patterns = [
            # Conclusión explícita
            r"(y as[íi] (?:fue|cambi[oó]|termin[oó]|pas[oó])|.+y ya est[áa]|.+y punto\.?$)",
            r"(al final|al final de cuentas|la moraleja|la lecci[oó]n|lo importante|la conclusi[oó]n)\b",
            r"(y ahora|ahora bien|as[íi] que|por eso|en definitiva|resumiendo)\b",
            # Cierre narrativo
            r"(y fue as[íi] como|desde entonces|despu[ée]s de eso|al final termin[oó])\b",
            # Evitar cierres abiertos/debilidad
            r"(?:\.\.\.\s*$|y entonces\s*$|y despu[eé]s\s*$|bueno,\s*$|nada m[aá]s\s*$)",
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _load_emotion_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Patrones de emociones para detectar picos emocionales."""
        return {
            "surprise": [re.compile(p, re.IGNORECASE) for p in [
                r"(no me lo creo|incre[íi]ble|impactante|alucinante|flip[ée])",
                r"(qu[ée]?|c[oó]mo\?|en serio\?|de verdad\?)",
            ]],
            "anger": [re.compile(p, re.IGNORECASE) for p in [
                r"(me enfad[oó]|me molesta|injusto|inaceptable|rabia|furibundo)",
            ]],
            "joy": [re.compile(p, re.IGNORECASE) for p in [
                r"(me encant[oó]|feliz|content[oó]simo|genial|maravilloso|espectacular)",
            ]],
            "fear": [re.compile(p, re.IGNORECASE) for p in [
                r"(me da miedo|terror|p[áa]nico|preocupad[oó]|ansiedad)",
            ]],
            "sadness": [re.compile(p, re.IGNORECASE) for p in [
                r"(triste|pena|duelo|lamento|arrepentimiento|me duele)",
            ]],
        }

    def _load_entity_patterns(self) -> List[re.Pattern]:
        """Patrones para detectar entidades importantes (nombres, cifras, lugares)."""
        return [
            re.compile(r"\b\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*(?:euros?|d[oó]lares?|\$|€|%|años?|meses?|d[ií]as?|horas?|personas?|clientes?|empleados?)\b", re.IGNORECASE),
            re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})*\b"),  # Nombres propios
            re.compile(r"\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{1,2}\b", re.IGNORECASE),
        ]

    async def select_clips(
        self,
        transcription: Dict[str, Any],
        video_duration: float,
        topic: Optional[str] = None,
        max_clips: int = 3,
        max_duration: int = 75
    ) -> AsyncGenerator[JobProgress, List[Clip]]:
        """
        Pipeline completo de selección de clips.
        """
        segments = transcription.get("segments", [])
        words = transcription.get("words", [])

        if not segments:
            yield JobProgress(stage="completed", percent=100, message="Sin contenido transcribible")
            return []

        yield JobProgress(stage="analyzing", percent=5, message="Analizando estructura conversacional...")

        # Convertir a modelos
        trans_segments = [TranscriptionSegment.from_dict(s) for s in segments]
        trans_words = [TranscriptionWord.from_dict(w) for w in words]

        # PASO 1: Detectar unidades conversacionales coherentes
        units = await self._detect_conversation_units(trans_segments, trans_words, video_duration)

        yield JobProgress(stage="enriching", percent=25, message="Enriqueciendo con entidades, emociones y relevancia...")

        # PASO 2: Enriquecer unidades (entidades, emociones, relevancia temática)
        units = await self._enrich_units(units, topic, trans_words)

        yield JobProgress(stage="scoring", percent=45, message="Puntuando cada unidad (gancho, desarrollo, cierre, claridad)...")

        # PASO 3: Puntuar cada unidad
        scored_units = await self._score_units(units, topic, trans_words)

        yield JobProgress(stage="filtering", percent=65, message="Filtrando duplicados, promos y seleccionando mejores...")

        # PASO 4: Filtrar y seleccionar mejores (anti-duplicados, anti-promo)
        selected_clips = await self._select_best_clips(scored_units, max_clips, max_duration, trans_words, video_duration)

        yield JobProgress(stage="refining", percent=85, message="Refinando boundaries y generando metadata...")

        # PASO 5: Refinar boundaries y generar metadata completa
        final_clips = await self._refine_clips(selected_clips, trans_segments, trans_words, video_duration, topic)

        yield JobProgress(
            stage="completed",
            percent=100,
            message=f"{len(final_clips)} clip(s) seleccionado(s) con alta confianza",
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
        """Detecta unidades conversacionales coherentes usando pausas, temas y estructura."""
        units = []
        current_segments = []
        current_words = []
        unit_start = 0.0

        for i, segment in enumerate(segments):
            current_segments.append(segment)
            current_words.extend(segment.words)

            # Determinar si es boundary de unidad
            is_boundary = self._is_unit_boundary(segment, segments, i)
            is_promo = self._is_promo_segment(segment)

            if is_boundary or is_promo or i == len(segments) - 1:
                unit_end = segment.end

                if current_segments:
                    unit = self._create_conversation_unit(
                        current_segments, current_words,
                        unit_start, unit_end, is_promo
                    )
                    if unit and unit.duration >= self.config.min_clip_duration:
                        units.append(unit)

                # Nueva unidad
                current_segments = []
                current_words = []
                unit_start = unit_end

        # Filtrar unidades muy cortas o puramente promocionales
        filtered = [u for u in units if u.duration >= self.config.min_clip_duration and u.promo_score < 0.7]
        logger.info(f"Unidades detectadas: {len(units)} → filtradas: {len(filtered)}")
        return filtered

    def _is_unit_boundary(
        self,
        segment: TranscriptionSegment,
        all_segments: List[TranscriptionSegment],
        index: int
    ) -> bool:
        """Determina si un segmento cierra una unidad conversacional."""
        text = segment.text.strip().lower()

        # 1. Pausa larga después (>2.5s)
        if index + 1 < len(all_segments):
            pause = all_segments[index + 1].start - segment.end
            if pause > 2.5:
                return True

        # 2. Patrones de cierre fuerte
        for pattern in self.closing_patterns:
            if pattern.search(text):
                return True

        # 3. Segmento muy largo (>20s) = probable fin de pensamiento
        if segment.end - segment.start > 20.0:
            return True

        # 4. Cambio de speaker detectado (si hay diarización)
        if index + 1 < len(all_segments):
            curr_speakers = set(w.speaker_id for w in segment.words if w.speaker_id)
            next_speakers = set(w.speaker_id for w in all_segments[index + 1].words if w.speaker_id)
            if curr_speakers and next_speakers and curr_speakers != next_speakers:
                # Cambio de hablante + pausa media = boundary probable
                pause = all_segments[index + 1].start - segment.end
                if pause > 1.0:
                    return True

        return False

    def _is_promo_segment(self, segment: TranscriptionSegment) -> bool:
        """Detecta segmentos promocionales con alta precisión."""
        text = segment.text.lower()
        promo_hits = sum(1 for p in self.promo_patterns if p.search(text))
        return promo_hits > 0

    def _create_conversation_unit(
        self,
        segments: List[TranscriptionSegment],
        words: List[TranscriptionWord],
        start: float,
        end: float,
        is_promo: bool
    ) -> Optional[ConversationUnit]:
        """Crea una unidad conversacional clasificada y enriquecida."""
        if not segments or len(" ".join(s.text for s in segments).strip()) < 30:
            return None

        full_text = " ".join(s.text for s in segments).strip()

        # Clasificar tipo de unidad
        unit_type, hook, development, closing = self._classify_unit(segments, full_text)

        # Detectar preguntas/respuestas
        has_question = self._has_question(segments)
        has_answer = self._has_answer(segments)

        # Speakers
        speakers = list(set(w.speaker_id for w in words if w.speaker_id is not None))

        # Confianza media
        confidence = sum(s.confidence for s in segments) / len(segments) if segments else 0.5

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
            has_question=has_question,
            has_answer=has_answer,
            is_promo=is_promo,
            promo_score=1.0 if is_promo else 0.0
        )

    def _classify_unit(
        self,
        segments: List[TranscriptionSegment],
        full_text: str
    ) -> Tuple[str, str, str, str]:
        """Clasifica la unidad y extrae hook/desarrollo/cierre."""
        first_seg = segments[0].text if segments else ""
        last_seg = segments[-1].text if segments else ""
        middle_text = " ".join(s.text for s in segments[1:-1]) if len(segments) > 2 else ""

        text_lower = full_text.lower()

        # Q&A: pregunta clara + respuesta desarrollada
        if self._has_question(segments) and self._has_answer(segments):
            q_idx = next((i for i, s in enumerate(segments) if self._is_question(s.text)), 0)
            hook = segments[q_idx].text if q_idx < len(segments) else first_seg
            development = " ".join(s.text for s in segments[q_idx+1:-1]) if len(segments) > q_idx + 2 else middle_text
            closing = last_seg
            return "qa", hook.strip(), development.strip(), closing.strip()

        # Anécdota: narrativa personal con remate
        if any(m in text_lower for m in ["me acuerdo", "recuerdo", "una vez", "había una vez", "me pasó", "me sucedió", "anécdota", "historia"]):
            return "anecdote", first_seg.strip(), middle_text.strip(), last_seg.strip()

        # Confesión/arrepentimiento
        if any(m in text_lower for m in ["me arrepiento", "fue un error", "me equivoqué", "no debería", "debí haber", "lo peor fue"]):
            return "confession", first_seg.strip(), middle_text.strip(), last_seg.strip()

        # Contradicción
        if any(m in text_lower for m in ["pero en realidad", "la verdad es que", "en realidad", "contradice", "lo contrario", "no es así"]):
            return "contradiction", first_seg.strip(), middle_text.strip(), last_seg.strip()

        # Decisión con consecuencias
        if any(m in text_lower for m in ["decidí", "decidimos", "elegí", "opté por", "me lancé", "cerré", "abandoné", "dejé", "cambié de"]):
            return "decision", first_seg.strip(), middle_text.strip(), last_seg.strip()

        # Opinión/insight
        return "opinion", first_seg.strip(), middle_text.strip(), last_seg.strip()

    def _has_question(self, segments: List[TranscriptionSegment]) -> bool:
        return any(self._is_question(s.text) for s in segments)

    def _has_answer(self, segments: List[TranscriptionSegment]) -> bool:
        for i, s in enumerate(segments):
            if self._is_question(s.text) and i + 1 < len(segments):
                next_seg = segments[i + 1]
                # Respuesta = más larga, explicativa, no es otra pregunta
                if len(next_seg.text) > len(s.text) * 1.2 and not self._is_question(next_seg.text):
                    return True
        return False

    def _is_question(self, text: str) -> bool:
        text = text.strip()
        for pattern in self.question_patterns:
            if pattern.search(text):
                return True
        return False

    async def _enrich_units(
        self,
        units: List[ConversationUnit],
        topic: Optional[str],
        all_words: List[TranscriptionWord]
    ) -> List[ConversationUnit]:
        """Enriquece unidades con entidades, emociones, relevancia temática."""
        for unit in units:
            full_text = unit.hook_text + " " + unit.development_text + " " + unit.closing_text

            # Entidades (nombres, cifras, fechas)
            unit.entities = self._extract_entities(full_text)

            # Picos emocionales
            unit.emotional_peaks = self._detect_emotional_peaks(unit)

            # Relevancia temática
            if topic:
                unit.topic_relevance = self._calculate_topic_relevance(unit, topic)

        return units

    def _extract_entities(self, text: str) -> List[str]:
        """Extrae entidades nombradas, cifras y referencias temporales."""
        entities = []
        for pattern in self.entity_patterns:
            matches = pattern.findall(text)
            entities.extend(matches)
        # Deduplicar manteniendo orden
        seen = set()
        unique = []
        for e in entities:
            e_lower = e.lower()
            if e_lower not in seen:
                seen.add(e_lower)
                unique.append(e)
        return unique[:10]  # Máx 10

    def _detect_emotional_peaks(self, unit: ConversationUnit) -> List[Tuple[float, str]]:
        """Detecta momentos de alta carga emocional en la unidad."""
        peaks = []
        full_text = (unit.hook_text + " " + unit.development_text + " " + unit.closing_text).lower()

        for emotion, patterns in self.emotion_patterns.items():
            for pattern in patterns:
                if pattern.search(full_text):
                    # Approximar timestamp al inicio de la unidad + offset
                    peaks.append((unit.start + 2.0, emotion))
        return peaks[:3]  # Máx 3

    def _calculate_topic_relevance(self, unit: ConversationUnit, topic: str) -> float:
        """Calcula relevancia semántica al tema solicitado."""
        topic_lower = topic.lower()
        unit_text = (unit.hook_text + " " + unit.development_text + " " + unit.closing_text).lower()

        # Palabras clave del tema
        topic_words = set(w for w in topic_lower.split() if len(w) > 3)
        unit_words = set(unit_text.split())

        if not topic_words:
            return 0.0

        # Overlap directo
        direct_overlap = len(topic_words & unit_words) / len(topic_words)

        # Sinónimos / relacionados (básico)
        related = {"cerrar": ["cerró", "cerrar", "cierre", "cerrada"],
                   "tienda": ["negocio", "local", "comercio", "empresa"],
                   "dinero": ["euros", "dólares", "rentable", "proveedor", "cliente", "pagar", "cobrar"]}

        for key, syns in related.items():
            if key in topic_lower:
                if any(s in unit_text for s in syns):
                    direct_overlap = min(direct_overlap + 0.15, 1.0)

        return min(direct_overlap, 1.0)

    async def _score_units(
        self,
        units: List[ConversationUnit],
        topic: Optional[str],
        all_words: List[TranscriptionWord]
    ) -> List[Tuple[ConversationUnit, float, Dict[str, float]]]:
        """Puntúa cada unidad con desglose explicable."""
        scored = []

        for unit in units:
            if unit.is_promo or unit.promo_score > 0.5:
                continue

            # Componentes de puntuación
            hook_score = self._score_hook(unit)
            dev_score = self._score_development(unit)
            close_score = self._score_closing(unit)
            clarity_score = self._score_clarity(unit, all_words)
            entity_score = self._score_entities(unit)
            emotion_score = self._score_emotion(unit)
            topic_bonus = unit.topic_relevance if topic else 0.0

            # Pesos configurables
            weights = {
                "hook": 0.28,
                "development": 0.28,
                "closing": 0.18,
                "clarity": 0.16,
                "entities": 0.05,
                "emotion": 0.05,
            }

            total = (
                hook_score * weights["hook"] +
                dev_score * weights["development"] +
                close_score * weights["closing"] +
                clarity_score * weights["clarity"] +
                entity_score * weights["entities"] +
                emotion_score * weights["emotion"] +
                topic_bonus * 0.10
            )

            breakdown = {
                "hook": round(hook_score, 3),
                "development": round(dev_score, 3),
                "closing": round(close_score, 3),
                "clarity": round(clarity_score, 3),
                "entities": round(entity_score, 3),
                "emotion": round(emotion_score, 3),
                "topic_relevance": round(topic_bonus, 3),
            }

            scored.append((unit, round(total, 3), breakdown))

        # Ordenar por puntuación descendente
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _score_hook(self, unit: ConversationUnit) -> float:
        """Puntúa la fuerza del gancho (primeros 5-10s)."""
        score = 0.4  # Base
        text = unit.hook_text.lower()

        # Patrones de gancho fuerte
        for pattern in self.hook_patterns:
            if pattern.search(text):
                score += 0.35
                break

        # Pregunta como gancho
        if unit.has_question:
            score += 0.15

        # Entidades en gancho (nombres, cifras)
        if unit.entities:
            score += min(len(unit.entities) * 0.05, 0.15)

        # Longitud adecuada (5-25 palabras)
        hook_words = len(unit.hook_text.split())
        if 5 <= hook_words <= 25:
            score += 0.1
        elif hook_words < 3:
            score -= 0.15

        return min(score, 1.0)

    def _score_development(self, unit: ConversationUnit) -> float:
        """Puntúa la riqueza del desarrollo."""
        if not unit.development_text:
            return 0.25

        score = 0.4
        text = unit.development_text.lower()
        words = text.split()

        # Longitud adecuada (30-200 palabras)
        if 30 <= len(words) <= 200:
            score += 0.25
        elif len(words) > 200:
            score += 0.15
        elif len(words) < 15:
            score -= 0.1

        # Lenguaje explicativo/causal
        explanatory = ["porque", "ya que", "puesto que", "la razón", "el motivo",
                       "explico", "te cuento", "pasó que", "sucedió que",
                       "por eso", "así que", "por tanto", "consecuencia"]
        if any(e in text for e in explanatory):
            score += 0.2

        # Detalles concretos (cifras, nombres propios)
        if re.search(r"\b\d+\b", text):
            score += 0.1
        if re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,}\b", text):
            score += 0.1

        # Múltiples speakers = conversación rica
        if len(unit.speakers) >= 2:
            score += 0.05

        return min(score, 1.0)

    def _score_closing(self, unit: ConversationUnit) -> float:
        """Puntúa la contundencia del cierre."""
        if not unit.closing_text:
            return 0.2

        score = 0.4
        text = unit.closing_text.lower()

        # Patrones de cierre fuerte
        for pattern in self.closing_patterns:
            if pattern.search(text):
                score += 0.35
                break

        # Lenguaje conclusivo
        conclusive = ["así que", "por eso", "en definitiva", "al final",
                      "la conclusión", "moraleja", "lección", "aprendí", "entendí"]
        if any(c in text for c in conclusive):
            score += 0.2

        # NO terminar en abierto
        if not text.rstrip().endswith(("...", "y entonces", "y después", "bueno,", "nada más", "pues eso")):
            score += 0.15

        return min(score, 1.0)

    def _score_clarity(self, unit: ConversationUnit, all_words: List[TranscriptionWord]) -> float:
        """Puntúa claridad transcripcional y separación de speakers."""
        if not unit.words:
            return 0.5

        word_confs = [w.confidence for w in unit.words if w.confidence > 0]
        if not word_confs:
            return 0.5

        avg_conf = sum(word_confs) / len(word_confs)
        low_conf_ratio = sum(1 for c in word_confs if c < 0.7) / len(word_confs)

        # Separación de speakers
        speaker_changes = 0
        prev_speaker = None
        for w in unit.words:
            if w.speaker_id is not None and w.speaker_id != prev_speaker:
                speaker_changes += 1
                prev_speaker = w.speaker_id

        # Ideal: 1-2 speakers con turnos claros
        if len(unit.speakers) == 1:
            speaker_score = 1.0
        elif len(unit.speakers) == 2 and speaker_changes <= 8:
            speaker_score = 0.95
        elif speaker_changes > 12:
            speaker_score = 0.6
        else:
            speaker_score = 0.8

        clarity = avg_conf * 0.6 + (1 - low_conf_ratio) * 0.25 + speaker_score * 0.15
        return min(clarity, 1.0)

    def _score_entities(self, unit: ConversationUnit) -> float:
        """Puntúa presencia de entidades concretas (nombres, cifras, fechas)."""
        if not unit.entities:
            return 0.3
        return min(0.3 + len(unit.entities) * 0.1, 1.0)

    def _score_emotion(self, unit: ConversationUnit) -> float:
        """Puntúa carga emocional detectada."""
        if not unit.emotional_peaks:
            return 0.4
        return min(0.4 + len(unit.emotional_peaks) * 0.2, 1.0)

    async def _select_best_clips(
        self,
        scored_units: List[Tuple[ConversationUnit, float, Dict[str, float]]],
        max_clips: int,
        max_duration: int,
        all_words: List[TranscriptionWord],
        video_duration: float
    ) -> List[Clip]:
        """Selecciona mejores clips no solapados, diversos y de calidad."""
        selected = []
        used_ranges = []  # (start, end)

        for unit, score, breakdown in scored_units:
            if len(selected) >= max_clips:
                break

            # Umbral mínimo de calidad
            if score < self.config.min_score_threshold:
                logger.info(f"Unidad descartada por score bajo: {score:.2f} < {self.config.min_score_threshold}")
                continue

            # Verificar solapamiento con clips ya seleccionados
            overlaps = False
            for used_start, used_end in used_ranges:
                overlap_start = max(unit.start, used_start)
                overlap_end = min(unit.end, used_end)
                overlap_duration = overlap_end - overlap_start
                if overlap_duration > 3.0:  # Más de 3s de solapamiento
                    overlaps = True
                    break

            if overlaps:
                continue

            # Ajustar duración si excede máximo
            duration = unit.end - unit.start
            if duration > max_duration:
                unit = self._trim_unit_smart(unit, max_duration, all_words)
                duration = unit.end - unit.start

            if duration < self.config.min_clip_duration:
                continue

            # Crear clip con metadata completa
            clip = await self._create_clip_from_unit(unit, score, breakdown, all_words, video_duration)
            selected.append(clip)
            used_ranges.append((unit.start, unit.end))

        logger.info(f"Clips seleccionados: {len(selected)} de {len(scored_units)} candidatos")
        return selected

    def _trim_unit_smart(
        self,
        unit: ConversationUnit,
        max_duration: float,
        all_words: List[TranscriptionWord]
    ) -> ConversationUnit:
        """Recorta unidad preservando hook y closing, ajustando development."""
        current_duration = unit.end - unit.start
        if current_duration <= max_duration:
            return unit

        excess = current_duration - max_duration

        # Prioridad: mantener hook (inicio) y closing (final), recortar development
        hook_duration = 0
        close_duration = 0
        if unit.segments:
            hook_duration = min(unit.segments[0].end - unit.segments[0].start, 10.0)
            close_duration = min(unit.segments[-1].end - unit.segments[-1].start, 10.0)

        dev_available = current_duration - hook_duration - close_duration
        if dev_available > excess:
            # Podemos recortar solo development
            new_end = unit.end - excess
            unit = self._truncate_unit(unit, new_end, all_words)
        else:
            # Recortar proportionalmente
            ratio = max_duration / current_duration
            new_end = unit.start + max_duration
            unit = self._truncate_unit(unit, new_end, all_words)

        return unit

    def _truncate_unit(
        self,
        unit: ConversationUnit,
        new_end: float,
        all_words: List[TranscriptionWord]
    ) -> ConversationUnit:
        """Trunca unidad a new_end ajustando segmentos y palabras."""
        new_segments = []
        new_words = []

        for seg in unit.segments:
            if seg.start >= new_end:
                break
            if seg.end <= new_end:
                new_segments.append(seg)
                new_words.extend(seg.words)
            else:
                # Segmento cortado
                truncated_words = [w for w in seg.words if w.start < new_end]
                if truncated_words:
                    from auto_clip_studio.models.job import TranscriptionSegment
                    new_seg = TranscriptionSegment(
                        id=seg.id,
                        start=seg.start,
                        end=new_end,
                        text=seg.text,  # Texto original, se recortará en UI
                        words=truncated_words,
                        speaker_id=seg.speaker_id,
                        confidence=seg.confidence
                    )
                    new_segments.append(new_seg)
                    new_words.extend(truncated_words)
                break

        unit.segments = new_segments
        unit.words = new_words
        unit.end = new_end

        # Recalcular development text
        if len(unit.segments) > 2:
            unit.development_text = " ".join(s.text for s in unit.segments[1:-1])
        else:
            unit.development_text = ""

        return unit

    async def _create_clip_from_unit(
        self,
        unit: ConversationUnit,
        score: float,
        breakdown: Dict[str, float],
        all_words: List[TranscriptionWord],
        video_duration: float
    ) -> Clip:
        """Crea objeto Clip completo con toda metadata."""

        # Filtrar palabras del rango del clip
        clip_words = [w for w in all_words if unit.start <= w.start < unit.end]

        # Generar social copy y hashtags
        social_copy = self._generate_social_copy(unit)
        hashtags = self._generate_hashtags(unit)

        # Explicación de puntuación
        explanation = self._generate_score_explanation(breakdown, unit)

        clip = Clip(
            start=unit.start,
            end=unit.end,
            duration=unit.end - unit.start,
            hook=unit.hook_text[:250],
            development=unit.development_text[:600],
            closing=unit.closing_text[:250],
            score=score,
            score_breakdown=breakdown,
            score_explanation=explanation,
            social_copy=social_copy,
            hashtags=hashtags,
            layout="solo_podcast",  # Default, se puede cambiar en UI
            transcription_segments=unit.segments,
            transcription_words=clip_words,
        )

        return clip

    def _generate_social_copy(self, unit: ConversationUnit) -> str:
        """Genera texto para redes sociales listo para copiar."""
        hook = unit.hook_text.strip()
        if len(hook) > 120:
            hook = hook[:117] + "..."

        copy = f"{hook}\n\n"

        # Añadir contexto si hay desarrollo fuerte
        if unit.development_text and len(unit.development_text) > 50:
            dev_preview = unit.development_text[:100].strip()
            copy += f"💬 {dev_preview}...\n\n"

        copy += "🎙️ Clip de podcast completo en el enlace de la bio\n\n"
        return copy

    def _generate_hashtags(self, unit: ConversationUnit) -> List[str]:
        """Genera hashtags relevantes y específicos."""
        tags = ["#PodcastClips", "#Shorts", "#Reels", "#TikTok", "#PodcastEnEspañol"]

        full_text = (unit.hook_text + " " + unit.development_text + " " + unit.closing_text).lower()

        # Temas detectados
        topic_tags = {
            "emprendimiento": ["negocio", "empresa", "startup", "emprender", "cerrar", "tienda", "local"],
            "dinero": ["dinero", "proveedor", "cliente", "rentable", "pagar", "cobrar", "euros", "facturar"],
            "decisiones": ["decidí", "elegí", "cambié", "me lancé", "arrepiento", "arrepentimiento"],
            "historias": ["recuerdo", "anécdota", "me pasó", "historia", "cuando era"],
            "consejos": ["consejo", "recomiendo", "clave", "truco", "aprendí", "error", "lección"],
            "marketing": ["marketing", "ventas", "clientes", "crecer", "escala", "estrategia"],
            "mentalidad": ["mentalidad", "mindset", "psicología", "creer", "limitar", "miedo"],
        }

        for tag, keywords in topic_tags.items():
            if any(kw in full_text for kw in keywords):
                tags.append(f"#{tag.capitalize()}")

        # Entidades como hashtags (nombres propios detectados)
        for entity in unit.entities[:3]:
            clean = re.sub(r'[^\w]', '', entity)
            if len(clean) > 3 and clean[0].isupper():
                tags.append(f"#{clean}")

        # Tipo de unidad
        type_tags = {
            "qa": "#PreguntaYRespuesta",
            "anecdote": "#Anécdota",
            "confession": "#Confesión",
            "contradiction": "#Contradicción",
            "decision": "#DecisiónClave",
        }
        if unit.unit_type in type_tags:
            tags.append(type_tags[unit.unit_type])

        return tags[:12]  # Máximo 12

    def _generate_score_explanation(
        self,
        breakdown: Dict[str, float],
        unit: ConversationUnit
    ) -> str:
        """Genera explicación en lenguaje natural de la puntuación."""
        parts = []

        if breakdown["hook"] > 0.75:
            parts.append("gancho muy potente que engancha al instante")
        elif breakdown["hook"] > 0.55:
            parts.append("buen gancho inicial")

        if breakdown["development"] > 0.75:
            parts.append("desarrollo rico en detalles y explicaciones")
        elif breakdown["development"] > 0.55:
            parts.append("desarrollo sólido con contenido sustancioso")

        if breakdown["closing"] > 0.75:
            parts.append("cierre contundente con moraleja clara")
        elif breakdown["closing"] > 0.55:
            parts.append("cierre satisfactorio")

        if breakdown["clarity"] < 0.6:
            parts.append("algunas palabras con transcripción incierta")

        if breakdown.get("entities", 0) > 0.6:
            parts.append("menciona nombres, cifras y datos concretos")

        if breakdown.get("emotion", 0) > 0.6:
            parts.append("picos emocionales detectados")

        if breakdown.get("topic_relevance", 0) > 0.5:
            parts.append("muy relevante al tema que indicaste")

        if not parts:
            return "Clip con potencial editorial moderado"

        return "Seleccionado por: " + ", ".join(parts) + "."

    async def _refine_clips(
        self,
        clips: List[Clip],
        all_segments: List[TranscriptionSegment],
        all_words: List[TranscriptionWord],
        video_duration: float,
        topic: Optional[str]
    ) -> List[Clip]:
        """Refina clips finales: markers de preview, validación de boundaries, deduplicación final."""
        refined = []

        for clip in clips:
            # Añadir markers de preview rápido
            clip.hook = f"[🔊 Escuchar inicio] {clip.hook}"
            clip.closing = f"{clip.closing} [▶ Ver últimos 5s]"

            # Validar que el final no corte palabra a medias
            clip = await self._validate_boundaries(clip, all_words)

            # Asegurar palabras del clip
            clip.transcription_words = [
                w for w in all_words
                if clip.start <= w.start < clip.end
            ]

            # Segmentos relevantes
            clip.transcription_segments = [
                s for s in all_segments
                if not (s.end <= clip.start or s.start >= clip.end)
            ]

            refined.append(clip)

        # Deduplicación final por similitud de contenido
        final = self._deduplicate_final(refined)
        return final

    async def _validate_boundaries(
        self,
        clip: Clip,
        all_words: List[TranscriptionWord]
    ) -> Clip:
        """Asegura que boundaries no corten palabras y último segundo es audible."""
        # Buscar palabra más cercana al final
        end_words = [w for w in all_words if abs(w.end - clip.end) < 1.0]
        if end_words:
            last_word = max(end_words, key=lambda w: w.end)
            # Si la última palabra termina después del clip, extender ligeramente
            if last_word.end > clip.end and last_word.end - clip.end < 0.5:
                clip.end = last_word.end + 0.1
                clip.duration = clip.end - clip.start

        # Similar para inicio
        start_words = [w for w in all_words if abs(w.start - clip.start) < 1.0]
        if start_words:
            first_word = min(start_words, key=lambda w: w.start)
            if first_word.start < clip.start and clip.start - first_word.start < 0.3:
                clip.start = max(0, first_word.start - 0.1)
                clip.duration = clip.end - clip.start

        return clip

    def _deduplicate_final(self, clips: List[Clip]) -> List[Clip]:
        """Elimina clips con contenido muy similar (similitud textual > 80%)."""
        if len(clips) <= 1:
            return clips

        unique = []
        for clip in clips:
            clip_text = (clip.hook + " " + clip.development + " " + clip.closing).lower()
            is_dup = False
            for existing in unique:
                exist_text = (existing.hook + " " + existing.development + " " + existing.closing).lower()
                sim = SequenceMatcher(None, clip_text, exist_text).ratio()
                if sim > 0.75:  # 75% similar = duplicado
                    is_dup = True
                    logger.info(f"Clip duplicado descartado (sim={sim:.2f}): {clip.id} vs {existing.id}")
                    break
            if not is_dup:
                unique.append(clip)
        return unique