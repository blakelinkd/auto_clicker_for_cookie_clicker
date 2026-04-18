import json
import shutil
from uuid import uuid4
from pathlib import Path

from clicker_bot.config import AppConfig
from clicker_bot.config_manager import load_config, save_config


def make_workspace_temp_dir():
    base_dir = Path.cwd() / ".test_tmp" / f"config_manager_{uuid4().hex}"
    base_dir.mkdir(parents=True, exist_ok=False)
    return base_dir


def cleanup_workspace_temp_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)


def test_save_and_load_default_config():
    """Save default config, load it back, fields match."""
    tmpdir = make_workspace_temp_dir()
    try:
        config_path = tmpdir / "test_config.json"
        config = AppConfig()
        save_config(config, config_path)
        assert config_path.exists()
        loaded = load_config(config_path)
        assert loaded.register_hotkeys == True
        assert loaded.auto_launch_game == False
        assert loaded.game_install_dir is None
    finally:
        cleanup_workspace_temp_dir(tmpdir)


def test_save_and_load_custom_config():
    """Save config with custom values."""
    tmpdir = make_workspace_temp_dir()
    try:
        config_path = tmpdir / "test_config.json"
        install_dir = Path("C:/Some/Path")
        config = AppConfig(
            register_hotkeys=False,
            auto_launch_game=True,
            game_install_dir=install_dir,
            main_cookie_clicking_enabled=False,
            wrath_cookie_clicking_enabled=False,
            building_autobuy_enabled=True,
            upgrade_horizon_seconds=900.0,
            building_horizon_seconds=1200.0,
            wrinkler_mode="shiny_hunt",
            garden_mode="shimmerlilly",
            building_caps={"Cursor": 123},
            ignored_building_caps=("Mine",),
            overlay_messages=({"event_id": "hud:test", "text": "Hello", "ttl_minutes": 2.0},),
        )
        save_config(config, config_path)
        # Verify JSON content
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["register_hotkeys"] == False
        assert data["auto_launch_game"] == True
        assert data["game_install_dir"] == str(install_dir)
        assert data["automation"]["main_cookie_clicking_enabled"] == False
        assert data["automation"]["wrath_cookie_clicking_enabled"] == False
        assert data["automation"]["building_caps"] == {"Cursor": 123}
        assert data["automation"]["overlay_messages"] == [{"event_id": "hud:test", "text": "Hello", "ttl_minutes": 2.0}]
        # Load back
        loaded = load_config(config_path)
        assert loaded.register_hotkeys == False
        assert loaded.auto_launch_game == True
        assert loaded.game_install_dir == install_dir
        assert loaded.main_cookie_clicking_enabled == False
        assert loaded.wrath_cookie_clicking_enabled == False
        assert loaded.building_autobuy_enabled == True
        assert loaded.upgrade_horizon_seconds == 900.0
        assert loaded.building_horizon_seconds == 1200.0
        assert loaded.wrinkler_mode == "shiny_hunt"
        assert loaded.garden_mode == "shimmerlilly"
        assert loaded.building_caps == {"Cursor": 123}
        assert loaded.ignored_building_caps == ("Mine",)
        assert loaded.overlay_messages == ({"event_id": "hud:test", "text": "Hello", "ttl_minutes": 2.0},)
    finally:
        cleanup_workspace_temp_dir(tmpdir)


def test_load_missing_file_returns_default():
    """Loading a non-existent config returns defaults."""
    tmpdir = make_workspace_temp_dir()
    try:
        config_path = tmpdir / "missing.json"
        config = load_config(config_path)
        assert config.register_hotkeys == True
        assert config.auto_launch_game == False
        assert config.game_install_dir is None
    finally:
        cleanup_workspace_temp_dir(tmpdir)


def test_load_corrupted_file_returns_default():
    """Corrupted JSON falls back to defaults."""
    tmpdir = make_workspace_temp_dir()
    try:
        config_path = tmpdir / "corrupt.json"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json")
        config = load_config(config_path)
        # Should not crash, returns default
        assert isinstance(config, AppConfig)
        assert config.register_hotkeys == True
        assert config.auto_launch_game == False
        assert config.game_install_dir is None
    finally:
        cleanup_workspace_temp_dir(tmpdir)


def test_config_without_optional_fields():
    """Backward compatibility: missing fields use defaults."""
    tmpdir = make_workspace_temp_dir()
    try:
        config_path = tmpdir / "old.json"
        data = {
            # Only older fields may be present
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        config = load_config(config_path)
        assert config.register_hotkeys == True  # default
        assert config.auto_launch_game == False
        assert config.game_install_dir is None
    finally:
        cleanup_workspace_temp_dir(tmpdir)
