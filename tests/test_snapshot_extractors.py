import unittest

from clicker_bot.snapshot_extractors import (
    extract_big_cookie,
    extract_buffs,
    extract_shimmers,
    extract_spell,
    normalize_snapshot_target,
)


class SnapshotExtractorTests(unittest.TestCase):
    @staticmethod
    def _to_screen_point(x, y):
        return x + 100, y + 200

    def test_normalize_snapshot_target_prefers_click_coordinates(self):
        target = normalize_snapshot_target(
            {"clickX": 5, "clickY": 6, "centerX": 9, "centerY": 10},
            self._to_screen_point,
        )

        self.assertEqual(
            target,
            {
                "client_x": 5,
                "client_y": 6,
                "screen_x": 105,
                "screen_y": 206,
            },
        )

    def test_extract_big_cookie_uses_center_coordinates(self):
        cookie = extract_big_cookie(
            {"bigCookie": {"centerX": 25, "centerY": 50}},
            to_screen_point=self._to_screen_point,
        )

        self.assertEqual(
            cookie,
            {
                "client_x": 25,
                "client_y": 50,
                "screen_x": 125,
                "screen_y": 250,
            },
        )

    def test_extract_spell_returns_spell_and_target_data(self):
        spell = extract_spell(
            {
                "spell": {
                    "id": 7,
                    "key": "hand_of_fate",
                    "name": "Force the Hand of Fate",
                    "ready": 1,
                    "onMinigame": 0,
                    "cost": 77,
                    "magic": 88,
                    "maxMagic": 99,
                    "rect": {"centerX": 12, "centerY": 34},
                }
            },
            to_screen_point=self._to_screen_point,
        )

        self.assertEqual(spell["id"], 7)
        self.assertEqual(spell["name"], "Force the Hand of Fate")
        self.assertTrue(spell["ready"])
        self.assertFalse(spell["on_minigame"])
        self.assertEqual(spell["screen_x"], 112)
        self.assertEqual(spell["screen_y"], 234)

    def test_extract_shimmers_skips_invalid_entries_and_carries_seed(self):
        shimmers = extract_shimmers(
            {
                "seed": "abc123",
                "shimmers": [
                    {"id": 1, "centerX": 10, "centerY": 20, "type": "golden", "wrath": False, "life": 3, "dur": 10},
                    {"id": 2, "centerX": None, "centerY": 20},
                    "bad",
                ],
            },
            to_screen_point=self._to_screen_point,
        )

        self.assertEqual(len(shimmers), 1)
        self.assertEqual(shimmers[0]["id"], 1)
        self.assertEqual(shimmers[0]["seed"], "abc123")
        self.assertEqual(shimmers[0]["screen_x"], 110)
        self.assertEqual(shimmers[0]["screen_y"], 220)

    def test_extract_buffs_falls_back_to_spellbook_active_buffs(self):
        buffs = extract_buffs(
            {
                "spellbook": {
                    "activeBuffs": [
                        {"key": "frenzy", "time": 10, "maxTime": 20, "multCpS": 7.0, "multClick": 1.0},
                        {"name": "Click frenzy", "time": 5, "maxTime": 10, "multCpS": 1.0, "multClick": 777.0},
                        {},
                    ]
                }
            }
        )

        self.assertEqual(
            buffs,
            [
                {
                    "key": "frenzy",
                    "name": "frenzy",
                    "time": 10,
                    "max_time": 20,
                    "mult_cpS": 7.0,
                    "mult_click": 1.0,
                },
                {
                    "key": "Click frenzy",
                    "name": "Click frenzy",
                    "time": 5,
                    "max_time": 10,
                    "mult_cpS": 1.0,
                    "mult_click": 777.0,
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
