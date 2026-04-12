import unittest

from stock_trader import StockTrader, TradeAction


class _LogStub:
    def __init__(self):
        self.messages = []

    def debug(self, message):
        pass

    def info(self, message):
        self.messages.append(message)

    def warning(self, message):
        pass

    def exception(self, message):
        raise AssertionError(message)


class _DbStub:
    def __init__(self):
        self.trade_events = []
        self.trade_decisions = []

    def load_positions(self):
        return {}

    def record_prices(self, observed_at_ms, goods):
        pass

    def get_recent_range_stats(self, good_ids, observed_at_ms, window_ms):
        return {}

    def get_price_series(self, good_ids, per_good_limit=None):
        return {}

    def upsert_position(self, **kwargs):
        pass

    def delete_position(self, good_id):
        pass

    def record_trade_event(self, **kwargs):
        self.trade_events.append(kwargs)

    def record_trade_decision(self, **kwargs):
        self.trade_decisions.append(kwargs)

    def get_runtime_stats(self):
        return {}


def _identity_point(x, y):
    return x, y


def _rect(x, y):
    return {
        "centerX": x,
        "centerY": y,
    }


def _snapshot(
    *,
    cookies=1000.0,
    on_minigame=True,
    include_controls=None,
    value=5.0,
    stock=0,
    can_sell=False,
    resting_value=None,
    mode=0,
    mode_name=None,
    delta=0.0,
    history=None,
    brokers=0,
    brokers_max=5,
    broker_cost=None,
    can_hire_broker=False,
    office_level=0,
    office_name="Credit garage",
    next_office_level=1,
    next_office_name="Tiny bank",
    office_upgrade_cost=None,
    office_upgrade_cursor_level=None,
    can_upgrade_office=False,
):
    if include_controls is None:
        include_controls = on_minigame
    return {
        "timestamp": 1000,
        "cookies": cookies,
        "cookiesPsRawHighest": 1.0,
        "bank": {
            "brokers": brokers,
            "brokersMax": brokers_max,
            "brokerCost": broker_cost,
            "brokerControl": _rect(12, 10) if on_minigame else None,
            "canHireBroker": can_hire_broker,
            "officeLevel": office_level,
            "officeName": office_name,
            "nextOfficeLevel": next_office_level,
            "nextOfficeName": next_office_name,
            "officeUpgradeCost": office_upgrade_cost,
            "officeUpgradeCursorLevel": office_upgrade_cursor_level,
            "officeUpgradeControl": _rect(14, 10) if on_minigame else None,
            "canUpgradeOffice": can_upgrade_office,
            "profit": 0.0,
            "ticks": 0,
            "tickFrames": 0,
            "secondsPerTick": 60.0,
            "nextTickAt": 61000,
            "onMinigame": on_minigame,
            "openControl": _rect(10, 10),
            "goods": [
                {
                    "id": 0,
                    "name": "Cinnamon",
                    "symbol": "CNM",
                    "value": value,
                    "restingValue": value if resting_value is None else resting_value,
                    "stock": stock,
                    "stockMax": 100,
                    "active": True,
                    "hidden": False,
                    "mode": mode,
                    "modeName": mode_name,
                    "modeTicksRemaining": 100,
                    "last": 0,
                    "delta": delta,
                    "history": [value] if history is None else list(history),
                    "buy": _rect(20, 20) if include_controls else None,
                    "buy1": _rect(20, 20) if include_controls else None,
                    "buy10": _rect(21, 20) if include_controls else None,
                    "buy100": _rect(22, 20) if include_controls else None,
                    "buyMax": _rect(23, 20) if include_controls else None,
                    "sell": _rect(30, 20) if include_controls else None,
                    "sell1": _rect(30, 20) if include_controls else None,
                    "sell10": _rect(31, 20) if include_controls else None,
                    "sell100": _rect(32, 20) if include_controls else None,
                    "sellAll": _rect(33, 20) if include_controls else None,
                    "canBuy": True,
                    "canBuy1": True,
                    "canBuy10": True,
                    "canBuy100": True,
                    "canBuyMax": True,
                    "canSell": can_sell,
                    "canSell1": can_sell,
                    "canSell10": can_sell,
                    "canSell100": can_sell,
                    "canSellAll": can_sell,
                }
            ],
        },
    }


