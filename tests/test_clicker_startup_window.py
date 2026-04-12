import unittest
from clicker_bot.startup_policy import (
    ATTACH_STARTUP_DELAY,
    GAME_ATTACH_WAIT_SECONDS,
    STARTUP_DELAY,
    should_launch_new_game_process,
)


class StartupWindowTests(unittest.TestCase):
    def test_attach_startup_delay_is_shorter_than_full_launch_delay(self):
        self.assertLess(ATTACH_STARTUP_DELAY, STARTUP_DELAY)

    def test_attach_wait_is_short(self):
        self.assertLessEqual(GAME_ATTACH_WAIT_SECONDS, 2.0)

    def test_launch_gate_still_keys_only_off_window_presence(self):
        self.assertTrue(should_launch_new_game_process(None))


if __name__ == "__main__":
    unittest.main()
