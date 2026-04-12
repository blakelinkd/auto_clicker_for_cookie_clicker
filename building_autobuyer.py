from dataclasses import dataclass
import math
import threading
import time


DEFAULT_RESERVE_COOKIES = 0.0
DEFAULT_RESERVE_CPS_SECONDS = 0.0
DEFAULT_PAYBACK_HORIZON_SECONDS = 60.0 * 60.0
BUILDING_ACTION_COOLDOWN = 0.35
MAX_BUILDING_SPEND_RATIO = 1.00
TEMPLE_TOTAL_BUILDINGS_MODULUS = 10
EARLY_RESERVE_TOTAL_BUILDINGS = 25
FULL_RESERVE_TOTAL_BUILDINGS = 400
MIN_RESERVE_SCALE = 0.05
BETTER_TARGET_PAYBACK_RATIO = 0.5
DRAGON_PRIORITY_COOKIES_RATIO = 0.25
DRAGON_PRIORITY_REMAINING_THRESHOLD = 3
DRAGON_PRIORITY_PAYBACK_RATIO = 1.5
EARLY_GAME_BULK_TOTAL_BUILDINGS = 80
EARLY_GAME_BULK_MAX_SINGLE_PRICE_RATIO = 0.10
MINIGAME_BUILDING_RETAIN_FLOORS = {
    "Farm": 300,
    "Bank": 1,
    "Temple": 1,
    "Wizard tower": 1,
}
# Cookie Clicker Steam build (resources/app/src/main.js):
# - Cursor-specific ownership achievements end at 1000.
# - All other current building-specific tiered achievements end at 700.
DEFAULT_BUILDING_CAPS = {}


@dataclass
class BuildingAction:
    kind: str
    screen_x: int
    screen_y: int
    building_id: int | None = None
    building_name: str | None = None
    quantity: int | None = None
    price: float | None = None
    delta_cps: float | None = None
    payback_seconds: float | None = None
    cookies: float | None = None
    reserve: float | None = None


