import json
from pathlib import Path
from typing import Any, Dict, Optional

from .config import AppConfig


CONFIG_FILE_NAME = "cookie_bot_config.json"


def _config_to_dict(config: AppConfig) -> Dict[str, Any]:
    """Convert AppConfig to JSON-serializable dict."""
    data = {
        "register_hotkeys": config.register_hotkeys,
        "auto_launch_game": config.auto_launch_game,
    }
    if config.game_install_dir is not None:
        data["game_install_dir"] = str(config.game_install_dir)
    return data


def _dict_to_config(data: Dict[str, Any]) -> AppConfig:
    """Convert dict to AppConfig."""
    game_install_dir = None
    if "game_install_dir" in data and data["game_install_dir"]:
        game_install_dir = Path(data["game_install_dir"]).absolute()
    return AppConfig(
        register_hotkeys=data.get("register_hotkeys", True),
        game_install_dir=game_install_dir,
        auto_launch_game=data.get("auto_launch_game", False),
    )


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from JSON file, or return default if file doesn't exist."""
    if config_path is None:
        config_path = Path.cwd() / CONFIG_FILE_NAME
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
        config_path = Path.cwd() / CONFIG_FILE_NAME
    data = _config_to_dict(config)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)