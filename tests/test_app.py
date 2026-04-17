import unittest
from types import SimpleNamespace

from clicker_bot.app import BotApplication
from clicker_bot.config import AppConfig


class _KeyboardStub:
    def __init__(self):
        self.bindings = []

    def add_hotkey(self, combo, callback):
        self.bindings.append((combo, callback))


class _DashboardStub:
    def __init__(self):
        self.run_calls = 0

    def run(self):
        self.run_calls += 1


class _LogStub:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def warning(self, message):
        self.messages.append(("warning", message))


class BotApplicationTests(unittest.TestCase):
    def test_run_registers_hotkeys_initializes_runtime_and_runs_dashboard(self):
        keyboard = _KeyboardStub()
        dashboard = _DashboardStub()
        log = _LogStub()
        calls = []
        legacy = SimpleNamespace(
            keyboard=keyboard,
            log=log,
            game_rect=None,
            exit_program=lambda: calls.append("exit"),
            toggle=lambda source="unknown": calls.append(("toggle", source)),
            cycle_wrinkler_mode=lambda: calls.append("cycle_wrinkler_mode"),
            toggle_stock_trading=lambda source="unknown": calls.append(("toggle_stock_trading", source)),
            toggle_building_autobuy=lambda source="unknown": calls.append(("toggle_building_autobuy", source)),
            toggle_upgrade_autobuy=lambda source="unknown": calls.append(("toggle_upgrade_autobuy", source)),
            toggle_ascension_prep=lambda source="unknown": calls.append(("toggle_ascension_prep", source)),
            _dump_shimmer_seed_history=lambda: calls.append("dump_shimmer_seed_history"),
            sync_mod_files=lambda: calls.append("sync_mod_files"),
            _launch_game_if_needed=lambda: calls.append("launch_game") or False,
            get_game_window=lambda log_missing=False: calls.append(("get_game_window", log_missing)) or (1, 2, 3, 4),
            _focus_game_window=lambda: calls.append("focus_game_window"),
            start_dashboard=lambda use_qt_hud=False: calls.append("start_dashboard") or dashboard,
        )

        app = BotApplication(legacy, config=AppConfig(register_hotkeys=True, auto_launch_game=True))

        result = app.run()

        self.assertIs(result, dashboard)
        self.assertEqual(len(keyboard.bindings), 8)
        self.assertLess(calls.index("sync_mod_files"), calls.index("launch_game"))
        self.assertLess(calls.index("sync_mod_files"), calls.index("start_dashboard"))
        self.assertIn(("get_game_window", False), calls)
        self.assertIn("focus_game_window", calls)
        self.assertEqual(dashboard.run_calls, 1)

    def test_register_hotkeys_is_idempotent(self):
        keyboard = _KeyboardStub()
        legacy = SimpleNamespace(
            keyboard=keyboard,
            exit_program=lambda: None,
            toggle=lambda source="unknown": None,
            cycle_wrinkler_mode=lambda: None,
            toggle_stock_trading=lambda source="unknown": None,
            toggle_building_autobuy=lambda source="unknown": None,
            toggle_upgrade_autobuy=lambda source="unknown": None,
            toggle_ascension_prep=lambda source="unknown": None,
            _dump_shimmer_seed_history=lambda: None,
        )

        app = BotApplication(legacy)

        app.register_hotkeys()
        app.register_hotkeys()

        self.assertEqual(len(keyboard.bindings), 8)
