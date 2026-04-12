import unittest
from clicker_bot.startup_policy import should_launch_new_game_process


class LaunchGateTests(unittest.TestCase):
    def test_launches_only_when_no_window(self):
        self.assertTrue(should_launch_new_game_process(None))

    def test_skips_launch_when_window_already_found(self):
        self.assertFalse(should_launch_new_game_process((0, 0, 100, 100)))


if __name__ == "__main__":
    unittest.main()
