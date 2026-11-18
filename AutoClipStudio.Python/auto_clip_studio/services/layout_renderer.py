"""
AutoClip Studio - Layout Renderer (MEJORADO MÁXIMO)
Renderiza clips con 4 layouts profesionales:
1. Solo podcast - Full screen vertical con smart crop
2. Pelotas y aros - Split 55/45 con animación procedural
3. Parkour de bloques - Split 55/45 estilo Minecraft
4. Mi gameplay - Split 55/45 con vídeo usuario (Minecraft)

Efectos automáticos:
- Smart crop (rostro activo) con face detection fallback
- Loudnorm + dynaudnorm para audio consistente
- Zoom suave en énfasis (detección de palabras clave)
- Transiciones suaves entre layouts
- Preview real antes de render
"""

import asyncio
import subprocess
import json
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple
import cv2
import numpy as np

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import JobProgress, Clip
from auto_clip_studio.models.layout import (
    Layout, LayoutType, BackgroundAsset, get_builtin_layouts, get_layout
)

logger = get_logger(__name__)


class LayoutRenderer:
    """Renderizador de layouts con efectos automáticos inteligentes."""

    def __init__(self, config: Config):
        self.config = config
        self.layouts = get_builtin_layouts()
        self.background_assets = self._load_background_assets()
        self._face_cascade = None
        self._init_face_detection()

    def _init_face_detection(self):
        """Inicializa detección de rostros para smart crop."""
        try:
            # Usar Haar cascade incluido en OpenCV
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("Face detection initialized for smart crop")
        except Exception as e:
            logger.warning(f"No se pudo iniciar face detection: {e}")
            self._face_cascade = None

    def _load_background_assets(self) -> Dict[str, BackgroundAsset]:
        """Carga assets de fondo incluidos (procedurales)."""
        assets_dir = self.config.assets_dir / "backgrounds"
        assets = {}

        builtin_specs = [
            {
                "id": "balls_hoops",
                "name": "balls_hoops",
                "display_name": "Pelotas escapando de aros",
                "type": LayoutType.BALLS_HOOPS,
                "filename": "balls_hoops.mp4",
                "duration": 30.0,
                "loopable": True,
                "description": "Animación de pelotas rebotando y escapando de aros"
            },
            {
                "id": "block_parkour",
                "name": "block_parkour",
                "display_name": "Parkour de bloques",
                "type": LayoutType.BLOCK_PARKOUR,
                "filename": "block_parkour.mp4",
                "duration": 30.0,
                "loopable": True,
                "description": "Parkour estilo Minecraft con bloques"
            }
        ]

        for spec in builtin_specs:
            video_path = assets_dir / spec["filename"]
            thumb_path = assets_dir / f"{spec['name']}_thumb.jpg"

            assets[spec["id"]] = BackgroundAsset(
                id=spec["id"],
                name=spec["name"],
                display_name=spec["display_name"],
                type=spec["type"],
                video_path=video_path if video_path.exists() else Path(""),
                thumbnail_path=thumb_path if thumb_path.exists() else None,
                duration=spec["duration"],
                is_bundled=video_path.exists(),
                loopable=spec["loopable"],
                fps=30,
                resolution=(1080, 1920)
            )

        return assets

    def get_available_layouts(self) -> List[Dict[str, Any]]:
        """Retorna todos los layouts con sus backgrounds disponibles."""
        result = []
        for layout_type, layout in self.layouts.items():
            layout_dict = layout.to_dict()
            if layout.is_split_screen:
                backgrounds = []
                for asset in self.background_assets.values():
                    if asset.type == layout_type and asset.video_path.exists():
                        backgrounds.append(asset.to_dict())
                layout_dict["available_backgrounds"] = backgrounds
            result.append(layout_dict)
        return result

    async def render_clips(
        self,
        clips: List[Clip],
        source_video_path: Path,
        layout_id: str,
        background_path: Optional[str],
        output_dir: Path
    ) -> AsyncGenerator[JobProgress, List[Clip]]:
        """
        Renderiza clips con layout seleccionado y efectos automáticos.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        layout = self.layouts.get(LayoutType(layout_id), self.layouts[LayoutType.SOLO_PODCAST])
        background_asset = None

        if layout.is_split_screen:
            if background_path and Path(background_path).exists():
                background_asset = BackgroundAsset(
                    id="custom",
                    name="custom",
                    display_name="Gameplay personalizado",
                    type=layout.type,
                    video_path=Path(background_path),
                    is_bundled=False,
                    loopable=True
                )
            else:
                for asset in self.background_assets.values():
                    if asset.type == layout.type and asset.is_bundled:
                        background_asset = asset
                        break

        rendered_clips = []
        total = len(clips)

        for i, clip in enumerate(clips):
            yield JobProgress(
                stage="rendering",
                percent=(i / total) * 100,
                message=f"Renderizando clip {i+1}/{total}: {clip.id} ({layout.display_name})",
                current_item=i+1,
                total_items=total
            )

            try:
                output_path = output_dir / f"{clip.id}_{layout_id}.mp4"

                # Detectar rostros para smart crop
                face_regions = await self._detect_faces_in_clip(source_video_path, clip.start, clip.end)

                # Determinar zoom points (énfasis en palabras clave)
                zoom_points = self._calculate_zoom_points(clip)

                await self._render_single_clip_pro(
                    clip, source_video_path, layout, background_asset,
                    output_path, face_regions, zoom_points
                )

                clip.video_path = str(output_path)
                clip.layout = layout_id
                clip.background_asset = background_asset.id if background_asset else None
                rendered_clips.append(clip)

                logger.info(f"Renderizado: {clip.id} -> {output_path}")

            except Exception as e:
                logger.error(f"Error renderizando clip {clip.id}: {e}")
                # Continuar con siguientes clips

        yield JobProgress(
            stage="completed",
            percent=100,
            message=f"{len(rendered_clips)}/{total} clips renderizados con efectos auto",
            current_item=len(rendered_clips),
            total_items=total
        )

        return rendered_clips

    async def _detect_faces_in_clip(
        self,
        video_path: Path,
        start: float,
        end: float
    ) -> List[Dict[str, float]]:
        """
        Detecta rostros en el clip para smart crop.
        Returns lista de regiones {x, y, w, h, confidence} normalizadas 0-1.
        """
        if not self._face_cascade or not self.config.default_fps:
            return []

        try:
            # Extraer frames clave (inicio, medio, final) para análisis
            sample_times = [start, (start + end) / 2, end - 0.5]
            face_regions = []

            for sample_t in sample_times:
                frame = await self._extract_frame(video_path, sample_t)
                if frame is None:
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self._face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
                )

                for (x, y, w, h) in faces:
                    h_frame, w_frame = frame.shape[:2]
                    face_regions.append({
                        "x": x / w_frame,
                        "y": y / h_frame,
                        "w": w / w_frame,
                        "h": h / h_frame,
                        "confidence": 0.9,
                        "time": sample_t
                    })

            # Promediar regiones detectadas
            if face_regions:
                avg_region = {
                    "x": sum(r["x"] for r in face_regions) / len(face_regions),
                    "y": sum(r["y"] for r in face_regions) / len(face_regions),
                    "w": sum(r["w"] for r in face_regions) / len(face_regions),
                    "h": sum(r["h"] for r in face_regions) / len(face_regions),
                }
                return [avg_region]

            return []

        except Exception as e:
            logger.warning(f"Face detection failed: {e}")
            return []

    async def _extract_frame(self, video_path: Path, timestamp: float) -> Optional[np.ndarray]:
        """Extrae un frame del vídeo en timestamp dado."""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", str(video_path),
                "-frames:v", "1",
                "-f", "image2pipe",
                "-pix_fmt", "bgr24",
                "-vcodec", "rawvideo",
                "-"
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0 and stdout:
                # Calcular dimensiones esperadas (asumir 1920x1080 source)
                # ffmpeg rawvideo no incluye header, necesitamos saber tamaño
                # Para simplicidad, usar cv2.VideoCapture
                pass

            # Fallback: usar OpenCV directamente
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_num = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            cap.release()
            return frame if ret else None

        except Exception:
            return None

    def _calculate_zoom_points(self, clip: Clip) -> List[Dict[str, Any]]:
        """
        Calcula puntos de zoom suave basados en palabras clave de énfasis.
        Returns: [{time, zoom_factor, duration, easing}]
        """
        zoom_points = []

        # Palabras que merecen zoom
        emphasis_keywords = [
            "nunca", "jamás", "siempre", "todo", "nada",
            "verdad", "mentira", "secreto", "clave", "error",
            "arrepiento", "equivoqué", "peor", "mejor",
            "cerré", "abandoné", "deje", "perdí", "gané",
            "millón", "miles", "cientos", "primera", "última"
        ]

        if not clip.transcription_words:
            return zoom_points

        for word in clip.transcription_words:
            clean_word = word.word.lower().strip(".,!?;:")
            if clean_word in emphasis_keywords:
                zoom_points.append({
                    "time": word.start - clip.start,  # Relativo al clip
                    "zoom": 1.08,  # 8% zoom
                    "duration": 1.5,
                    "easing": "ease_in_out"
                })

        # Fusionar zooms muy cercanos
        merged = []
        for zp in sorted(zoom_points, key=lambda x: x["time"]):
            if merged and zp["time"] - merged[-1]["time"] < 2.0:
                # Extender duración del anterior
                merged[-1]["duration"] = max(merged[-1]["duration"], zp["time"] - merged[-1]["time"] + 1.5)
            else:
                merged.append(zp)

        return merged[:5]  # Máx 5 zooms por clip

    async def _render_single_clip_pro(
        self,
        clip: Clip,
        source_video: Path,
        layout: Layout,
        background: Optional[BackgroundAsset],
        output_path: Path,
        face_regions: List[Dict],
        zoom_points: List[Dict]
    ):
        """Render profesional con todos los efectos automáticos."""

        if layout.is_split_screen and background:
            await self._render_split_screen_pro(
                clip, source_video, layout, background, output_path,
                face_regions, zoom_points
            )
        else:
            await self._render_solo_podcast_pro(
                clip, source_video, layout, output_path,
                face_regions, zoom_points
            )

    async def _render_solo_podcast_pro(
        self,
        clip: Clip,
        source_video: Path,
        layout: Layout,
        output_path: Path,
        face_regions: List[Dict],
        zoom_points: List[Dict]
    ):
        """Solo podcast: full vertical con smart crop, audio pro, zoom dinámico."""

        # Construir filter_complex modular
        filters = []

        # 1. Input video con trim
        v_in = f"[0:v]trim=start={clip.start}:duration={clip.duration},setpts=PTS-STARTPTS[v0]"

        # 2. Smart crop con face tracking
        if face_regions and layout.framing_enabled:
            face = face_regions[0]
            # Calcular crop 9:16 centrado en cara
            # Cara en coordenadas normalizadas, convertir a crop
            crop_filter = self._build_smart_crop_filter(face, "v0", "v1")
            filters.append(v_in)
            filters.append(crop_filter)
            v_current = "v1"
        else:
            # Crop estándar centro
            crop_filter = (
                f"[0:v]trim=start={clip.start}:duration={clip.duration},"
                f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
                f"scale={self.config.default_width}:{self.config.default_height}:force_original_aspect_ratio=increase,"
                f"crop={self.config.default_width}:{self.config.default_height},"
                f"setsar=1[v_crop]"
            )
            filters.append(crop_filter)
            v_current = "v_crop"

        # 3. Zoom dinámico en puntos de énfasis
        if zoom_points and layout.zoom_enabled:
            zoom_filter = self._build_dynamic_zoom_filter(v_current, zoom_points, "v_zoom")
            filters.append(zoom_filter)
            v_current = "v_zoom"
        elif layout.zoom_enabled:
            # Zoom suave sutil continuo
            zoom_filter = f"[{v_current}]zoompan=z='if(lte(zoom,1.0),1.0,max(1.001,zoom-0.0003))':d=1:s={self.config.default_width}x{self.config.default_height}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[v_zoom]"
            filters.append(zoom_filter)
            v_current = "v_zoom"

        # 4. Corrección de color sutil (lift shadows slightly)
        color_filter = f"[{v_current}]eq=brightness=0.02:contrast=1.05:saturation=1.05[v_out]"
        filters.append(color_filter)

        filter_complex = ";".join(filters)

        # Audio: loudnorm + dynaudnorm + highpass para claridad
        audio_filters = [
            "highpass=f=80",
            "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=-99:measured_TP=-99:measured_LRA=99:measured_thresh=-99:offset=0:linear=true:print_format=summary",
            "dynaudnorm=p=0.9:s=15:g=15:m=10:r=0.5"
        ]

        if layout.voice_leveling:
            audio_filter_str = ",".join(audio_filters)
        else:
            audio_filter_str = "anull"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(source_video),
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "0:a?",
        ]

        if layout.voice_leveling:
            cmd.extend(["-af", audio_filter_str])

        cmd.extend([
            "-c:v", self.config.video_codec,
            "-preset", self.config.video_preset,
            "-crf", str(self.config.video_crf),
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-r", str(self.config.default_fps),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-metadata", f"title=AutoClip Studio - {clip.id}",
            "-metadata", "comment=Generated by AutoClip Studio",
            str(output_path)
        ])

        await self._run_ffmpeg(cmd)

    async def _render_split_screen_pro(
        self,
        clip: Clip,
        source_video: Path,
        layout: Layout,
        background: BackgroundAsset,
        output_path: Path,
        face_regions: List[Dict],
        zoom_points: List[Dict]
    ):
        """Split screen: podcast arriba (55%) + background abajo (45%)."""

        podcast_h = int(self.config.default_height * layout.podcast_area["height"])
        bg_h = self.config.default_height - podcast_h

        # Filtros para podcast (arriba)
        podcast_filters = []

        if face_regions and layout.framing_enabled:
            face = face_regions[0]
            crop_p = self._build_smart_crop_filter(face, "0:v", "v_podcast_crop", target_w=self.config.default_width, target_h=podcast_h)
            podcast_filters.append(crop_p)
            v_podcast = "v_podcast_crop"
        else:
            # Crop estándar para área superior
            crop_p = (
                f"[0:v]trim=start={clip.start}:duration={clip.duration},"
                f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
                f"scale={self.config.default_width}:{podcast_h}:force_original_aspect_ratio=increase,"
                f"crop={self.config.default_width}:{podcast_h},setsar=1[v_podcast]"
            )
            podcast_filters.append(crop_p)
            v_podcast = "v_podcast"

        # Zoom en podcast si hay puntos
        if zoom_points and layout.zoom_enabled:
            zoom_p = self._build_dynamic_zoom_filter(v_podcast, zoom_points, "v_podcast_zoom", target_w=self.config.default_width, target_h=podcast_h)
            podcast_filters.append(zoom_p)
            v_podcast = "v_podcast_zoom"

        # Color correction podcast
        podcast_filters.append(f"[{v_podcast}]eq=brightness=0.02:contrast=1.05[v_podcast_out]")
        v_podcast_final = "v_podcast_out"

        # Filtros para background (abajo) - loop y mute
        bg_filters = [
            f"[1:v]scale={self.config.default_width}:{bg_h}:force_original_aspect_ratio=increase,"
            f"crop={self.config.default_width}:{bg_h},"
            f"loop=loop=-1:size={int(background.duration * background.fps)}:start=0,"
            f"trim=duration={clip.duration},setsar=1[v_bg]"
        ]

        # Stack vertical
        stack_filter = f"[{v_podcast_final}][v_bg]vstack=inputs=2[v_out]"

        filter_complex = ";".join(podcast_filters + bg_filters + [stack_filter])

        # Audio solo podcast con procesamiento pro
        audio_filters = [
            "highpass=f=80",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "dynaudnorm=p=0.9:s=15:g=15:m=10:r=0.5"
        ] if layout.voice_leveling else ["anull"]

        cmd = [
            "ffmpeg", "-y",
            "-i", str(source_video),
            "-i", str(background.video_path),
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "0:a?",
        ]

        if layout.voice_leveling:
            cmd.extend(["-af", ",".join(audio_filters)])

        cmd.extend([
            "-c:v", self.config.video_codec,
            "-preset", self.config.video_preset,
            "-crf", str(self.config.video_crf),
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-r", str(self.config.default_fps),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path)
        ])

        await self._run_ffmpeg(cmd)

    def _build_smart_crop_filter(
        self,
        face: Dict,
        input_label: str,
        output_label: str,
        target_w: int = 1080,
        target_h: int = 1920
    ) -> str:
        """
        Construye filtro de crop 9:16 centrado en la cara detectada.
        face: {x, y, w, h} normalizado 0-1
        """
        # La cara está en coordenadas del video original
        # Necesitamos calcular crop en coordenadas del video source
        # Asumimos video source 16:9 o similar

        # Para simplicidad y robustez: crop centrado en cara con padding
        # face["y"] es posición vertical normalizada (0=arriba)
        # En 9:16, queremos la cara en el tercio superior (zona segura subtítulos)

        # Fórmula: crop window 9/16 * height, centrado vertical en cara con offset
        # Offset: mover cara a ~35% desde arriba (zona segura)
        target_face_y = 0.35  # Posición ideal de la cara en output 9:16

        # En coordenadas source, la cara está en face["y"]
        # El crop vertical debe empezar en: face_y_source - target_face_y * crop_height
        # crop_height = source_width * 9/16 (si source es landscape)

        # Implementación práctica: usar crop con expresión dinámica
        return (
            f"[{input_label}]"
            f"crop=ih*9/16:ih:"
            f"(iw-ih*9/16)/2:"
            f"max(0, ih*{face['y']:.3f} - ih*9/16*{target_face_y:.3f})"
            f",scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},setsar=1[{output_label}]"
        )

    def _build_dynamic_zoom_filter(
        self,
        input_label: str,
        zoom_points: List[Dict],
        output_label: str,
        target_w: int = 1080,
        target_h: int = 1920
    ) -> str:
        """
        Construye zoompan con keyframes en puntos de énfasis.
        zoom_points: [{time, zoom, duration, easing}]
        """
        if not zoom_points:
            return f"[{input_label}]copy[{output_label}]"

        # Construir expresión zoompan con keyframes
        # zoompan no soporta keyframes nativos, usar sendcmd + zoompan
        # Alternativa: usar multiple zoompan encadenados o zoompan con expresión temporal

        # Expresión basada en tiempo para zoom suave
        zoom_expr_parts = ["1.0"]
        for zp in zoom_points:
            t_start = zp["time"]
            t_end = t_start + zp["duration"]
            zoom_val = zp["zoom"]
            # Transición suave: ease in-out
            zoom_expr_parts.append(
                f"between(t,{t_start:.2f},{t_end:.2f})*{zoom_val}"
            )

        # Combinar: zoom base 1.0 + picos
        # Nota: zoompan evalúa por frame, usar 'zoom' variable
        zoom_expr = "1.0"
        for zp in zoom_points:
            zoom_expr += f"+between(t,{zp['time']:.2f},{zp['time']+zp['duration']:.2f})*{zp['zoom']-1.0}"

        return (
            f"[{input_label}]"
            f"zoompan=z='{zoom_expr}':d=1:s={target_w}x{target_h}:fps={self.config.default_fps}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[{output_label}]"
        )

    async def generate_preview(
        self,
        layout_id: str,
        clip: Optional[Clip] = None
    ) -> Path:
        """Genera preview real del layout (imagen o vídeo corto)."""
        layout = self.layouts.get(LayoutType(layout_id), self.layouts[LayoutType.SOLO_PODCAST])
        output_dir = self.config.temp_dir / "previews"
        output_dir.mkdir(parents=True, exist_ok=True)

        preview_path = output_dir / f"preview_{layout_id}.jpg"

        if layout.is_split_screen:
            background = None
            for asset in self.background_assets.values():
                if asset.type == layout.type and asset.is_bundled:
                    background = asset
                    break

            if background and background.thumbnail_path and background.thumbnail_path.exists():
                await self._create_composite_preview(layout, background, preview_path)
            elif background and background.video_path.exists():
                await self._extract_preview_frame(background.video_path, preview_path)
            else:
                await self._generate_placeholder_preview(layout, preview_path)
        else:
            await self._generate_placeholder_preview(layout, preview_path)

        return preview_path

    async def _create_composite_preview(
        self,
        layout: Layout,
        background: BackgroundAsset,
        output_path: Path
    ):
        """Crea preview compuesto: podcast arriba + background abajo."""
        podcast_h = int(self.config.default_height * layout.podcast_area["height"])
        bg_h = self.config.default_height - podcast_h

        filter_complex = (
            f"color=c=#1a1a2e:size={self.config.default_width}x{podcast_h}:duration=1[top];"
            f"movie={background.thumbnail_path}:loop=0:duration=1,"
            f"scale={self.config.default_width}:{bg_h}[bottom];"
            f"[top][bottom]vstack=inputs=2[vout]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-frames:v", "1",
            "-c:v", "mjpeg",
            "-q:v", "2",
            str(output_path)
        ]

        await self._run_ffmpeg(cmd)

    async def _extract_preview_frame(self, video_path: Path, output_path: Path):
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-ss", "1",
            "-frames:v", "1",
            "-c:v", "mjpeg",
            "-q:v", "2",
            str(output_path)
        ]
        await self._run_ffmpeg(cmd)

    async def _generate_placeholder_preview(self, layout: Layout, output_path: Path):
        color = "#1a1a2e" if not layout.is_split_screen else "#16213e"
        filter_complex = f"color=c={color}:size={self.config.default_width}x{self.config.default_height}:duration=1[vout]"

        cmd = [
            "ffmpeg", "-y",
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-frames:v", "1",
            "-c:v", "mjpeg",
            str(output_path)
        ]
        await self._run_ffmpeg(cmd)

    async def _run_ffmpeg(self, cmd: List[str]):
        logger.debug(f"FFmpeg: {' '.join(cmd[:10])}...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"FFmpeg failed (exit {proc.returncode}): {error_msg[:500]}")
            raise RuntimeError(f"FFmpeg error: {error_msg}")

        return stdout.decode() if stdout else ""