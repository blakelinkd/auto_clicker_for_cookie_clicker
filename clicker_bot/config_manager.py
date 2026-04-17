import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .config import AppConfig


CONFIG_FILE_NAME = "cookie_bot_config.json"


def _get_config_dir() -> Path:
    r"""Get config directory, handling frozen vs development mode.
    
    In frozen mode (PyInstaller), use %LOCALAPPDATA%\CookieClickerAutoClicker.
    In development mode, use current working directory (portable).
    """
    if getattr(sys, 'frozen', False):
        local_app_data = os.environ.get('LOCALAPPDATA')
        if local_app_data:
            config_dir = Path(local_app_data) / 'CookieClickerAutoClicker'
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir
    return Path.cwd()


def _config_to_dict(config: AppConfig) -> Dict[str, Any]:
    """Convert AppConfig to JSON-serializable dict."""
    data = {
        "register_hotkeys": config.register_hotkeys,
        "auto_launch_game": config.auto_launch_game,
        "use_qt_hud": config.use_qt_hud,
        "automation": {
            "main_cookie_clicking_enabled": config.main_cookie_clicking_enabled,
            "shimmer_autoclick_enabled": config.shimmer_autoclick_enabled,
            "wrath_cookie_clicking_enabled": config.wrath_cookie_clicking_enabled,
            "stock_trading_enabled": config.stock_trading_enabled,
            "lucky_reserve_enabled": config.lucky_reserve_enabled,
            "building_autobuy_enabled": config.building_autobuy_enabled,
            "upgrade_autobuy_enabled": config.upgrade_autobuy_enabled,
            "ascension_prep_enabled": config.ascension_prep_enabled,
            "garden_automation_enabled": config.garden_automation_enabled,
            "garden_mode": config.garden_mode,
            "upgrade_horizon_seconds": config.upgrade_horizon_seconds,
            "building_horizon_seconds": config.building_horizon_seconds,
            "wrinkler_mode": config.wrinkler_mode,
            "building_caps": dict(config.building_caps),
            "ignored_building_caps": list(config.ignored_building_caps),
        },
    }
    if config.game_install_dir is not None:
        data["game_install_dir"] = str(config.game_install_dir)
    return data


def _dict_to_config(data: Dict[str, Any]) -> AppConfig:
    """Convert dict to AppConfig."""
    game_install_dir = None
    if "game_install_dir" in data and data["game_install_dir"]:
        game_install_dir = Path(data["game_install_dir"]).absolute()
    automation = data.get("automation") if isinstance(data.get("automation"), dict) else {}
    building_caps = automation.get("building_caps") if isinstance(automation.get("building_caps"), dict) else {}
    ignored_building_caps = automation.get("ignored_building_caps")
    if not isinstance(ignored_building_caps, list):
        ignored_building_caps = []
    return AppConfig(
        register_hotkeys=data.get("register_hotkeys", True),
        game_install_dir=game_install_dir,
        auto_launch_game=data.get("auto_launch_game", False),
        use_qt_hud=data.get("use_qt_hud", True),
        main_cookie_clicking_enabled=bool(automation.get("main_cookie_clicking_enabled", True)),
        shimmer_autoclick_enabled=bool(automation.get("shimmer_autoclick_enabled", True)),
        wrath_cookie_clicking_enabled=bool(automation.get("wrath_cookie_clicking_enabled", True)),
        stock_trading_enabled=bool(automation.get("stock_trading_enabled", False)),
        lucky_reserve_enabled=bool(automation.get("lucky_reserve_enabled", False)),
        building_autobuy_enabled=bool(automation.get("building_autobuy_enabled", False)),
        upgrade_autobuy_enabled=bool(automation.get("upgrade_autobuy_enabled", True)),
        ascension_prep_enabled=bool(automation.get("ascension_prep_enabled", False)),
        garden_automation_enabled=bool(automation.get("garden_automation_enabled", False)),
        garden_mode=str(automation.get("garden_mode", "auto")),
        upgrade_horizon_seconds=float(automation.get("upgrade_horizon_seconds", 30 * 60)),
        building_horizon_seconds=float(automation.get("building_horizon_seconds", 3 * 60)),
        wrinkler_mode=str(automation.get("wrinkler_mode", "hold")),
        building_caps={
            str(name): int(cap)
            for name, cap in building_caps.items()
            if isinstance(cap, (int, float)) and int(cap) >= 0
        },
        ignored_building_caps=tuple(str(name) for name in ignored_building_caps),
    )


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from JSON file, or return default if file doesn't exist."""
    if config_path is None:
        config_path = _get_config_dir() / CONFIG_FILE_NAME
    if not config_path.exists():
        return AppConfig()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _dict_to_config(data)
    except Exception as e:
        # If file is corrupted, fall back to defaults
        # TODO: maybe log warning
        return AppConfig()


def save_config(config: AppConfig, config_path: Optional[Path] = None) -> None:
    """Save configuration to JSON file."""
    if config_path is None:
        config_path = _get_config_dir() / CONFIG_FILE_NAME
    data = _config_to_dict(config)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
