import unittest

from clicker_bot.pause_policy import (
    GARDEN_LONG_BUFF_THRESHOLD_FRAMES,
    get_active_click_buff_names,
    has_buff_only_non_click_pause,
    has_long_positive_active_buff,
    has_positive_active_buffs,
    should_allow_garden_action,
    should_allow_non_click_actions_during_pause,
)
from garden_controller import GardenController


PRODUCTION_STACK_BUFF_KEYS = {
    "Frenzy",
    "Dragon Harvest",
    "Elder frenzy",
    "Building special",
}
KNOWN_NEGATIVE_BUFFS = {
    "Clot",
    "Ruin cookies",
    "Cursed finger",
}
KNOWN_CLICK_VALUE_BUFFS = {
    "Click frenzy",
    "Dragonflight",
}


class GardenGateTests(unittest.TestCase):
    def test_allows_garden_action_without_positive_buffs(self):
        allowed = should_allow_garden_action(
            {"buffs": []},
            {"planner_state": "harvest_target"},
            production_stack_buff_keys=PRODUCTION_STACK_BUFF_KEYS,
            known_click_value_buffs=KNOWN_CLICK_VALUE_BUFFS,
        )
        self.assertTrue(allowed)

    def test_allows_garden_action_for_short_production_buff(self):
        snapshot = {
            "buffs": [
                {"name": "Frenzy", "time": 3000, "maxTime": 3600, "multCpS": 7.0},
            ]
        }
        allowed = should_allow_garden_action(
            snapshot,
            {"planner_state": "harvest_target"},
            production_stack_buff_keys=PRODUCTION_STACK_BUFF_KEYS,
            known_click_value_buffs=KNOWN_CLICK_VALUE_BUFFS,
        )
        self.assertTrue(allowed)

    def test_allows_garden_action_for_long_positive_buff(self):
        snapshot = {
            "buffs": [
                {"name": "Dragon Harvest", "time": 12000, "maxTime": 12000, "multCpS": 15.0},
            ]
        }
        allowed = should_allow_garden_action(
            snapshot,
            {"planner_state": "harvest_target"},
            production_stack_buff_keys=PRODUCTION_STACK_BUFF_KEYS,
            known_click_value_buffs=KNOWN_CLICK_VALUE_BUFFS,
        )
        self.assertTrue(allowed)

    def test_non_click_pause_helper_currently_keeps_actions_paused(self):
        snapshot = {
            "buffs": [
                {"name": "Dragon Harvest", "time": 12000, "maxTime": 12000, "multCpS": 15.0},
            ]
        }
        allowed = should_allow_non_click_actions_during_pause(
            snapshot,
            ("valuable_buffs=('Dragon Harvest',)",),
        )
        self.assertFalse(allowed)

    def test_keeps_other_non_click_actions_paused_when_reason_is_not_buff_only(self):
        snapshot = {
            "buffs": [
                {"name": "Dragon Harvest", "time": 12000, "maxTime": 12000, "multCpS": 15.0},
            ]
        }
        allowed = should_allow_non_click_actions_during_pause(
            snapshot,
            ("valuable_buffs=('Dragon Harvest',)", "combo_reason=buffing"),
        )
        self.assertFalse(allowed)

    def test_active_click_buff_names_skip_production_buffs(self):
        names = get_active_click_buff_names(
            [
                {"name": "Frenzy", "multClick": 777.0},
                {"name": "Click frenzy", "multClick": 777.0},
            ],
            production_stack_buff_keys=PRODUCTION_STACK_BUFF_KEYS,
            known_click_value_buffs=KNOWN_CLICK_VALUE_BUFFS,
        )
        self.assertEqual(names, ("Click frenzy",))

    def test_positive_and_long_buff_helpers_detect_spellbook_buffs(self):
        snapshot = {
            "spellbook": {
                "activeBuffs": [
                    {
                        "name": "Helpful buff",
                        "time": GARDEN_LONG_BUFF_THRESHOLD_FRAMES + 1,
                        "maxTime": GARDEN_LONG_BUFF_THRESHOLD_FRAMES + 1,
                    }
                ]
            }
        }
        self.assertTrue(has_positive_active_buffs(snapshot, known_negative_buffs=KNOWN_NEGATIVE_BUFFS))
        self.assertTrue(
            has_long_positive_active_buff(
                snapshot,
                known_negative_buffs=KNOWN_NEGATIVE_BUFFS,
                long_buff_threshold_frames=GARDEN_LONG_BUFF_THRESHOLD_FRAMES,
            )
        )

    def test_buff_only_pause_helper_requires_all_reasons_to_be_click_buffs(self):
        self.assertTrue(has_buff_only_non_click_pause(("click_buffs=('Click frenzy',)",)))
        self.assertFalse(has_buff_only_non_click_pause(("click_buffs=('Click frenzy',)", "combo_stage=spawn")))


