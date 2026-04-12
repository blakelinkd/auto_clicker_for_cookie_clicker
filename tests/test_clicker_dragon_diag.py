import unittest

from clicker_bot.dragon_diagnostics import build_dragon_diag
from clicker_bot.snapshot_extractors import normalize_snapshot_target


class DragonDiagTests(unittest.TestCase):
    @staticmethod
    def _extract_dragon_diag(snapshot, to_screen_point):
        return build_dragon_diag(
            snapshot,
            to_screen_point=to_screen_point,
            normalize_target=normalize_snapshot_target,
        )

    def test_cookie_stage_is_actionable_when_affordable(self):
        snapshot = {
            "dragon": {
                "unlocked": True,
                "open": False,
                "level": 2,
                "maxLevel": 27,
                "currentName": "Dragon egg",
                "nextAction": "Chip it",
                "nextCostText": "4000000 cookies",
                "nextCostAffordable": True,
                "nextCostType": "cookies",
                "nextCookieOnly": True,
                "dragonTab": {"clickX": 10, "clickY": 20},
            }
        }
        diag = self._extract_dragon_diag(snapshot, lambda x, y: (x + 100, y + 200))
        self.assertTrue(diag["available"])
        self.assertTrue(diag["actionable"])
        self.assertEqual(diag["reason"], "dragon_ready")
        self.assertEqual(diag["open_target"]["screen_x"], 110)

    def test_building_sacrifice_stage_becomes_actionable_when_affordable(self):
        snapshot = {
            "dragon": {
                "unlocked": True,
                "open": True,
                "level": 5,
                "maxLevel": 27,
                "currentName": "Krumblor, cookie hatchling",
                "nextAction": "Train Dragon Cursor",
                "nextCostText": "100 cursors",
                "nextCostAffordable": True,
                "nextCostType": "building_sacrifice",
                "nextCookieOnly": False,
                "nextRequiredBuildingName": "Cursor",
                "nextRequiredBuildingAmount": 100,
                "nextRequiredBuildingOwned": 100,
                "dragonTab": {"clickX": 10, "clickY": 20},
                "actionButton": {"clickX": 30, "clickY": 40},
            }
        }
        diag = self._extract_dragon_diag(snapshot, lambda x, y: (x, y))
        self.assertTrue(diag["available"])
        self.assertTrue(diag["actionable"])
        self.assertEqual(diag["reason"], "dragon_ready")
        self.assertEqual(diag["next_required_building_name"], "Cursor")
        self.assertEqual(diag["next_required_building_owned"], 100)

    def test_building_sacrifice_stage_waits_when_floor_not_met(self):
        snapshot = {
            "dragon": {
                "unlocked": True,
                "open": True,
                "level": 5,
                "maxLevel": 27,
                "currentName": "Krumblor, cookie hatchling",
                "nextAction": "Train Dragon Cursor",
                "nextCostText": "100 cursors",
                "nextCostAffordable": False,
                "nextCostType": "building_sacrifice",
                "nextCookieOnly": False,
                "nextRequiredBuildingName": "Cursor",
                "nextRequiredBuildingAmount": 100,
                "nextRequiredBuildingOwned": 63,
                "dragonTab": {"clickX": 10, "clickY": 20},
                "actionButton": {"clickX": 30, "clickY": 40},
            }
        }
        diag = self._extract_dragon_diag(snapshot, lambda x, y: (x, y))
        self.assertTrue(diag["available"])
        self.assertFalse(diag["actionable"])
        self.assertEqual(diag["reason"], "waiting_for_dragon_building_floor")

    def test_building_sacrifice_stage_waits_when_affordable_flag_is_wrong(self):
        snapshot = {
            "dragon": {
                "unlocked": True,
                "open": True,
                "level": 23,
                "maxLevel": 27,
                "currentName": "Krumblor, cookie dragon",
                "nextAction": "Train Supreme Intellect Aura",
                "nextCostText": "100 cortex bakers",
                "nextCostAffordable": True,
                "nextCostType": "building_sacrifice",
                "nextCookieOnly": False,
                "nextRequiredBuildingName": "Cortex baker",
                "nextRequiredBuildingAmount": 100,
                "nextRequiredBuildingOwned": 56,
                "dragonTab": {"clickX": 10, "clickY": 20},
                "actionButton": {"clickX": 30, "clickY": 40},
            }
        }
        diag = self._extract_dragon_diag(snapshot, lambda x, y: (x, y))
        self.assertTrue(diag["available"])
        self.assertFalse(diag["actionable"])
        self.assertEqual(diag["reason"], "waiting_for_dragon_building_floor")


if __name__ == "__main__":
    unittest.main()
