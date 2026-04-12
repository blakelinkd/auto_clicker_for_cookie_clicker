import unittest
from types import SimpleNamespace

from clicker_bot.activation import BotActivationController


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
        self.state = SimpleNamespace(click_thread="click-thread", dom_thread="dom-thread")
        self.start_calls = []
        self.stop_calls = 0

    def start(self, *, enable_click_loop):
        self.start_calls.append(enable_click_loop)

    def stop(self):
        self.stop_calls += 1


class BotActivationControllerTests(unittest.TestCase):
    def test_toggle_on_launches_and_starts_lifecycle(self):
        log = _LogStub()
        runtime_updates = []
        mode_changes = []
        events = []
        reset_calls = []
        game_rect_state = {"value": None}
        active = {"value": False}
        lifecycle = _LifecycleStub()
        get_window_calls = []

        def flip_active():
            active["value"] = not active["value"]
            return active["value"]

        controller = BotActivationController(
            log=log,
            flip_active=flip_active,
            set_runtime=lambda **kwargs: runtime_updates.append(kwargs),
            log_mode_change=lambda feature, enabled, source="unknown": mode_changes.append((feature, enabled, source)),
            reset_shimmer_tracking=lambda reason, clear_click_state=False: reset_calls.append((reason, clear_click_state)),
            record_event=lambda message: events.append(message),
            get_game_window=lambda log_missing=True: get_window_calls.append(log_missing) or None,
            launch_game_if_needed=lambda: events.append("launch"),
            focus_game_window=lambda: events.append("focus"),
            get_main_cookie_clicking_enabled=lambda: True,
            get_lifecycle=lambda: lifecycle,
            set_click_thread=lambda value: game_rect_state.__setitem__("click_thread", value),
            set_dom_thread=lambda value: game_rect_state.__setitem__("dom_thread", value),
            set_game_rect=lambda value: game_rect_state.__setitem__("value", value),
        )

        state = controller.toggle(source="hotkey")

        self.assertTrue(state)
        self.assertEqual(runtime_updates[-1], {"active": True})
        self.assertEqual(mode_changes[-1], ("Clicker", True, "hotkey"))
        self.assertEqual(reset_calls[-1], ("bot_started", True))
        self.assertIn("Clicker ON", events)
        self.assertIn("launch", events)
        self.assertEqual(get_window_calls, [True, False])
        self.assertEqual(lifecycle.start_calls, [True])
        self.assertEqual(game_rect_state["click_thread"], "click-thread")
        self.assertEqual(game_rect_state["dom_thread"], "dom-thread")

    def test_toggle_off_stops_lifecycle(self):
        log = _LogStub()
        runtime_updates = []
        events = []
        reset_calls = []
        active = {"value": True}
        lifecycle = _LifecycleStub()

        def flip_active():
            active["value"] = not active["value"]
            return active["value"]

        controller = BotActivationController(
            log=log,
            flip_active=flip_active,
            set_runtime=lambda **kwargs: runtime_updates.append(kwargs),
            log_mode_change=lambda *args, **kwargs: None,
            reset_shimmer_tracking=lambda reason, clear_click_state=False: reset_calls.append((reason, clear_click_state)),
            record_event=lambda message: events.append(message),
            get_game_window=lambda log_missing=True: (1, 2, 3, 4),
            launch_game_if_needed=lambda: None,
            focus_game_window=lambda: None,
            get_main_cookie_clicking_enabled=lambda: True,
            get_lifecycle=lambda: lifecycle,
            set_click_thread=lambda value: None,
            set_dom_thread=lambda value: None,
            set_game_rect=lambda value: None,
        )

        state = controller.toggle(source="hud_button")

        self.assertFalse(state)
        self.assertEqual(runtime_updates[-1], {"active": False})
        self.assertEqual(reset_calls[-1], ("bot_paused", True))
        self.assertEqual(lifecycle.stop_calls, 1)
        self.assertEqual(events[-1], "Clicker OFF")