class BuildingAutobuyer:
    def __init__(
        self,
        log,
        reserve_cookies=DEFAULT_RESERVE_COOKIES,
        reserve_cps_seconds=DEFAULT_RESERVE_CPS_SECONDS,
        payback_horizon_seconds=DEFAULT_PAYBACK_HORIZON_SECONDS,
        max_spend_ratio=MAX_BUILDING_SPEND_RATIO,
        building_caps=None,
    ):
        self.log = log
        self.reserve_cookies = float(reserve_cookies)
        self.reserve_cps_seconds = float(reserve_cps_seconds)
        self.payback_horizon_seconds = float(payback_horizon_seconds)
        self.max_spend_ratio = float(max_spend_ratio)
        self.default_building_caps = dict(DEFAULT_BUILDING_CAPS)
        self.building_caps = dict(DEFAULT_BUILDING_CAPS if building_caps is None else building_caps)
        self.ignored_building_caps = set()
        self.settings_lock = threading.Lock()
        self.last_action_time = 0.0
        self.last_candidate_signature = None
        self.buy_clicks = 0
        self.last_building_summary = None
        self.observed_peak_amounts = {}

    def extract_state(self, snapshot, to_screen_point):
        if not snapshot or not isinstance(snapshot, dict):
            return None

        raw_buildings = snapshot.get("buildings")
        if not isinstance(raw_buildings, list):
            return None

        cookies = snapshot.get("cookies")
        cookies_ps = snapshot.get("cookiesPs")
        if cookies is None:
            cookies = 0.0
        if cookies_ps is None:
            cookies_ps = 0.0

        buildings = []
        for raw in raw_buildings:
            if not isinstance(raw, dict):
                continue
            building_id = raw.get("id")
            if building_id is None:
                continue

            price = raw.get("price")
            bulk_price = raw.get("bulkPrice")
            if price is None and bulk_price is None:
                continue

            stored_cps = raw.get("storedCps")
            stored_total_cps = raw.get("storedTotalCps")
            amount = int(raw.get("amount", 0))
            normalized_price = float(bulk_price if bulk_price is not None else price)
            delta_cps = self._estimate_delta_cps(stored_cps, stored_total_cps, amount)
            target = self._normalize_target(raw.get("target") or raw.get("row"), to_screen_point)

            buildings.append(
                {
                    "id": int(building_id),
                    "name": raw.get("name") or f"building-{building_id}",
                    "amount": amount,
                    "level": int(raw.get("level", 0)),
                    "price": normalized_price,
                    "base_price": None if raw.get("basePrice") is None else float(raw.get("basePrice")),
                    "sum_price_10": None if raw.get("sumPrice10") is None else float(raw.get("sumPrice10")),
                    "sum_price_100": None if raw.get("sumPrice100") is None else float(raw.get("sumPrice100")),
                    "stored_cps": 0.0 if stored_cps is None else float(stored_cps),
                    "stored_total_cps": 0.0 if stored_total_cps is None else float(stored_total_cps),
                    "delta_cps": delta_cps,
                    "locked": bool(raw.get("locked")),
                    "can_buy": bool(raw.get("canBuy")),
                    "can_sell": bool(raw.get("canSell")),
                    "sell_value_1": None if raw.get("sellValue1") is None else float(raw.get("sellValue1")),
                    "sell_value_10": None if raw.get("sellValue10") is None else float(raw.get("sellValue10")),
                    "sell_value_100": None if raw.get("sellValue100") is None else float(raw.get("sellValue100")),
                    "target": target,
                }
            )

        return {
            "cookies": float(cookies),
            "cookies_ps": float(cookies_ps),
            "store_buy_mode": self._extract_store_buy_mode(snapshot),
            "store_buy_bulk": self._extract_store_buy_bulk(snapshot),
            "total_buildings": sum(item["amount"] for item in buildings),
            "buildings": buildings,
            "dragon_target": self._extract_dragon_target(snapshot, buildings),
            "minigame_targets": self._extract_minigame_targets(buildings),
            "active_building_buffs": self._extract_active_building_buffs(snapshot),
        }

    def get_action(self, snapshot, to_screen_point, now=None):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None

        now = time.monotonic() if now is None else now
        if (now - self.last_action_time) < BUILDING_ACTION_COOLDOWN:
            return None

        self._update_observed_peak_amounts(state["buildings"])
        trim_candidate = self._find_cap_trim_candidate(
            state["buildings"],
            dragon_target=state.get("dragon_target"),
        )
        if trim_candidate is not None:
            target = trim_candidate["target"]
            quantity = self._select_cap_trim_quantity(trim_candidate)
            return BuildingAction(
                kind="sell_building",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                building_id=trim_candidate["id"],
                building_name=trim_candidate["name"],
                quantity=quantity,
                price=self._get_sell_value_for_quantity(trim_candidate, quantity),
                delta_cps=trim_candidate["delta_cps"],
                payback_seconds=0.0,
                cookies=state["cookies"],
                reserve=0.0,
            )
        reserve = self._calculate_reserve(state["cookies"], state["cookies_ps"], state["total_buildings"])
        candidate = self._find_best_candidate(
            state["buildings"],
            state["cookies"],
            state["cookies_ps"],
            reserve,
            dragon_target=state.get("dragon_target"),
            minigame_targets=state.get("minigame_targets"),
            active_building_buffs=state.get("active_building_buffs"),
            require_affordable=True,
        )
        next_candidate = self._find_best_candidate(
            state["buildings"],
            state["cookies"],
            state["cookies_ps"],
            reserve,
            dragon_target=state.get("dragon_target"),
            minigame_targets=state.get("minigame_targets"),
            active_building_buffs=state.get("active_building_buffs"),
            require_affordable=False,
        )
        hold_for_better_target = self._should_hold_for_better_target(candidate, next_candidate)
        if hold_for_better_target:
            candidate = None
        signature = self._candidate_signature(candidate)
        if signature != self.last_candidate_signature:
            self.last_candidate_signature = signature
            if candidate is None:
                self.log.debug(
                    "Building decision: no_candidate "
                    f"cookies={state['cookies']:.1f} reserve={reserve:.1f} "
                    f"total_buildings={state['total_buildings']} mode={state['store_buy_mode']} "
                    f"bulk={state['store_buy_bulk']}"
                )
            else:
                self.log.debug(
                    "Building decision: candidate "
                    f"name={candidate['name']} price={candidate['price']:.1f} "
                    f"delta_cps={candidate['delta_cps']:.4f} payback={candidate['payback_seconds']:.1f}s "
                    f"cookies={state['cookies']:.1f} reserve={reserve:.1f} "
                    f"total_buildings={state['total_buildings']} mode={state['store_buy_mode']} "
                    f"bulk={state['store_buy_bulk']}"
                )

        if candidate is None:
            return None

        target = candidate["target"]
        quantity = self._limit_buy_quantity(
            candidate,
            self._select_buy_quantity(candidate, state["cookies"], reserve, state["total_buildings"]),
        )
        return BuildingAction(
            kind="buy_building",
            screen_x=target["screen_x"],
            screen_y=target["screen_y"],
            building_id=candidate["id"],
            building_name=candidate["name"],
            quantity=quantity,
            price=candidate["price"],
            delta_cps=candidate["delta_cps"],
            payback_seconds=candidate["payback_seconds"],
            cookies=state["cookies"],
            reserve=reserve,
        )

    def record_action(self, action):
        self.last_action_time = time.monotonic()
        self.buy_clicks += 1
        verb = "sell" if action.kind == "sell_building" else "buy"
        self.last_building_summary = (
            f"{verb} {action.building_name} x{1 if action.quantity is None else action.quantity} @ {0.0 if action.price is None else action.price:.1f}"
        )
        self.log.info(
            f"Building {verb} click name={action.building_name} id={action.building_id} "
            f"quantity={1 if action.quantity is None else action.quantity} "
            f"price={0.0 if action.price is None else action.price:.1f} "
            f"delta_cps={0.0 if action.delta_cps is None else action.delta_cps:.4f} "
            f"payback={0.0 if action.payback_seconds is None else action.payback_seconds:.1f}s "
            f"cookies={0.0 if action.cookies is None else action.cookies:.1f} "
            f"reserve={0.0 if action.reserve is None else action.reserve:.1f}"
        )

    def get_diagnostics(self, snapshot, to_screen_point):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return {
                "available": False,
                "reason": "no_building_data",
            }

        self._update_observed_peak_amounts(state["buildings"])
        reserve = self._calculate_reserve(state["cookies"], state["cookies_ps"], state["total_buildings"])
        total_buildings = state["total_buildings"]
        candidate = self._find_best_candidate(
            state["buildings"],
            state["cookies"],
            state["cookies_ps"],
            reserve,
            dragon_target=state.get("dragon_target"),
            minigame_targets=state.get("minigame_targets"),
            active_building_buffs=state.get("active_building_buffs"),
            require_affordable=True,
        )
        next_candidate = self._find_best_candidate(
            state["buildings"],
            state["cookies"],
            state["cookies_ps"],
            reserve,
            dragon_target=state.get("dragon_target"),
            minigame_targets=state.get("minigame_targets"),
            active_building_buffs=state.get("active_building_buffs"),
            require_affordable=False,
        )
        affordable = sum(
            1
            for item in state["buildings"]
            if not item["locked"] and item["target"] is not None and item["price"] > 0 and state["cookies"] >= item["price"]
        )
        aligned = (total_buildings % TEMPLE_TOTAL_BUILDINGS_MODULUS) == 0
        hold_for_better_target = self._should_hold_for_better_target(candidate, next_candidate)
        held_candidate = candidate if hold_for_better_target else None
        if hold_for_better_target:
            candidate = None
        if hold_for_better_target:
            reason = "saving_for_better_horizon_target"
        elif state.get("dragon_target") and candidate is not None and candidate.get("dragon_target"):
            reason = "dragon_building_floor_ready"
        elif state.get("dragon_target") and next_candidate is not None and next_candidate.get("dragon_target"):
            reason = "waiting_for_dragon_building_floor"
        elif candidate is not None:
            reason = "buy_ready"
        elif next_candidate is not None:
            reason = "waiting_for_cash_horizon_candidate"
        else:
            reason = "no_buy_in_horizon"
        return {
            "available": True,
            "reason": reason,
            "cookies": state["cookies"],
            "cookies_ps": state["cookies_ps"],
            "store_buy_mode": state["store_buy_mode"],
            "store_buy_bulk": state["store_buy_bulk"],
            "reserve": reserve,
            "reserve_scale": self._calculate_reserve_scale(total_buildings),
            "effective_reserve_cps_seconds": self.reserve_cps_seconds * self._calculate_reserve_scale(total_buildings),
            "cap_floor": self._calculate_cap_floor(state["cookies"]),
            "spendable": max(0.0, state["cookies"] - reserve),
            "spend_cap_ratio": self.max_spend_ratio,
            "payback_horizon_seconds": self.payback_horizon_seconds,
            "buildings_total": len(state["buildings"]),
            "total_buildings": total_buildings,
            "temple_modulus": TEMPLE_TOTAL_BUILDINGS_MODULUS,
            "temple_aligned": aligned,
            "buys_to_alignment": (TEMPLE_TOTAL_BUILDINGS_MODULUS - (total_buildings % TEMPLE_TOTAL_BUILDINGS_MODULUS)) % TEMPLE_TOTAL_BUILDINGS_MODULUS,
            "affordable": affordable,
            "candidate": None if candidate is None else candidate["name"],
            "candidate_price": None if candidate is None else candidate["price"],
            "candidate_quantity": None
            if candidate is None
            else self._limit_buy_quantity(
                candidate,
                self._select_buy_quantity(candidate, state["cookies"], reserve, state["total_buildings"]),
            ),
            "candidate_delta_cps": None if candidate is None else candidate["delta_cps"],
            "candidate_payback_seconds": None if candidate is None else candidate["payback_seconds"],
            "candidate_effective_delta_cps": None if candidate is None else candidate.get("effective_delta_cps"),
            "candidate_active_buff_multiplier": None if candidate is None else candidate.get("active_buff_multiplier"),
            "held_candidate": None if held_candidate is None else held_candidate["name"],
            "held_candidate_price": None if held_candidate is None else held_candidate["price"],
            "held_candidate_delta_cps": None if held_candidate is None else held_candidate["delta_cps"],
            "held_candidate_payback_seconds": None if held_candidate is None else held_candidate["payback_seconds"],
            "next_candidate": None if next_candidate is None else next_candidate["name"],
            "next_candidate_price": None if next_candidate is None else next_candidate["price"],
            "next_candidate_quantity": None
            if next_candidate is None
            else self._limit_buy_quantity(
                next_candidate,
                self._select_buy_quantity(next_candidate, state["cookies"], reserve, state["total_buildings"]),
            ),
            "next_candidate_delta_cps": None if next_candidate is None else next_candidate["delta_cps"],
            "next_candidate_payback_seconds": None if next_candidate is None else next_candidate["payback_seconds"],
            "next_candidate_can_buy": None if next_candidate is None else next_candidate["can_buy"],
            "next_candidate_effective_delta_cps": None if next_candidate is None else next_candidate.get("effective_delta_cps"),
            "next_candidate_active_buff_multiplier": None if next_candidate is None else next_candidate.get("active_buff_multiplier"),
            "active_building_buffs": tuple(
                {
                    "building_id": int(building_id),
                    "building_name": buff.get("buildingName"),
                    "buff_name": buff.get("name"),
                    "type": buff.get("type"),
                    "multiplier": buff.get("multCpS"),
                }
                for building_id, buff in sorted((state.get("active_building_buffs") or {}).items())
            ),
            "dragon_target": state.get("dragon_target"),
            "minigame_targets": state.get("minigame_targets"),
            "buildings": [self._describe_building_cap(item) for item in state["buildings"]],
        }

    def _extract_store_buy_mode(self, snapshot):
        if not isinstance(snapshot, dict):
            return None
        store = snapshot.get("store")
        if isinstance(store, dict) and store.get("buyMode") is not None:
            return store.get("buyMode")
        return snapshot.get("storeBuyMode")

    def _extract_store_buy_bulk(self, snapshot):
        if not isinstance(snapshot, dict):
            return None
        store = snapshot.get("store")
        if isinstance(store, dict) and store.get("buyBulk") is not None:
            return store.get("buyBulk")
        return None

    def _find_best_candidate(
        self,
        buildings,
        cookies,
        cookies_ps,
        reserve,
        dragon_target=None,
        minigame_targets=None,
        active_building_buffs=None,
        require_affordable=True,
    ):
        spendable = cookies - reserve
        horizon_budget = cookies + (max(0.0, float(cookies_ps)) * self.payback_horizon_seconds)
        dragon_candidate = self._find_dragon_target_candidate(
            buildings,
            spendable,
            horizon_budget,
            dragon_target,
            require_affordable=require_affordable,
        )
        standard_candidate = self._find_standard_candidate(
            buildings,
            spendable,
            horizon_budget,
            active_building_buffs=active_building_buffs,
            require_affordable=require_affordable,
        )
        if self._should_prioritize_dragon_candidate(
            dragon_candidate,
            standard_candidate,
            cookies,
        ):
            return dragon_candidate
        if standard_candidate is not None:
            return standard_candidate
        return dragon_candidate

    def _find_standard_candidate(
        self,
        buildings,
        spendable,
        horizon_budget,
        active_building_buffs=None,
        require_affordable=True,
    ):
        candidates = []
        active_building_buffs = active_building_buffs or {}
        for item in buildings:
            if item["locked"]:
                continue
            if item["target"] is None:
                continue
            if require_affordable and not item["can_buy"]:
                continue
            cap = self._get_cap_for_building(item)
            if cap is not None and int(item["amount"]) >= int(cap):
                continue
            if item["price"] <= 0:
                continue
            if not require_affordable and horizon_budget < item["price"]:
                continue
            if require_affordable and spendable < item["price"]:
                continue
            if item["delta_cps"] <= 0:
                continue

            buff_mult = self._get_building_buff_multiplier(item, active_building_buffs)
            effective_delta_cps = float(item["delta_cps"]) * buff_mult
            if effective_delta_cps <= 0:
                continue
            payback_seconds = item["price"] / effective_delta_cps
            candidate = dict(item)
            candidate["payback_seconds"] = payback_seconds
            candidate["active_buff_multiplier"] = buff_mult
            candidate["effective_delta_cps"] = effective_delta_cps
            candidates.append(candidate)

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item["payback_seconds"], item["price"], item["id"]))
        return candidates[0]

    def _should_prioritize_dragon_candidate(self, dragon_candidate, standard_candidate, cookies):
        if dragon_candidate is None:
            return False
        if standard_candidate is None:
            return True
        remaining = int(dragon_candidate.get("dragon_remaining") or 0)
        if remaining <= DRAGON_PRIORITY_REMAINING_THRESHOLD:
            return True
        price = float(dragon_candidate.get("price") or 0.0)
        if price > 0.0 and price <= (max(0.0, float(cookies)) * DRAGON_PRIORITY_COOKIES_RATIO):
            return True
        dragon_payback = float(dragon_candidate.get("payback_seconds") or 0.0)
        standard_payback = float(standard_candidate.get("payback_seconds") or 0.0)
        if (
            math.isfinite(dragon_payback)
            and dragon_payback > 0.0
            and standard_payback > 0.0
            and dragon_payback <= (standard_payback * DRAGON_PRIORITY_PAYBACK_RATIO)
        ):
            return True
        return False

    def _find_dragon_target_candidate(self, buildings, spendable, horizon_budget, dragon_target, require_affordable=True):
        if not isinstance(dragon_target, dict):
            return None
        target_id = dragon_target.get("building_id")
        required_amount = int(dragon_target.get("required_amount") or 0)
        for item in buildings:
            item_id = item.get("id")
            if target_id is None or item_id is None or int(item_id) != int(target_id):
                continue
            if item["locked"] or item["target"] is None or item["price"] <= 0:
                return None
            if int(item.get("amount") or 0) >= required_amount:
                return None
            if require_affordable:
                if not item["can_buy"] or spendable < item["price"]:
                    return None
            elif horizon_budget < item["price"]:
                return None
            payback_seconds = math.inf
            if item["delta_cps"] > 0:
                payback_seconds = item["price"] / item["delta_cps"]
            candidate = dict(item)
            candidate["payback_seconds"] = payback_seconds
            candidate["dragon_target"] = True
            candidate["dragon_required_amount"] = required_amount
            candidate["dragon_remaining"] = max(0, required_amount - int(item.get("amount") or 0))
            return candidate
        return None

    def _find_cap_trim_candidate(self, buildings, dragon_target=None):
        active_dragon_target_id = None
        if isinstance(dragon_target, dict) and dragon_target.get("building_id") is not None:
            try:
                active_dragon_target_id = int(dragon_target.get("building_id"))
            except Exception:
                active_dragon_target_id = None
        for item in buildings:
            if item["locked"] or item["target"] is None:
                continue
            item_id = int(item.get("id") or -1)
            if active_dragon_target_id is not None and item_id == active_dragon_target_id:
                continue
            cap = self._get_cap_for_building(item)
            if cap is None:
                continue
            amount = int(item.get("amount") or 0)
            if amount <= int(cap):
                continue
            if not item.get("can_buy", False) and not item.get("can_sell", False):
                continue
            if not item.get("can_sell", False):
                continue
            candidate = dict(item)
            candidate["over_cap"] = amount - int(cap)
            return candidate
        return None

    def _select_cap_trim_quantity(self, candidate):
        if not isinstance(candidate, dict):
            return 1
        over_cap = max(0, int(candidate.get("over_cap") or 0))
        if over_cap >= 100 and candidate.get("sell_value_100") is not None:
            return 100
        if over_cap >= 10 and candidate.get("sell_value_10") is not None:
            return 10
        return 1

    def _get_sell_value_for_quantity(self, candidate, quantity):
        if not isinstance(candidate, dict):
            return None
        quantity = max(1, int(quantity or 1))
        if quantity >= 100 and candidate.get("sell_value_100") is not None:
            return candidate.get("sell_value_100")
        if quantity >= 10 and candidate.get("sell_value_10") is not None:
            return candidate.get("sell_value_10")
        return candidate.get("sell_value_1")

    def _extract_dragon_target(self, snapshot, buildings):
        if not isinstance(snapshot, dict):
            return None
        dragon = snapshot.get("dragon")
        if not isinstance(dragon, dict):
            return None
        if dragon.get("nextCostType") != "building_sacrifice":
            return None
        required_amount = int(dragon.get("nextRequiredBuildingAmount") or 0)
        building_id = dragon.get("nextRequiredBuildingId")
        if building_id is None or required_amount <= 0:
            return None
        building_id = int(building_id)
        current_amount = None
        for item in buildings:
            item_id = item.get("id")
            if item_id is not None and int(item_id) == building_id:
                current_amount = int(item.get("amount") or 0)
                break
        return {
            "building_id": building_id,
            "building_name": dragon.get("nextRequiredBuildingName"),
            "required_amount": required_amount,
            "current_amount": current_amount,
            "remaining": None if current_amount is None else max(0, required_amount - current_amount),
        }

    def _extract_active_building_buffs(self, snapshot):
        if not isinstance(snapshot, dict):
            return {}
        raw_buffs = snapshot.get("buffs")
        if not isinstance(raw_buffs, list):
            return {}
        active = {}
        for buff in raw_buffs:
            if not isinstance(buff, dict):
                continue
            buff_type = buff.get("type")
            building_id = buff.get("buildingId")
            if buff_type not in {"building buff", "building debuff"} or building_id is None:
                continue
            try:
                building_id = int(building_id)
            except Exception:
                continue
            mult = buff.get("multCpS")
            if not isinstance(mult, (int, float)) or float(mult) <= 0.0:
                continue
            current = active.get(building_id)
            if current is None or float(mult) > float(current.get("multCpS") or 0.0):
                active[building_id] = {
                    "name": buff.get("name"),
                    "type": buff_type,
                    "multCpS": float(mult),
                    "buildingName": buff.get("buildingName"),
                }
        return active

    def _get_building_buff_multiplier(self, item, active_building_buffs):
        if not isinstance(item, dict):
            return 1.0
        entry = active_building_buffs.get(int(item.get("id") or -1))
        if not isinstance(entry, dict):
            return 1.0
        mult = entry.get("multCpS")
        if not isinstance(mult, (int, float)) or float(mult) <= 0.0:
            return 1.0
        return float(mult)

    def _extract_minigame_targets(self, buildings):
        targets = []
        for item in buildings:
            name = item.get("name")
            if not name:
                continue
            required_amount = MINIGAME_BUILDING_RETAIN_FLOORS.get(name)
            if required_amount is None:
                continue
            current_amount = int(item.get("amount") or 0)
            targets.append(
                {
                    "building_id": int(item.get("id")),
                    "building_name": name,
                    "required_amount": int(required_amount),
                    "current_amount": current_amount,
                    "remaining": max(0, int(required_amount) - current_amount),
                }
            )
        return targets

    def _should_hold_for_better_target(self, candidate, next_candidate):
        if candidate is None or next_candidate is None:
            return False
        if int(candidate.get("id") or -1) == int(next_candidate.get("id") or -2):
            return False
        candidate_payback = float(candidate.get("payback_seconds") or 0.0)
        next_payback = float(next_candidate.get("payback_seconds") or 0.0)
        if candidate_payback <= 0.0 or next_payback <= 0.0:
            return False
        return next_payback <= (candidate_payback * BETTER_TARGET_PAYBACK_RATIO)

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

    def _update_observed_peak_amounts(self, buildings):
        for item in buildings:
            building_id = int(item.get("id") or 0)
            amount = int(item.get("amount") or 0)
            previous = int(self.observed_peak_amounts.get(building_id, 0))
            if amount > previous:
                self.observed_peak_amounts[building_id] = amount

    def _select_buy_quantity(self, candidate, cookies, reserve, total_buildings):
        if not isinstance(candidate, dict):
            return 1
        spendable = max(0.0, float(cookies) - float(reserve))
        if spendable <= 0.0:
            return 1
        recovery_gap = self._get_recovery_gap(candidate)
        if recovery_gap <= 0:
            return self._select_early_game_batch_quantity(candidate, spendable, total_buildings)
        if recovery_gap >= 100 and candidate.get("sum_price_100") is not None and float(candidate["sum_price_100"]) <= spendable:
            return 100
        if recovery_gap >= 10 and candidate.get("sum_price_10") is not None and float(candidate["sum_price_10"]) <= spendable:
            return 10
        return 1

    def _get_recovery_gap(self, candidate):
        if not isinstance(candidate, dict):
            return 0
        building_id = int(candidate.get("id") or 0)
        amount = int(candidate.get("amount") or 0)
        peak = int(self.observed_peak_amounts.get(building_id, amount))
        return max(0, peak - amount)

    def _limit_buy_quantity(self, candidate, quantity):
        if not isinstance(candidate, dict):
            return 1
        quantity = max(1, int(quantity or 1))
        amount = int(candidate.get("amount") or 0)
        if candidate.get("dragon_target"):
            remaining = max(0, int(candidate.get("dragon_remaining") or 0))
            return 1 if remaining <= 0 else min(quantity, remaining)
        cap = self._get_cap_for_building(candidate)
        if cap is None:
            return quantity
        remaining_to_cap = max(0, int(cap) - amount)
        if remaining_to_cap <= 0:
            return 1
        if remaining_to_cap >= quantity:
            return quantity
        if remaining_to_cap >= 100 and quantity >= 100:
            return 100
        if remaining_to_cap >= 10 and quantity >= 10:
            return 10
        return 1

    def _select_early_game_batch_quantity(self, candidate, spendable, total_buildings):
        if int(total_buildings or 0) > EARLY_GAME_BULK_TOTAL_BUILDINGS:
            return 1
        price = candidate.get("price")
        delta_cps = candidate.get("delta_cps")
        if not isinstance(price, (int, float)) or float(price) <= 0.0:
            return 1
        if not isinstance(delta_cps, (int, float)) or float(delta_cps) <= 0.0:
            return 1
        if float(price) > (float(spendable) * EARLY_GAME_BULK_MAX_SINGLE_PRICE_RATIO):
            return 1
        if self._bulk_quantity_is_reasonable(candidate, quantity=100, total_price=candidate.get("sum_price_100"), spendable=spendable):
            return 100
        if self._bulk_quantity_is_reasonable(candidate, quantity=10, total_price=candidate.get("sum_price_10"), spendable=spendable):
            return 10
        return 1

    def _bulk_quantity_is_reasonable(self, candidate, quantity, total_price, spendable):
        if quantity <= 1 or total_price is None:
            return False
        total_price = float(total_price)
        if total_price <= 0.0 or total_price > float(spendable):
            return False
        delta_cps = float(candidate.get("delta_cps") or 0.0)
        if delta_cps <= 0.0:
            return False
        bundle_payback_seconds = total_price / (delta_cps * float(quantity))
        return math.isfinite(bundle_payback_seconds) and bundle_payback_seconds <= self.payback_horizon_seconds

    def _estimate_delta_cps(self, stored_cps, stored_total_cps, amount):
        if stored_cps is not None:
            value = float(stored_cps)
            if math.isfinite(value) and value > 0:
                return value
        if stored_total_cps is not None:
            total = float(stored_total_cps)
            if math.isfinite(total) and total > 0:
                divisor = max(1, amount)
                return total / divisor
        return 0.0

    def _calculate_cap_floor(self, cookies):
        keep_ratio = max(0.0, 1.0 - self.max_spend_ratio)
        return max(0.0, float(cookies)) * keep_ratio

    def _calculate_reserve_scale(self, total_buildings):
        total_buildings = max(0, int(total_buildings or 0))
        if total_buildings <= EARLY_RESERVE_TOTAL_BUILDINGS:
            return MIN_RESERVE_SCALE
        if total_buildings >= FULL_RESERVE_TOTAL_BUILDINGS:
            return 1.0
        span = FULL_RESERVE_TOTAL_BUILDINGS - EARLY_RESERVE_TOTAL_BUILDINGS
        progress = (total_buildings - EARLY_RESERVE_TOTAL_BUILDINGS) / float(span)
        return MIN_RESERVE_SCALE + (1.0 - MIN_RESERVE_SCALE) * progress

    def _calculate_reserve(self, cookies, cookies_ps, total_buildings):
        reserve_scale = self._calculate_reserve_scale(total_buildings)
        cps_reserve = max(0.0, float(cookies_ps)) * self.reserve_cps_seconds * reserve_scale
        cap_floor = self._calculate_cap_floor(cookies)
        return max(self.reserve_cookies, cps_reserve, cap_floor)

    def _candidate_signature(self, candidate):
        if candidate is None:
            return None
        return (
            candidate["id"],
            round(candidate["price"], 3),
            round(candidate["delta_cps"], 6),
            round(candidate["payback_seconds"], 3),
        )

    def get_runtime_stats(self):
        with self.settings_lock:
            building_caps = dict(self.building_caps)
            ignored_building_caps = sorted(self.ignored_building_caps)
        return {
            "buy_clicks": self.buy_clicks,
            "last_building": self.last_building_summary,
            "reserve_cookies": self.reserve_cookies,
            "reserve_cps_seconds": self.reserve_cps_seconds,
            "payback_horizon_seconds": self.payback_horizon_seconds,
            "max_spend_ratio": self.max_spend_ratio,
            "building_caps": building_caps,
            "default_building_caps": dict(self.default_building_caps),
            "ignored_building_caps": ignored_building_caps,
        }

    def set_payback_horizon_seconds(self, horizon_seconds):
        horizon_seconds = float(horizon_seconds)
        if horizon_seconds <= 0:
            raise ValueError("horizon must be positive")
        with self.settings_lock:
            self.payback_horizon_seconds = horizon_seconds
            return self.payback_horizon_seconds

    def set_building_cap(self, building_name, cap):
        if not building_name:
            raise ValueError("building_name is required")
        with self.settings_lock:
            default_cap = self.default_building_caps.get(building_name)
            if cap is None:
                if default_cap is None:
                    self.building_caps.pop(building_name, None)
                else:
                    self.building_caps[building_name] = int(default_cap)
                return self.building_caps.get(building_name)
            cap = int(cap)
            if cap < 0:
                raise ValueError("cap must be non-negative")
            self.building_caps[building_name] = cap
            return cap

    def set_building_cap_ignored(self, building_name, ignored):
        if not building_name:
            raise ValueError("building_name is required")
        with self.settings_lock:
            if ignored:
                self.ignored_building_caps.add(str(building_name))
            else:
                self.ignored_building_caps.discard(str(building_name))
            return str(building_name) in self.ignored_building_caps

    def _describe_building_cap(self, item):
        amount = int(item.get("amount", 0))
        name = item.get("name")
        default_cap = self.default_building_caps.get(name)
        current_cap = self._get_cap_for_building(item)
        manual_cap = self._get_manual_cap(name)
        cap_ignored = self._is_cap_ignored(name)
        remaining = None if current_cap is None else max(0, int(current_cap) - amount)
        return {
            "id": item.get("id"),
            "name": name,
            "amount": amount,
            "default_cap": default_cap,
            "cap": current_cap,
            "manual_cap": manual_cap,
            "cap_ignored": cap_ignored,
            "remaining_to_cap": remaining,
            "cap_reached": False if current_cap is None else amount >= int(current_cap),
        }

    def _get_cap_for_building(self, item):
        name = item.get("name")
        with self.settings_lock:
            if name in self.ignored_building_caps:
                return None
            if name in self.building_caps:
                return self.building_caps[name]
            building_id = item.get("id")
            return self.building_caps.get(building_id)

    def _get_manual_cap(self, building_name):
        with self.settings_lock:
            value = self.building_caps.get(building_name)
            if value is None:
                return None
            default_cap = self.default_building_caps.get(building_name)
            return None if default_cap == value else value

    def _is_cap_ignored(self, building_name):
        with self.settings_lock:
            return building_name in self.ignored_building_caps
