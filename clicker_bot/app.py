from dataclasses import dataclass
from types import ModuleType
from typing import Callable

from .config import AppConfig


@dataclass(frozen=True)
class HotkeyBinding:
    combo: str
    callback: Callable[[], None]


class BotApplication:
    """Owns startup wiring while legacy runtime logic remains in clicker.py."""

    def __init__(self, legacy_module: ModuleType, config: AppConfig | None = None):
        self.legacy = legacy_module
        self.config = AppConfig() if config is None else config
        self._hotkeys_registered = False

    def get_hotkey_bindings(self) -> tuple[HotkeyBinding, ...]:
        return (
            HotkeyBinding("ctrl+alt+f11", self.legacy.exit_program),
            HotkeyBinding("ctrl+alt+f12", lambda: self.legacy.toggle(source="hotkey_ctrl_alt_f12")),
            HotkeyBinding("ctrl+alt+f8", self.legacy.cycle_wrinkler_mode),
            HotkeyBinding("ctrl+alt+f9", lambda: self.legacy.toggle_stock_trading(source="hotkey_ctrl_alt_f9")),
            HotkeyBinding("ctrl+alt+f10", lambda: self.legacy.toggle_building_autobuy(source="hotkey_ctrl_alt_f10")),
            HotkeyBinding("ctrl+alt+f7", lambda: self.legacy.toggle_upgrade_autobuy(source="hotkey_ctrl_alt_f7")),
            HotkeyBinding("ctrl+alt+f6", lambda: self.legacy.toggle_ascension_prep(source="hotkey_ctrl_alt_f6")),
            HotkeyBinding("ctrl+alt+f5", self.legacy._dump_shimmer_seed_history),
        )

    def register_hotkeys(self) -> None:
        if not self.config.register_hotkeys or self._hotkeys_registered:
            return
        for binding in self.get_hotkey_bindings():
            self.legacy.keyboard.add_hotkey(binding.combo, binding.callback)
        self._hotkeys_registered = True

    def initialize_runtime(self) -> bool:
        self.legacy.sync_mod_files()
        launched_game = self.legacy._launch_game_if_needed()
        self.legacy.game_rect = self.legacy.get_game_window(log_missing=False)
        if not self.legacy.game_rect:
            self.legacy.log.warning("Game window not found at startup - will retry on toggle.")
        else:
            self.legacy._focus_game_window()
        return launched_game

    def run(self):
        self.register_hotkeys()
        self.initialize_runtime()
        self.legacy.log.info(
            "Auto-clicker ready. Bot starts paused; use the HUD Bot button or Ctrl+Alt+F12 to start. "
            "(Ctrl+Alt+F8 to cycle wrinkler mode, "
            "Ctrl+Alt+F6 to toggle ascension prep, Ctrl+Alt+F7 to toggle upgrade autobuy, Ctrl+Alt+F9 to toggle stock trading, Ctrl+Alt+F10 to toggle building autobuy, "
            "Ctrl+Alt+F11 to exit)"
        )
        dashboard = self.legacy.start_dashboard()
        dashboard.run()
        return dashboard


def build_default_application() -> BotApplication:
    import clicker

    return BotApplication(clicker)


def main() -> None:
    build_default_application().run()
