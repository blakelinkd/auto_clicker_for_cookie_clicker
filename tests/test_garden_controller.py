import unittest

from clicker_bot.features.garden_controller import GardenController


def _identity_point(x, y):
    return x, y


class _LogStub:
    def info(self, message):
        pass


def _rect(x, y):
    return {
        "left": x - 5,
        "top": y - 5,
        "right": x + 5,
        "bottom": y + 5,
        "width": 10,
        "height": 10,
        "centerX": x,
        "centerY": y,
    }


def _garden_snapshot(timestamp, next_step_at, cookies):
    plot = []
    for y in range(3):
        for x in range(3):
            plant_key = None
            is_mature = False
            is_dying = False
            age = 0
            mature_age = None
            if (x, y) in {(1, 0), (1, 2)}:
                plant_key = "bakerWheat"
                is_mature = True
                is_dying = True
                age = 95
                mature_age = 35
            elif (x, y) in {(0, 1), (2, 1)}:
                plant_key = "thumbcorn"
                is_mature = True
                is_dying = True
                age = 95
                mature_age = 20
            plot.append(
                {
                    "x": x,
                    "y": y,
                    "unlocked": True,
                    "target": _rect(100 + (x * 20), 100 + (y * 20)),
                    "plantId": None,
                    "plantKey": plant_key,
                    "plantName": plant_key,
                    "age": age,
                    "matureAge": mature_age,
                    "isMature": is_mature,
                    "isDying": is_dying,
                    "immortal": False,
                }
            )

    return {
        "timestamp": timestamp,
        "cookies": cookies,
        "garden": {
            "onMinigame": True,
            "openControl": _rect(50, 50),
            "farmLevel": 9,
            "farmAmount": 200,
            "soil": {"id": 3, "key": "woodchips", "name": "Wood Chips", "tickMinutes": 5},
            "soils": [
                {"id": 1, "key": "fertilizer", "name": "Fertilizer", "tickMinutes": 3, "selected": False, "available": True, "target": _rect(20, 20)},
                {"id": 3, "key": "woodchips", "name": "Wood Chips", "tickMinutes": 5, "selected": True, "available": True, "target": _rect(30, 20)},
                {"id": 4, "key": "clay", "name": "Clay", "tickMinutes": 15, "selected": False, "available": True, "target": _rect(40, 20)},
            ],
            "freeze": False,
            "nextStepAt": next_step_at,
            "nextSoilAt": timestamp - 1000,
            "plotWidth": 3,
            "plotHeight": 3,
            "plotTileCount": 9,
            "plotOccupied": 4,
            "plotMature": 4,
            "plantsUnlocked": 2,
            "plantsTotal": 3,
            "seedSelected": None,
            "seeds": [
                {"id": 0, "key": "bakerWheat", "name": "Baker's wheat", "unlocked": True, "plantable": True, "selected": False, "matureAge": 35, "cost": 1, "target": _rect(10, 200)},
                {"id": 1, "key": "thumbcorn", "name": "Thumbcorn", "unlocked": True, "plantable": True, "selected": False, "matureAge": 20, "cost": 5, "target": _rect(30, 200)},
                {"id": 2, "key": "cronerice", "name": "Cronerice", "unlocked": False, "plantable": True, "selected": False, "matureAge": 55, "cost": 15, "target": _rect(50, 200)},
            ],
            "plot": plot,
        },
    }


