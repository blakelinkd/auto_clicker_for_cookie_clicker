from collections import deque
from dataclasses import dataclass
import math
import threading
import time


OPEN_BANK_COOLDOWN = 1.0
TRADE_COOLDOWN = 0.15
OPPOSITE_TRADE_SETTLE_SECONDS = 1.1
BUY_RETRY_BACKOFF_SECONDS = 2.0
BUY_CONFIRM_TIMEOUT_SECONDS = 0.8
BROKER_BUY_COOLDOWN = 0.35
BASE_BROKER_OVERHEAD = 0.20
BROKER_REDUCTION = 0.95
BROKER_PRICE_SECONDS = 20 * 60
RANGE_WINDOW_MS = 30 * 60 * 1000
MIN_RANGE_SAMPLES = 20
DEFAULT_BUY_PRICE_MAX = 10.0
DEFAULT_SELL_PRICE_MIN = 50.0
MIN_THRESHOLD_SAMPLES = 500
THRESHOLD_REFRESH_INTERVAL_MS = 5 * 60 * 1000
RANGE_STATS_REFRESH_INTERVAL_MS = 30 * 1000
SOFT_FLOOR_PRICE = 5.0
BUY_PERCENTILE_CANDIDATES = (0.10, 0.15, 0.20, 0.25, 0.30)
SELL_PERCENTILE_CANDIDATES = (0.65, 0.70, 0.75, 0.80, 0.85)
MAX_PORTFOLIO_EXPOSURE_RATIO = 0.25
POSITION_SAMPLE_INTERVAL_SECONDS = 2.0
PERFORMANCE_HISTORY_LIMIT = 240
TRAILING_STOP_ARM_GAIN = 0.12
TRAILING_STOP_GIVEBACK_FRACTION = 0.35
TRAILING_STOP_MIN_HOLD_SECONDS = 20.0
RESTING_VALUE_BUY_DISCOUNT_MIN = 0.18
RANGE_AVG_BUY_DISCOUNT_MIN = 0.05
RESTING_VALUE_BUY_CEILING_RATIO = 0.85
RESTING_VALUE_SELL_PREMIUM_MIN = 0.08
ENTRY_PROFIT_SELL_FLOOR = 0.03
ROLLOVER_PROFIT_SELL_FLOOR = 0.06
ROLLOVER_GIVEBACK_FRACTION = 0.05
RANGE_POSITION_BUY_MAX = 0.35
THRESHOLD_SELL_BREAKOUT_RATIO = 1.10
HIDDEN_STATE_RANGE_POSITION_BUY_MAX = 0.20
FAVORABLE_RANGE_POSITION_SELL_MIN = 0.80
PROFITABLE_REENTRY_COOLDOWN_SECONDS = 180.0
PROFITABLE_REENTRY_DISCOUNT_MIN = 0.12
CHAOTIC_REENTRY_COOLDOWN_SECONDS = 300.0
CHAOTIC_REENTRY_DISCOUNT_MIN = 0.22
EXTREME_BARGAIN_RESTING_RATIO = 0.45
BUY_FAVORABLE_MODES = {"stable", "slow_rise", "fast_rise"}
BUY_UNFAVORABLE_MODES = {"slow_fall", "fast_fall"}
SELL_BEARISH_MODES = {"slow_fall", "fast_fall", "chaotic"}
MODE_NAME_BY_ID = {
    0: "stable",
    1: "slow_rise",
    2: "slow_fall",
    3: "fast_rise",
    4: "fast_fall",
    5: "chaotic",
}


@dataclass
class TradeAction:
    kind: str
    screen_x: int
    screen_y: int
    repeats: int = 1
    shares: int = 1
    good_id: int | None = None
    good_name: str | None = None
    price: float | None = None
    cookies: float | None = None
    unit_cost_cookies: float | None = None
    unit_sale_cookies: float | None = None
    reason: str | None = None
    context: dict | None = None


