from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    """Minimal startup configuration for the application shell."""

    register_hotkeys: bool = True
    game_install_dir: Optional[Path] = None
    auto_launch_game: bool = False
    use_qt_hud: bool = True