class GardenControllerMutationWindowTests(unittest.TestCase):
    def setUp(self):
        self.controller = GardenController(_LogStub())

    def _set_fertilizer_active(self, snapshot):
        snapshot["garden"]["soil"] = {"id": 1, "key": "fertilizer", "name": "Fertilizer", "tickMinutes": 3}
        for soil in snapshot["garden"]["soils"]:
            soil["selected"] = soil["key"] == "fertilizer"

    def test_refreshes_layout_after_last_mutation_tick_when_affordable(self):
        before_deadline = _garden_snapshot(timestamp=1000, next_step_at=1500, cookies=20)
        self._set_fertilizer_active(before_deadline)
        action = self.controller.get_action(before_deadline, _identity_point, now=1.0)
        self.assertTrue(action is None or action.kind in {"set_soil", "select_seed", "plant_seed"})

        after_deadline = _garden_snapshot(timestamp=1600, next_step_at=2200, cookies=20)
        self._set_fertilizer_active(after_deadline)
        action = self.controller.get_action(after_deadline, _identity_point, now=2.0)
        self.assertIsNotNone(action)
        self.assertIn(action.kind, {"set_soil", "clear_tile", "select_seed", "plant_seed"})

    def test_holds_refresh_when_replant_cost_is_not_affordable(self):
        before_deadline = _garden_snapshot(timestamp=1000, next_step_at=1500, cookies=4)
        self._set_fertilizer_active(before_deadline)
        action = self.controller.get_action(before_deadline, _identity_point, now=1.0)
        self.assertTrue(action is None or action.kind == "set_soil")

        after_deadline = _garden_snapshot(timestamp=1600, next_step_at=2200, cookies=4)
        self._set_fertilizer_active(after_deadline)
        action = self.controller.get_action(after_deadline, _identity_point, now=2.0)
        self.assertTrue(action is None or action.kind == "set_soil")

    def test_refocuses_garden_when_targets_are_missing(self):
        snapshot = _garden_snapshot(timestamp=1600, next_step_at=2200, cookies=20)
        snapshot["garden"]["plot"] = [
            dict(tile, target=None) if tile["unlocked"] else tile
            for tile in snapshot["garden"]["plot"]
        ]

        action = self.controller.get_action(snapshot, _identity_point, now=2.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "focus_garden")

    def test_opens_garden_when_closed_even_without_immediate_work(self):
        snapshot = _garden_snapshot(timestamp=1600, next_step_at=2200, cookies=20)
        snapshot["garden"]["onMinigame"] = False

        action = self.controller.get_action(snapshot, _identity_point, now=2.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "open_garden")

    def test_prefers_woodchips_for_mutation_plan_when_available(self):
        snapshot = _garden_snapshot(timestamp=1600, next_step_at=2200, cookies=20)
        state = self.controller.extract_state(snapshot, _identity_point)
        plan = self.controller._choose_plan(state)

        desired_soil = self.controller._choose_desired_soil(state, plan)

        self.assertIsNotNone(desired_soil)
        self.assertEqual(desired_soil["key"], "woodchips")

    def test_falls_back_to_fertilizer_for_mutation_plan_when_woodchips_unavailable(self):
        snapshot = _garden_snapshot(timestamp=1600, next_step_at=2200, cookies=20)
        for soil in snapshot["garden"]["soils"]:
            if soil["key"] == "woodchips":
                soil["available"] = False
        state = self.controller.extract_state(snapshot, _identity_point)
        plan = self.controller._choose_plan(state)

        desired_soil = self.controller._choose_desired_soil(state, plan)

        self.assertIsNotNone(desired_soil)
        self.assertEqual(desired_soil["key"], "fertilizer")

    def test_keeps_support_layout_while_target_is_growing(self):
        snapshot = _garden_snapshot(timestamp=1600, next_step_at=2200, cookies=20)
        for tile in snapshot["garden"]["plot"]:
            if tile["x"] == 1 and tile["y"] == 1:
                tile["plantId"] = 2
                tile["plantKey"] = "cronerice"
                tile["plantName"] = "cronerice"
                tile["isMature"] = False
                tile["isDying"] = False
                tile["age"] = 10
                tile["matureAge"] = 55
            elif tile["unlocked"]:
                tile["plantId"] = None
                tile["plantKey"] = None
                tile["plantName"] = None
                tile["isMature"] = False
                tile["isDying"] = False
                tile["age"] = 0
                tile["matureAge"] = None

        action = self.controller.get_action(snapshot, _identity_point, now=2.0)

        self.assertIsNotNone(action)
        self.assertIn(action.kind, {"set_soil", "select_seed", "plant_seed"})

    def test_harvests_any_mature_locked_seed_not_just_active_plan_target(self):
        snapshot = _garden_snapshot(timestamp=1600, next_step_at=2200, cookies=20)
        snapshot["garden"]["seeds"].append(
            {
                "id": 3,
                "key": "gildmillet",
                "name": "Gildmillet",
                "unlocked": False,
                "plantable": True,
                "selected": False,
                "matureAge": 40,
                "cost": 30,
                "target": _rect(70, 200),
            }
        )
        center_tile = next(
            tile for tile in snapshot["garden"]["plot"]
            if tile["x"] == 1 and tile["y"] == 1
        )
        center_tile["plantId"] = 3
        center_tile["plantKey"] = "gildmillet"
        center_tile["plantName"] = "Gildmillet"
        center_tile["isMature"] = True
        center_tile["isDying"] = False
        center_tile["age"] = 50
        center_tile["matureAge"] = 40

        action = self.controller.get_action(snapshot, _identity_point, now=2.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "harvest_target")
        self.assertIn("gildmillet", action.detail)
        self.assertEqual((action.tile_x, action.tile_y), (1, 1))


if __name__ == "__main__":
    unittest.main()
