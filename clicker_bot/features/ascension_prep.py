from dataclasses import dataclass
import threading
import time


EVERYTHING_THRESHOLDS = (100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700)
CURSOR_THRESHOLDS = EVERYTHING_THRESHOLDS + (800, 900, 1000)
NON_CURSOR_MAX_THRESHOLD = EVERYTHING_THRESHOLDS[-1]
ACTION_COOLDOWN_SECONDS = 0.35


@dataclass
class AscensionPrepAction:
    kind: str
    building_id: int
    building_name: str
    quantity: int
    threshold: int
    phase: str
    unit_value: float | None = None
    total_value: float | None = None
    cookies: float | None = None
    reason: str | None = None


class AscensionPrepController:
    def __init__(self, log):
        self.log = log
        self.lock = threading.Lock()
        self.last_action_time = 0.0
        self.action_count = 0
        self.last_action_summary = None

    def extract_state(self, snapshot):
        if not isinstance(snapshot, dict):
            return None
        raw_buildings = snapshot.get("buildings")
        if not isinstance(raw_buildings, list):
            return None
        cookies = float(snapshot.get("cookies") or 0.0)
        buildings = []
        for raw in raw_buildings:
            if not isinstance(raw, dict):
                continue
            building_id = raw.get("id")
            if building_id is None:
                continue
            buildings.append(
                {
                    "id": int(building_id),
                    "name": str(raw.get("name") or f"building-{building_id}"),
                    "amount": int(raw.get("amount") or 0),
                    "price": None if raw.get("price") is None else float(raw.get("price")),
                    "sum_price_10": None if raw.get("sumPrice10") is None else float(raw.get("sumPrice10")),
                    "sum_price_100": None if raw.get("sumPrice100") is None else float(raw.get("sumPrice100")),
                    "sell_value_1": None if raw.get("sellValue1") is None else float(raw.get("sellValue1")),
                    "sell_value_10": None if raw.get("sellValue10") is None else float(raw.get("sellValue10")),
                    "sell_value_100": None if raw.get("sellValue100") is None else float(raw.get("sellValue100")),
                    "can_buy": bool(raw.get("canBuy")),
                    "can_sell": bool(raw.get("canSell")),
                    "locked": bool(raw.get("locked")),
                }
            )
        if not buildings:
            return None
        buildings.sort(key=lambda item: item["id"])
        return {
            "cookies": cookies,
            "buildings": buildings,
        }

    def get_action(self, snapshot, now=None):
        state = self.extract_state(snapshot)
        if state is None:
            return None
        now = time.monotonic() if now is None else float(now)
        with self.lock:
            if (now - self.last_action_time) < ACTION_COOLDOWN_SECONDS:
                return None
        plan = plan_ascension_prep(state)
        if plan is None:
            return None
        return AscensionPrepAction(
            kind=plan["kind"],
            building_id=plan["building"]["id"],
            building_name=plan["building"]["name"],
            quantity=plan["quantity"],
            threshold=plan["threshold"],
            phase=plan["phase"],
            unit_value=plan.get("unit_value"),
            total_value=plan.get("total_value"),
            cookies=state["cookies"],
            reason=plan.get("reason"),
        )

    def get_diagnostics(self, snapshot):
        state = self.extract_state(snapshot)
        if state is None:
            return {
                "available": False,
                "reason": "no_building_data",
            }
        plan = plan_ascension_prep(state)
        progress = compute_ascension_prep_progress(state)
        if plan is None:
            return {
                "available": True,
                "reason": "done",
                "cookies": state["cookies"],
                **progress,
            }
        return {
            "available": True,
            "reason": plan["reason"],
            "cookies": state["cookies"],
            "phase": plan["phase"],
            "threshold": plan["threshold"],
            "kind": plan["kind"],
            "building": plan["building"]["name"],
            "quantity": plan["quantity"],
            "unit_value": plan.get("unit_value"),
            "total_value": plan.get("total_value"),
            **progress,
        }

    def record_action(self, action):
        with self.lock:
            self.last_action_time = time.monotonic()
            self.action_count += 1
            self.last_action_summary = (
                f"{action.kind} {action.quantity} {action.building_name} toward {action.threshold}"
            )
        self.log.info(
            f"Ascension prep action kind={action.kind} name={action.building_name} "
            f"id={action.building_id} quantity={action.quantity} threshold={action.threshold} "
            f"phase={action.phase} unit_value={0.0 if action.unit_value is None else action.unit_value:.1f} "
            f"total_value={0.0 if action.total_value is None else action.total_value:.1f} "
            f"cookies={0.0 if action.cookies is None else action.cookies:.1f} "
            f"reason={action.reason}"
        )

    def get_runtime_stats(self):
        with self.lock:
            return {
                "action_count": self.action_count,
                "last_action": self.last_action_summary,
            }


def compute_ascension_prep_progress(state):
    buildings = list(state.get("buildings") or [])
    if not buildings:
        return {
            "everything_threshold": None,
            "everything_progress": None,
            "cursor_threshold": None,
            "cursor_progress": None,
            "surplus_buildings": 0,
            "deficit_buildings": 0,
        }
    min_amount = min(int(item["amount"]) for item in buildings)
    everything_threshold = next((value for value in EVERYTHING_THRESHOLDS if min_amount < value), EVERYTHING_THRESHOLDS[-1])
    everything_progress = sum(1 for item in buildings if int(item["amount"]) >= everything_threshold)
    cursor = next((item for item in buildings if item["name"] == "Cursor"), None)
    cursor_amount = 0 if cursor is None else int(cursor["amount"])
    cursor_threshold = next((value for value in CURSOR_THRESHOLDS if cursor_amount < value), CURSOR_THRESHOLDS[-1])
    return {
        "everything_threshold": everything_threshold,
        "everything_progress": everything_progress,
        "cursor_threshold": cursor_threshold,
        "cursor_progress": cursor_amount,
        "surplus_buildings": sum(1 for item in buildings if _surplus_amount(item, everything_threshold, phase="everything") > 0),
        "deficit_buildings": sum(1 for item in buildings if _deficit_amount(item, everything_threshold, phase="everything") > 0),
    }


