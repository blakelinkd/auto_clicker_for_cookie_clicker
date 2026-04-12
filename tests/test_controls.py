import unittest
from types import SimpleNamespace

from clicker_bot.controls import BotControls


class _LogStub:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, message):
        self.infos.append(message)

    def warning(self, message):
        self.warnings.append(message)


class _LifecycleStub:
    def __init__(self):
        self.state = SimpleNamespace(click_thread="thread")
        self.ensure_calls = 0

    def ensure_click_loop(self):
        self.ensure_calls += 1
        return True


class _AutobuyerStub:
    def __init__(self):
        self.payback_horizon_seconds = 600.0
        self.caps = {}
        self.ignored = {}

    def set_building_cap(self, name, cap):
        self.caps[name] = cap
        return 123 if cap is None else cap

    def set_payback_horizon_seconds(self, value):
        self.payback_horizon_seconds = float(value)
        return self.payback_horizon_seconds

    def set_building_cap_ignored(self, name, ignored):
        self.ignored[name] = bool(ignored)
        return self.ignored[name]


class BotControlsTests(unittest.TestCase):
    def _build_controls(self):
        log = _LogStub()
        runtime_updates = []
        events = []
        mode_changes = []
        lifecycle = _LifecycleStub()
        autobuyer = _AutobuyerStub()
        state = {
            "active": True,
            "main_cookie_clicking_enabled": False,
            "shimmer_autoclick_enabled": True,
            "building_autobuy_enabled": False,
            "lucky_reserve_enabled": False,
            "upgrade_autobuy_enabled": True,
            "ascension_prep_enabled": False,
            "stock_trading_enabled": False,
            "upgrade_horizon_seconds": 1800.0,
            "click_thread": None,
        }

        def setter(name):
            return lambda value: state.__setitem__(name, value)

        controls = BotControls(
            log=log,
            set_runtime=lambda **kwargs: runtime_updates.append(kwargs),
            record_event=lambda message: events.append(message),
            log_mode_change=lambda feature, enabled, source="unknown": mode_changes.append((feature, enabled, source)),
            get_active=lambda: state["active"],
            get_main_cookie_clicking_enabled=lambda: state["main_cookie_clicking_enabled"],
            set_main_cookie_clicking_enabled=setter("main_cookie_clicking_enabled"),
            get_shimmer_autoclick_enabled=lambda: state["shimmer_autoclick_enabled"],
            set_shimmer_autoclick_enabled=setter("shimmer_autoclick_enabled"),
            get_building_autobuy_enabled=lambda: state["building_autobuy_enabled"],
            set_building_autobuy_enabled=setter("building_autobuy_enabled"),
            get_lucky_reserve_enabled=lambda: state["lucky_reserve_enabled"],
            set_lucky_reserve_enabled=setter("lucky_reserve_enabled"),
            get_upgrade_autobuy_enabled=lambda: state["upgrade_autobuy_enabled"],
            set_upgrade_autobuy_enabled=setter("upgrade_autobuy_enabled"),
            get_ascension_prep_enabled=lambda: state["ascension_prep_enabled"],
            set_ascension_prep_enabled=setter("ascension_prep_enabled"),
            get_stock_trading_enabled=lambda: state["stock_trading_enabled"],
            set_stock_trading_enabled=setter("stock_trading_enabled"),
            get_lifecycle=lambda: lifecycle,
            set_click_thread=setter("click_thread"),
            building_autobuyer=autobuyer,
            set_upgrade_horizon_value=setter("upgrade_horizon_seconds"),
            wrinkler_controller=SimpleNamespace(mode="hold"),
            wrinkler_modes=("hold", "seasonal_farm", "shiny_hunt"),
        )
        return controls, state, runtime_updates, events, mode_changes, lifecycle, autobuyer, log

    def test_toggle_main_autoclick_updates_runtime_and_starts_click_loop(self):
        controls, state, runtime_updates, events, mode_changes, lifecycle, _autobuyer, log = self._build_controls()

        enabled = controls.toggle_main_autoclick(source="hud_button")

        self.assertTrue(enabled)
        self.assertTrue(state["main_cookie_clicking_enabled"])
        self.assertEqual(runtime_updates[-1], {"main_cookie_clicking_enabled": True})
        self.assertEqual(events[-1], "Main autoclick ON")
        self.assertEqual(mode_changes[-1], ("Main autoclick", True, "hud_button"))
        self.assertEqual(state["click_thread"], "thread")
        self.assertEqual(lifecycle.ensure_calls, 1)
        self.assertTrue(any("Main cookie click loop enabled" in msg for msg in log.infos))

    def test_set_upgrade_horizon_validates_and_updates(self):
        controls, state, runtime_updates, events, _mode_changes, _lifecycle, _autobuyer, _log = self._build_controls()

        ok, value = controls.set_upgrade_horizon_seconds(900)

        self.assertTrue(ok)
        self.assertEqual(value, 900.0)
        self.assertEqual(state["upgrade_horizon_seconds"], 900.0)
        self.assertEqual(runtime_updates[-1], {"upgrade_horizon_seconds": 900.0})
        self.assertEqual(events[-1], "Upgrade horizon set to 15m")

    def test_cycle_wrinkler_mode_updates_runtime(self):
        controls, _state, runtime_updates, events, _mode_changes, _lifecycle, _autobuyer, _log = self._build_controls()

        next_mode = controls.cycle_wrinkler_mode()

        self.assertEqual(next_mode, "seasonal_farm")
        self.assertEqual(runtime_updates[-1], {"wrinkler_mode": "seasonal_farm"})
        self.assertEqual(events[-1], "Wrinkler mode seasonal_farm")
