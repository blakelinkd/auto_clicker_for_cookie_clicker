from dataclasses import dataclass
import math
import re
import time

from building_autobuyer import (
    DEFAULT_RESERVE_COOKIES,
    DEFAULT_RESERVE_CPS_SECONDS,
    MAX_BUILDING_SPEND_RATIO,
)
from building_store import BuildingStoreController
from combo_evaluator import (
    CLICK_STACK_BUFF_KEYS,
    evaluate_combo_buffs,
)


PRICE_INCREASE = 1.15
GODZAMOK_CLICK_BONUS_BY_LEVEL = {
    1: 0.01,
    2: 0.005,
    3: 0.0025,
}
GODZAMOK_BUFF_SECONDS = 10.0
CLICK_RATE_SAFETY = 0.85
PROFIT_MARGIN_MULTIPLIER = 1.10
COMBO_SELL_QUANTITIES = (100, 10, 1)
EXCLUDED_BUILDINGS = {"Wizard tower"}
MINIGAME_BUILDING_RETAIN_FLOORS = {
    "Farm": 300,
    "Bank": 1,
    "Temple": 1,
    "Wizard tower": 1,
}
GODZAMOK_REBUY_PAYBACK_TOLERANCE = 1.05
GODZAMOK_REBUY_MAX_WAIT_SECONDS = 5.0
GODZAMOK_REBUY_MAX_STALLS = 3
GODZAMOK_REBUY_BULKS = (100, 10, 1)
HAND_OF_FATE_KEY = "hand of fate"
CRAFTY_PIXIES_KEY = "summon crafty pixies"
CRAFTY_PIXIES_BUFF = "Crafty pixies"
NASTY_GOBLINS_BUFF = "Nasty goblins"
CRAFTY_PIXIES_PRICE_FACTOR = 0.98
NASTY_GOBLINS_PRICE_FACTOR = 1.02


@dataclass
class GodzamokAction:
    kind: str
    screen_x: int
    screen_y: int
    detail: str
    building_id: int | None = None
    building_name: str | None = None
    quantity: int | None = None
    expected_net: float | None = None
    store_mode: int | None = None
    store_bulk: int | None = None
    current_store_mode: int | None = None
    current_store_bulk: int | None = None