def plan_ascension_prep(state):
    buildings = list(state.get("buildings") or [])
    if not buildings:
        return None
    cookies = float(state.get("cookies") or 0.0)
    min_amount = min(int(item["amount"]) for item in buildings)
    next_everything = next((value for value in EVERYTHING_THRESHOLDS if min_amount < value), None)
    if next_everything is not None:
        return _plan_for_threshold(buildings, cookies, threshold=next_everything, phase="everything")
    cursor = next((item for item in buildings if item["name"] == "Cursor"), None)
    if cursor is None:
        return None
    cursor_amount = int(cursor["amount"])
    next_cursor = next((value for value in CURSOR_THRESHOLDS if cursor_amount < value), None)
    if next_cursor is not None:
        return _plan_for_threshold(buildings, cookies, threshold=next_cursor, phase="cursor")
    return None


def _plan_for_threshold(buildings, cookies, *, threshold, phase):
    deficits = []
    for item in buildings:
        deficit = _deficit_amount(item, threshold, phase=phase)
        if deficit <= 0:
            continue
        deficits.append((item, deficit))
    if not deficits:
        return None

    deficits.sort(key=lambda pair: (float("inf") if pair[0]["price"] is None else float(pair[0]["price"]), pair[0]["id"]))
    for item, deficit in deficits:
        buy_quantity, total_price = _best_buy_quantity(item, deficit, cookies)
        if buy_quantity > 0 and total_price is not None:
            return {
                "kind": "buy",
                "phase": phase,
                "threshold": threshold,
                "building": item,
                "quantity": buy_quantity,
                "unit_value": item.get("price"),
                "total_value": total_price,
                "reason": "buy_deficit",
            }

    cheapest_item = deficits[0][0]
    funding_gap = None
    if cheapest_item.get("price") is not None:
        funding_gap = max(0.0, float(cheapest_item["price"]) - float(cookies))

    surpluses = []
    for item in buildings:
        surplus = _surplus_amount(item, threshold, phase=phase)
        if surplus <= 0:
            continue
        surpluses.append((item, surplus))
    surpluses.sort(
        key=lambda pair: (
            -(float(pair[0]["sell_value_1"]) if pair[0].get("sell_value_1") is not None else -1.0),
            pair[0]["id"],
        )
    )
    for item, surplus in surpluses:
        sell_quantity, total_value = _best_sell_quantity(item, surplus, funding_gap)
        if sell_quantity > 0 and total_value is not None:
            return {
                "kind": "sell",
                "phase": phase,
                "threshold": threshold,
                "building": item,
                "quantity": sell_quantity,
                "unit_value": item.get("sell_value_1"),
                "total_value": total_value,
                "reason": "sell_surplus",
            }

    return {
        "kind": "wait",
        "phase": phase,
        "threshold": threshold,
        "building": cheapest_item,
        "quantity": 0,
        "unit_value": cheapest_item.get("price"),
        "total_value": cheapest_item.get("price"),
        "reason": "waiting_for_cash",
    }


def _deficit_amount(item, threshold, *, phase):
    amount = int(item.get("amount") or 0)
    if phase == "cursor" and item.get("name") != "Cursor":
        return 0
    return max(0, int(threshold) - amount)


def _surplus_amount(item, threshold, *, phase):
    amount = int(item.get("amount") or 0)
    name = item.get("name")
    if phase == "everything":
        floor = int(threshold)
    else:
        floor = int(threshold) if name == "Cursor" else NON_CURSOR_MAX_THRESHOLD
    return max(0, amount - floor)


def _best_buy_quantity(item, deficit, cookies):
    price1 = item.get("price")
    if price1 is None or not item.get("can_buy"):
        return 0, None
    price1 = float(price1)
    if deficit >= 100 and item.get("sum_price_100") is not None and float(item["sum_price_100"]) <= float(cookies):
        return 100, float(item["sum_price_100"])
    if deficit >= 10 and item.get("sum_price_10") is not None and float(item["sum_price_10"]) <= float(cookies):
        return 10, float(item["sum_price_10"])
    if price1 <= float(cookies):
        return 1, price1
    return 0, None


def _best_sell_quantity(item, surplus, funding_gap):
    if not item.get("can_sell"):
        return 0, None
    sell1 = item.get("sell_value_1")
    if sell1 is None:
        return 0, None
    sell1 = float(sell1)
    target_gap = 0.0 if funding_gap is None else max(0.0, float(funding_gap))
    if (
        surplus >= 100
        and item.get("sell_value_100") is not None
        and (
            target_gap <= 0.0
            or float(item["sell_value_100"]) <= (target_gap * 1.35)
            or surplus == 100
        )
    ):
        return 100, float(item["sell_value_100"])
    if (
        surplus >= 10
        and item.get("sell_value_10") is not None
        and (
            target_gap <= 0.0
            or float(item["sell_value_10"]) <= (target_gap * 1.35)
            or surplus < 100
        )
    ):
        return 10, float(item["sell_value_10"])
    return 1, sell1