class StockTraderReserveTests(unittest.TestCase):
    def setUp(self):
        self.db = _DbStub()
        self.log = _LogStub()
        self.trader = StockTrader(self.log, self.db)

    def _set_range_stats(self, *, range_min, range_max, range_avg=None, samples=200):
        self.trader.range_stats_cache = {
            0: {
                "min": float(range_min),
                "max": float(range_max),
                "avg": float(range_avg if range_avg is not None else (range_min + range_max) / 2.0),
                "samples": int(samples),
            }
        }
        self.trader.range_stats_refreshed_at_ms = 1000

    def test_buy_action_respects_reserved_cookies(self):
        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=5.0),
            _identity_point,
            now=10.0,
            buy_reserve_cookies=995.0,
        )

        self.assertIsNone(action)

    def test_buy_action_can_be_disabled_without_blocking_sells(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 40.0,
                "avg_entry_cookies": 40.0,
            }
        }

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=60.0,
                stock=10,
                can_sell=True,
                mode=4,
                mode_name="fast_fall",
                delta=-0.20,
                resting_value=45.0,
            ),
            _identity_point,
            now=10.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "sell")

    def test_buy_blocked_diagnostics_are_reported(self):
        diag = self.trader.get_diagnostics(
            _snapshot(cookies=1000.0, value=5.0),
            _identity_point,
            allow_buy_actions=False,
            buy_reserve_cookies=750.0,
        )

        self.assertEqual(diag["reason"], "buy_blocked")
        self.assertFalse(diag["buy_actions_enabled"])
        self.assertEqual(diag["buy_reserve_cookies"], 750.0)

    def test_buy_action_respects_twenty_five_percent_portfolio_cap(self):
        self.trader.positions = {
            0: {
                "shares": 75,
                "avg_entry": 5.0,
                "avg_entry_cookies": 5.0,
            }
        }

        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=5.0, stock=75),
            _identity_point,
            now=10.0,
        )

        self.assertIsNone(action)

        diag = self.trader.get_diagnostics(
            _snapshot(cookies=1000.0, value=5.0, stock=75),
            _identity_point,
        )

        self.assertEqual(diag["portfolio_cap_ratio"], 0.25)
        self.assertEqual(diag["reason"], "portfolio_cap_reached")

    def test_buy_action_can_proceed_below_twenty_five_percent_cap(self):
        self.trader.positions = {
            0: {
                "shares": 25,
                "avg_entry": 5.0,
                "avg_entry_cookies": 5.0,
            }
        }

        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=5.0, stock=25),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy")

    def test_upgrades_office_before_trade_when_available(self):
        self._set_range_stats(range_min=4.0, range_max=10.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=4.2,
                resting_value=7.0,
                history=[8.0, 7.5, 6.0, 5.0, 4.2],
                office_level=0,
                office_name="Credit garage",
                next_office_level=1,
                next_office_name="Tiny bank",
                office_upgrade_cost=100,
                office_upgrade_cursor_level=2,
                can_upgrade_office=True,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "upgrade_office")

    def test_skips_office_upgrade_when_button_not_actionable(self):
        self._set_range_stats(range_min=4.0, range_max=10.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=4.2,
                resting_value=7.0,
                history=[8.0, 7.5, 6.0, 5.0, 4.2],
                office_level=0,
                office_name="Credit garage",
                next_office_level=1,
                next_office_name="Tiny bank",
                office_upgrade_cost=100,
                office_upgrade_cursor_level=2,
                can_upgrade_office=False,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy")

    def test_hires_broker_before_buy_when_trade_budget_allows(self):
        self._set_range_stats(range_min=4.0, range_max=10.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=4.2,
                resting_value=7.0,
                history=[8.0, 7.5, 6.0, 5.0, 4.2],
                brokers=0,
                brokers_max=10,
                broker_cost=50.0,
                can_hire_broker=True,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "hire_broker")

    def test_skips_broker_buy_when_it_would_consume_trade_budget(self):
        self._set_range_stats(range_min=4.0, range_max=10.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=30.0,
                value=4.2,
                resting_value=7.0,
                history=[8.0, 7.5, 6.0, 5.0, 4.2],
                brokers=0,
                brokers_max=10,
                broker_cost=26.0,
                can_hire_broker=True,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy")

    def test_uses_broker_price_fallback_from_cps_when_feed_cost_missing(self):
        self._set_range_stats(range_min=4.0, range_max=10.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=2000.0,
                value=4.2,
                resting_value=7.0,
                history=[8.0, 7.5, 6.0, 5.0, 4.2],
                brokers=0,
                brokers_max=10,
                broker_cost=None,
                can_hire_broker=True,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "hire_broker")

    def test_returns_open_bank_action_when_trade_signal_exists_but_minigame_is_closed(self):
        self._set_range_stats(range_min=4.0, range_max=10.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                on_minigame=False,
                include_controls=False,
                value=4.2,
                resting_value=7.0,
                history=[8.0, 7.5, 6.0, 5.0, 4.2],
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "open_bank")
        self.assertEqual((action.screen_x, action.screen_y), (10, 10))

    def test_reports_bank_closed_can_open_when_trade_signal_exists(self):
        self._set_range_stats(range_min=4.0, range_max=10.0)

        diag = self.trader.get_diagnostics(
            _snapshot(
                cookies=1000.0,
                on_minigame=False,
                include_controls=False,
                value=4.2,
                resting_value=7.0,
                history=[8.0, 7.5, 6.0, 5.0, 4.2],
            ),
            _identity_point,
        )

        self.assertEqual(diag["reason"], "bank_closed_can_open")
        self.assertTrue(diag["has_open_target"])

    def test_opens_bank_when_closed_even_without_learned_signal_yet(self):
        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                on_minigame=False,
                include_controls=False,
                value=12.0,
                resting_value=None,
                mode=None,
                mode_name=None,
                delta=None,
                history=[],
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "open_bank")
        self.assertEqual((action.screen_x, action.screen_y), (10, 10))

    def test_reports_bank_closed_can_open_without_learned_signal_yet(self):
        diag = self.trader.get_diagnostics(
            _snapshot(
                cookies=1000.0,
                on_minigame=False,
                include_controls=False,
                value=12.0,
                resting_value=None,
                mode=None,
                mode_name=None,
                delta=None,
                history=[],
            ),
            _identity_point,
        )

        self.assertEqual(diag["reason"], "bank_closed_can_open")
        self.assertTrue(diag["has_open_target"])

    def test_trailing_stop_sell_can_trigger_before_threshold(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 10.0,
                "avg_entry_cookies": 10.0,
                "opened_at": 0.0,
                "peak_price": 12.5,
                "peak_at": 5.0,
            }
        }

        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=11.0, stock=10, can_sell=True),
            _identity_point,
            now=40.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "sell")
        diag = self.trader.get_diagnostics(
            _snapshot(cookies=1000.0, value=11.0, stock=10, can_sell=True),
            _identity_point,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )
        self.assertEqual(diag["sell_reason"], "trailing_stop")

    def test_threshold_sell_does_not_fire_at_loss(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 60.0,
                "avg_entry_cookies": 60.0,
                "opened_at": 0.0,
                "peak_price": 60.0,
                "peak_at": 0.0,
            }
        }

        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=55.0, stock=10, can_sell=True),
            _identity_point,
            now=40.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNone(action)

    def test_trailing_stop_does_not_fire_at_loss(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 12.0,
                "avg_entry_cookies": 12.0,
                "opened_at": 0.0,
                "peak_price": 15.0,
                "peak_at": 5.0,
            }
        }

        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=11.0, stock=10, can_sell=True),
            _identity_point,
            now=40.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNone(action)

    def test_runtime_stats_include_performance_history(self):
        self.trader.positions = {
            0: {
                "shares": 5,
                "avg_entry": 10.0,
                "avg_entry_cookies": 10.0,
                "opened_at": 0.0,
                "peak_price": 10.0,
                "peak_at": 0.0,
            }
        }

        self.trader.get_diagnostics(
            _snapshot(cookies=1000.0, value=12.0, stock=5, can_sell=True),
            _identity_point,
        )
        self.trader.get_diagnostics(
            {
                **_snapshot(cookies=1000.0, value=13.0, stock=5, can_sell=True),
                "timestamp": 4000,
            },
            _identity_point,
        )

        stats = self.trader.get_runtime_stats()
        self.assertIn("performance_history", stats)
        self.assertGreaterEqual(len(stats["performance_history"]), 1)
        self.assertIn("session_roi", stats)
        latest = stats["performance_history"][-1]
        self.assertIn("net_pnl", latest)
        self.assertIn("cost_basis", latest)
        self.assertIn("session_roi", latest)

    def test_buy_action_can_use_hidden_state_discount_and_mode(self):
        self._set_range_stats(range_min=20.0, range_max=40.0, range_avg=30.0)
        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=24.0,
                resting_value=40.0,
                mode=1,
                mode_name="slow_rise",
                delta=0.05,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy")

    def test_record_action_logs_max_buy_label(self):
        self.trader.record_action(
            TradeAction(
                kind="buy",
                screen_x=20,
                screen_y=20,
                shares=-1,
                good_id=0,
                good_name="Cinnamon",
                price=5.0,
                cookies=1000.0,
            )
        )

        self.assertTrue(any("shares=MAX" in message for message in self.log.messages))

    def test_buy_action_avoids_bearish_hidden_state(self):
        self._set_range_stats(range_min=20.0, range_max=40.0, range_avg=30.0)
        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=24.0,
                resting_value=40.0,
                mode=4,
                mode_name="fast_fall",
                delta=-0.2,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNone(action)

    def test_buy_action_avoids_hidden_state_entry_near_resting_value(self):
        self._set_range_stats(range_min=20.0, range_max=40.0, range_avg=30.0)
        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=35.0,
                resting_value=40.0,
                mode=1,
                mode_name="slow_rise",
                delta=0.05,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNone(action)

    def test_buy_action_avoids_hidden_state_entry_when_not_near_recent_low(self):
        self._set_range_stats(range_min=20.0, range_max=40.0, range_avg=30.0)
        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=27.0,
                resting_value=40.0,
                mode=1,
                mode_name="slow_rise",
                delta=0.05,
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNone(action)

    def test_sell_action_can_use_bearish_reversion_signal(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 20.0,
                "avg_entry_cookies": 20.0,
                "opened_at": 0.0,
                "peak_price": 35.0,
                "peak_at": 5.0,
            }
        }

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=35.0,
                resting_value=30.0,
                stock=10,
                can_sell=True,
                mode=4,
                mode_name="fast_fall",
                delta=-0.15,
            ),
            _identity_point,
            now=10.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "sell")

    def test_buy_action_waits_for_better_reentry_after_profitable_sell(self):
        self.trader.last_profitable_sell_price_by_good[0] = 50.0
        self.trader.last_profitable_sell_time_by_good[0] = 9.0
        self._set_range_stats(range_min=35.0, range_max=60.0, range_avg=47.5)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=46.0,
                resting_value=80.0,
                mode=1,
                mode_name="slow_rise",
                delta=0.05,
                history=[46.0, 45.0, 44.0],
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNone(action)

    def test_buy_action_allows_discounted_reentry_after_profitable_sell(self):
        self.trader.last_profitable_sell_price_by_good[0] = 50.0
        self.trader.last_profitable_sell_time_by_good[0] = 9.0
        self._set_range_stats(range_min=35.0, range_max=80.0, range_avg=57.5)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=40.0,
                resting_value=80.0,
                mode=1,
                mode_name="slow_rise",
                delta=0.05,
                history=[40.0, 39.0, 38.0],
            ),
            _identity_point,
            now=10.0,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy")

    def test_sell_action_can_use_rollover_signal(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 20.0,
                "avg_entry_cookies": 20.0,
                "opened_at": 0.0,
                "peak_price": 30.0,
                "peak_at": 5.0,
            }
        }

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=27.0,
                resting_value=30.0,
                stock=10,
                can_sell=True,
                mode=1,
                mode_name="slow_rise",
                delta=-0.05,
                history=[27.0, 28.5, 29.5],
            ),
            _identity_point,
            now=10.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "sell")
        diag = self.trader.get_diagnostics(
            _snapshot(
                cookies=1000.0,
                value=35.0,
                resting_value=30.0,
                stock=10,
                can_sell=True,
                mode=4,
                mode_name="fast_fall",
                delta=-0.15,
            ),
            _identity_point,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )
        self.assertEqual(diag["sell_reason"], "bearish_reversion")

    def test_threshold_sell_waits_in_favorable_mode_while_momentum_is_positive(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 20.0,
                "avg_entry_cookies": 20.0,
                "opened_at": 0.0,
                "peak_price": 56.0,
                "peak_at": 5.0,
            }
        }
        self.trader.thresholds_by_good = {
            0: {"buy": 10.0, "sell": 50.0, "samples": 1000, "trades": 10, "learned": True}
        }
        self.trader.thresholds_refreshed_at_ms = 1000
        self._set_range_stats(range_min=20.0, range_max=80.0, range_avg=50.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=54.0,
                resting_value=40.0,
                stock=10,
                can_sell=True,
                mode=1,
                mode_name="slow_rise",
                delta=0.20,
                history=[54.0, 53.0, 52.0],
            ),
            _identity_point,
            now=40.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNone(action)

    def test_threshold_sell_waits_below_recent_high_even_if_above_threshold(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 20.0,
                "avg_entry_cookies": 20.0,
                "opened_at": 0.0,
                "peak_price": 56.0,
                "peak_at": 5.0,
            }
        }
        self.trader.thresholds_by_good = {
            0: {"buy": 10.0, "sell": 50.0, "samples": 1000, "trades": 10, "learned": True}
        }
        self.trader.thresholds_refreshed_at_ms = 1000
        self._set_range_stats(range_min=20.0, range_max=80.0, range_avg=50.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=52.0,
                resting_value=40.0,
                stock=10,
                can_sell=True,
                mode=1,
                mode_name="slow_rise",
                delta=0.02,
                history=[52.0, 51.0, 50.0],
            ),
            _identity_point,
            now=40.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNone(action)

    def test_threshold_sell_still_fires_after_breakout_extension(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 20.0,
                "avg_entry_cookies": 20.0,
                "opened_at": 0.0,
                "peak_price": 60.0,
                "peak_at": 5.0,
            }
        }
        self.trader.thresholds_by_good = {
            0: {"buy": 10.0, "sell": 50.0, "samples": 1000, "trades": 10, "learned": True}
        }
        self.trader.thresholds_refreshed_at_ms = 1000
        self._set_range_stats(range_min=20.0, range_max=70.0, range_avg=45.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=60.0,
                resting_value=40.0,
                stock=10,
                can_sell=True,
                mode=1,
                mode_name="slow_rise",
                delta=0.20,
                history=[60.0, 59.0, 58.0],
            ),
            _identity_point,
            now=40.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "sell")

    def test_threshold_sell_fires_near_recent_high_in_favorable_mode(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 20.0,
                "avg_entry_cookies": 20.0,
                "opened_at": 0.0,
                "peak_price": 68.0,
                "peak_at": 5.0,
            }
        }
        self.trader.thresholds_by_good = {
            0: {"buy": 10.0, "sell": 50.0, "samples": 1000, "trades": 10, "learned": True}
        }
        self.trader.thresholds_refreshed_at_ms = 1000
        self._set_range_stats(range_min=20.0, range_max=70.0, range_avg=45.0)

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=63.0,
                resting_value=40.0,
                stock=10,
                can_sell=True,
                mode=1,
                mode_name="slow_rise",
                delta=0.02,
                history=[63.0, 62.0, 61.0],
            ),
            _identity_point,
            now=40.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "sell")

    def test_threshold_sell_still_fires_in_non_favorable_mode(self):
        self.trader.positions = {
            0: {
                "shares": 10,
                "avg_entry": 20.0,
                "avg_entry_cookies": 20.0,
                "opened_at": 0.0,
                "peak_price": 52.0,
                "peak_at": 5.0,
            }
        }
        self.trader.thresholds_by_good = {
            0: {"buy": 10.0, "sell": 50.0, "samples": 1000, "trades": 10, "learned": True}
        }
        self.trader.thresholds_refreshed_at_ms = 1000

        action = self.trader.get_action(
            _snapshot(
                cookies=1000.0,
                value=52.0,
                resting_value=40.0,
                stock=10,
                can_sell=True,
                mode=2,
                mode_name="slow_fall",
                delta=-0.05,
                history=[52.0, 53.0, 54.0],
            ),
            _identity_point,
            now=40.0,
            allow_buy_actions=False,
            allow_sell_actions=True,
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "sell")

    def test_threshold_simulation_uses_current_broker_overhead(self):
        no_broker_profit, _ = self.trader._simulate_threshold_strategy(
            [10.0, 60.0],
            10.0,
            60.0,
            brokers=0,
        )
        many_broker_profit, _ = self.trader._simulate_threshold_strategy(
            [10.0, 60.0],
            10.0,
            60.0,
            brokers=25,
        )

        self.assertGreater(many_broker_profit, no_broker_profit)

    def test_diagnostics_and_trade_confirmation_write_trade_dataset_rows(self):
        diag = self.trader.get_diagnostics(
            _snapshot(cookies=1000.0, value=5.0),
            _identity_point,
        )
        self.assertEqual(diag["reason"], "buy_ready")
        self.assertEqual(len(self.db.trade_decisions), 1)

        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=5.0),
            _identity_point,
            now=10.0,
        )
        self.assertIsNotNone(action)
        self.trader.record_action(action)
        self.assertEqual(len(self.db.trade_events), 1)
        self.assertEqual(self.db.trade_events[0]["phase"], "click")

        buy_snapshot = self.trader.extract_state(
            _snapshot(cookies=1000.0, value=5.0, stock=10),
            _identity_point,
        )
        self.trader._apply_observed_changes(
            {0: buy_snapshot["goods"][0]},
            now=self.trader.pending_actions[0]["timestamp"] + 0.2,
        )
        self.assertEqual(len(self.db.trade_events), 2)
        self.assertEqual(self.db.trade_events[-1]["phase"], "confirm")
        self.assertEqual(self.db.trade_events[-1]["kind"], "buy")

    def test_failed_buy_100_downgrades_next_attempt_to_10(self):
        action = self.trader.get_action(
            _snapshot(cookies=10000.0, value=5.0),
            _identity_point,
            now=10.0,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy")
        self.assertEqual(action.shares, 100)

        self.trader.record_action(action)
        pending_started = self.trader.pending_actions[0]["timestamp"]
        self.trader._apply_observed_changes(
            {
                0: self.trader.extract_state(_snapshot(cookies=1000.0, value=5.0), _identity_point)["goods"][0]
            },
            now=pending_started + 1.0,
        )
        self.assertEqual(self.trader.buy_size_cap_by_good.get(0), 10)

        action = self.trader.get_action(
            _snapshot(cookies=10000.0, value=5.0),
            _identity_point,
            now=pending_started + 3.0,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action.shares, 10)

    def test_failed_buy_10_downgrades_next_attempt_to_1(self):
        self.trader.buy_size_cap_by_good[0] = 10
        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=5.0),
            _identity_point,
            now=10.0,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "buy")
        self.assertEqual(action.shares, 10)

        self.trader.record_action(action)
        pending_started = self.trader.pending_actions[0]["timestamp"]
        self.trader._apply_observed_changes(
            {
                0: self.trader.extract_state(_snapshot(cookies=1000.0, value=5.0), _identity_point)["goods"][0]
            },
            now=pending_started + 1.0,
        )
        self.assertEqual(self.trader.buy_size_cap_by_good.get(0), 1)

        action = self.trader.get_action(
            _snapshot(cookies=1000.0, value=5.0),
            _identity_point,
            now=pending_started + 3.0,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action.shares, 1)


if __name__ == "__main__":
    unittest.main()
