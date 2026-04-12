import unittest

from clicker_bot.upgrade_diagnostics import build_upgrade_diag


class UpgradeDiagnosticsTests(unittest.TestCase):
    def _build_diag(self, snapshot):
        return build_upgrade_diag(
            snapshot,
            resolve_candidate_metrics=self._resolve_candidate_metrics,
            estimate_attached_wrinkler_bank=self._estimate_wrinkler_bank,
            afford_horizon_seconds=30 * 60,
            auto_buy_payback_seconds=3 * 60,
            cheap_upgrade_sweep_ratio=0.10,
        )

    @staticmethod
    def _estimate_wrinkler_bank(snapshot):
        wrinklers = snapshot.get("wrinklers", {}).get("wrinklers", [])
        return sum(float(item.get("estimatedReward") or 0.0) for item in wrinklers if int(item.get("phase") or 0) == 2)

    @staticmethod
    def _resolve_candidate_metrics(snapshot, item):
        if item.get("deltaCps") is not None:
            candidate = dict(item)
            price = float(item.get("price") or 0.0)
            delta_cps = float(item.get("deltaCps") or 0.0)
            candidate["price"] = price
            candidate["deltaCps"] = delta_cps
            candidate["paybackSeconds"] = float("inf") if delta_cps <= 0 else price / delta_cps
            return candidate

        power = item.get("power")
        if power is None:
            return None

        price = float(item.get("price") or 0.0)
        delta_cps = float(power)
        if bool(item.get("kitten")):
            delta_cps *= float(snapshot.get("milkProgress") or 0.0)
        if item.get("pool") == "cookie":
            delta_cps *= max(1.0, float(snapshot.get("cookiesPsRawHighest") or snapshot.get("cookiesPs") or 0.0))

        candidate = dict(item)
        candidate["price"] = price
        candidate["deltaCps"] = delta_cps
        candidate["paybackSeconds"] = float("inf") if delta_cps <= 0 else price / delta_cps
        return candidate

    def test_prefers_best_upgrade_within_afford_horizon(self):
        snapshot = {
            "cookies": 100.0,
            "cookiesPsRawHighest": 10.0,
            "globalCpsMult": 1.0,
            "milkProgress": 1.0,
            "wrinklers": {"wrinklers": [{"phase": 2, "estimatedReward": 200.0}]},
            "upgrades": [
                {"id": 1, "displayName": "Near Kitten", "price": 1200.0, "power": 0.1, "kitten": True, "canBuy": False},
                {"id": 2, "displayName": "Far Cookie", "price": 50000.0, "power": 50.0, "pool": "cookie", "canBuy": False},
            ],
        }

        diag = self._build_diag(snapshot)

        self.assertEqual(diag["candidate"], "Near Kitten")
        self.assertEqual(diag["reason"], "upgrade_ready")
        self.assertEqual(diag["horizon_reachable"], 1)

    def test_reports_no_candidate_when_nothing_is_reachable_in_horizon(self):
        snapshot = {
            "cookies": 0.0,
            "cookiesPsRawHighest": 1.0,
            "globalCpsMult": 1.0,
            "wrinklers": {"wrinklers": []},
            "upgrades": [
                {"id": 1, "displayName": "Too Far Cookie", "price": 5000.0, "power": 10.0, "pool": "cookie", "canBuy": False},
            ],
        }

        diag = self._build_diag(snapshot)

        self.assertIsNone(diag["candidate"])
        self.assertEqual(diag["reason"], "no_upgrade_in_horizon")
        self.assertEqual(diag["horizon_reachable"], 0)

    def test_falls_back_to_affordable_upgrade_when_horizon_has_no_candidates(self):
        snapshot = {
            "cookies": 400.0,
            "cookiesPsRawHighest": 0.0,
            "globalCpsMult": 1.0,
            "wrinklers": {"wrinklers": []},
            "upgrades": [
                {"id": 3, "displayName": "Cheap Cosmetic", "price": 50.0, "canBuy": True},
                {"id": 4, "displayName": "Another Cheap Upgrade", "price": 75.0, "canBuy": True},
            ],
        }

        diag = self._build_diag(snapshot)

        self.assertEqual(diag["candidate"], "Cheap Cosmetic")
        self.assertEqual(diag["reason"], "upgrade_ready_affordable_fallback")
        self.assertEqual(diag["horizon_reachable"], 0)
        self.assertTrue(diag["candidate_can_buy"])

    def test_sweeps_cheap_affordable_upgrade_under_ten_percent_of_cash(self):
        snapshot = {
            "cookies": 10000.0,
            "cookiesPsRawHighest": 50.0,
            "globalCpsMult": 1.0,
            "wrinklers": {"wrinklers": []},
            "upgrades": [
                {"id": 8, "displayName": "Cheap Sweep", "price": 900.0, "canBuy": True},
                {"id": 9, "displayName": "Horizon Pick", "price": 2500.0, "power": 0.01, "pool": "cookie", "canBuy": True},
            ],
        }

        diag = self._build_diag(snapshot)

        self.assertEqual(diag["candidate"], "Cheap Sweep")
        self.assertEqual(diag["reason"], "upgrade_ready_cash_sweep")
        self.assertTrue(diag["candidate_can_buy"])

    def test_sweeps_affordable_upgrade_under_three_minute_payback(self):
        snapshot = {
            "cookies": 10000.0,
            "cookiesPsRawHighest": 50.0,
            "globalCpsMult": 1.0,
            "wrinklers": {"wrinklers": []},
            "upgrades": [
                {"id": 8, "displayName": "Quick Return", "price": 2500.0, "deltaCps": 20.0, "canBuy": True},
                {"id": 9, "displayName": "Cheap Sweep", "price": 900.0, "canBuy": True},
            ],
        }

        diag = self._build_diag(snapshot)

        self.assertEqual(diag["candidate"], "Quick Return")
        self.assertEqual(diag["reason"], "upgrade_ready_payback_sweep")
        self.assertTrue(diag["candidate_can_buy"])

    def test_ignores_toggle_pool_items_for_cash_sweep(self):
        snapshot = {
            "cookies": 10000.0,
            "cookiesPsRawHighest": 50.0,
            "globalCpsMult": 1.0,
            "wrinklers": {"wrinklers": []},
            "upgrades": [
                {"id": 333, "displayName": "Milk selector", "price": 0.0, "pool": "toggle", "canBuy": True},
                {"id": 8, "displayName": "Cheap Sweep", "price": 900.0, "canBuy": True},
            ],
        }

        diag = self._build_diag(snapshot)

        self.assertEqual(diag["candidate"], "Cheap Sweep")
        self.assertEqual(diag["reason"], "upgrade_ready_cash_sweep")

    def test_ignores_research_pool_items_for_autobuy(self):
        snapshot = {
            "cookies": 10000.0,
            "cookiesPsRawHighest": 50.0,
            "globalCpsMult": 1.0,
            "wrinklers": {"wrinklers": []},
            "upgrades": [
                {"id": 69, "displayName": "One mind", "price": 100.0, "pool": "tech", "canBuy": True},
                {"id": 8, "displayName": "Cheap Sweep", "price": 900.0, "canBuy": True},
            ],
        }

        diag = self._build_diag(snapshot)

        self.assertEqual(diag["candidate"], "Cheap Sweep")
        self.assertEqual(diag["reason"], "upgrade_ready_cash_sweep")


if __name__ == "__main__":
    unittest.main()