class StockTrader:
    def __init__(self, log, db):
        self.log = log
        self.db = db
        self.positions = self.db.load_positions()
        self.pending_actions = {}
        self.last_open_click = 0.0
        self.last_trade_click = 0.0
        self.last_bank_upgrade_click = 0.0
        self.last_trade_kind_by_good = {}
        self.last_trade_time_by_good = {}
        self.buy_retry_after_by_good = {}
        self.buy_size_cap_by_good = {}
        self.last_sell_price_by_good = {}
        self.last_sell_time_by_good = {}
        self.last_profitable_sell_price_by_good = {}
        self.last_profitable_sell_time_by_good = {}
        self.last_recorded_timestamp = None
        self.last_history_timestamp = None
        self.range_stats_cache = {}
        self.buy_clicks = 0
        self.sell_clicks = 0
        self.buy_confirms = 0
        self.sell_confirms = 0
        self.realized_pnl = 0.0
        self.total_confirmed_buy_cost = sum(
            float(position.get("shares", 0)) * float(position.get("avg_entry_cookies", 0.0))
            for position in self.positions.values()
        )
        self.last_trade_summary = None
        self.last_buy_pick = None
        self.thresholds_by_good = {}
        self.thresholds_refreshed_at_ms = None
        self.range_stats_refreshed_at_ms = None
        self.profile = {}
        self.profile_last_log_at = {}
        self.performance_history = deque(maxlen=PERFORMANCE_HISTORY_LIMIT)
        self.last_performance_sample_at = None
        self.peak_cost_basis = self._current_exposure_cost_basis()
        self.cache_lock = threading.Lock()
        self.threshold_refresh_lock = threading.Lock()
        self.threshold_refresh_in_flight = False
        self.last_decision_signature = None
        self.last_decision_logged_at_ms = 0

    def extract_state(self, snapshot, to_screen_point):
        started = time.perf_counter()
        if not snapshot or not isinstance(snapshot, dict):
            return None

        bank = snapshot.get("bank")
        if not isinstance(bank, dict):
            return None

        cookies = snapshot.get("cookies")
        if cookies is None:
            cookies = 0

        goods = []
        for good in bank.get("goods", []):
            if not isinstance(good, dict):
                continue
            value = good.get("value")
            stock = good.get("stock")
            stock_max = good.get("stockMax")
            if value is None or stock is None:
                continue
            goods.append(
                {
                    "id": int(good.get("id", -1)),
                    "symbol": good.get("symbol"),
                    "name": good.get("name") or good.get("symbol") or f"good-{good.get('id', '?')}",
                    "value": float(value),
                    "resting_value": None
                    if good.get("restingValue") is None
                    else float(good.get("restingValue")),
                    "stock": int(stock),
                    "stock_max": None if stock_max is None else int(stock_max),
                    "active": bool(good.get("active", True)),
                    "hidden": bool(good.get("hidden", False)),
                    "mode": None if good.get("mode") is None else int(good.get("mode")),
                    "mode_name": good.get("modeName")
                    or MODE_NAME_BY_ID.get(
                        None if good.get("mode") is None else int(good.get("mode"))
                    ),
                    "mode_ticks_remaining": None
                    if good.get("modeTicksRemaining") is None
                    else int(good.get("modeTicksRemaining")),
                    "last": None if good.get("last") is None else int(good.get("last")),
                    "delta": None if good.get("delta") is None else float(good.get("delta")),
                    "unit_sale_cookies": float(value) * float(snapshot.get("cookiesPsRawHighest") or snapshot.get("cookiesPs") or 0.0),
                    "history": [
                        float(item)
                        for item in good.get("history", [])
                        if item is not None
                    ],
                    "buy_target": self._normalize_target(good.get("buy"), to_screen_point),
                    "buy_targets": {
                        1: self._normalize_target(good.get("buy1") or good.get("buy"), to_screen_point),
                        10: self._normalize_target(good.get("buy10"), to_screen_point),
                        100: self._normalize_target(good.get("buy100"), to_screen_point),
                        -1: self._normalize_target(good.get("buyMax"), to_screen_point),
                    },
                    "sell_target": self._normalize_target(good.get("sellAll") or good.get("sell"), to_screen_point),
                    "sell_targets": {
                        1: self._normalize_target(good.get("sell1") or good.get("sell"), to_screen_point),
                        10: self._normalize_target(good.get("sell10"), to_screen_point),
                        100: self._normalize_target(good.get("sell100"), to_screen_point),
                        -1: self._normalize_target(good.get("sellAll"), to_screen_point),
                    },
                    "can_buy": bool(good.get("canBuy")),
                    "can_buy_1": bool(good.get("canBuy1", good.get("canBuy"))),
                    "can_buy_10": bool(good.get("canBuy10")),
                    "can_buy_100": bool(good.get("canBuy100")),
                    "can_buy_max": bool(good.get("canBuyMax")),
                    "can_sell": bool(good.get("canSellAll") or good.get("canSell")),
                    "can_sell_1": bool(good.get("canSell1", good.get("canSell"))),
                    "can_sell_10": bool(good.get("canSell10")),
                    "can_sell_100": bool(good.get("canSell100")),
                    "can_sell_all": bool(good.get("canSellAll")),
                }
            )

        state = {
            "timestamp": snapshot.get("timestamp"),
            "cookies": float(cookies),
            "cookies_ps_raw_highest": float(snapshot.get("cookiesPsRawHighest") or snapshot.get("cookiesPs") or 0.0),
            "brokers": int(bank.get("brokers") or 0),
            "office_level": None
            if bank.get("officeLevel") is None
            else int(bank.get("officeLevel")),
            "office_name": bank.get("officeName"),
            "brokers_max": None if bank.get("brokersMax") is None else int(bank.get("brokersMax")),
            "broker_cost": None if bank.get("brokerCost") is None else float(bank.get("brokerCost")),
            "broker_target": self._normalize_target(bank.get("brokerControl"), to_screen_point),
            "can_hire_broker": bool(bank.get("canHireBroker")),
            "next_office_level": None
            if bank.get("nextOfficeLevel") is None
            else int(bank.get("nextOfficeLevel")),
            "next_office_name": bank.get("nextOfficeName"),
            "office_upgrade_cost": bank.get("officeUpgradeCost"),
            "office_upgrade_cursor_level": None
            if bank.get("officeUpgradeCursorLevel") is None
            else int(bank.get("officeUpgradeCursorLevel")),
            "office_upgrade_target": self._normalize_target(bank.get("officeUpgradeControl"), to_screen_point),
            "can_upgrade_office": bool(bank.get("canUpgradeOffice")),
            "profit": None if bank.get("profit") is None else float(bank.get("profit")),
            "ticks": None if bank.get("ticks") is None else int(bank.get("ticks")),
            "tick_frames": None
            if bank.get("tickFrames") is None
            else int(bank.get("tickFrames")),
            "seconds_per_tick": None
            if bank.get("secondsPerTick") is None
            else float(bank.get("secondsPerTick")),
            "next_tick_at": None
            if bank.get("nextTickAt") is None
            else int(bank.get("nextTickAt")),
            "on_minigame": bool(bank.get("onMinigame")),
            "open_target": self._normalize_target(bank.get("openControl"), to_screen_point),
            "goods": goods,
        }
        self._record_history(state)
        self._attach_recent_stats(state)
        self._refresh_thresholds_if_needed(state)
        self._attach_thresholds(state)
        self._record_profile("extract_state", time.perf_counter() - started, spike_ms=20.0)
        return state

    def get_action(
        self,
        snapshot,
        to_screen_point,
        now=None,
        allow_buy_actions=True,
        allow_sell_actions=True,
        buy_reserve_cookies=0.0,
    ):
        started = time.perf_counter()
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None

        now = time.monotonic() if now is None else now
        goods = {item["id"]: item for item in state["goods"]}
        self._apply_observed_changes(goods, now)
        self._reconcile_positions(goods, state["brokers"], state["cookies_ps_raw_highest"])
        self._update_position_markers(goods, now)
        self._record_performance_snapshot(state, goods, now)

        sell_candidate = self._find_sell_candidate(goods)
        buy_candidate = self._find_buy_candidate(
            goods,
            state["cookies"],
            state["brokers"],
            state["cookies_ps_raw_highest"],
            now,
        )

        if not state["on_minigame"]:
            latent_sell_candidate = self._find_sell_candidate(goods, require_targets=False)
            latent_buy_candidate = self._find_buy_candidate(
                goods,
                state["cookies"],
                state["brokers"],
                state["cookies_ps_raw_highest"],
                now,
                require_targets=False,
            )
            if (
                (allow_sell_actions or allow_buy_actions)
                and state["open_target"] is not None
                and (now - self.last_open_click) >= OPEN_BANK_COOLDOWN
            ):
                target = state["open_target"]
                self._record_profile("get_action", time.perf_counter() - started, spike_ms=20.0)
                return TradeAction(
                    kind="open_bank",
                    screen_x=target["screen_x"],
                    screen_y=target["screen_y"],
                    cookies=state["cookies"],
                    context={
                        "buy_candidate": self._compact_good_context(latent_buy_candidate),
                        "sell_candidate": self._compact_good_context(
                            None if latent_sell_candidate is None else latent_sell_candidate[0]
                        ),
                    },
                )
            return None

        planned_buy_cost = self._planned_buy_cost(
            buy_candidate,
            goods,
            state["cookies"],
            state["brokers"],
            state["cookies_ps_raw_highest"],
            buy_reserve_cookies,
        )
        if (now - self.last_bank_upgrade_click) >= BROKER_BUY_COOLDOWN:
            office_upgrade_action = self._get_office_upgrade_action(
                state,
                allow_buy_actions=allow_buy_actions,
                allow_sell_actions=allow_sell_actions,
                planned_buy_cost=planned_buy_cost,
            )
            if office_upgrade_action is not None:
                self._record_profile("get_action", time.perf_counter() - started, spike_ms=20.0)
                return office_upgrade_action
            broker_action = self._get_broker_action(
                state,
                allow_buy_actions=allow_buy_actions,
                allow_sell_actions=allow_sell_actions,
                planned_buy_cost=planned_buy_cost,
            )
            if broker_action is not None:
                self._record_profile("get_action", time.perf_counter() - started, spike_ms=20.0)
                return broker_action

        if allow_sell_actions and sell_candidate is not None and (now - self.last_trade_click) >= TRADE_COOLDOWN:
            good, _position, sell_reason = sell_candidate
            sell_size = self._choose_sell_size(good, _position)
            target = good["sell_targets"].get(sell_size)
            if target is None:
                return None
            self._record_profile("get_action", time.perf_counter() - started, spike_ms=20.0)
            return TradeAction(
                kind="sell",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                shares=sell_size,
                good_id=good["id"],
                good_name=good["name"],
                price=good["value"],
                cookies=state["cookies"],
                unit_cost_cookies=None,
                unit_sale_cookies=float(good["value"]) * float(state["cookies_ps_raw_highest"]),
                reason=sell_reason,
                context=self._compact_good_context(good),
            )

        if allow_buy_actions and buy_candidate is not None and (now - self.last_trade_click) >= TRADE_COOLDOWN:
            good = buy_candidate
            if good["value"] <= 0:
                return None
            unit_cost_cookies = self._estimate_buy_cost(
                good["value"],
                state["brokers"],
                state["cookies_ps_raw_highest"],
            )
            available_cookies = max(0.0, float(state["cookies"]) - max(0.0, float(buy_reserve_cookies)))
            affordable = math.floor(available_cookies / unit_cost_cookies)
            if affordable <= 0:
                return None
            exposure = self._current_exposure_mark_to_market(goods, state["cookies_ps_raw_highest"])
            remaining_capacity = self._exposure_cap(state["cookies"], exposure) - exposure
            max_affordable_by_cap = math.floor(remaining_capacity / unit_cost_cookies)
            capped_affordable = min(affordable, max_affordable_by_cap)
            size_cap = self.buy_size_cap_by_good.get(good["id"])
            if size_cap is not None:
                capped_affordable = min(capped_affordable, int(size_cap))
            buy_size = self._choose_buy_size(good, capped_affordable, allow_max=(capped_affordable == affordable))
            target = good["buy_targets"].get(buy_size)
            if target is None:
                return None
            self._record_profile("get_action", time.perf_counter() - started, spike_ms=20.0)
            return TradeAction(
                kind="buy",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                shares=buy_size,
                good_id=good["id"],
                good_name=good["name"],
                price=good["value"],
                cookies=state["cookies"],
                unit_cost_cookies=unit_cost_cookies,
                unit_sale_cookies=None,
                reason="buy_ready",
                context=self._compact_good_context(good),
            )

        self._record_profile("get_action", time.perf_counter() - started, spike_ms=20.0)
        return None

    def get_diagnostics(
        self,
        snapshot,
        to_screen_point,
        allow_buy_actions=True,
        allow_sell_actions=True,
        buy_reserve_cookies=0.0,
    ):
        started = time.perf_counter()
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return {
                "available": False,
                "reason": "no_bank_data",
            }

        goods = {item["id"]: item for item in state["goods"]}
        now = time.monotonic()
        self._apply_observed_changes(goods, now)
        self._reconcile_positions(goods, state["brokers"], state["cookies_ps_raw_highest"])
        self._update_position_markers(goods, now)
        self._record_performance_snapshot(state, goods, now)
        sell_candidate = self._find_sell_candidate(goods)
        buy_candidate = self._find_buy_candidate(
            goods,
            state["cookies"],
            state["brokers"],
            state["cookies_ps_raw_highest"],
            now,
        )
        latent_sell_candidate = self._find_sell_candidate(goods, require_targets=False)
        latent_buy_candidate = self._find_buy_candidate(
            goods,
            state["cookies"],
            state["brokers"],
            state["cookies_ps_raw_highest"],
            now,
            require_targets=False,
        )

        goods_with_buy = sum(1 for item in state["goods"] if item["buy_target"] is not None)
        goods_with_sell = sum(1 for item in state["goods"] if item["sell_target"] is not None)
        goods_buy_enabled = sum(1 for item in state["goods"] if item["buy_target"] is not None and item["can_buy"])
        goods_in_buy_zone = sum(1 for item in state["goods"] if self._is_buy_zone(item, now))
        goods_with_thresholds = sum(1 for item in state["goods"] if item.get("threshold_learned"))
        goods_at_capacity = sum(
            1
            for item in state["goods"]
            if item["stock_max"] is not None and item["stock"] >= item["stock_max"]
        )
        goods_with_history = sum(1 for item in state["goods"] if item.get("range_samples", 0) >= MIN_RANGE_SAMPLES)
        goods_with_hidden_state = sum(
            1
            for item in state["goods"]
            if item.get("mode") is not None
            and item.get("mode_ticks_remaining") is not None
            and item.get("resting_value") is not None
        )
        goods_above_resting = sum(
            1
            for item in state["goods"]
            if item.get("resting_value") is not None and item["value"] > item["resting_value"]
        )
        held_goods = len(self.positions)
        held_shares = sum(position["shares"] for position in self.positions.values())
        exposure = self._current_exposure_mark_to_market(goods, state["cookies_ps_raw_highest"])
        exposure_cap = self._exposure_cap(state["cookies"], exposure)
        exposure_ratio = 0.0 if exposure_cap <= 0 else exposure / max(state["cookies"] + exposure, 1e-9)
        buy_cookies_available = max(0.0, float(state["cookies"]) - max(0.0, float(buy_reserve_cookies)))

        if not state["on_minigame"]:
            if allow_sell_actions or allow_buy_actions:
                reason = "bank_closed_can_open" if state["open_target"] is not None else "bank_closed_missing_open_control"
            else:
                reason = "bank_closed_no_trade_signal"
        elif allow_sell_actions and sell_candidate is not None:
            reason = "sell_ready"
        elif buy_candidate is not None and not allow_buy_actions:
            reason = "buy_blocked"
        elif allow_buy_actions and buy_candidate is not None:
            reason = "buy_ready"
        elif exposure >= exposure_cap > 0:
            reason = "portfolio_cap_reached"
        elif held_goods > 0:
            reason = "holding_waiting_for_target"
        else:
            reason = "no_buy_signal"

        display_buy_candidate = buy_candidate if state["on_minigame"] else latent_buy_candidate
        display_sell_candidate = sell_candidate if state["on_minigame"] else latent_sell_candidate

        result = {
            "available": True,
            "reason": reason,
            "cookies": state["cookies"],
            "cookies_ps_raw_highest": state["cookies_ps_raw_highest"],
            "brokers": state["brokers"],
            "office_level": state["office_level"],
            "office_name": state["office_name"],
            "brokers_max": state["brokers_max"],
            "broker_cost": state["broker_cost"],
            "can_hire_broker": bool(state["can_hire_broker"] and state["broker_target"] is not None),
            "next_office_level": state["next_office_level"],
            "next_office_name": state["next_office_name"],
            "office_upgrade_cost": state["office_upgrade_cost"],
            "office_upgrade_cursor_level": state["office_upgrade_cursor_level"],
            "can_upgrade_office": bool(state["can_upgrade_office"] and state["office_upgrade_target"] is not None),
            "market_profit": state["profit"],
            "next_tick_at": state["next_tick_at"],
            "seconds_per_tick": state["seconds_per_tick"],
            "on_minigame": state["on_minigame"],
            "has_open_target": state["open_target"] is not None,
            "goods_total": len(state["goods"]),
            "goods_with_buy_target": goods_with_buy,
            "goods_with_sell_target": goods_with_sell,
            "goods_with_buy_enabled": goods_buy_enabled,
            "goods_in_buy_zone": goods_in_buy_zone,
            "goods_with_thresholds": goods_with_thresholds,
            "goods_at_capacity": goods_at_capacity,
            "goods_with_history": goods_with_history,
            "goods_with_hidden_state": goods_with_hidden_state,
            "goods_above_resting": goods_above_resting,
            "held_goods": held_goods,
            "held_shares": held_shares,
            "portfolio_exposure": exposure,
            "portfolio_cap": exposure_cap,
            "portfolio_cap_ratio": MAX_PORTFOLIO_EXPOSURE_RATIO,
            "portfolio_exposure_ratio": exposure_ratio,
            "portfolio_remaining": max(0.0, exposure_cap - exposure),
            "buy_actions_enabled": bool(allow_buy_actions),
            "sell_actions_enabled": bool(allow_sell_actions),
            "buy_reserve_cookies": max(0.0, float(buy_reserve_cookies)),
            "buy_cookies_available": buy_cookies_available,
            "buy_candidate": None if display_buy_candidate is None else display_buy_candidate["name"],
            "sell_candidate": None if display_sell_candidate is None else display_sell_candidate[0]["name"],
            "buy_threshold": None if display_buy_candidate is None else display_buy_candidate.get("buy_threshold"),
            "sell_threshold": None if display_sell_candidate is None else display_sell_candidate[0].get("sell_threshold"),
            "buy_candidate_mode": None if display_buy_candidate is None else display_buy_candidate.get("mode_name"),
            "buy_candidate_resting_value": None
            if display_buy_candidate is None
            else display_buy_candidate.get("resting_value"),
            "sell_candidate_mode": None
            if display_sell_candidate is None
            else display_sell_candidate[0].get("mode_name"),
            "sell_candidate_resting_value": None
            if display_sell_candidate is None
            else display_sell_candidate[0].get("resting_value"),
            "sell_reason": None if display_sell_candidate is None else display_sell_candidate[2],
        }
        self._record_trade_decision_snapshot(
            state=state,
            result=result,
            buy_candidate=buy_candidate,
            sell_candidate=sell_candidate,
        )
        self._record_profile("get_diagnostics", time.perf_counter() - started, spike_ms=20.0)
        return result

    def record_action(self, action):
        now = time.monotonic()
        event_at_ms = int(time.time() * 1000)
        if action.kind == "open_bank":
            self.last_open_click = now
            self.db.record_trade_event(
                event_at_ms=event_at_ms,
                phase="click",
                kind=action.kind,
                cookies=action.cookies,
                extra=action.context,
            )
            return

        if action.kind in {"hire_broker", "upgrade_office"}:
            self.last_bank_upgrade_click = now
            self.db.record_trade_event(
                event_at_ms=event_at_ms,
                phase="click",
                kind=action.kind,
                cookies=action.cookies,
                extra=action.context,
            )
            return

        self.last_trade_click = now
        if action.good_id is None or action.price is None:
            return

        previous_shares = self.positions.get(action.good_id, {}).get("shares", 0)
        self.pending_actions[action.good_id] = {
            "kind": action.kind,
            "price": action.price,
            "name": action.good_name,
            "previous_shares": previous_shares,
            "unit_cost_cookies": 0.0 if action.unit_cost_cookies is None else float(action.unit_cost_cookies),
            "unit_sale_cookies": 0.0 if action.unit_sale_cookies is None else float(action.unit_sale_cookies),
            "shares": int(action.shares),
            "timestamp": now,
            "context": dict(action.context or {}),
            "reason": action.reason,
        }
        self.last_trade_kind_by_good[action.good_id] = action.kind
        self.last_trade_time_by_good[action.good_id] = now
        context = dict(action.context or {})
        self.db.record_trade_event(
            event_at_ms=event_at_ms,
            phase="click",
            kind=action.kind,
            good_id=action.good_id,
            symbol=context.get("symbol"),
            name=action.good_name,
            shares=action.shares,
            price=action.price,
            cookies=action.cookies,
            unit_cost_cookies=action.unit_cost_cookies,
            unit_sale_cookies=action.unit_sale_cookies,
            previous_shares=previous_shares,
            reason=action.reason,
            mode_name=context.get("mode_name"),
            resting_value=context.get("resting_value"),
            range_min=context.get("range_min"),
            range_max=context.get("range_max"),
            range_avg=context.get("range_avg"),
            range_position=context.get("range_position"),
            buy_threshold=context.get("buy_threshold"),
            sell_threshold=context.get("sell_threshold"),
            delta=context.get("delta"),
            history=context.get("history"),
            extra=context,
        )

        if action.kind == "buy":
            self.buy_clicks += 1
            self.last_trade_summary = f"BUY click {action.good_name} @ {action.price:.2f}"
            self.log.info(
                f"Stock buy click good={action.good_name} id={action.good_id} "
                f"shares={self._format_logged_shares(action.shares)} price={action.price:.2f} cookies={action.cookies:.1f}"
            )
        elif action.kind == "sell":
            self.sell_clicks += 1
            self.last_trade_summary = f"SELL click {action.good_name} @ {action.price:.2f}"
            self.log.info(
                f"Stock sell click good={action.good_name} id={action.good_id} "
                f"shares={self._format_logged_shares(action.shares)} price={action.price:.2f} cookies={action.cookies:.1f}"
            )

    def _format_logged_shares(self, shares):
        return "MAX" if int(shares or 0) < 0 else str(int(shares or 0))

    def _apply_observed_changes(self, goods, now):
        for good_id in list(self.pending_actions):
            good = goods.get(good_id)
            if good is None:
                continue

            pending = self.pending_actions[good_id]
            observed_shares = good["stock"]
            previous_shares = pending["previous_shares"]

            if pending["kind"] == "buy":
                if observed_shares > previous_shares:
                    delta_shares = observed_shares - previous_shares
                    position = self.positions.get(good_id)
                    avg_entry_before = 0.0 if position is None else float(position.get("avg_entry", 0.0))
                    avg_entry_cookies_before = 0.0 if position is None else float(position.get("avg_entry_cookies", 0.0))
                    if position is None:
                        position = {"shares": 0, "avg_entry": 0.0, "avg_entry_cookies": 0.0}
                        self.positions[good_id] = position
                    total_cost = (position["shares"] * position["avg_entry"]) + (delta_shares * pending["price"])
                    total_cookie_cost = (
                        (position["shares"] * float(position.get("avg_entry_cookies", 0.0)))
                        + (delta_shares * float(pending.get("unit_cost_cookies", 0.0)))
                    )
                    position["shares"] = observed_shares
                    if position["shares"] > 0:
                        position["avg_entry"] = total_cost / position["shares"]
                        position["avg_entry_cookies"] = total_cookie_cost / position["shares"]
                    self._initialize_or_update_position_metadata(position, pending["price"], now)
                    self._persist_position(good_id, good, position)
                    self.log.info(
                        f"Stock buy confirmed good={pending['name']} id={good_id} "
                        f"price={pending['price']:.2f} stock={observed_shares}"
                    )
                    self.total_confirmed_buy_cost += delta_shares * float(pending.get("unit_cost_cookies", 0.0))
                    self.buy_confirms += 1
                    self.last_trade_summary = (
                        f"BUY {pending['name']} +{delta_shares} @ {pending['price']:.2f}"
                    )
                    context = dict(pending.get("context") or {})
                    self.db.record_trade_event(
                        event_at_ms=int(time.time() * 1000),
                        phase="confirm",
                        kind="buy",
                        good_id=good_id,
                        symbol=good.get("symbol"),
                        name=pending["name"],
                        shares=delta_shares,
                        price=pending["price"],
                        unit_cost_cookies=pending.get("unit_cost_cookies"),
                        previous_shares=previous_shares,
                        observed_shares=observed_shares,
                        avg_entry_before=avg_entry_before,
                        avg_entry_after=position.get("avg_entry"),
                        avg_entry_cookies_before=avg_entry_cookies_before,
                        avg_entry_cookies_after=position.get("avg_entry_cookies"),
                        reason=pending.get("reason"),
                        mode_name=good.get("mode_name"),
                        resting_value=good.get("resting_value"),
                        range_min=good.get("range_min"),
                        range_max=good.get("range_max"),
                        range_avg=good.get("range_avg"),
                        range_position=good.get("range_position"),
                        buy_threshold=good.get("buy_threshold"),
                        sell_threshold=good.get("sell_threshold"),
                        delta=good.get("delta"),
                        history=good.get("history"),
                        extra=context,
                    )
                    self.buy_size_cap_by_good.pop(good_id, None)
                    self.buy_retry_after_by_good.pop(good_id, None)
                    self.pending_actions.pop(good_id, None)
                elif good.get("last") == 2:
                    self.db.record_trade_event(
                        event_at_ms=int(time.time() * 1000),
                        phase="rejected",
                        kind="buy",
                        good_id=good_id,
                        symbol=good.get("symbol"),
                        name=pending["name"],
                        shares=pending.get("shares"),
                        price=pending.get("price"),
                        previous_shares=previous_shares,
                        observed_shares=observed_shares,
                        reason="game_last_rejected_buy",
                        mode_name=good.get("mode_name"),
                        resting_value=good.get("resting_value"),
                        range_min=good.get("range_min"),
                        range_max=good.get("range_max"),
                        range_avg=good.get("range_avg"),
                        range_position=good.get("range_position"),
                        buy_threshold=good.get("buy_threshold"),
                        sell_threshold=good.get("sell_threshold"),
                        delta=good.get("delta"),
                        history=good.get("history"),
                        extra=pending.get("context"),
                    )
                    self._downgrade_buy_size_cap(good_id, pending.get("shares"))
                    self.buy_retry_after_by_good[good_id] = now + BUY_RETRY_BACKOFF_SECONDS
                    self.pending_actions.pop(good_id, None)
                elif (now - pending["timestamp"]) >= BUY_CONFIRM_TIMEOUT_SECONDS:
                    self.log.debug(
                        f"Stock buy not confirmed good={pending['name']} id={good_id} "
                        f"price={pending['price']:.2f} stock={observed_shares}; backing off"
                    )
                    self.db.record_trade_event(
                        event_at_ms=int(time.time() * 1000),
                        phase="timeout",
                        kind="buy",
                        good_id=good_id,
                        symbol=good.get("symbol"),
                        name=pending["name"],
                        shares=pending.get("shares"),
                        price=pending.get("price"),
                        previous_shares=previous_shares,
                        observed_shares=observed_shares,
                        reason="buy_not_confirmed",
                        mode_name=good.get("mode_name"),
                        resting_value=good.get("resting_value"),
                        range_min=good.get("range_min"),
                        range_max=good.get("range_max"),
                        range_avg=good.get("range_avg"),
                        range_position=good.get("range_position"),
                        buy_threshold=good.get("buy_threshold"),
                        sell_threshold=good.get("sell_threshold"),
                        delta=good.get("delta"),
                        history=good.get("history"),
                        extra=pending.get("context"),
                    )
                    self._downgrade_buy_size_cap(good_id, pending.get("shares"))
                    self.buy_retry_after_by_good[good_id] = now + BUY_RETRY_BACKOFF_SECONDS
                    self.pending_actions.pop(good_id, None)
            elif pending["kind"] == "sell":
                if observed_shares < previous_shares:
                    delta_shares = previous_shares - observed_shares
                    position = self.positions.get(good_id)
                    avg_entry = 0.0 if position is None else float(position.get("avg_entry", 0.0))
                    avg_entry_cookies = 0.0 if position is None else float(position.get("avg_entry_cookies", 0.0))
                    if position is not None:
                        position["shares"] = observed_shares
                        if observed_shares <= 0:
                            self.positions.pop(good_id, None)
                            self.db.delete_position(good_id)
                        else:
                            self._persist_position(good_id, good, position)
                    pnl = delta_shares * (pending["price"] - avg_entry)
                    realized_pnl_cookies = (
                        delta_shares * float(pending.get("unit_sale_cookies", 0.0))
                    ) - (delta_shares * avg_entry_cookies)
                    self.realized_pnl += realized_pnl_cookies
                    self.last_sell_price_by_good[good_id] = float(pending["price"])
                    self.last_sell_time_by_good[good_id] = float(now)
                    if realized_pnl_cookies > 0.0:
                        self.last_profitable_sell_price_by_good[good_id] = float(pending["price"])
                        self.last_profitable_sell_time_by_good[good_id] = float(now)
                    self.log.info(
                        f"Stock sell confirmed good={pending['name']} id={good_id} "
                        f"price={pending['price']:.2f} stock={observed_shares}"
                    )
                    self.sell_confirms += 1
                    self.last_trade_summary = (
                        f"SELL {pending['name']} -{delta_shares} @ {pending['price']:.2f} pnl={realized_pnl_cookies:.2f}"
                    )
                    self.db.record_trade_event(
                        event_at_ms=int(time.time() * 1000),
                        phase="confirm",
                        kind="sell",
                        good_id=good_id,
                        symbol=good.get("symbol"),
                        name=pending["name"],
                        shares=delta_shares,
                        price=pending["price"],
                        unit_sale_cookies=pending.get("unit_sale_cookies"),
                        previous_shares=previous_shares,
                        observed_shares=observed_shares,
                        avg_entry_before=avg_entry,
                        avg_entry_after=avg_entry if observed_shares > 0 else 0.0,
                        avg_entry_cookies_before=avg_entry_cookies,
                        avg_entry_cookies_after=avg_entry_cookies if observed_shares > 0 else 0.0,
                        realized_pnl_cookies=realized_pnl_cookies,
                        reason=pending.get("reason"),
                        mode_name=good.get("mode_name"),
                        resting_value=good.get("resting_value"),
                        range_min=good.get("range_min"),
                        range_max=good.get("range_max"),
                        range_avg=good.get("range_avg"),
                        range_position=good.get("range_position"),
                        buy_threshold=good.get("buy_threshold"),
                        sell_threshold=good.get("sell_threshold"),
                        delta=good.get("delta"),
                        history=good.get("history"),
                        extra=pending.get("context"),
                    )
                    self.pending_actions.pop(good_id, None)
                elif good.get("last") == 1:
                    self.db.record_trade_event(
                        event_at_ms=int(time.time() * 1000),
                        phase="rejected",
                        kind="sell",
                        good_id=good_id,
                        symbol=good.get("symbol"),
                        name=pending["name"],
                        shares=pending.get("shares"),
                        price=pending.get("price"),
                        previous_shares=previous_shares,
                        observed_shares=observed_shares,
                        reason="game_last_rejected_sell",
                        mode_name=good.get("mode_name"),
                        resting_value=good.get("resting_value"),
                        range_min=good.get("range_min"),
                        range_max=good.get("range_max"),
                        range_avg=good.get("range_avg"),
                        range_position=good.get("range_position"),
                        buy_threshold=good.get("buy_threshold"),
                        sell_threshold=good.get("sell_threshold"),
                        delta=good.get("delta"),
                        history=good.get("history"),
                        extra=pending.get("context"),
                    )
                    self.pending_actions.pop(good_id, None)

    def _record_history(self, state):
        started = time.perf_counter()
        timestamp = state.get("timestamp")
        if timestamp is None or timestamp == self.last_recorded_timestamp:
            return
        self.db.record_prices(timestamp, state["goods"])
        self.last_recorded_timestamp = timestamp
        self._record_profile("record_history", time.perf_counter() - started, spike_ms=10.0)

    def _attach_recent_stats(self, state):
        started = time.perf_counter()
        timestamp = state.get("timestamp")
        if timestamp is None:
            for good in state["goods"]:
                good["range_min"] = None
                good["range_max"] = None
                good["range_avg"] = None
                good["range_samples"] = 0
                good["range_position"] = None
            return

        needs_refresh = False
        with self.cache_lock:
            cached_stats = self.range_stats_cache
            cached_refreshed_at_ms = self.range_stats_refreshed_at_ms
            if (
                cached_refreshed_at_ms is None
                or not cached_stats
                or (int(timestamp) - int(cached_refreshed_at_ms)) >= RANGE_STATS_REFRESH_INTERVAL_MS
            ):
                needs_refresh = True

        if needs_refresh:
            refreshed_stats = self.db.get_recent_range_stats(
                [good["id"] for good in state["goods"]],
                timestamp,
                RANGE_WINDOW_MS,
            )
            with self.cache_lock:
                self.range_stats_cache = refreshed_stats
                self.range_stats_refreshed_at_ms = int(timestamp)
                self.last_history_timestamp = int(timestamp)
                cached_stats = self.range_stats_cache
        else:
            self.last_history_timestamp = int(timestamp)

        for good in state["goods"]:
            stats = cached_stats.get(good["id"], {})
            range_min = stats.get("min")
            range_max = stats.get("max")
            range_avg = stats.get("avg")
            range_samples = int(stats.get("samples") or 0)
            range_position = None
            if (
                range_min is not None
                and range_max is not None
                and range_max > range_min
            ):
                range_position = (good["value"] - range_min) / (range_max - range_min)
            good["range_min"] = range_min
            good["range_max"] = range_max
            good["range_avg"] = range_avg
            good["range_samples"] = range_samples
            good["range_position"] = range_position
        self._record_profile("attach_recent_stats", time.perf_counter() - started, spike_ms=15.0)

    def _normalize_target(self, rect, to_screen_point):
        if not isinstance(rect, dict):
            return None
        center_x = rect.get("centerX")
        center_y = rect.get("centerY")
        if center_x is None or center_y is None:
            return None
        screen_x, screen_y = to_screen_point(center_x, center_y)
        return {
            "client_x": int(center_x),
            "client_y": int(center_y),
            "screen_x": int(screen_x),
            "screen_y": int(screen_y),
        }

    def _reconcile_positions(self, goods, brokers, cookies_scale):
        estimated_unit_cookie_costs = {
            good_id: self._estimate_buy_cost(good["value"], brokers, cookies_scale)
            for good_id, good in goods.items()
            if good.get("value") is not None and float(good.get("value") or 0.0) > 0
        }

        for good_id in list(self.positions):
            good = goods.get(good_id)
            if good is None or good["stock"] <= 0:
                self.positions.pop(good_id, None)
                self.db.delete_position(good_id)
                continue

            position = self.positions[good_id]
            live_shares = int(good["stock"])
            persisted_shares = int(position.get("shares", 0))

            if not position.get("avg_entry") or float(position.get("avg_entry", 0.0)) <= 0:
                position["avg_entry"] = float(good["value"])
            if not position.get("avg_entry_cookies") or float(position.get("avg_entry_cookies", 0.0)) <= 0:
                position["avg_entry_cookies"] = float(estimated_unit_cookie_costs.get(good_id, 0.0))
            self._initialize_or_update_position_metadata(position, float(good["value"]), time.monotonic())

            if live_shares == persisted_shares:
                if position.get("name") != good.get("name") or position.get("symbol") != good.get("symbol"):
                    self._persist_position(good_id, good, position)
                continue

            if live_shares < persisted_shares:
                position["shares"] = live_shares
                if position["shares"] <= 0:
                    self.positions.pop(good_id, None)
                    self.db.delete_position(good_id)
                else:
                    self._persist_position(good_id, good, position)
                continue

            added_shares = live_shares - persisted_shares
            estimated_unit_cost = float(estimated_unit_cookie_costs.get(good_id, 0.0))
            total_value_cost = (persisted_shares * float(position.get("avg_entry", 0.0))) + (added_shares * float(good["value"]))
            total_cookie_cost = (
                (persisted_shares * float(position.get("avg_entry_cookies", 0.0)))
                + (added_shares * estimated_unit_cost)
            )
            position["shares"] = live_shares
            position["avg_entry"] = total_value_cost / max(1, live_shares)
            position["avg_entry_cookies"] = total_cookie_cost / max(1, live_shares)
            self._persist_position(good_id, good, position)
            self.log.info(
                f"Stock position resynced good={good.get('name')} id={good_id} "
                f"persisted_shares={persisted_shares} live_shares={live_shares}"
            )

        for good_id, good in goods.items():
            live_shares = int(good.get("stock") or 0)
            if live_shares <= 0 or good_id in self.positions:
                continue
            estimated_unit_cost = float(estimated_unit_cookie_costs.get(good_id, 0.0))
            position = {
                "shares": live_shares,
                "avg_entry": float(good["value"]),
                "avg_entry_cookies": estimated_unit_cost,
                "symbol": good.get("symbol"),
                "name": good.get("name"),
            }
            self._initialize_or_update_position_metadata(position, float(good["value"]), time.monotonic())
            self.positions[good_id] = position
            self._persist_position(good_id, good, position)
            self.log.info(
                f"Stock position imported from live holdings good={good.get('name')} "
                f"id={good_id} shares={live_shares}"
            )

    def _find_sell_candidate(self, goods, require_targets=True):
        best = None
        for good_id in sorted(self.positions):
            good = goods.get(good_id)
            if good is None:
                continue
            if require_targets and good["sell_target"] is None:
                continue
            if not good.get("can_sell", False):
                continue
            if good["last"] == 1:
                continue
            position = self.positions[good_id]
            if position["shares"] <= 0:
                continue
            if self._is_opposite_trade_locked(good_id, "sell"):
                continue
            sell_reason = self._sell_reason(good, position)
            if sell_reason is None:
                continue
            score = (good["value"], position["shares"])
            if best is None or score > best[0]:
                best = (score, good, position, sell_reason)
        if best is None:
            return None
        return best[1], best[2], best[3]

    def _find_buy_candidate(self, goods, cookies, brokers, cookies_scale, now, require_targets=True):
        exposure = self._current_exposure_mark_to_market(goods, cookies_scale)
        exposure_cap = self._exposure_cap(cookies, exposure)
        remaining_capacity = exposure_cap - exposure
        if remaining_capacity <= 0:
            return None
        candidates = []
        for good_id in sorted(goods):
            good = goods[good_id]
            if require_targets and good["buy_target"] is None:
                continue
            if not good.get("can_buy", False):
                continue
            if good_id in self.pending_actions:
                continue
            retry_after = self.buy_retry_after_by_good.get(good_id, 0.0)
            if now < retry_after:
                continue
            if good["last"] == 2:
                continue
            if good["value"] <= 0:
                continue
            estimated_cost = self._estimate_buy_cost(good["value"], brokers, cookies_scale)
            if cookies < estimated_cost:
                continue
            if remaining_capacity < estimated_cost:
                continue
            if good["stock_max"] is not None and good["stock"] >= good["stock_max"]:
                continue
            if self._is_opposite_trade_locked(good_id, "buy"):
                continue
            if self._is_buy_zone(good, now):
                score = (-float(good["value"]), int(good.get("stock_max") or 0) - int(good.get("stock") or 0))
                candidates.append((score, good))

        if candidates:
            return self._pick_buy_candidate(candidates)
        return None

    def _pick_buy_candidate(self, candidates):
        candidates = sorted(candidates, key=lambda item: item[0], reverse=True)
        if not candidates:
            return None

        if self.last_buy_pick is not None:
            for _score, good in candidates:
                if good["id"] != self.last_buy_pick:
                    self.last_buy_pick = good["id"]
                    return good

        chosen = candidates[0][1]
        self.last_buy_pick = chosen["id"]
        return chosen

    def _choose_buy_size(self, good, max_shares, allow_max=False):
        if max_shares <= 0:
            return 0
        stock_max = good.get("stock_max")
        current_stock = int(good.get("stock") or 0)
        if stock_max is None:
            room = max_shares
        else:
            room = min(max_shares, max(0, stock_max - current_stock))
        if room <= 0:
            return 0
        if allow_max and good.get("can_buy_max") and good["buy_targets"].get(-1) is not None:
            return -1
        for size, enabled_key in ((100, "can_buy_100"), (10, "can_buy_10"), (1, "can_buy_1")):
            if room >= size and good.get(enabled_key) and good["buy_targets"].get(size) is not None:
                return size
        return 0

    def _downgrade_buy_size_cap(self, good_id, requested_shares):
        requested = int(requested_shares or 0)
        if requested >= 100:
            next_cap = 10
        elif requested >= 10:
            next_cap = 1
        elif requested >= 1:
            next_cap = 1
        else:
            return
        current_cap = self.buy_size_cap_by_good.get(int(good_id))
        if current_cap is None:
            self.buy_size_cap_by_good[int(good_id)] = next_cap
        else:
            self.buy_size_cap_by_good[int(good_id)] = min(int(current_cap), int(next_cap))

    def _choose_sell_size(self, good, position):
        shares = int(position.get("shares") or 0)
        if shares <= 0:
            return 0
        if good.get("can_sell_all") and good["sell_targets"].get(-1) is not None:
            return -1
        for size, enabled_key in ((100, "can_sell_100"), (10, "can_sell_10"), (1, "can_sell_1")):
            if shares >= size and good.get(enabled_key) and good["sell_targets"].get(size) is not None:
                return size
        return 0

    def _is_buy_zone(self, good, now=None):
        value = float(good.get("value") or 0.0)
        if value <= 0:
            return False
        if not self._passes_reentry_guard(good, now):
            return False
        if not self._passes_contextual_buy_filters(good):
            return False
        if value <= float(good.get("buy_threshold") or DEFAULT_BUY_PRICE_MAX):
            return True
        return self._is_hidden_state_buy_zone(good)

    def _initialize_or_update_position_metadata(self, position, reference_price, now):
        opened_at = position.get("opened_at")
        if opened_at is None:
            position["opened_at"] = float(now)
        peak_price = float(position.get("peak_price", 0.0) or 0.0)
        reference_price = float(reference_price or 0.0)
        if peak_price <= 0.0:
            position["peak_price"] = reference_price
            position["peak_at"] = float(now)
        elif reference_price > peak_price:
            position["peak_price"] = reference_price
            position["peak_at"] = float(now)
        position["last_mark_price"] = reference_price
        position["last_mark_at"] = float(now)

    def _update_position_markers(self, goods, now):
        for good_id, position in self.positions.items():
            good = goods.get(good_id)
            if good is None:
                continue
            self._initialize_or_update_position_metadata(position, float(good.get("value") or 0.0), now)

    def _sell_reason(self, good, position):
        if not self._is_profitable_exit(good, position):
            return None
        if self._should_sell_on_threshold(good, position):
            return "threshold"
        if self._should_sell_on_bearish_reversion(good, position):
            return "bearish_reversion"
        if self._should_sell_on_rollover(good, position):
            return "rollover"
        if self._should_trailing_stop(good, position):
            return "trailing_stop"
        return None

    def _should_sell_on_threshold(self, good, position):
        value = float(good.get("value") or 0.0)
        sell_threshold = float(good.get("sell_threshold") or DEFAULT_SELL_PRICE_MIN)
        if value < sell_threshold:
            return False
        mode_name = good.get("mode_name")
        if mode_name not in BUY_FAVORABLE_MODES:
            return True
        if value >= (sell_threshold * THRESHOLD_SELL_BREAKOUT_RATIO):
            return True
        if self._has_negative_momentum(good):
            return True
        if self._is_near_recent_high(good):
            return True
        entry_price = float(position.get("avg_entry") or 0.0)
        if entry_price > 0.0:
            profit_ratio = (value / entry_price) - 1.0
            if profit_ratio >= TRAILING_STOP_ARM_GAIN:
                return False
        return False

    def _is_profitable_exit(self, good, position):
        unit_sale_cookies = float(good.get("unit_sale_cookies") or 0.0)
        avg_entry_cookies = float(position.get("avg_entry_cookies") or 0.0)
        if unit_sale_cookies > 0.0 and avg_entry_cookies > 0.0:
            return unit_sale_cookies >= avg_entry_cookies
        value = float(good.get("value") or 0.0)
        entry_price = float(position.get("avg_entry") or 0.0)
        if value <= 0.0 or entry_price <= 0.0:
            return False
        return value >= entry_price

    def _is_hidden_state_buy_zone(self, good):
        mode_name = good.get("mode_name")
        if mode_name in BUY_UNFAVORABLE_MODES:
            return False
        if mode_name is not None and mode_name not in BUY_FAVORABLE_MODES and mode_name != "chaotic":
            return False
        resting_value = good.get("resting_value")
        value = float(good.get("value") or 0.0)
        if resting_value is None or value <= 0.0:
            return False
        if value > (float(resting_value) * RESTING_VALUE_BUY_CEILING_RATIO):
            return False
        discount = self._discount_to_resting_value(good)
        if discount < RESTING_VALUE_BUY_DISCOUNT_MIN:
            return False
        range_avg = good.get("range_avg")
        if range_avg is not None and self._discount_to_avg(good) < RANGE_AVG_BUY_DISCOUNT_MIN:
            return False
        if not self._is_extreme_absolute_bargain(good) and not self._is_near_recent_low(
            good, max_position=HIDDEN_STATE_RANGE_POSITION_BUY_MAX
        ):
            return False
        if mode_name == "chaotic":
            return self._is_extreme_absolute_bargain(good) and self._has_buy_reversal(good)
        return True

    def _passes_contextual_buy_filters(self, good):
        if not self._has_buy_reversal(good):
            return self._is_extreme_absolute_bargain(good)
        if good.get("mode_name") == "chaotic" and not self._is_extreme_absolute_bargain(good):
            return False
        range_position = good.get("range_position")
        if (
            range_position is not None
            and float(range_position) > RANGE_POSITION_BUY_MAX
            and not self._is_extreme_absolute_bargain(good)
        ):
            return False
        return True

    def _passes_reentry_guard(self, good, now):
        good_id = int(good.get("id", -1))
        last_sell_at = self.last_profitable_sell_time_by_good.get(good_id)
        last_sell_price = self.last_profitable_sell_price_by_good.get(good_id)
        if last_sell_at is None or last_sell_price is None or float(last_sell_price) <= 0.0:
            return True
        if now is None:
            now = time.monotonic()
        mode_name = good.get("mode_name")
        cooldown = PROFITABLE_REENTRY_COOLDOWN_SECONDS
        required_discount = PROFITABLE_REENTRY_DISCOUNT_MIN
        if mode_name == "chaotic":
            cooldown = CHAOTIC_REENTRY_COOLDOWN_SECONDS
            required_discount = CHAOTIC_REENTRY_DISCOUNT_MIN
        if (float(now) - float(last_sell_at)) >= cooldown:
            return True
        value = float(good.get("value") or 0.0)
        discount_from_last_sell = 1.0 - (value / float(last_sell_price))
        return discount_from_last_sell >= required_discount

    def _recent_history(self, good, count=3):
        history = good.get("history") or []
        values = []
        for item in history[:count]:
            if item is None:
                continue
            values.append(float(item))
        return values

    def _has_buy_reversal(self, good):
        if self._is_extreme_absolute_bargain(good):
            return True
        delta = good.get("delta")
        if delta is not None and float(delta) >= 0.0:
            return True
        history = self._recent_history(good, count=3)
        if len(history) >= 3 and history[0] >= history[1] <= history[2]:
            return True
        if len(history) >= 2 and history[0] >= history[1]:
            return True
        return False

    def _has_negative_momentum(self, good):
        delta = good.get("delta")
        if delta is not None and float(delta) < 0.0:
            return True
        history = self._recent_history(good, count=2)
        return len(history) >= 2 and history[0] < history[1]

    def _is_extreme_absolute_bargain(self, good):
        value = float(good.get("value") or 0.0)
        resting_value = good.get("resting_value")
        if value <= 0.0:
            return False
        if resting_value is None or float(resting_value) <= 0.0:
            return value <= (SOFT_FLOOR_PRICE * 2.0)
        return value <= max(SOFT_FLOOR_PRICE * 2.0, float(resting_value) * EXTREME_BARGAIN_RESTING_RATIO)

    def _is_near_recent_low(self, good, max_position=RANGE_POSITION_BUY_MAX):
        range_position = good.get("range_position")
        return range_position is not None and float(range_position) <= float(max_position)

    def _is_near_recent_high(self, good, min_position=FAVORABLE_RANGE_POSITION_SELL_MIN):
        range_position = good.get("range_position")
        return range_position is not None and float(range_position) >= float(min_position)

    def _should_sell_on_bearish_reversion(self, good, position):
        mode_name = good.get("mode_name")
        if mode_name not in SELL_BEARISH_MODES:
            return False
        value = float(good.get("value") or 0.0)
        entry_price = float(position.get("avg_entry") or 0.0)
        if value <= 0.0 or entry_price <= 0.0:
            return False
        profit_ratio = (value / entry_price) - 1.0
        if profit_ratio < ENTRY_PROFIT_SELL_FLOOR:
            return False
        premium = self._premium_to_resting_value(good)
        if premium < RESTING_VALUE_SELL_PREMIUM_MIN:
            return False
        delta = good.get("delta")
        if delta is not None and float(delta) > 0.15 and mode_name != "chaotic":
            return False
        return True

    def _should_sell_on_rollover(self, good, position):
        value = float(good.get("value") or 0.0)
        entry_price = float(position.get("avg_entry") or 0.0)
        peak_price = float(position.get("peak_price") or 0.0)
        if value <= 0.0 or entry_price <= 0.0 or peak_price <= entry_price:
            return False
        profit_ratio = (value / entry_price) - 1.0
        if profit_ratio < ROLLOVER_PROFIT_SELL_FLOOR:
            return False
        if not self._has_negative_momentum(good):
            return False
        giveback_ratio = (peak_price - value) / max(peak_price, 1e-9)
        if giveback_ratio < ROLLOVER_GIVEBACK_FRACTION and good.get("mode_name") not in BUY_UNFAVORABLE_MODES:
            return False
        return True

    def _discount_to_resting_value(self, good):
        resting_value = good.get("resting_value")
        value = float(good.get("value") or 0.0)
        if resting_value is None or resting_value <= 0.0 or value <= 0.0:
            return 0.0
        return max(0.0, (float(resting_value) - value) / float(resting_value))

    def _premium_to_resting_value(self, good):
        resting_value = good.get("resting_value")
        value = float(good.get("value") or 0.0)
        if resting_value is None or resting_value <= 0.0 or value <= 0.0:
            return 0.0
        return max(0.0, (value - float(resting_value)) / float(resting_value))

    def _should_trailing_stop(self, good, position):
        entry_price = float(position.get("avg_entry") or 0.0)
        current_price = float(good.get("value") or 0.0)
        peak_price = float(position.get("peak_price") or 0.0)
        opened_at = position.get("opened_at")
        if entry_price <= 0.0 or current_price <= 0.0 or peak_price <= entry_price:
            return False
        if opened_at is None:
            return False
        held_seconds = max(0.0, time.monotonic() - float(opened_at))
        if held_seconds < TRAILING_STOP_MIN_HOLD_SECONDS:
            return False
        peak_gain = (peak_price / entry_price) - 1.0
        if peak_gain < TRAILING_STOP_ARM_GAIN:
            return False
        peak_profit = peak_price - entry_price
        protected_floor = peak_price - (peak_profit * TRAILING_STOP_GIVEBACK_FRACTION)
        return current_price <= protected_floor

    def _discount_to_avg(self, good):
        range_avg = good.get("range_avg")
        value = float(good.get("value") or 0.0)
        if range_avg is None or range_avg <= 0 or value <= 0:
            return 0.0
        return max(0.0, (range_avg - value) / range_avg)

    def _is_opposite_trade_locked(self, good_id, desired_kind):
        last_kind = self.last_trade_kind_by_good.get(good_id)
        last_time = self.last_trade_time_by_good.get(good_id)
        if last_kind is None or last_kind == desired_kind or last_time is None:
            return False
        return (time.monotonic() - last_time) < OPPOSITE_TRADE_SETTLE_SECONDS

    def _buy_overhead_multiplier(self, brokers):
        overhead = BASE_BROKER_OVERHEAD * math.pow(BROKER_REDUCTION, max(0, brokers))
        return 1.0 + overhead

    def _estimate_buy_cost(self, value, brokers, cookies_scale):
        return value * self._buy_overhead_multiplier(brokers) * max(0.0, float(cookies_scale))

    def _planned_buy_cost(self, buy_candidate, goods, cookies, brokers, cookies_scale, buy_reserve_cookies):
        if buy_candidate is None:
            return 0.0
        unit_cost_cookies = self._estimate_buy_cost(
            buy_candidate["value"],
            brokers,
            cookies_scale,
        )
        available_cookies = max(0.0, float(cookies) - max(0.0, float(buy_reserve_cookies)))
        affordable = math.floor(available_cookies / unit_cost_cookies)
        if affordable <= 0:
            return 0.0
        exposure = self._current_exposure_mark_to_market(goods, cookies_scale)
        remaining_capacity = self._exposure_cap(cookies, exposure) - exposure
        max_affordable_by_cap = math.floor(remaining_capacity / unit_cost_cookies)
        capped_affordable = min(affordable, max_affordable_by_cap)
        size_cap = self.buy_size_cap_by_good.get(buy_candidate["id"])
        if size_cap is not None:
            capped_affordable = min(capped_affordable, int(size_cap))
        buy_size = self._choose_buy_size(
            buy_candidate,
            capped_affordable,
            allow_max=(capped_affordable == affordable),
        )
        if buy_size <= 0:
            return 0.0
        if buy_size < 0:
            buy_size = capped_affordable
        return float(unit_cost_cookies) * float(buy_size)

    def _get_office_upgrade_action(self, state, *, allow_buy_actions, allow_sell_actions, planned_buy_cost):
        if not (allow_buy_actions or allow_sell_actions):
            return None
        if not state.get("can_upgrade_office"):
            return None
        target = state.get("office_upgrade_target")
        if target is None:
            return None
        return TradeAction(
            kind="upgrade_office",
            screen_x=target["screen_x"],
            screen_y=target["screen_y"],
            cookies=state["cookies"],
            reason="upgrade_office_before_trade",
            context={
                "office_level": state.get("office_level"),
                "next_office_level": state.get("next_office_level"),
                "office_name": state.get("office_name"),
                "next_office_name": state.get("next_office_name"),
                "office_upgrade_cost": state.get("office_upgrade_cost"),
                "office_upgrade_cursor_level": state.get("office_upgrade_cursor_level"),
                "planned_buy_cost": planned_buy_cost,
            },
        )

    def _get_broker_action(self, state, *, allow_buy_actions, allow_sell_actions, planned_buy_cost):
        if not (allow_buy_actions or allow_sell_actions):
            return None
        if not state.get("can_hire_broker"):
            return None
        target = state.get("broker_target")
        broker_cost = self._resolve_broker_cost(state)
        if target is None or broker_cost <= 0.0:
            return None
        trade_reserve = planned_buy_cost if allow_buy_actions else 0.0
        if float(state["cookies"]) < (trade_reserve + broker_cost):
            return None
        return TradeAction(
            kind="hire_broker",
            screen_x=target["screen_x"],
            screen_y=target["screen_y"],
            cookies=state["cookies"],
            reason="hire_broker_before_trade",
            context={
                "brokers": state.get("brokers"),
                "brokers_max": state.get("brokers_max"),
                "broker_cost": broker_cost,
                "planned_buy_cost": planned_buy_cost,
            },
        )

    def _resolve_broker_cost(self, state):
        broker_cost = state.get("broker_cost")
        if broker_cost is not None:
            try:
                broker_cost = float(broker_cost)
            except Exception:
                broker_cost = None
            if broker_cost is not None and math.isfinite(broker_cost) and broker_cost > 0.0:
                return broker_cost
        cookies_scale = float(state.get("cookies_ps_raw_highest") or 0.0)
        if cookies_scale <= 0.0:
            return 0.0
        return cookies_scale * BROKER_PRICE_SECONDS

    def _refresh_thresholds_if_needed(self, state):
        started = time.perf_counter()
        timestamp = state.get("timestamp")
        if timestamp is None:
            return
        with self.cache_lock:
            has_fresh_thresholds = (
                self.thresholds_refreshed_at_ms is not None
                and self.thresholds_by_good
                and (int(timestamp) - int(self.thresholds_refreshed_at_ms)) < THRESHOLD_REFRESH_INTERVAL_MS
            )

        if not has_fresh_thresholds:
            self._start_threshold_refresh(state["goods"], timestamp, state.get("brokers") or 0)

        self._record_profile("refresh_thresholds", time.perf_counter() - started, spike_ms=50.0)

    def _start_threshold_refresh(self, goods, timestamp, brokers):
        with self.threshold_refresh_lock:
            if self.threshold_refresh_in_flight:
                return
            self.threshold_refresh_in_flight = True

        goods_snapshot = [
            {
                "id": int(good["id"]),
                "name": good.get("name"),
            }
            for good in goods
        ]
        refresh_timestamp = int(timestamp)

        worker = threading.Thread(
            target=self._run_threshold_refresh,
            args=(goods_snapshot, refresh_timestamp, int(brokers or 0)),
            name="stock-threshold-refresh",
            daemon=True,
        )
        worker.start()

    def _run_threshold_refresh(self, goods, timestamp, brokers):
        started = time.perf_counter()
        try:
            series_by_good = self.db.get_price_series([good["id"] for good in goods])
            thresholds = {}
            learned = 0
            for good in goods:
                optimized = self._optimize_thresholds(series_by_good.get(good["id"], ()), brokers)
                thresholds[good["id"]] = optimized
                if optimized.get("learned"):
                    learned += 1
            with self.cache_lock:
                self.thresholds_by_good = thresholds
                self.thresholds_refreshed_at_ms = int(timestamp)
            self.log.info(
                f"Stock thresholds refreshed learned={learned}/{len(goods)} "
                f"timestamp={timestamp}"
            )
        except Exception:
            self.log.exception("Stock threshold refresh failed")
        finally:
            with self.threshold_refresh_lock:
                self.threshold_refresh_in_flight = False
            self._record_profile("refresh_thresholds", time.perf_counter() - started, spike_ms=50.0)

    def _attach_thresholds(self, state):
        with self.cache_lock:
            thresholds_by_good = dict(self.thresholds_by_good)
        for good in state["goods"]:
            thresholds = thresholds_by_good.get(good["id"])
            if thresholds is None:
                thresholds = {
                    "buy": DEFAULT_BUY_PRICE_MAX,
                    "sell": DEFAULT_SELL_PRICE_MIN,
                    "samples": 0,
                    "trades": 0,
                    "learned": False,
                }
            good["buy_threshold"] = float(thresholds["buy"])
            good["sell_threshold"] = float(thresholds["sell"])
            good["threshold_samples"] = int(thresholds.get("samples") or 0)
            good["threshold_trades"] = int(thresholds.get("trades") or 0)
            good["threshold_learned"] = bool(thresholds.get("learned"))

    def _optimize_thresholds(self, series, brokers=0):
        started = time.perf_counter()
        prices = [float(value) for value in series if value is not None]
        if len(prices) < MIN_THRESHOLD_SAMPLES:
            result = {
                "buy": DEFAULT_BUY_PRICE_MAX,
                "sell": DEFAULT_SELL_PRICE_MIN,
                "samples": len(prices),
                "trades": 0,
                "learned": False,
            }
            self._record_profile("optimize_thresholds", time.perf_counter() - started, spike_ms=15.0)
            return result

        sorted_prices = sorted(prices)
        buy_candidates = self._build_threshold_candidates(sorted_prices, BUY_PERCENTILE_CANDIDATES)
        sell_candidates = self._build_threshold_candidates(sorted_prices, SELL_PERCENTILE_CANDIDATES)
        if sorted_prices:
            buy_candidates = sorted({max(SOFT_FLOOR_PRICE, value) for value in buy_candidates})
        best = None
        for buy_threshold in buy_candidates:
            for sell_threshold in sell_candidates:
                if sell_threshold <= buy_threshold:
                    continue
                profit, trades = self._simulate_threshold_strategy(
                    prices,
                    buy_threshold,
                    sell_threshold,
                    brokers=brokers,
                )
                if trades <= 0:
                    continue
                score = (profit, trades, -(sell_threshold - buy_threshold))
                if best is None or score > best["score"]:
                    best = {
                        "buy": buy_threshold,
                        "sell": sell_threshold,
                        "profit": profit,
                        "trades": trades,
                        "score": score,
                    }

        if best is None:
            result = {
                "buy": DEFAULT_BUY_PRICE_MAX,
                "sell": DEFAULT_SELL_PRICE_MIN,
                "samples": len(prices),
                "trades": 0,
                "learned": False,
            }
            self._record_profile("optimize_thresholds", time.perf_counter() - started, spike_ms=15.0)
            return result

        result = {
            "buy": float(best["buy"]),
            "sell": float(best["sell"]),
            "samples": len(prices),
            "trades": int(best["trades"]),
            "learned": True,
        }
        self._record_profile("optimize_thresholds", time.perf_counter() - started, spike_ms=15.0)
        return result

    def _build_threshold_candidates(self, sorted_prices, percentiles):
        candidates = set()
        last_index = len(sorted_prices) - 1
        for percentile in percentiles:
            index = min(last_index, max(0, int(round(last_index * float(percentile)))))
            candidates.add(float(sorted_prices[index]))
        return sorted(candidates)

    def _simulate_threshold_strategy(self, prices, buy_threshold, sell_threshold, brokers=0):
        holding = False
        buy_price = 0.0
        profit = 0.0
        trades = 0
        buy_cost_multiplier = self._buy_overhead_multiplier(brokers)
        for price in prices:
            if not holding:
                if price <= buy_threshold:
                    holding = True
                    buy_price = price
            elif price >= sell_threshold:
                profit += price - (buy_price * buy_cost_multiplier)
                trades += 1
                holding = False
                buy_price = 0.0
        return profit, trades

    def _current_exposure_cost_basis(self):
        return sum(
            float(position.get("shares", 0)) * float(position.get("avg_entry_cookies", 0.0))
            for position in self.positions.values()
        )

    def _current_exposure_mark_to_market(self, goods, cookies_scale):
        scale = max(0.0, float(cookies_scale))
        exposure = 0.0
        for good_id, position in self.positions.items():
            good = goods.get(good_id)
            if good is None:
                exposure += float(position.get("shares", 0)) * float(position.get("avg_entry_cookies", 0.0))
                continue
            exposure += float(position.get("shares", 0)) * float(good.get("value", 0.0)) * scale
        return exposure

    def _compact_good_context(self, good):
        if not isinstance(good, dict):
            return None
        return {
            "id": int(good.get("id", -1)),
            "symbol": good.get("symbol"),
            "name": good.get("name"),
            "value": None if good.get("value") is None else float(good.get("value")),
            "resting_value": None if good.get("resting_value") is None else float(good.get("resting_value")),
            "mode_name": good.get("mode_name"),
            "range_min": None if good.get("range_min") is None else float(good.get("range_min")),
            "range_max": None if good.get("range_max") is None else float(good.get("range_max")),
            "range_avg": None if good.get("range_avg") is None else float(good.get("range_avg")),
            "range_position": None if good.get("range_position") is None else float(good.get("range_position")),
            "buy_threshold": None if good.get("buy_threshold") is None else float(good.get("buy_threshold")),
            "sell_threshold": None if good.get("sell_threshold") is None else float(good.get("sell_threshold")),
            "delta": None if good.get("delta") is None else float(good.get("delta")),
            "stock": None if good.get("stock") is None else int(good.get("stock")),
            "stock_max": None if good.get("stock_max") is None else int(good.get("stock_max")),
            "history": [float(item) for item in (good.get("history") or [])[:8]],
        }

    def _record_trade_decision_snapshot(self, *, state, result, buy_candidate, sell_candidate):
        observed_at_ms = int(state.get("timestamp") or int(time.time() * 1000))
        buy_good = self._compact_good_context(buy_candidate)
        sell_good = self._compact_good_context(None if sell_candidate is None else sell_candidate[0])
        signature = (
            observed_at_ms // 15000,
            result.get("reason"),
            None if buy_good is None else buy_good.get("id"),
            None if sell_good is None else sell_good.get("id"),
            result.get("sell_reason"),
        )
        if signature == self.last_decision_signature:
            return
        self.last_decision_signature = signature
        self.last_decision_logged_at_ms = observed_at_ms
        self.db.record_trade_decision(
            observed_at_ms=observed_at_ms,
            reason=result.get("reason"),
            action_kind=(
                "sell"
                if result.get("reason") == "sell_ready"
                else "buy"
                if result.get("reason") == "buy_ready"
                else "open_bank"
                if str(result.get("reason", "")).startswith("bank_closed_")
                else None
            ),
            buy_candidate_id=None if buy_good is None else buy_good.get("id"),
            buy_candidate_name=None if buy_good is None else buy_good.get("name"),
            sell_candidate_id=None if sell_good is None else sell_good.get("id"),
            sell_candidate_name=None if sell_good is None else sell_good.get("name"),
            sell_reason=result.get("sell_reason"),
            cookies=result.get("cookies"),
            portfolio_exposure=result.get("portfolio_exposure"),
            portfolio_cap=result.get("portfolio_cap"),
            portfolio_remaining=result.get("portfolio_remaining"),
            buy_reserve_cookies=result.get("buy_reserve_cookies"),
            buy_actions_enabled=result.get("buy_actions_enabled"),
            sell_actions_enabled=result.get("sell_actions_enabled"),
            buy_good=buy_good,
            sell_good=sell_good,
            extra={
                "brokers": result.get("brokers"),
                "market_profit": result.get("market_profit"),
                "on_minigame": result.get("on_minigame"),
                "goods_in_buy_zone": result.get("goods_in_buy_zone"),
                "goods_with_thresholds": result.get("goods_with_thresholds"),
                "portfolio_cap_ratio": result.get("portfolio_cap_ratio"),
            },
        )

    def _persist_position(self, good_id, good, position):
        self.db.upsert_position(
            good_id=good_id,
            symbol=good.get("symbol"),
            name=good.get("name"),
            shares=position["shares"],
            avg_entry=position.get("avg_entry", 0.0),
            avg_entry_cookies=position.get("avg_entry_cookies", 0.0),
            updated_at_ms=int(time.time() * 1000),
        )

    def _exposure_cap(self, cookies, exposure):
        total_funds = max(0.0, float(cookies)) + max(0.0, float(exposure))
        return total_funds * MAX_PORTFOLIO_EXPOSURE_RATIO

    def get_runtime_stats(self):
        exposure = self._current_exposure_cost_basis()
        latest_performance = self.performance_history[-1] if self.performance_history else None
        return {
            "buy_clicks": self.buy_clicks,
            "sell_clicks": self.sell_clicks,
            "buy_confirms": self.buy_confirms,
            "sell_confirms": self.sell_confirms,
            "realized_pnl": self.realized_pnl,
            "held_goods": len(self.positions),
            "held_shares": sum(position["shares"] for position in self.positions.values()),
            "last_trade": self.last_trade_summary,
            "portfolio_exposure": exposure,
            "portfolio_cap_ratio": MAX_PORTFOLIO_EXPOSURE_RATIO,
            "net_pnl": None if latest_performance is None else latest_performance["net_pnl"],
            "unrealized_pnl": None if latest_performance is None else latest_performance["unrealized_pnl"],
            "session_roi": None if latest_performance is None else latest_performance["session_roi"],
            "session_capital_base": max(
                float(self.total_confirmed_buy_cost),
                float(self.peak_cost_basis),
                float(exposure),
            ),
            "performance_history": list(self.performance_history),
            "profile": {
                key: {
                    "avg_ms": round(float(value["avg_ms"]), 3),
                    "max_ms": round(float(value["max_ms"]), 3),
                    "count": int(value["count"]),
                }
                for key, value in self.profile.items()
            },
            "db_profile": self.db.get_runtime_stats(),
        }

    def _compute_session_roi(self, net_pnl, cost_basis):
        capital_base = max(
            float(self.total_confirmed_buy_cost),
            float(self.peak_cost_basis),
            float(cost_basis),
        )
        if capital_base <= 0.0:
            return None
        return float(net_pnl) / capital_base

    def _record_performance_snapshot(self, state, goods, now):
        if self.last_performance_sample_at is not None and (now - self.last_performance_sample_at) < POSITION_SAMPLE_INTERVAL_SECONDS:
            return
        cost_basis = self._current_exposure_cost_basis()
        self.peak_cost_basis = max(float(self.peak_cost_basis), float(cost_basis))
        mark_to_market = self._current_exposure_mark_to_market(goods, state.get("cookies_ps_raw_highest") or 0.0)
        unrealized_pnl = mark_to_market - cost_basis
        net_pnl = self.realized_pnl + unrealized_pnl
        roi = None if cost_basis <= 0.0 else net_pnl / cost_basis
        session_roi = self._compute_session_roi(net_pnl, cost_basis)
        self.performance_history.append(
            {
                "timestamp": int(state.get("timestamp") or int(time.time() * 1000)),
                "cost_basis": cost_basis,
                "mark_to_market": mark_to_market,
                "unrealized_pnl": unrealized_pnl,
                "net_pnl": net_pnl,
                "roi": roi,
                "session_roi": session_roi,
            }
        )
        self.last_performance_sample_at = now

    def _record_profile(self, key, elapsed_seconds, spike_ms):
        elapsed_ms = float(elapsed_seconds) * 1000.0
        stat = self.profile.get(key)
        if stat is None:
            stat = {"avg_ms": elapsed_ms, "max_ms": elapsed_ms, "count": 1}
        else:
            count = int(stat["count"]) + 1
            stat["avg_ms"] = ((float(stat["avg_ms"]) * int(stat["count"])) + elapsed_ms) / count
            stat["max_ms"] = max(float(stat["max_ms"]), elapsed_ms)
            stat["count"] = count
        self.profile[key] = stat
        last_logged = float(self.profile_last_log_at.get(key, 0.0))
        now = time.monotonic()
        if elapsed_ms >= float(spike_ms) and (now - last_logged) >= 5.0:
            self.profile_last_log_at[key] = now
            self.log.warning(f"Stock profiler spike op={key} elapsed_ms={elapsed_ms:.1f}")
