import unittest
from types import SimpleNamespace

from clicker_bot.minigame_access import plan_minigame_store_access


class MinigameAccessTests(unittest.TestCase):
    def test_prefers_grimoire_when_closed_without_open_target(self):
        calls = []

        owner, action = plan_minigame_store_access(
            {},
            spell_diag={"reason": "grimoire_closed", "has_open_target": False},
            bank_diag={"reason": "bank_closed_missing_open_control"},
            garden_diag={"reason": "garden_closed_missing_open_control"},
            minigame_building_ids={"grimoire": 7, "bank": 5, "garden": 2},
            plan_focus_building=lambda snapshot, to_screen_point, building_id: calls.append(building_id)
            or SimpleNamespace(kind=f"open_{building_id}"),
            to_screen_point=lambda x, y: (x, y),
        )

        self.assertEqual(owner, "grimoire")
        self.assertEqual(action.kind, "open_7")
        self.assertEqual(calls, [7])

    def test_skips_grimoire_when_open_target_exists_and_falls_back_to_bank(self):
        calls = []

        owner, action = plan_minigame_store_access(
            {},
            spell_diag={"reason": "grimoire_closed", "has_open_target": True},
            bank_diag={"reason": "bank_closed_missing_open_control"},
            garden_diag={"reason": "garden_closed_missing_open_control"},
            minigame_building_ids={"grimoire": 7, "bank": 5, "garden": 2},
            plan_focus_building=lambda snapshot, to_screen_point, building_id: calls.append(building_id)
            or SimpleNamespace(kind=f"open_{building_id}"),
            to_screen_point=lambda x, y: (x, y),
        )

        self.assertEqual(owner, "bank")
        self.assertEqual(action.kind, "open_5")
        self.assertEqual(calls, [5])

    def test_tries_next_candidate_when_focus_action_is_unavailable(self):
        calls = []

        def plan_focus_building(snapshot, to_screen_point, building_id):
            calls.append(building_id)
            if building_id == 5:
                return None
            return SimpleNamespace(kind=f"open_{building_id}")

        owner, action = plan_minigame_store_access(
            {},
            spell_diag={},
            bank_diag={"reason": "bank_closed_missing_open_control"},
            garden_diag={"reason": "garden_closed_missing_open_control"},
            minigame_building_ids={"grimoire": 7, "bank": 5, "garden": 2},
            plan_focus_building=plan_focus_building,
            to_screen_point=lambda x, y: (x, y),
        )

        self.assertEqual(owner, "garden")
        self.assertEqual(action.kind, "open_2")
        self.assertEqual(calls, [5, 2])

    def test_returns_none_when_no_candidates_can_be_opened(self):
        owner, action = plan_minigame_store_access(
            {},
            spell_diag={},
            bank_diag={"reason": "bank_closed_missing_open_control"},
            garden_diag={"reason": "garden_closed_missing_open_control"},
            minigame_building_ids={"grimoire": 7, "bank": 5, "garden": 2},
            plan_focus_building=lambda snapshot, to_screen_point, building_id: None,
            to_screen_point=lambda x, y: (x, y),
        )

        self.assertIsNone(owner)
        self.assertIsNone(action)


if __name__ == "__main__":
    unittest.main()
