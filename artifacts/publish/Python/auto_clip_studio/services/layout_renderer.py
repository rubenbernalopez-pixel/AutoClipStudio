"""
AutoClip Studio - Layout Renderer
Renders clips with different layouts: solo podcast, split-screen with backgrounds.
Generates FFmpeg filter graphs for complex video compositions.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
import json

from auto_clip_studio.utils.config import Config
from auto_clip_studio.utils.logger import get_logger
from auto_clip_studio.models.job import JobProgress, Clip
from auto_clip_studio.models.layout import (
    Layout, LayoutType, BackgroundAsset, get_builtin_layouts, get_layout
)

logger = get_logger(__name__)


class LayoutRenderer:
    """Renders clips with various layouts using FFmpeg."""

    def __init__(self, config: Config):
        self.config = config
        self.layouts = get_builtin_layouts()
        self.background_assets = self._load_background_assets()

    def _load_background_assets(self) -> Dict[str, BackgroundAsset]:
        """Load built-in background assets."""
        assets_dir = self.config.assets_dir / "backgrounds"
        assets = {}

        # Built-in assets specs
        builtin_specs = [
            {
                "id": "balls_hoops",
                "name": "balls_hoops",
                "display_name": "Pelotas escapando de aros",
                "type": LayoutType.BALLS_HOOPS,
                "filename": "balls_hoops.mp4",
                "duration": 30.0,
                "loopable": True
            },
            {
                "id": "block_parkour",
                "name": "block_parkour",
                "display_name": "Parkour de bloques",
                "type": LayoutType.BLOCK_PARKOUR,
                "filename": "block_parkour.mp4",
                "duration": 30.0,
                "loopable": True
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
        """Get all available layouts with their background assets."""
        result = []
        for layout_type, layout in self.layouts.items():
            layout_dict = layout.to_dict()
            # Add available backgrounds for split-screen layouts
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
        Render clips with selected layout.
        Yields progress, returns rendered clips.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        layout = self.layouts.get(LayoutType(layout_id), self.layouts[LayoutType.SOLO_PODCAST])
        background_asset = None

        if layout.is_split_screen:
            if background_path:
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
                # Use first available bundled background for this layout
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
                message=f"Renderizando clip {i+1}/{total}: {clip.id}",
                current_item=i+1,
                total_items=total
            )

            try:
                output_path = output_dir / f"{clip.id}_{layout_id}.mp4"

                await self._render_single_clip(
                    clip, source_video_path, layout, background_asset, output_path
                )

                clip.video_path = str(output_path)
                clip.layout = layout_id
                clip.background_asset = background_asset.id if background_asset else None
                rendered_clips.append(clip)

                logger.info(f"Rendered clip {clip.id} to {output_path}")

            except Exception as e:
                logger.error(f"Failed to render clip {clip.id}: {e}")
                # Continue with other clips

        yield JobProgress(
            stage="completed",
            percent=100,
            message=f"{len(rendered_clips)}/{total} clips renderizados",
            current_item=len(rendered_clips),
            total_items=total
        )

        return rendered_clips

    async def _render_single_clip(
        self,
        clip: Clip,
        source_video: Path,
        layout: Layout,
        background: Optional[BackgroundAsset],
        output_path: Path
    ):
        """Render a single clip with the specified layout."""
        if layout.is_split_screen and background:
            await self._render_split_screen(clip, source_video, layout, background, output_path)
        else:
            await self._render_solo_podcast(clip, source_video, layout, output_path)

    async def _render_solo_podcast(
        self,
        clip: Clip,
        source_video: Path,
        layout: Layout,
        output_path: Path
    ):
        """Render solo podcast layout (full screen vertical)."""
        # Build FFmpeg filter graph
        filters = []

        # 1. Crop and scale source to 9:16
        # Detect source aspect ratio and crop appropriately
        crop_filter = self._build_crop_filter(clip, source_video)
        filters.append(crop_filter)

        # 2. Apply smart framing (face tracking) if enabled
        if layout.framing_enabled:
            # This would use a more complex filter; simplified for now
            pass

        # 3. Apply subtle zoom if enabled
        if layout.zoom_enabled:
            zoom_filter = "zoompan=z='if(lte(zoom,1.0),1.0,max(1.001,zoom-0.0005))':d=1:s=1080x1920"
            filters.append(zoom_filter)

        # 4. Voice leveling (audio filter)
        audio_filters = []
        if layout.voice_leveling:
            audio_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
            audio_filters.append("dynaudnorm=p=0.9:s=10")

        filter_complex = ";".join(filters)
        if filter_complex:
            filter_complex = f"[0:v]{filter_complex}[vout]"
        else:
            filter_complex = "[0:v]copy[vout]"

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(clip.start),
            "-t", str(clip.duration),
            "-i", str(source_video),
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "0:a?",
        ]

        if audio_filters:
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
            str(output_path)
        ])

        await self._run_ffmpeg(cmd)

    async def _render_split_screen(
        self,
        clip: Clip,
        source_video: Path,
        layout: Layout,
        background: BackgroundAsset,
        output_path: Path
    ):
        """Render split-screen layout (podcast top, background bottom)."""
        podcast_h = int(self.config.default_height * layout.podcast_area["height"])
        bg_h = self.config.default_height - podcast_h

        # Build filter graph for split screen
        filter_parts = []

        # Podcast video: crop to 9:16, scale to top portion
        filter_parts.append(
            f"[0:v]trim=start={clip.start}:duration={clip.duration},"
            f"scale={self.config.default_width}:{podcast_h}:force_original_aspect_ratio=decrease,"
            f"pad={self.config.default_width}:{podcast_h}:(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1[vpodcast]"
        )

        # Background video: loop to clip duration, scale to bottom portion
        filter_parts.append(
            f"[1:v]scale={self.config.default_width}:{bg_h}:force_original_aspect_ratio=increase,"
            f"crop={self.config.default_width}:{bg_h},"
            f"loop=loop=-1:size={int(background.duration * background.fps)}:start=0,"
            f"trim=duration={clip.duration},"
            f"setsar=1[vbg]"
        )

        # Stack vertically
        filter_parts.append(
            f"[vpodcast][vbg]vstack=inputs=2[vout]"
        )

        filter_complex = ";".join(filter_parts)

        # Audio: only podcast audio, with leveling
        audio_filters = []
        if layout.voice_leveling:
            audio_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
            audio_filters.append("dynaudnorm=p=0.9:s=10")

        cmd = [
            "ffmpeg", "-y",
            "-i", str(source_video),
            "-i", str(background.video_path),
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "0:a?",
        ]

        if audio_filters:
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

    def _build_crop_filter(self, clip: Clip, source_video: Path) -> str:
        """Build crop filter to convert source to 9:16 vertical."""
        # Get source video dimensions
        # For now, use a standard crop that works for most landscape sources
        # In production, this would detect faces and crop intelligently
        return (
            f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
            f"scale={self.config.default_width}:{self.config.default_height}:force_original_aspect_ratio=increase,"
            f"crop={self.config.default_width}:{self.config.default_height}"
        )

    async def generate_preview(
        self,
        layout_id: str,
        clip: Optional[Clip] = None
    ) -> Path:
        """Generate a preview image/video for a layout."""
        layout = self.layouts.get(LayoutType(layout_id), self.layouts[LayoutType.SOLO_PODCAST])
        output_dir = self.config.temp_dir / "previews"
        output_dir.mkdir(parents=True, exist_ok=True)

        preview_path = output_dir / f"preview_{layout_id}.jpg"

        if layout.is_split_screen:
            # Use background asset thumbnail or generate from video
            background = None
            for asset in self.background_assets.values():
                if asset.type == layout.type and asset.is_bundled:
                    background = asset
                    break

            if background and background.thumbnail_path and background.thumbnail_path.exists():
                # Create composite preview
                await self._create_composite_preview(layout, background, preview_path)
            elif background and background.video_path.exists():
                # Extract frame from background video
                await self._extract_preview_frame(background.video_path, preview_path)
            else:
                # Generate placeholder
                await self._generate_placeholder_preview(layout, preview_path)
        else:
            # Solo podcast preview
            await self._generate_placeholder_preview(layout, preview_path)

        return preview_path

    async def _create_composite_preview(
        self,
        layout: Layout,
        background: BackgroundAsset,
        output_path: Path
    ):
        """Create a composite preview showing split-screen layout."""
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
            str(output_path)
        ]

        await self._run_ffmpeg(cmd)

    async def _extract_preview_frame(self, video_path: Path, output_path: Path):
        """Extract a frame from video for preview."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-ss", "1",
            "-frames:v", "1",
            "-c:v", "mjpeg",
            str(output_path)
        ]
        await self._run_ffmpeg(cmd)

    async def _generate_placeholder_preview(self, layout: Layout, output_path: Path):
        """Generate a placeholder preview image."""
        # Create a simple colored preview
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
        """Run FFmpeg command asynchronously."""
        logger.debug(f"Running FFmpeg: {' '.join(cmd)}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"FFmpeg failed (exit {proc.returncode}): {error_msg}")
            raise RuntimeError(f"FFmpeg error: {error_msg}")

        return stdout.decode() if stdout else ""