import time
import unittest
import unittest.mock

from clicker_bot.reserve_policy import ReservePolicy, apply_building_burst_purchase_goal


class LuckyReservePolicyTests(unittest.TestCase):
    def setUp(self):
        self.log = unittest.mock.Mock()
        self.policy = ReservePolicy(
            lucky_reserve_cps_seconds=600.0,
            crafty_pixies_buff="Crafty pixies",
            building_buff_burst_min_remaining_seconds=8.0,
            cookie_clicker_fps=30.0,
            log=self.log,
            monotonic=time.monotonic,
        )
        self.lucky_reserve_enabled = True

    def test_lucky_reserve_uses_unbuffed_cps_for_hard_target(self):
        snapshot = {
            "cookiesPs": 700.0,
            "cookiesPsRawHighest": 100.0,
        }

        hard_reserve = self.policy.get_lucky_cookie_reserve(snapshot, use_live_cps=False)
        live_reserve = self.policy.get_lucky_cookie_reserve(snapshot, use_live_cps=True)

        cps_seconds = self.policy.lucky_reserve_cps_seconds
        self.assertEqual(hard_reserve, 100.0 * cps_seconds)
        self.assertEqual(live_reserve, 700.0 * cps_seconds)

    def test_building_burst_window_requires_matching_building_buff_and_pixies(self):
        snapshot = {
            "buffs": [
                {
                    "name": "Ore vein",
                    "type": "building buff",
                    "buildingName": "Mine",
                    "multCpS": 7.0,
                    "time": 30.0 * 30.0,
                },
                {
                    "name": "Crafty pixies",
                    "type": "building buff",
                    "time": 30.0 * 10.0,
                },
            ]
        }
        building_diag = {"candidate": "Mine"}

        burst = self.policy.get_building_buff_burst_window(snapshot, building_diag, spell_diag=None)

        self.assertTrue(burst["active"])
        self.assertEqual(burst["building_name"], "Mine")
        self.assertEqual(burst["buff_name"], "Ore vein")
        self.assertTrue(burst["pixies_active"])

    def test_building_burst_window_can_activate_when_pixies_is_ready_for_same_target(self):
        snapshot = {
            "buffs": [
                {
                    "name": "Juicy profits",
                    "type": "building buff",
                    "buildingName": "Bank",
                    "multCpS": 10.0,
                    "time": 30.0 * 12.0,
                }
            ],
        }
        building_diag = {"candidate": "Bank"}
        spell_diag = {
            "reason": "crafty_pixies_ready",
            "crafty_pixies_target": "Bank",
        }

        burst = self.policy.get_building_buff_burst_window(snapshot, building_diag, spell_diag=spell_diag)

        self.assertTrue(burst["active"])
        self.assertFalse(burst["pixies_active"])
        self.assertTrue(burst["pixies_ready"])

    def test_global_reserve_keeps_hard_lucky_as_baseline_but_releases_building_hold_during_burst(self):
        snapshot = {
            "cookiesPs": 700.0,
            "cookiesPsRawHighest": 100.0,
            "buffs": [
                {
                    "name": "Ore vein",
                    "type": "building buff",
                    "buildingName": "Mine",
                    "multCpS": 7.0,
                    "time": 30.0 * 12.0,
                },
                {
                    "name": "Crafty pixies",
                    "type": "building buff",
                    "time": 30.0 * 8.0,
                },
            ],
        }
        building_diag = {"candidate": "Mine"}

        reserve = self.policy.get_global_cookie_reserve(
            snapshot,
            {},
            get_garden_cookie_reserve=lambda current_snapshot, garden_diag: 0.0,
            lucky_reserve_enabled=self.lucky_reserve_enabled,
            building_diag=building_diag,
            spell_diag=None,
        )

        cps_seconds = self.policy.lucky_reserve_cps_seconds
        self.assertEqual(reserve["hard_lucky_reserve"], 100.0 * cps_seconds)
        self.assertEqual(reserve["live_lucky_reserve"], 700.0 * cps_seconds)
        self.assertEqual(reserve["soft_lucky_delta"], 600.0 * cps_seconds)
        self.assertEqual(reserve["total_reserve"], 100.0 * cps_seconds)
        self.assertEqual(reserve["building_total_reserve"], 0.0)
        self.assertTrue(reserve["burst_window"]["active"])

    def test_global_reserve_skips_lucky_hold_when_toggle_is_off(self):
        snapshot = {
            "cookiesPs": 700.0,
            "cookiesPsRawHighest": 100.0,
            "buffs": [],
        }
        self.lucky_reserve_enabled = False

        reserve = self.policy.get_global_cookie_reserve(
            snapshot,
            {},
            get_garden_cookie_reserve=lambda current_snapshot, garden_diag: 0.0,
            lucky_reserve_enabled=self.lucky_reserve_enabled,
            building_diag={"candidate": "Mine"},
            spell_diag=None,
        )

        self.assertFalse(reserve["lucky_reserve_enabled"])
        self.assertEqual(reserve["lucky_reserve"], 0.0)
        self.assertEqual(reserve["hard_lucky_reserve"], 0.0)
        self.assertEqual(reserve["live_lucky_reserve"], 0.0)
        self.assertEqual(reserve["total_reserve"], 0.0)

    def test_burst_purchase_goal_forces_wrinkler_liquidation_for_next_building(self):
        purchase_goal = {
            "kind": "upgrade",
            "name": "Existing upgrade",
            "price": 1000.0,
        }
        snapshot = {"cookies": 500.0}
        building_diag = {
            "next_candidate": "Mine",
            "next_candidate_price": 900.0,
            "next_candidate_payback_seconds": 12.0,
            "next_candidate_can_buy": False,
        }
        burst_window = {
            "active": True,
            "building_name": "Mine",
            "buff_name": "Ore vein",
            "remaining_seconds": 11.0,
        }

        goal = apply_building_burst_purchase_goal(
            snapshot,
            building_diag,
            purchase_goal,
            burst_window,
        )

        self.assertEqual(goal["kind"], "building")
        self.assertEqual(goal["name"], "Mine")
        self.assertEqual(goal["price"], 900.0)
        self.assertEqual(goal["shortfall"], 400.0)
        self.assertTrue(goal["force_wrinkler_liquidation"])

    def test_lucky_reserve_multiplier_scaling(self):
        multiplier_func = self.policy.get_lucky_reserve_multiplier

        snapshot_no_ascension = {}
        self.assertEqual(multiplier_func(snapshot_no_ascension), 1.0)

        snapshot_with_ascension = {"ascension": {}}
        self.assertEqual(multiplier_func(snapshot_with_ascension), 1.0)

        snapshot = {"ascension": {"ascendGain": 0}}
        self.assertEqual(multiplier_func(snapshot), 0.3)

        snapshot = {"ascension": {"ascendGain": 25}}
        self.assertAlmostEqual(multiplier_func(snapshot), 0.3 + 0.7 * (25 / 30.0))

        snapshot = {"ascension": {"ascendGain": 30}}
        self.assertEqual(multiplier_func(snapshot), 1.0)

        snapshot = {"ascension": {"ascendGain": 100}}
        self.assertEqual(multiplier_func(snapshot), 1.0)

        snapshot = {"ascension": {"currentPrestige": 100}}
        self.assertEqual(multiplier_func(snapshot), 0.3)

        snapshot = {"ascension": {"currentPrestige": 2550}}
        self.assertAlmostEqual(multiplier_func(snapshot), 0.3 + 0.7 * (2550 - 100) / (3000 - 100))

        snapshot = {"ascension": {"currentPrestige": 3000}}
        self.assertEqual(multiplier_func(snapshot), 1.0)

        snapshot = {"ascension": {"ascendGain": 10, "currentPrestige": 1000}}
        self.assertAlmostEqual(multiplier_func(snapshot), 0.3 + 0.7 * (10 / 30.0))


if __name__ == "__main__":
    unittest.main()
