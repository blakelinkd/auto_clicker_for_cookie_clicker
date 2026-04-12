import unittest

from clicker_bot.stock_helpers import (
    build_disabled_bank_diag,
    get_stock_buy_controls,
    has_cookies_after_reserve,
    should_defer_stock_actions_for_upgrade,
    should_pause_stock_trading,
    stock_trade_management_active,
)


class StockGateTests(unittest.TestCase):
    def test_does_not_pause_for_production_buff(self):
        self.assertFalse(
            should_pause_stock_trading(
                [
                    {"name": "Frenzy", "multCpS": 7.0},
                    {"name": "Dragon Harvest", "multCpS": 15.0},
                ]
            )
        )

    def test_does_not_pause_for_click_buff(self):
        self.assertFalse(
            should_pause_stock_trading(
                [
                    {"name": "Click frenzy", "multClick": 777.0},
                ]
            )
        )

    def test_defers_stock_actions_when_affordable_upgrade_is_pending(self):
        self.assertTrue(
            should_defer_stock_actions_for_upgrade(
                {"cookies": 1000.0},
                {
                    "candidate_can_buy": True,
                    "candidate_id": 7,
                    "candidate_price": 100.0,
                },
                upgrade_autobuy_enabled=True,
                global_cookie_reserve=0.0,
            )
        )

    def test_does_not_defer_stock_actions_when_upgrade_autobuy_is_off(self):
        self.assertFalse(
            should_defer_stock_actions_for_upgrade(
                {"cookies": 1000.0},
                {
                    "candidate_can_buy": True,
                    "candidate_id": 7,
                    "candidate_price": 100.0,
                },
                upgrade_autobuy_enabled=False,
                global_cookie_reserve=0.0,
            )
        )

    def test_has_cookies_after_reserve_requires_price(self):
        self.assertFalse(has_cookies_after_reserve({"cookies": 1000.0}, None, 0.0))

    def test_get_stock_buy_controls_uses_reserve_only(self):
        controls = get_stock_buy_controls({"reserve": 999.0}, False, 125.0)

        self.assertTrue(controls["allow_buy_actions"])
        self.assertEqual(controls["buy_reserve_cookies"], 125.0)
        self.assertEqual(controls["reason"], "stock_ignores_building_constraints")

    def test_build_disabled_bank_diag_reports_position_summary(self):
        diag = build_disabled_bank_diag(
            {
                "cookies": 500.0,
                "cookiesPsRawHighest": 12.0,
                "bank": {
                    "brokers": 4,
                    "onMinigame": True,
                    "openControl": {"x": 1},
                    "goods": [{"id": 1}, {"id": 2}, None],
                },
            },
            held_positions={
                1: {"shares": 3},
                2: {"shares": 7},
            },
        )

        self.assertTrue(diag["available"])
        self.assertFalse(diag["enabled"])
        self.assertEqual(diag["reason"], "trading_disabled")
        self.assertEqual(diag["goods_total"], 2)
        self.assertEqual(diag["held_goods"], 2)
        self.assertEqual(diag["held_shares"], 10)
        self.assertTrue(diag["has_open_target"])

    def test_stock_trade_management_active_when_pending_actions_exist(self):
        self.assertTrue(
            stock_trade_management_active(
                stock_trading_enabled=False,
                held_positions={},
                pending_actions={1: {"kind": "buy"}},
            )
        )


if __name__ == "__main__":
    unittest.main()
