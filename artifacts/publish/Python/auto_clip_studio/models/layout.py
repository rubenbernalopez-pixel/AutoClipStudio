"""
AutoClip Studio - Layout Models
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class LayoutType(str, Enum):
    SOLO_PODCAST = "solo_podcast"
    BALLS_HOOPS = "balls_hoops"  # "Pelotas escapando de aros"
    BLOCK_PARKOUR = "block_parkour"  # "Parkour de bloques"
    MY_GAMEPLAY = "my_gameplay"  # "Mi gameplay"


@dataclass
class BackgroundAsset:
    """Background asset for split-screen layouts."""
    id: str
    name: str
    display_name: str
    type: LayoutType
    video_path: Path
    thumbnail_path: Optional[Path] = None
    duration: float = 0.0  # Loop duration in seconds
    is_bundled: bool = True  # True for built-in, False for user-provided
    loopable: bool = True
    fps: int = 30
    resolution: tuple = (1080, 1920)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "type": self.type.value,
            "video_path": str(self.video_path),
            "thumbnail_path": str(self.thumbnail_path) if self.thumbnail_path else None,
            "duration": self.duration,
            "is_bundled": self.is_bundled,
            "loopable": self.loopable,
            "fps": self.fps,
            "resolution": self.resolution
        }


@dataclass
class Layout:
    """Layout configuration for clip rendering."""
    type: LayoutType
    name: str
    display_name: str
    description: str
    is_split_screen: bool = False
    background_asset: Optional[BackgroundAsset] = None
    podcast_area: Dict[str, float] = None  # x, y, width, height as 0-1 ratios
    background_area: Dict[str, float] = None
    subtitle_area: Dict[str, float] = None  # Safe area for subtitles
    zoom_enabled: bool = True
    framing_enabled: bool = True
    voice_leveling: bool = True

    def __post_init__(self):
        if self.podcast_area is None:
            if self.is_split_screen:
                self.podcast_area = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.55}
                self.background_area = {"x": 0.0, "y": 0.55, "width": 1.0, "height": 0.45}
            else:
                self.podcast_area = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
                self.background_area = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}

        if self.subtitle_area is None:
            # Safe area avoiding platform UI (bottom 15%, top 10%, sides 5%)
            self.subtitle_area = {"x": 0.05, "y": 0.10, "width": 0.90, "height": 0.75}

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "is_split_screen": self.is_split_screen,
            "background_asset": self.background_asset.to_dict() if self.background_asset else None,
            "podcast_area": self.podcast_area,
            "background_area": self.background_area,
            "subtitle_area": self.subtitle_area,
            "zoom_enabled": self.zoom_enabled,
            "framing_enabled": self.framing_enabled,
            "voice_leveling": self.voice_leveling
        }


# Built-in layouts
BUILTIN_LAYOUTS = {
    LayoutType.SOLO_PODCAST: Layout(
        type=LayoutType.SOLO_PODCAST,
        name="solo_podcast",
        display_name="Solo pódcast",
        description="Vídeo vertical del pódcast a pantalla completa con subtítulos karaoke",
        is_split_screen=False,
        zoom_enabled=True,
        framing_enabled=True,
        voice_leveling=True
    ),
    LayoutType.BALLS_HOOPS: Layout(
        type=LayoutType.BALLS_HOOPS,
        name="balls_hoops",
        display_name="Pelotas escapando de aros",
        description="Pantalla dividida: pódcast arriba, animación de pelotas rebotando y escapando de aros abajo",
        is_split_screen=True,
        zoom_enabled=True,
        framing_enabled=True,
        voice_leveling=True
    ),
    LayoutType.BLOCK_PARKOUR: Layout(
        type=LayoutType.BLOCK_PARKOUR,
        name="block_parkour",
        display_name="Parkour de bloques",
        description="Pantalla dividida: pódcast arriba, parkour de bloques estilo Minecraft abajo",
        is_split_screen=True,
        zoom_enabled=True,
        framing_enabled=True,
        voice_leveling=True
    ),
    LayoutType.MY_GAMEPLAY: Layout(
        type=LayoutType.MY_GAMEPLAY,
        name="my_gameplay",
        display_name="Mi gameplay",
        description="Pantalla dividida: pódcast arriba, tu partida de Minecraft abajo (vídeo propio)",
        is_split_screen=True,
        zoom_enabled=True,
        framing_enabled=True,
        voice_leveling=True
    ),
}


def get_builtin_layouts() -> Dict[LayoutType, Layout]:
    """Get all built-in layouts."""
    return BUILTIN_LAYOUTS.copy()


def get_layout(layout_type: LayoutType) -> Layout:
    """Get a specific built-in layout."""
    return BUILTIN_LAYOUTS.get(layout_type, BUILTIN_LAYOUTS[LayoutType.SOLO_PODCAST])