class GodzamokComboEngine:
    def __init__(self, log, click_interval):
        self.log = log
        self.click_interval = float(click_interval)
        self.store = BuildingStoreController()
        self.pending = None
        self.fire_count = 0
        self.last_combo_summary = None
        self.total_estimated_profit = 0.0
        self.last_estimated_profit = None

    def get_action(self, snapshot, to_screen_point, now=None):
        now = time.monotonic() if now is None else now
        state = self._extract_state(snapshot, to_screen_point)
        if state is None:
            return None

        if self.pending is not None:
            return self._advance_pending(state, snapshot, to_screen_point, now)

        if self._should_open_temple(state):
            return GodzamokAction(
                kind="open_temple",
                screen_x=int(state["temple_open_target"]["screen_x"]),
                screen_y=int(state["temple_open_target"]["screen_y"]),
                detail="open_temple",
            )

        spell_action = self._get_spell_action(state)
        if spell_action is not None:
            return spell_action

        candidate = self._find_candidate(state)
        if candidate is None:
            return None

        store_action = self.store.plan_sell(
            snapshot,
            to_screen_point,
            candidate["building_id"],
            quantity=candidate["quantity"],
        )
        if store_action is None:
            return None
        if store_action.kind == "click_building":
            self.pending = {
                "phase": "await_sell_confirm",
                "building_id": candidate["building_id"],
                "building_name": candidate["building_name"],
                "quantity": candidate["quantity"],
                "initial_amount": candidate["amount"],
                "expected_net": candidate["net_profit"],
                "expected_gain": candidate["extra_click_gain"],
                "round_trip_cost": candidate["round_trip_cost"],
                "pixies_planned": candidate["pixies_planned"],
                "pixies_expected_savings": candidate["pixies_expected_savings"],
                "pixies_fail_chance": candidate["pixies_fail_chance"],
                "sold_at": None,
            }
        return self._wrap_store_action(
            store_action,
            detail="godzamok_sell_prep" if store_action.kind != "click_building" else "godzamok_sell",
            building_id=candidate["building_id"],
            building_name=candidate["building_name"],
            quantity=candidate["quantity"],
            expected_net=candidate["net_profit"],
        )

    def get_diagnostics(self, snapshot, to_screen_point):
        state = self._extract_state(snapshot, to_screen_point)
        if state is None:
            return {"available": False, "reason": "no_combo_data"}
        if self.pending is not None:
            return {
                "available": True,
                "reason": self.pending["phase"],
                "building": self.pending.get("building_name"),
                "quantity": self.pending.get("quantity"),
                "expected_net": self.pending.get("expected_net"),
                "pixies_planned": self.pending.get("pixies_planned"),
                "pixies_expected_savings": self.pending.get("pixies_expected_savings"),
                "fire_count": self.fire_count,
            }
        candidate = self._find_candidate(state)
        return {
            "available": True,
            "reason": "combo_ready" if candidate is not None else self._combo_block_reason(state),
            "ruin_level": state["ruin_level"],
            "ruin_bonus_per_sale": state["ruin_bonus_per_sale"],
            "computed_mouse_cps": state["computed_mouse_cps"],
            "buffs": tuple(buff["name"] for buff in state["buffs"]),
            "temple_on_minigame": state["temple_on_minigame"],
            "temple_has_open_target": state["temple_open_target"] is not None,
            "combo_stage": state["combo_eval"]["stage"],
            "click_buffs": tuple(sorted(state["combo_eval"]["click_buffs"])),
            "production_buffs": tuple(sorted(state["combo_eval"]["production_buffs"])),
            "hand_ready": state["hand_ready"],
            "magic": state["magic"],
            "max_magic": state["max_magic"],
            "candidate_building": None if candidate is None else candidate["building_name"],
            "candidate_quantity": None if candidate is None else candidate["quantity"],
            "candidate_net": None if candidate is None else candidate["net_profit"],
            "candidate_gain": None if candidate is None else candidate["extra_click_gain"],
            "candidate_cost": None if candidate is None else candidate["round_trip_cost"],
            "candidate_uses_pixies": None if candidate is None else candidate["pixies_planned"],
            "candidate_pixies_savings": None if candidate is None else candidate["pixies_expected_savings"],
            "fire_count": self.fire_count,
        }

    def record_action(self, action):
        if action.kind == "click_building" and self.pending is not None and self.pending["phase"] == "await_sell_confirm":
            self.log.info(
                f"Godzamok combo sell click building={self.pending['building_name']} "
                f"quantity={self.pending['quantity']} expected_net={self.pending['expected_net']:.1f}"
            )
        elif action.kind == "click_building" and self.pending is not None and self.pending["phase"] == "rebuy":
            self.log.info(
                f"Godzamok combo rebuy click building={self.pending['building_name']} "
                f"quantity={self.pending['quantity']}"
            )
        elif action.kind == "cast_spell" and self.pending is not None and self.pending["phase"] == "cast_pixies":
            self.log.info(
                f"Godzamok combo cast spell key={action.detail} "
                f"building={self.pending['building_name']} quantity={self.pending['quantity']}"
            )
        elif action.kind in {"set_store_mode", "set_store_bulk"} and self.pending is not None and self.pending["phase"] == "reset_store":
            current_mode = "?" if action.current_store_mode is None else action.current_store_mode
            next_mode = "?" if action.store_mode is None else action.store_mode
            current_bulk = "?" if action.current_store_bulk is None else action.current_store_bulk
            next_bulk = "?" if action.store_bulk is None else action.store_bulk
            self.log.info(
                f"Godzamok combo store reset action={action.kind} "
                f"mode={current_mode}->{next_mode} "
                f"bulk={current_bulk}->{next_bulk}"
            )

    def get_runtime_stats(self):
        return {
            "fire_count": self.fire_count,
            "last_combo": self.last_combo_summary,
            "last_estimated_profit": self.last_estimated_profit,
            "total_estimated_profit": self.total_estimated_profit,
            "pending_phase": None if self.pending is None else self.pending.get("phase"),
        }

    def has_pending(self):
        return self.pending is not None

    def owns_spellcasting(self, snapshot, to_screen_point):
        if self.pending is None:
            return False
        return self.pending.get("phase") == "cast_pixies"

    def _advance_pending(self, state, snapshot, to_screen_point, now):
        building = state["buildings"].get(self.pending["building_id"])
        if building is None:
            self.pending = None
            return None

        if self.pending["phase"] == "await_sell_confirm":
            if building["amount"] <= self.pending["initial_amount"] - self.pending["quantity"]:
                self.pending["phase"] = "buffing"
                self.pending["sold_at"] = now
                self.fire_count += 1
                self.last_estimated_profit = float(self.pending["expected_net"])
                self.total_estimated_profit += float(self.pending["expected_net"])
                self.last_combo_summary = (
                    f"{self.pending['building_name']} x{self.pending['quantity']} "
                    f"net={self.pending['expected_net']:.1f}"
                )
                self.log.info(
                    f"Godzamok combo fired building={self.pending['building_name']} "
                    f"quantity={self.pending['quantity']} expected_net={self.pending['expected_net']:.1f} "
                    f"total_estimated_profit={self.total_estimated_profit:.1f}"
                )
            return None

        if self.pending["phase"] == "buffing":
            sold_at = self.pending.get("sold_at") or now
            if (now - sold_at) < GODZAMOK_BUFF_SECONDS:
                return None
            rebuy_decision = self._choose_rebuy_strategy(state, building)
            self.pending["rebuy_strategy"] = rebuy_decision["strategy"]
            self.pending["rebuy_payback_seconds"] = rebuy_decision["rebuy_payback_seconds"]
            self.pending["best_autobuy_name"] = rebuy_decision["best_autobuy_name"]
            self.pending["best_autobuy_payback_seconds"] = rebuy_decision["best_autobuy_payback_seconds"]
            if rebuy_decision["strategy"] == "rebuy":
                if self.pending.get("pixies_planned") and self._can_cast_pixies_now(state):
                    self.pending["phase"] = "cast_pixies"
                else:
                    self.pending["phase"] = "rebuy"
                    self.pending["rebuy_started_at"] = now
                    self.pending["rebuy_last_amount"] = building["amount"]
                    self.pending["rebuy_stall_count"] = 0
                    self.pending["rebuy_last_unavailable"] = None
                self.log.info(
                    f"Godzamok combo rebuy chosen building={self.pending['building_name']} "
                    f"quantity={self.pending['quantity']} "
                    f"rebuy_payback={0.0 if rebuy_decision['rebuy_payback_seconds'] is None else rebuy_decision['rebuy_payback_seconds']:.1f}s "
                    f"alt={rebuy_decision['best_autobuy_name'] or '-'} "
                    f"alt_payback={0.0 if rebuy_decision['best_autobuy_payback_seconds'] is None else rebuy_decision['best_autobuy_payback_seconds']:.1f}s"
                )
            else:
                self.pending["phase"] = "reset_store"
                self.log.info(
                    f"Godzamok combo deferring rebuy building={self.pending['building_name']} "
                    f"quantity={self.pending['quantity']} "
                    f"rebuy_payback={0.0 if rebuy_decision['rebuy_payback_seconds'] is None else rebuy_decision['rebuy_payback_seconds']:.1f}s "
                    f"alt={rebuy_decision['best_autobuy_name'] or '-'} "
                    f"alt_payback={0.0 if rebuy_decision['best_autobuy_payback_seconds'] is None else rebuy_decision['best_autobuy_payback_seconds']:.1f}s"
                )
            return None

        if self.pending["phase"] == "cast_pixies":
            if state["buff_names"] & {CRAFTY_PIXIES_BUFF, NASTY_GOBLINS_BUFF}:
                self.pending["phase"] = "rebuy_setup"
                return None
            pixies_spell = state["spells_by_key"].get(CRAFTY_PIXIES_KEY)
            if pixies_spell is None or not pixies_spell.get("ready"):
                self.pending["phase"] = "rebuy_setup"
                return None
            return GodzamokAction(
                kind="cast_spell",
                screen_x=int(pixies_spell["screen_x"]),
                screen_y=int(pixies_spell["screen_y"]),
                detail=CRAFTY_PIXIES_KEY,
                building_id=self.pending["building_id"],
                building_name=self.pending["building_name"],
                quantity=self.pending["quantity"],
                expected_net=self.pending["expected_net"],
            )

        if self.pending["phase"] == "rebuy_setup":
            reset_action = self.store.plan_reset_to_default(snapshot, to_screen_point)
            if reset_action is None:
                return None
            if reset_action.kind == "store_ready":
                self.pending["phase"] = "rebuy"
                if self.pending.get("rebuy_started_at") is None:
                    self.pending["rebuy_started_at"] = now
                if self.pending.get("rebuy_last_amount") is None:
                    self.pending["rebuy_last_amount"] = building["amount"]
                if self.pending.get("rebuy_stall_count") is None:
                    self.pending["rebuy_stall_count"] = 0
                return None
            return self._wrap_store_action(
                reset_action,
                detail="godzamok_rebuy_setup",
                building_id=self.pending["building_id"],
                building_name=self.pending["building_name"],
                quantity=1,
                expected_net=self.pending["expected_net"],
            )

        if self.pending["phase"] == "rebuy":
            rebuy_started_at = float(self.pending.get("rebuy_started_at") or now)
            remaining_needed = max(0, int(self.pending["initial_amount"]) - int(building["amount"]))
            if building["amount"] < self.pending["initial_amount"]:
                last_amount = self.pending.get("rebuy_last_amount")
                if last_amount is None or int(building["amount"]) != int(last_amount):
                    self.pending["rebuy_last_amount"] = building["amount"]
                    self.pending["rebuy_stall_count"] = 0
                elif (now - rebuy_started_at) >= GODZAMOK_REBUY_MAX_WAIT_SECONDS:
                    stall_count = int(self.pending.get("rebuy_stall_count") or 0) + 1
                    self.pending["rebuy_stall_count"] = stall_count
                    self.pending["rebuy_started_at"] = now
                    self.log.info(
                        f"Godzamok combo rebuy stalled building={self.pending['building_name']} "
                        f"quantity={self.pending['quantity']} amount={building['amount']} "
                        f"target={self.pending['initial_amount']} stalls={stall_count}"
                    )
                    if stall_count >= GODZAMOK_REBUY_MAX_STALLS:
                        self.log.info(
                            f"Godzamok combo rebuy aborting building={self.pending['building_name']} "
                            f"quantity={self.pending['quantity']} amount={building['amount']} "
                            f"target={self.pending['initial_amount']}"
                        )
                        self.pending["phase"] = "reset_store"
                        return None
                    self.pending["phase"] = "rebuy_setup"
                    return None
            if (
                bool(state.get("building_autobuy_enabled"))
                and (now - rebuy_started_at) >= GODZAMOK_REBUY_MAX_WAIT_SECONDS
                and building["amount"] < self.pending["initial_amount"]
            ):
                self.log.info(
                    f"Godzamok combo rebuy timeout deferring building={self.pending['building_name']} "
                    f"quantity={self.pending['quantity']} waited={now - rebuy_started_at:.1f}s"
                )
                self.pending["phase"] = "reset_store"
                return None
            if building["amount"] >= self.pending["initial_amount"]:
                self.log.info(
                    f"Godzamok combo rebuy complete building={self.pending['building_name']} "
                    f"quantity={self.pending['quantity']}"
                )
                self.pending["phase"] = "reset_store"
                return None
            if remaining_needed <= 0:
                self.pending["phase"] = "reset_store"
                return None
            rebuy_quantity = self._select_rebuy_quantity(remaining_needed)
            store_action = self.store.plan_buy(
                snapshot,
                to_screen_point,
                self.pending["building_id"],
                quantity=rebuy_quantity,
            )
            if store_action is None:
                unavailable_state = (
                    int(remaining_needed),
                    int(rebuy_quantity),
                    int(state["store"]["buy_mode"]),
                    int(state["store"]["buy_bulk"]),
                )
                if self.pending.get("rebuy_last_unavailable") != unavailable_state:
                    self.pending["rebuy_last_unavailable"] = unavailable_state
                    self.log.info(
                        f"Godzamok combo rebuy unavailable building={self.pending['building_name']} "
                        f"remaining={remaining_needed} requested={rebuy_quantity} "
                        f"store_mode={state['store']['buy_mode']} "
                        f"store_bulk={state['store']['buy_bulk']}"
                    )
                return None
            self.pending["rebuy_last_unavailable"] = None
            return self._wrap_store_action(
                store_action,
                detail="godzamok_rebuy",
                building_id=self.pending["building_id"],
                building_name=self.pending["building_name"],
                quantity=rebuy_quantity,
                expected_net=self.pending["expected_net"],
            )
        if self.pending["phase"] == "reset_store":
            reset_action = self.store.plan_reset_to_default(snapshot, to_screen_point)
            if reset_action is None:
                return None
            if reset_action.kind == "store_ready":
                self.log.info("Godzamok combo store reset complete mode=1 bulk=1")
                self.pending = None
                return None
            return self._wrap_store_action(
                reset_action,
                detail="godzamok_reset_store",
                building_id=self.pending["building_id"],
                building_name=self.pending["building_name"],
                quantity=1,
                expected_net=self.pending["expected_net"],
            )
        return None

    def _select_rebuy_quantity(self, remaining_needed):
        remaining_needed = max(1, int(remaining_needed))
        for bulk in GODZAMOK_REBUY_BULKS:
            if remaining_needed >= bulk:
                return bulk
        return 1

    def _wrap_store_action(
        self,
        store_action,
        *,
        detail,
        building_id,
        building_name,
        quantity,
        expected_net,
    ):
        return GodzamokAction(
            kind=store_action.kind,
            screen_x=store_action.screen_x,
            screen_y=store_action.screen_y,
            detail=detail,
            building_id=building_id,
            building_name=building_name,
            quantity=quantity,
            expected_net=expected_net,
            store_mode=store_action.store_mode,
            store_bulk=store_action.store_bulk,
            current_store_mode=store_action.current_store_mode,
            current_store_bulk=store_action.current_store_bulk,
        )

    def _extract_state(self, snapshot, to_screen_point):
        store_state = self.store.extract_state(snapshot, to_screen_point)
        if store_state is None:
            return None
        temple = snapshot.get("temple") if isinstance(snapshot, dict) else None
        spellbook = snapshot.get("spellbook") if isinstance(snapshot, dict) else None
        buffs = snapshot.get("buffs") if isinstance(snapshot, dict) else None
        if not isinstance(buffs, list):
            buffs = []
        ruin_level = 0
        temple_on_minigame = False
        temple_open_target = None
        if isinstance(temple, dict):
            ruin_level = int(temple.get("ruinLevel") or 0)
            temple_on_minigame = bool(temple.get("onMinigame"))
            temple_open_target = self.store._normalize_target(temple.get("openControl"), to_screen_point)
        hand_ready = False
        magic = 0.0
        max_magic = 0.0
        magic_regen_per_second = 0.0
        spells = []
        if isinstance(spellbook, dict):
            magic = float(spellbook.get("magic") or 0.0)
            max_magic = float(spellbook.get("maxMagic") or 0.0)
            magic_regen_per_second = float(spellbook.get("magicRegenPerSecond") or 0.0)
            for spell in spellbook.get("spells", []):
                if not isinstance(spell, dict):
                    continue
                rect = spell.get("rect")
                target = self.store._normalize_target(rect, to_screen_point)
                if target is None:
                    continue
                spells.append(
                    {
                        "key": spell.get("key"),
                        "name": spell.get("name"),
                        "cost": None if spell.get("cost") is None else float(spell.get("cost")),
                        "fail_chance": None if spell.get("failChance") is None else float(spell.get("failChance")),
                        "ready": bool(spell.get("ready")),
                        "screen_x": target["screen_x"],
                        "screen_y": target["screen_y"],
                    }
                )
            hand_spell = next((spell for spell in spells if spell.get("key") == HAND_OF_FATE_KEY), None)
            hand_ready = hand_spell is not None and bool(hand_spell.get("ready"))
        else:
            hand_spell = None
        buff_names = {buff.get("name") for buff in buffs if isinstance(buff, dict) and buff.get("name")}
        combo_eval = evaluate_combo_buffs(buff_names)
        return {
            "buildings": store_state["buildings"],
            "store": store_state["store"],
            "cookies": float(snapshot.get("cookies") or 0.0),
            "cookies_ps": float(snapshot.get("cookiesPs") or 0.0),
            "building_autobuy_enabled": bool(snapshot.get("_building_autobuy_enabled", False)),
            "ruin_level": ruin_level,
            "ruin_bonus_per_sale": GODZAMOK_CLICK_BONUS_BY_LEVEL.get(ruin_level, 0.0),
            "temple_on_minigame": temple_on_minigame,
            "temple_open_target": temple_open_target,
            "buffs": [buff for buff in buffs if isinstance(buff, dict)],
            "buff_names": buff_names,
            "computed_mouse_cps": float(snapshot.get("computedMouseCps") or 0.0),
            "magic": magic,
            "max_magic": max_magic,
            "magic_regen_per_second": magic_regen_per_second,
            "hand_ready": hand_ready,
            "hand_spell": hand_spell,
            "spells_by_key": {spell["key"]: spell for spell in spells if spell.get("key")},
            "combo_eval": combo_eval,
            "sell_retain_floors": self._build_sell_retain_floors(snapshot, store_state["buildings"]),
        }

    def _find_candidate(self, state):
        bonus_per_sale = float(state.get("ruin_bonus_per_sale") or 0.0)
        if bonus_per_sale <= 0:
            return None
        if state["computed_mouse_cps"] <= 0:
            return None
        if not state.get("combo_eval", {}).get("should_fire_godzamok"):
            return None

        click_rate = 0.0 if self.click_interval <= 0 else (1.0 / self.click_interval) * CLICK_RATE_SAFETY
        current_cookies = max(0.0, float(state.get("cookies") or 0.0))
        best_autobuy = self._find_best_autobuy_candidate(state)
        best = None
        for building in state["buildings"].values():
            if building["name"] in EXCLUDED_BUILDINGS:
                continue
            if not building["can_sell"]:
                continue
            if building["amount"] <= 0:
                continue
            retain_floor = max(0, int(state.get("sell_retain_floors", {}).get(building["name"], 0)))
            for quantity in COMBO_SELL_QUANTITIES:
                if building["amount"] < quantity:
                    continue
                if (int(building["amount"]) - int(quantity)) < retain_floor:
                    continue
                rebuy_cost = self._estimate_rebuy_cost(building, quantity)
                if rebuy_cost is None or rebuy_cost <= 0:
                    continue
                round_trip_cost = self._estimate_round_trip_cost(building, quantity)
                if round_trip_cost <= 0 or current_cookies + 1e-9 < round_trip_cost:
                    continue
                pixies_plan = self._plan_pixies_for_rebuy(state, building, quantity)
                adjusted_round_trip_cost = round_trip_cost - pixies_plan["expected_savings"]
                devastation_mult = 1.0 + (bonus_per_sale * quantity)
                extra_click_gain = state["computed_mouse_cps"] * (devastation_mult - 1.0) * click_rate * GODZAMOK_BUFF_SECONDS
                lost_cps_cost = max(0.0, float(building.get("stored_cps") or 0.0)) * quantity * GODZAMOK_BUFF_SECONDS
                net_profit = extra_click_gain - round_trip_cost - lost_cps_cost
                if extra_click_gain <= 0:
                    continue
                if net_profit <= (round_trip_cost * (PROFIT_MARGIN_MULTIPLIER - 1.0)):
                    continue
                if not self._projected_rebuy_quantity_is_competitive(
                    state,
                    building,
                    quantity,
                    best_autobuy=best_autobuy,
                    allow_pixies=pixies_plan["should_cast"],
                ):
                    continue
                score = (net_profit, -adjusted_round_trip_cost, quantity)
                if best is None or score > best["score"]:
                    best = {
                        "score": score,
                        "building_id": building["id"],
                        "building_name": building["name"],
                        "amount": building["amount"],
                        "quantity": quantity,
                        "extra_click_gain": extra_click_gain,
                        "round_trip_cost": round_trip_cost,
                        "rebuy_cost": rebuy_cost,
                        "net_profit": net_profit,
                        "pixies_planned": pixies_plan["should_cast"],
                        "pixies_expected_savings": pixies_plan["expected_savings"],
                        "pixies_fail_chance": pixies_plan["fail_chance"],
                    }
        return best

    def _estimate_round_trip_cost(self, building, quantity):
        price = float(building.get("price") or 0.0)
        sell_multiplier = float(building.get("sell_multiplier") or 0.25)
        if price <= 0 or quantity <= 0:
            return 0.0
        geometric_sum = 0.0
        for step in range(1, int(quantity) + 1):
            geometric_sum += price / math.pow(PRICE_INCREASE, step)
        return geometric_sum * max(0.0, 1.0 - sell_multiplier)

    def _choose_rebuy_strategy(self, state, building):
        rebuy_payback = self._estimate_rebuy_payback_seconds(
            state,
            building,
            self.pending["quantity"],
            allow_pixies=bool(self.pending.get("pixies_planned")),
        )
        best_autobuy = self._find_best_autobuy_candidate(state)
        if not bool(state.get("building_autobuy_enabled")):
            return {
                "strategy": "rebuy",
                "rebuy_payback_seconds": rebuy_payback,
                "best_autobuy_name": None if best_autobuy is None else best_autobuy["name"],
                "best_autobuy_payback_seconds": None if best_autobuy is None else best_autobuy["payback_seconds"],
            }
        if rebuy_payback is None:
            return {
                "strategy": "defer",
                "rebuy_payback_seconds": None,
                "best_autobuy_name": None if best_autobuy is None else best_autobuy["name"],
                "best_autobuy_payback_seconds": None if best_autobuy is None else best_autobuy["payback_seconds"],
            }
        if best_autobuy is None:
            return {
                "strategy": "rebuy",
                "rebuy_payback_seconds": rebuy_payback,
                "best_autobuy_name": None,
                "best_autobuy_payback_seconds": None,
            }
        if best_autobuy["id"] == building["id"]:
            return {
                "strategy": "rebuy",
                "rebuy_payback_seconds": rebuy_payback,
                "best_autobuy_name": best_autobuy["name"],
                "best_autobuy_payback_seconds": best_autobuy["payback_seconds"],
            }
        if rebuy_payback <= (best_autobuy["payback_seconds"] * GODZAMOK_REBUY_PAYBACK_TOLERANCE):
            strategy = "rebuy"
        else:
            strategy = "defer"
        return {
            "strategy": strategy,
            "rebuy_payback_seconds": rebuy_payback,
            "best_autobuy_name": best_autobuy["name"],
            "best_autobuy_payback_seconds": best_autobuy["payback_seconds"],
        }

    def _estimate_rebuy_payback_seconds(self, state, building, quantity, allow_pixies=False):
        cost = self._estimate_rebuy_cost(building, quantity)
        if cost is None or cost <= 0:
            return None
        if allow_pixies:
            cost -= self._plan_pixies_for_rebuy(state, building, quantity)["expected_savings"]
        restored_cps = max(0.0, float(building.get("stored_cps") or 0.0)) * max(1, int(quantity))
        if restored_cps <= 0:
            return None
        return cost / restored_cps

    def _projected_rebuy_quantity_is_competitive(
        self,
        state,
        building,
        quantity,
        *,
        best_autobuy,
        allow_pixies=False,
    ):
        if best_autobuy is None:
            return True
        projected_payback = self._estimate_projected_rebuy_payback_seconds(
            building,
            quantity,
            allow_pixies=allow_pixies,
        )
        if projected_payback is None:
            return False
        if int(best_autobuy.get("id") or -1) == int(building.get("id") or -2):
            return True
        return projected_payback <= (float(best_autobuy["payback_seconds"]) * GODZAMOK_REBUY_PAYBACK_TOLERANCE)

    def _estimate_projected_rebuy_payback_seconds(self, building, quantity, allow_pixies=False):
        cost = self._estimate_projected_rebuy_cost(building, quantity)
        if cost is None or cost <= 0:
            return None
        if allow_pixies:
            cost *= CRAFTY_PIXIES_PRICE_FACTOR
        restored_cps = max(0.0, float(building.get("stored_cps") or 0.0)) * max(1, int(quantity))
        if restored_cps <= 0:
            return None
        return cost / restored_cps

    def _estimate_projected_rebuy_cost(self, building, quantity):
        quantity = max(1, int(quantity))
        current_price = float(building.get("price") or 0.0)
        if current_price <= 0:
            return None
        cost = 0.0
        for step in range(quantity):
            cost += current_price / math.pow(PRICE_INCREASE, quantity - 1 - step)
        return cost if math.isfinite(cost) and cost > 0 else None

    def _estimate_rebuy_cost(self, building, quantity):
        quantity = int(quantity)
        if quantity <= 1:
            value = building.get("price")
        elif quantity <= 10:
            value = building.get("sum_price_10")
        elif quantity <= 100:
            value = building.get("sum_price_100")
        else:
            value = None
        if value is None:
            return None
        cost = float(value)
        return cost if math.isfinite(cost) and cost > 0 else None

    def _find_best_autobuy_candidate(self, state):
        reserve = self._calculate_building_reserve(state["cookies"], state["cookies_ps"])
        spendable = float(state["cookies"]) - reserve
        if spendable <= 0:
            return None

        candidates = []
        for building in state["buildings"].values():
            if building["target"] is None:
                continue
            if not building["can_buy"]:
                continue
            price = float(building.get("price") or 0.0)
            delta_cps = max(0.0, float(building.get("stored_cps") or 0.0))
            if price <= 0 or delta_cps <= 0 or spendable < price:
                continue
            candidates.append(
                {
                    "id": building["id"],
                    "name": building["name"],
                    "price": price,
                    "delta_cps": delta_cps,
                    "payback_seconds": price / delta_cps,
                }
            )

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item["payback_seconds"], item["price"], item["id"]))
        return candidates[0]

    def _calculate_building_reserve(self, cookies, cookies_ps):
        cps_reserve = max(0.0, float(cookies_ps)) * DEFAULT_RESERVE_CPS_SECONDS
        cap_floor = max(0.0, float(cookies)) * max(0.0, 1.0 - MAX_BUILDING_SPEND_RATIO)
        return max(DEFAULT_RESERVE_COOKIES, cps_reserve, cap_floor)

    def _plan_pixies_for_rebuy(self, state, building, quantity):
        rebuy_cost = self._estimate_rebuy_cost(building, quantity)
        if rebuy_cost is None or rebuy_cost <= 0:
            return {"should_cast": False, "expected_savings": 0.0, "fail_chance": None}
        buff_names = state.get("buff_names") or set()
        if CRAFTY_PIXIES_BUFF in buff_names:
            return {"should_cast": False, "expected_savings": 0.0, "fail_chance": 0.0}
        pixies_spell = state.get("spells_by_key", {}).get(CRAFTY_PIXIES_KEY)
        if pixies_spell is None:
            return {"should_cast": False, "expected_savings": 0.0, "fail_chance": None}
        spell_cost = pixies_spell.get("cost")
        if spell_cost is None or self._estimate_magic_at_rebuy(state) + 1e-9 < float(spell_cost):
            return {"should_cast": False, "expected_savings": 0.0, "fail_chance": pixies_spell.get("fail_chance")}
        fail_chance = float(pixies_spell.get("fail_chance") or 0.0)
        success_factor = self._crafty_pixies_success_factor(state)
        failure_factor = self._crafty_pixies_failure_factor(state)
        expected_modifier = ((1.0 - fail_chance) * success_factor) + (fail_chance * failure_factor)
        expected_savings = rebuy_cost * max(0.0, 1.0 - expected_modifier)
        return {
            "should_cast": expected_savings > 0.0,
            "expected_savings": expected_savings,
            "fail_chance": fail_chance,
        }

    def _estimate_magic_at_rebuy(self, state):
        current_magic = max(0.0, float(state.get("magic") or 0.0))
        max_magic = max(0.0, float(state.get("max_magic") or 0.0))
        regen = max(0.0, float(state.get("magic_regen_per_second") or 0.0))
        return min(max_magic, current_magic + (regen * GODZAMOK_BUFF_SECONDS))

    def _crafty_pixies_success_factor(self, state):
        buff_names = state.get("buff_names") or set()
        if NASTY_GOBLINS_BUFF in buff_names:
            return CRAFTY_PIXIES_PRICE_FACTOR / NASTY_GOBLINS_PRICE_FACTOR
        return CRAFTY_PIXIES_PRICE_FACTOR

    def _crafty_pixies_failure_factor(self, state):
        buff_names = state.get("buff_names") or set()
        if NASTY_GOBLINS_BUFF in buff_names:
            return 1.0
        return NASTY_GOBLINS_PRICE_FACTOR

    def _can_cast_pixies_now(self, state):
        pixies_spell = state.get("spells_by_key", {}).get(CRAFTY_PIXIES_KEY)
        return pixies_spell is not None and bool(pixies_spell.get("ready"))

    def _combo_block_reason(self, state):
        if float(state.get("ruin_bonus_per_sale") or 0.0) <= 0:
            return "godzamok_not_slotted"
        if self._should_open_temple(state):
            return "temple_closed_can_open"
        if self._get_spell_action(state) is not None:
            return "hand_of_fate_prep"
        if state["computed_mouse_cps"] <= 0:
            return "no_click_value"
        combo_eval = state.get("combo_eval", {})
        if not combo_eval.get("can_spawn_click_buff") and not combo_eval.get("should_fire_godzamok"):
            return "waiting_for_combo_stack"
        if not combo_eval.get("should_fire_godzamok"):
            return "waiting_for_click_stack"
        if not self._has_sellable_building_above_floor(state):
            return "combo_blocked_by_sell_floor"
        return "combo_not_profitable"

    def _should_open_temple(self, state):
        if not isinstance(state, dict):
            return False
        if state.get("temple_on_minigame"):
            return False
        if state.get("temple_open_target") is None:
            return False
        return float(state.get("ruin_bonus_per_sale") or 0.0) > 0.0

    def _has_sellable_building_above_floor(self, state):
        floors = state.get("sell_retain_floors", {})
        for building in state.get("buildings", {}).values():
            if building["name"] in EXCLUDED_BUILDINGS:
                continue
            if not building.get("can_sell"):
                continue
            amount = int(building.get("amount") or 0)
            if amount <= 0:
                continue
            retain_floor = max(0, int(floors.get(building["name"], 0)))
            if amount > retain_floor:
                return True
        return False

    def _build_sell_retain_floors(self, snapshot, buildings):
        floors = dict(MINIGAME_BUILDING_RETAIN_FLOORS)
        if not isinstance(snapshot, dict):
            return floors
        dragon = snapshot.get("dragon")
        if not isinstance(dragon, dict):
            return floors
        next_cost_type = dragon.get("nextCostType")
        if next_cost_type == "building_sacrifice":
            building_name = dragon.get("nextRequiredBuildingName")
            required_amount = dragon.get("nextRequiredBuildingAmount")
            if building_name and isinstance(required_amount, (int, float)):
                floors[str(building_name)] = max(
                    int(floors.get(str(building_name), 0)),
                    max(0, int(required_amount)),
                )
        elif next_cost_type == "special":
            required_amount = self._parse_dragon_all_buildings_requirement(dragon.get("nextCostText"))
            if required_amount is not None:
                for building in buildings.values():
                    name = building.get("name")
                    if not name:
                        continue
                    floors[str(name)] = max(int(floors.get(str(name), 0)), required_amount)
        return floors

    def _parse_dragon_all_buildings_requirement(self, next_cost_text):
        if not isinstance(next_cost_text, str):
            return None
        if "every building" not in next_cost_text.lower():
            return None
        match = re.search(r"(\d+)", next_cost_text)
        if not match:
            return None
        return max(0, int(match.group(1)))

    def _get_spell_action(self, state):
        if float(state.get("ruin_bonus_per_sale") or 0.0) <= 0:
            return None
        if not state["hand_ready"] or not state.get("hand_spell"):
            return None
        buff_names = state.get("buff_names") or set()
        if buff_names & CLICK_STACK_BUFF_KEYS:
            return None
        combo_eval = state.get("combo_eval", evaluate_combo_buffs(buff_names))
        if not combo_eval.get("can_spawn_click_buff"):
            return None
        hand = state["hand_spell"]
        return GodzamokAction(
            kind="cast_spell",
            screen_x=int(hand["screen_x"]),
            screen_y=int(hand["screen_y"]),
            detail="godzamok_hand_of_fate",
        )
