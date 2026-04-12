import unittest
from unittest.mock import patch

from clicker_bot.lifecycle import BotLifecycle, BotLifecycleState


class _ThreadStub:
    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon
        self.started = False
        self._alive = False

    def start(self):
        self.started = True
        self._alive = True

    def is_alive(self):
        return self._alive


class BotLifecycleTests(unittest.TestCase):
    def test_start_creates_dom_and_optional_click_threads(self):
        state = BotLifecycleState()
        lifecycle = BotLifecycle(state=state, click_loop=lambda: None, dom_loop=lambda: None)

        with patch("clicker_bot.lifecycle.threading.Thread", side_effect=lambda **kwargs: _ThreadStub(**kwargs)):
            lifecycle.start(enable_click_loop=True)

        self.assertTrue(state.active)
        self.assertIsNotNone(state.click_thread)
        self.assertTrue(state.click_thread.started)
        self.assertIsNotNone(state.dom_thread)
        self.assertTrue(state.dom_thread.started)

    def test_ensure_click_loop_reuses_existing_live_thread(self):
        state = BotLifecycleState(click_thread=_ThreadStub())
        state.click_thread._alive = True
        lifecycle = BotLifecycle(state=state, click_loop=lambda: None, dom_loop=lambda: None)

        with patch("clicker_bot.lifecycle.threading.Thread", side_effect=lambda **kwargs: _ThreadStub(**kwargs)):
            started = lifecycle.ensure_click_loop()

        self.assertFalse(started)