class GardenControllerAccessTests(unittest.TestCase):
    def test_does_not_open_garden_without_farms(self):
        controller = GardenController(log=_StubLog())
        snapshot = {
            "cookies": 10.0,
            "garden": {
                "onMinigame": False,
                "openControl": {"centerX": 10, "centerY": 20},
                "farmLevel": 1,
                "farmAmount": 0,
                "seeds": [],
                "soils": [],
                "plot": [],
            },
        }

        action = controller.get_action(snapshot, lambda x, y: (x, y), now=10.0)
        diag = controller.get_diagnostics(snapshot, lambda x, y: (x, y))

        self.assertIsNone(action)
        self.assertEqual(diag["reason"], "garden_unavailable")

    def test_does_not_open_garden_when_plan_is_not_affordable(self):
        controller = GardenController(log=_StubLog())
        snapshot = {
            "cookies": 10.0,
            "garden": {
                "onMinigame": False,
                "openControl": {"centerX": 10, "centerY": 20},
                "farmLevel": 1,
                "farmAmount": 1,
                "seedSelected": None,
                "soil": {"key": "dirt", "name": "Dirt"},
                "seeds": [
                    {"key": "bakerWheat", "name": "Baker's wheat", "unlocked": True, "plantable": True},
                    {"key": "thumbcorn", "name": "Thumbcorn", "unlocked": True, "plantable": True},
                    {"key": "cronerice", "name": "Cronerice", "unlocked": False, "plantable": False},
                ],
                "soils": [],
                "plot": [],
            },
        }

        action = controller.get_action(snapshot, lambda x, y: (x, y), now=10.0)

        self.assertIsNone(action)


class GardenLayoutTests(unittest.TestCase):
    def test_dense_mixed_cross_layout_for_three_by_three_plot(self):
        controller = GardenController(log=_StubLog())
        state = {
            "plot": [
                {"x": x, "y": y, "unlocked": True}
                for y in range(1, 4)
                for x in range(1, 4)
            ]
        }

        layout = controller._desired_layout(state, "mixed_cross", ("cronerice", "thumbcorn"))

        self.assertEqual(
            layout,
            {
                (1, 1): "cronerice",
                (2, 1): "thumbcorn",
                (1, 2): "thumbcorn",
                (3, 2): "cronerice",
                (2, 3): "cronerice",
                (3, 3): "thumbcorn",
            },
        )

    def test_dense_single_cross_layout_for_three_by_three_plot(self):
        controller = GardenController(log=_StubLog())
        state = {
            "plot": [
                {"x": x, "y": y, "unlocked": True}
                for y in range(1, 4)
                for x in range(1, 4)
            ]
        }

        layout = controller._desired_layout(state, "single_cross", ("bakerWheat",))

        self.assertEqual(
            layout,
            {
                (1, 1): "bakerWheat",
                (2, 1): "bakerWheat",
                (1, 2): "bakerWheat",
                (3, 2): "bakerWheat",
                (2, 3): "bakerWheat",
                (3, 3): "bakerWheat",
            },
        )


class _StubLog:
    def info(self, message):
        pass


if __name__ == "__main__":
    unittest.main()
