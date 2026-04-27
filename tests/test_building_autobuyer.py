import unittest

from clicker_bot.features.building_autobuyer import BuildingAutobuyer


class _LogStub:
    def debug(self, message):
        pass

    def info(self, message):
        pass

    def warning(self, message):
        pass


def _identity_point(x, y):
    return x, y


def _rect(x, y):
    return {
        "centerX": x,
        "centerY": y,
    }


def _snapshot(*, cookies=1000.0, cookies_ps=10.0, price=300.0, stored_cps=1.0, sum_price_10=None, sum_price_100=None, amount=10):
    return {
        "cookies": cookies,
        "cookiesPs": cookies_ps,
        "store": {
            "buyMode": 1,
            "buyBulk": 1,
        },
        "buildings": [
            {
                "id": 0,
                "name": "Cursor",
                "amount": amount,
                "price": price,
                "sumPrice10": sum_price_10,
                "sumPrice100": sum_price_100,
                "storedCps": stored_cps,
                "target": _rect(10, 10),
                "canBuy": True,
            }
        ],
    }


class BuildingAutobuyerHorizonTests(unittest.TestCase):
    def test_horizon_includes_reachable_buildings_even_with_long_payback(self):
        autobuyer = BuildingAutobuyer(_LogStub(), reserve_cps_seconds=0.0, max_spend_ratio=1.0, payback_horizon_seconds=120.0)

        diag = autobuyer.get_diagnostics(
            _snapshot(price=300.0, stored_cps=1.0),
            _identity_point,
        )

        self.assertEqual(diag["reason"], "buy_ready")
        self.assertEqual(diag["candidate"], "Cursor")
        self.assertEqual(diag["payback_horizon_seconds"], 120.0)

    def test_early_ascension_run_scales_down_cps_reserve(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=600.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )

        diag = autobuyer.get_diagnostics(
            _snapshot(cookies=900.0, cookies_ps=4.0, price=100.0, stored_cps=1.0),
            _identity_point,
        )

        self.assertEqual(diag["reason"], "buy_ready")
        self.assertEqual(diag["candidate"], "Cursor")
        self.assertLess(diag["reserve"], 900.0)
        self.assertAlmostEqual(diag["reserve_scale"], 0.05)
        self.assertAlmostEqual(diag["effective_reserve_cps_seconds"], 30.0)

    def test_large_run_keeps_full_cps_reserve(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=600.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )
        snapshot = _snapshot(cookies=900.0, cookies_ps=4.0, price=100.0, stored_cps=1.0)
        snapshot["buildings"][0]["amount"] = 400

        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertEqual(diag["reserve_scale"], 1.0)
        self.assertAlmostEqual(diag["effective_reserve_cps_seconds"], 600.0)
        self.assertGreater(diag["reserve"], 900.0)

    def test_recovery_mode_uses_bulk_100_for_large_buyback_gap(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )
        autobuyer.get_diagnostics(
            _snapshot(
                cookies=1_000_000.0,
                price=100.0,
                stored_cps=10.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=400,
            ),
            _identity_point,
        )

        action = autobuyer.get_action(
            _snapshot(
                cookies=1_000_000.0,
                price=100.0,
                stored_cps=10.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=250,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.quantity, 100)

    def test_recovery_mode_uses_bulk_10_for_medium_buyback_gap(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )
        autobuyer.get_diagnostics(
            _snapshot(
                cookies=10_000.0,
                price=100.0,
                stored_cps=10.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=80,
            ),
            _identity_point,
        )

        action = autobuyer.get_action(
            _snapshot(
                cookies=10_000.0,
                price=100.0,
                stored_cps=10.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=68,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.quantity, 10)

    def test_batches_to_10_when_bundle_is_affordable_even_beyond_early_game(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )

        action = autobuyer.get_action(
            _snapshot(
                cookies=10_000.0,
                price=100.0,
                stored_cps=10.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=90,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.quantity, 10)

    def test_early_game_batches_to_100_when_bundle_is_affordable_and_within_horizon(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )

        action = autobuyer.get_action(
            _snapshot(
                cookies=1_000_000.0,
                price=100.0,
                stored_cps=10.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=20,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.quantity, 100)

    def test_early_game_batches_to_10_when_100_is_not_affordable(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )

        action = autobuyer.get_action(
            _snapshot(
                cookies=10_000.0,
                price=100.0,
                stored_cps=10.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=20,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.quantity, 10)

    def test_early_game_does_not_batch_when_bundle_payback_is_outside_horizon(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=20.0,
        )

        action = autobuyer.get_action(
            _snapshot(
                cookies=10_000.0,
                price=100.0,
                stored_cps=1.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=20,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.quantity, 1)

    def test_late_game_batches_with_sufficient_spendable(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )

        action = autobuyer.get_action(
            _snapshot(
                cookies=1_000_000.0,
                price=100.0,
                stored_cps=10.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=120,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.quantity, 100)

    def test_late_game_batches_even_when_bundle_payback_exceeds_horizon(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=20.0,
        )

        action = autobuyer.get_action(
            _snapshot(
                cookies=1_000_000.0,
                price=100.0,
                stored_cps=1.0,
                sum_price_10=1_500.0,
                sum_price_100=100_000.0,
                amount=120,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.quantity, 100)

    def test_holds_affordable_filler_when_better_horizon_target_exists(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        snapshot = {
            "cookies": 500.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 10,
                    "price": 100.0,
                    "storedCps": 0.1,
                    "target": _rect(10, 10),
                    "canBuy": True,
                },
                {
                    "id": 2,
                    "name": "Farm",
                    "amount": 0,
                    "price": 1100.0,
                    "storedCps": 8.24,
                    "target": _rect(20, 20),
                    "canBuy": True,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNone(action)
        self.assertEqual(diag["reason"], "saving_for_better_horizon_target")
        self.assertEqual(diag["held_candidate"], "Cursor")
        self.assertEqual(diag["next_candidate"], "Farm")

    def test_dragon_building_floor_prioritizes_required_building(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        snapshot = {
            "cookies": 500.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "dragon": {
                "nextCostType": "building_sacrifice",
                "nextRequiredBuildingId": 0,
                "nextRequiredBuildingName": "Cursor",
                "nextRequiredBuildingAmount": 100,
            },
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 63,
                    "price": 120.0,
                    "storedCps": 0.1,
                    "target": _rect(10, 10),
                    "canBuy": True,
                },
                {
                    "id": 2,
                    "name": "Farm",
                    "amount": 300,
                    "price": 300.0,
                    "storedCps": 8.24,
                    "target": _rect(20, 20),
                    "canBuy": True,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.building_name, "Cursor")
        self.assertEqual(diag["reason"], "dragon_building_floor_ready")
        self.assertEqual(diag["candidate"], "Cursor")
        self.assertEqual(diag["dragon_target"]["remaining"], 37)

    def test_minigame_floor_does_not_force_rebuy_ahead_of_natural_growth(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        snapshot = {
            "cookies": 600_000_000_000.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "dragon": {
                "nextCostType": "building_sacrifice",
                "nextRequiredBuildingId": 5,
                "nextRequiredBuildingName": "Bank",
                "nextRequiredBuildingAmount": 100,
            },
            "buildings": [
                {
                    "id": 2,
                    "name": "Farm",
                    "amount": 12,
                    "price": 6_000.0,
                    "storedCps": 284.0,
                    "target": _rect(20, 20),
                    "canBuy": True,
                },
                {
                    "id": 5,
                    "name": "Bank",
                    "amount": 92,
                    "price": 537_000_000_000.0,
                    "storedCps": 23_000.0,
                    "target": _rect(30, 30),
                    "canBuy": True,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.building_name, "Farm")
        self.assertEqual(diag["reason"], "buy_ready")
        self.assertEqual(diag["candidate"], "Farm")
        self.assertEqual(diag["next_candidate"], "Farm")
        self.assertEqual(diag["minigame_targets"][0]["remaining"], 288)

    def test_dragon_building_floor_waits_for_required_building_cash(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        snapshot = {
            "cookies": 50.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "dragon": {
                "nextCostType": "building_sacrifice",
                "nextRequiredBuildingId": 0,
                "nextRequiredBuildingName": "Cursor",
                "nextRequiredBuildingAmount": 100,
            },
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 63,
                    "price": 120.0,
                    "storedCps": 0.1,
                    "target": _rect(10, 10),
                    "canBuy": False,
                },
                {
                    "id": 2,
                    "name": "Farm",
                    "amount": 300,
                    "price": 100.0,
                    "storedCps": 8.24,
                    "target": _rect(20, 20),
                    "canBuy": False,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNone(action)
        self.assertEqual(diag["reason"], "waiting_for_cash_horizon_candidate")
        self.assertEqual(diag["next_candidate"], "Farm")

    def test_prefers_building_with_active_building_buff(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        snapshot = {
            "cookies": 1_000_000.0,
            "cookiesPs": 1_000.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "buffs": [
                {
                    "name": "Ore vein",
                    "type": "building buff",
                    "buildingId": 3,
                    "buildingName": "Mine",
                    "multCpS": 20.0,
                }
            ],
            "buildings": [
                {
                    "id": 2,
                    "name": "Farm",
                    "amount": 100,
                    "price": 1000.0,
                    "storedCps": 100.0,
                    "target": _rect(10, 10),
                    "canBuy": True,
                },
                {
                    "id": 3,
                    "name": "Mine",
                    "amount": 100,
                    "price": 1500.0,
                    "storedCps": 20.0,
                    "target": _rect(20, 20),
                    "canBuy": True,
                },
            ],
        }

        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertEqual(diag["candidate"], "Mine")
        self.assertEqual(diag["candidate_active_buff_multiplier"], 20.0)
        self.assertGreater(diag["candidate_effective_delta_cps"], diag["candidate_delta_cps"])
        self.assertIsNone(diag["dragon_target"])

    def test_dragon_floor_does_not_override_better_growth_until_close(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        snapshot = {
            "cookies": 600_000_000_000.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "dragon": {
                "nextCostType": "building_sacrifice",
                "nextRequiredBuildingId": 5,
                "nextRequiredBuildingName": "Bank",
                "nextRequiredBuildingAmount": 100,
            },
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 100,
                    "price": 1_000.0,
                    "storedCps": 100.0,
                    "target": _rect(10, 10),
                    "canBuy": True,
                },
                {
                    "id": 5,
                    "name": "Bank",
                    "amount": 92,
                    "price": 537_000_000_000.0,
                    "storedCps": 23_000.0,
                    "target": _rect(30, 30),
                    "canBuy": True,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.building_name, "Cursor")
        self.assertEqual(diag["reason"], "buy_ready")
        self.assertEqual(diag["candidate"], "Cursor")
        self.assertEqual(diag["next_candidate"], "Cursor")

    def test_dragon_floor_takes_over_when_stage_is_almost_complete(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        snapshot = {
            "cookies": 600_000_000_000.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "dragon": {
                "nextCostType": "building_sacrifice",
                "nextRequiredBuildingId": 5,
                "nextRequiredBuildingName": "Bank",
                "nextRequiredBuildingAmount": 100,
            },
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 100,
                    "price": 1_000.0,
                    "storedCps": 100.0,
                    "target": _rect(10, 10),
                    "canBuy": True,
                },
                {
                    "id": 5,
                    "name": "Bank",
                    "amount": 98,
                    "price": 537_000_000_000.0,
                    "storedCps": 23_000.0,
                    "target": _rect(30, 30),
                    "canBuy": True,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.building_name, "Bank")
        self.assertEqual(diag["reason"], "dragon_building_floor_ready")
        self.assertEqual(diag["candidate"], "Bank")
        self.assertEqual(diag["dragon_target"]["remaining"], 2)

    def test_manual_cap_allows_dragon_floor_then_trims_after_requirement_clears(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        autobuyer.set_building_cap("Bank", 98)
        snapshot = {
            "cookies": 600_000_000_000.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "dragon": {
                "nextCostType": "building_sacrifice",
                "nextRequiredBuildingId": 5,
                "nextRequiredBuildingName": "Bank",
                "nextRequiredBuildingAmount": 100,
            },
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 100,
                    "price": 1_000.0,
                    "storedCps": 100.0,
                    "target": _rect(10, 10),
                    "canBuy": True,
                },
                {
                    "id": 5,
                    "name": "Bank",
                    "amount": 98,
                    "price": 537_000_000_000.0,
                    "storedCps": 23_000.0,
                    "target": _rect(30, 30),
                    "canBuy": True,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy_building")
        self.assertEqual(action.building_name, "Bank")
        self.assertEqual(diag["reason"], "dragon_building_floor_ready")
        self.assertEqual(diag["candidate"], "Bank")
        self.assertEqual(diag["buildings"][1]["manual_cap"], 98)
        self.assertTrue(diag["buildings"][1]["cap_reached"])
        self.assertEqual(diag["dragon_target"]["remaining"], 2)

        post_dragon_snapshot = {
            "cookies": 600_000_000_000.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "dragon": {
                "nextCostType": "cookie",
            },
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 100,
                    "price": 1_000.0,
                    "storedCps": 100.0,
                    "target": _rect(10, 10),
                    "canBuy": True,
                    "canSell": True,
                    "sellValue1": 100.0,
                },
                {
                    "id": 5,
                    "name": "Bank",
                    "amount": 100,
                    "price": 537_000_000_000.0,
                    "storedCps": 23_000.0,
                    "target": _rect(30, 30),
                    "canBuy": True,
                    "canSell": True,
                    "sellValue1": 100.0,
                },
            ],
        }

        trim_action = autobuyer.get_action(post_dragon_snapshot, _identity_point, now=11.0)

        self.assertIsNotNone(trim_action)
        self.assertEqual(trim_action.kind, "sell_building")
        self.assertEqual(trim_action.building_name, "Bank")
        self.assertEqual(trim_action.quantity, 1)

    def test_dragon_floor_at_two_hundred_suspends_caps_temporarily(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        autobuyer.set_building_cap("Bank", 98)
        snapshot = {
            "cookies": 600_000_000_000.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "dragon": {
                "nextCostType": "building_sacrifice",
                "nextRequiredBuildingId": 0,
                "nextRequiredBuildingName": "Cursor",
                "nextRequiredBuildingAmount": 200,
            },
            "buildings": [
                {
                    "id": 5,
                    "name": "Bank",
                    "amount": 98,
                    "price": 537_000_000_000.0,
                    "storedCps": 23_000.0,
                    "target": _rect(30, 30),
                    "canBuy": True,
                    "canSell": True,
                    "sellValue1": 100.0,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy_building")
        self.assertEqual(action.building_name, "Bank")
        self.assertTrue(diag["dragon_cap_override_active"])
        self.assertTrue(diag["buildings"][0]["cap_ignored"])
        self.assertIsNone(diag["buildings"][0]["cap"])

    def test_manual_cap_clamps_bulk_buy_quantity(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )
        autobuyer.set_building_cap("Wizard tower", 50)
        snapshot = {
            "cookies": 10_000_000_000.0,
            "cookiesPs": 1_000_000.0,
            "store": {"buyMode": 1, "buyBulk": 100},
            "buildings": [
                {
                    "id": 7,
                    "name": "Wizard tower",
                    "amount": 49,
                    "price": 330_000_000.0,
                    "sumPrice10": 5_000_000_000.0,
                    "sumPrice100": 9_000_000_000.0,
                    "storedCps": 44_440.0,
                    "target": _rect(30, 30),
                    "canBuy": True,
                    "canSell": True,
                    "sellValue1": 100.0,
                    "sellValue10": 1_000.0,
                    "sellValue100": 10_000.0,
                }
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy_building")
        self.assertEqual(action.building_name, "Wizard tower")
        self.assertEqual(action.quantity, 1)
        self.assertEqual(diag["candidate_quantity"], 1)
        self.assertEqual(diag["buildings"][0]["manual_cap"], 50)
        self.assertEqual(diag["buildings"][0]["remaining_to_cap"], 1)

    def test_cap_trim_uses_bulk_sell_when_far_over_cap(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=3600.0,
        )
        autobuyer.set_building_cap("Wizard tower", 50)
        snapshot = {
            "cookies": 10_000_000_000.0,
            "cookiesPs": 1_000_000.0,
            "store": {"buyMode": 1, "buyBulk": 100},
            "dragon": {"nextCostType": "cookie"},
            "buildings": [
                {
                    "id": 7,
                    "name": "Wizard tower",
                    "amount": 149,
                    "price": 330_000_000.0,
                    "storedCps": 44_440.0,
                    "target": _rect(30, 30),
                    "canBuy": True,
                    "canSell": True,
                    "sellValue1": 100.0,
                    "sellValue10": 1_000.0,
                    "sellValue100": 10_000.0,
                }
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "sell_building")
        self.assertEqual(action.building_name, "Wizard tower")
        self.assertEqual(action.quantity, 10)
        self.assertEqual(action.price, 1_000.0)

    def test_minigame_floor_is_reported_but_not_forced(self):
        autobuyer = BuildingAutobuyer(
            _LogStub(),
            reserve_cps_seconds=0.0,
            max_spend_ratio=1.0,
            payback_horizon_seconds=180.0,
        )
        snapshot = {
            "cookies": 5_000.0,
            "cookiesPs": 10.0,
            "store": {"buyMode": 1, "buyBulk": 1},
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 100,
                    "price": 100.0,
                    "storedCps": 5.0,
                    "target": _rect(10, 10),
                    "canBuy": True,
                },
                {
                    "id": 2,
                    "name": "Farm",
                    "amount": 250,
                    "price": 500.0,
                    "storedCps": 0.1,
                    "target": _rect(20, 20),
                    "canBuy": True,
                },
            ],
        }

        action = autobuyer.get_action(snapshot, _identity_point, now=10.0)
        diag = autobuyer.get_diagnostics(snapshot, _identity_point)

        self.assertIsNotNone(action)
        self.assertEqual(action.building_name, "Cursor")
        self.assertEqual(diag["reason"], "buy_ready")
        self.assertEqual(diag["candidate"], "Cursor")
        self.assertEqual(diag["minigame_targets"][0]["remaining"], 50)


if __name__ == "__main__":
    unittest.main()
