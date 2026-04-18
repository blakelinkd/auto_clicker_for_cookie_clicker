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
    main_cookie_clicking_enabled: bool = True
    shimmer_autoclick_enabled: bool = True
    wrath_cookie_clicking_enabled: bool = True
    stock_trading_enabled: bool = False
    lucky_reserve_enabled: bool = False
    building_autobuy_enabled: bool = False
    upgrade_autobuy_enabled: bool = True
    ascension_prep_enabled: bool = False
    garden_automation_enabled: bool = False
    garden_mode: str = "auto"
    upgrade_horizon_seconds: float = 30 * 60
    building_horizon_seconds: float = 3 * 60
    wrinkler_mode: str = "hold"
    building_caps: dict[str, int] = field(default_factory=dict)
    ignored_building_caps: tuple[str, ...] = field(default_factory=tuple)
    overlay_messages: tuple[dict, ...] = field(default_factory=tuple)
