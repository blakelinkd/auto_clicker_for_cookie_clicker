from dataclasses import dataclass
import time

from clicker_bot.features.combo_evaluator import VALUABLE_BUFF_KEYS, evaluate_combo_buffs
HAND_OF_FATE_KEY = "hand of fate"
HAGGLERS_CHARM_KEY = "haggler's charm"
STRETCH_TIME_KEY = "stretch time"
RESURRECT_ABOMINATION_KEY = "resurrect abomination"
CRAFTY_PIXIES_KEY = "summon crafty pixies"
CRAFTY_PIXIES_BUFF = "Crafty pixies"
NASTY_GOBLINS_BUFF = "Nasty goblins"
CRAFTY_PIXIES_PRICE_FACTOR = 0.98
NASTY_GOBLINS_PRICE_FACTOR = 1.02
HAND_OF_FATE_CLICK_OUTCOMES = {"click frenzy"}
HAND_OF_FATE_ECONOMIC_OUTCOMES = {
    "building special",
    "click frenzy",
    "frenzy",
    "dragon harvest",
}
HAND_OF_FATE_STACKABLE_OUTCOME_BUFFS = {
    "building special": "Building special",
    "click frenzy": "Click frenzy",
    "dragon harvest": "Dragon Harvest",
    "dragonflight": "Dragonflight",
    "frenzy": "Frenzy",
}
RESERVED_STEP_SPELL_KEYS = {
    HAND_OF_FATE_KEY,
    STRETCH_TIME_KEY,
    RESURRECT_ABOMINATION_KEY,
}
DISALLOWED_STEP_SPELL_KEYS = {
    "gambler's fever dream",
    "spontaneous edifice",
}
PRODUCTION_TRIGGER_BUFFS = {
    "Frenzy",
    "Dragon Harvest",
    "Elder frenzy",
    "Building special",
}
STRETCH_ECONOMIC_BUFFS = {
    "Click frenzy",
    "Cookie storm",
    "Cursed finger",
    "Dragonflight",
    "Dragon Harvest",
    "Elder frenzy",
    "Building special",
    "Frenzy",
}
STRETCH_TARGET_BUFFS = STRETCH_ECONOMIC_BUFFS
STRETCH_TIME_MIN_REMAINING = 3.0
STACKED_STRETCH_TIME_REMAINING_BY_BUFF = {
    "Building special": 12.0,
    "Click frenzy": 5.0,
    "Dragon Harvest": 10.0,
    "Dragonflight": 5.0,
    "Elder frenzy": 4.0,
    "Frenzy": 10.0,
}
CRAFTY_PIXIES_MIN_COOKIES_RATIO = 0.75
CRAFTY_PIXIES_MIN_CPS_SECONDS = 180.0


@dataclass
class SpellAction:
    kind: str
    key: str
    name: str
    screen_x: int
    screen_y: int
    cost: float | None = None
    magic: float | None = None
    max_magic: float | None = None
    reason: str | None = None


class SpellAutocaster:
    def __init__(self, log):
        self.log = log
        self.last_cast_by_key = {}
        self.cast_count = 0
        self.last_spell_summary = None
        self.pending_hand_cookie = None

    def get_action(self, snapshot, to_screen_point, now=None, building_diag=None):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None

        now = time.monotonic() if now is None else now
        if not state["on_minigame"]:
            if self._should_open_grimoire(state, now, building_diag):
                return SpellAction(
                    kind="open_grimoire",
                    key="open_grimoire",
                    name="Open Grimoire",
                    screen_x=state["open_target"]["screen_x"],
                    screen_y=state["open_target"]["screen_y"],
                    magic=state["magic"],
                    max_magic=state["max_magic"],
                    reason="open_grimoire",
                )
            return None

        hand = state["spells_by_key"].get(HAND_OF_FATE_KEY)
        if self._can_cast_hand_of_fate(state, hand, now):
            forecast = state.get("hand_of_fate_forecast") or {}
            outcome = forecast.get("outcome")
            return SpellAction(
                kind="cast_spell",
                key=hand["key"],
                name=hand["name"],
                screen_x=hand["screen_x"],
                screen_y=hand["screen_y"],
                cost=hand["cost"],
                magic=state["magic"],
                max_magic=state["max_magic"],
                reason=f"spawn_{str(outcome).replace(' ', '_')}" if outcome else "spawn_shimmer",
            )

        return None

    def get_diagnostics(self, snapshot, to_screen_point, building_diag=None):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return {"available": False, "reason": "no_spellbook_data"}

        hand = state["spells_by_key"].get(HAND_OF_FATE_KEY)
        valuable_buffs = [buff["name"] for buff in state["buffs"] if self._is_valuable_buff(buff["name"])]
        long_running_buffs = self._get_long_running_buffs(state)
        combo_eval = evaluate_combo_buffs(
            {buff["name"] for buff in state["buffs"]},
            spell_ready=bool(hand and hand.get("ready")),
        )
        hand_forecast = state.get("hand_of_fate_forecast") or {}
        reactive_stack = self._has_reactive_combo_stack(state)
        now = time.monotonic()
        hand_castable = self._can_cast_hand_of_fate(state, hand, now)

        reason = "no_spell_signal"
        candidate = None
        if not state["on_minigame"]:
            reason = "grimoire_closed"
        elif hand_castable:
            reason = "hand_of_fate_ready_on_long_buff"
            candidate = hand_forecast.get("outcome") or hand["name"]
        elif hand is None:
            reason = "hand_of_fate_missing"
        elif not long_running_buffs:
            reason = "waiting_for_long_buff"
            candidate = hand_forecast.get("outcome") or hand["name"]
        elif self._recently_cast(hand["key"], now, cooldown=1.5):
            reason = "hand_of_fate_recently_cast"
            candidate = hand_forecast.get("outcome") or hand["name"]
        elif not hand.get("ready") or not self._has_enough_magic(state, hand):
            reason = "waiting_for_hand_of_fate_mana"
            candidate = hand_forecast.get("outcome") or hand["name"]

        return {
            "available": True,
            "reason": reason,
            "on_minigame": state["on_minigame"],
            "has_open_target": state["open_target"] is not None,
            "magic": state["magic"],
            "max_magic": state["max_magic"],
            "spells_total": len(state["spells"]),
            "ready_spells": sum(1 for spell in state["spells"] if spell["ready"]),
            "valuable_buffs": tuple(valuable_buffs),
            "combo_stage": combo_eval["stage"],
            "combo_phase": combo_eval["phase"],
            "hand_of_fate_outcome": hand_forecast.get("outcome"),
            "hand_of_fate_backfire": hand_forecast.get("backfire"),
            "hand_of_fate_fail_chance": hand_forecast.get("failChance"),
            "hand_of_fate_cast_index": hand_forecast.get("castIndex"),
            "hand_of_fate_target_offset": None,
            "hand_of_fate_target_outcome": None,
            "spell_advance_ready": None,
            "stretch_time_target": None,
            "reactive_combo_stack": reactive_stack,
            "candidate": candidate,
            "long_running_buffs": tuple(buff["name"] for buff in long_running_buffs),
            "crafty_pixies_target": None,
            "crafty_pixies_expected_savings": None,
            "crafty_pixies_target_price": None,
            "wrinklers_active": state["wrinklers_active"],
            "wrinklers_attached": state["wrinklers_attached"],
            "wrinklers_max": state["wrinklers_max"],
            "wrinklers_open_slots": state["wrinklers_open_slots"],
            "elder_wrath": state["elder_wrath"],
        }

    def record_action(self, action):
        cast_at = time.monotonic()
        self.last_cast_by_key[action.key] = cast_at
        self.cast_count += 1
        self.last_spell_summary = f"{action.name} ({action.reason})"
        if action.key == HAND_OF_FATE_KEY:
            self.pending_hand_cookie = {
                "cast_at": cast_at,
                "expected_outcome": action.reason.removeprefix("spawn_").replace("_", " "),
                "target_shimmer_id": None,
            }
        self.log.info(
            f"Spell cast click key={action.key} name={action.name} "
            f"magic={0.0 if action.magic is None else action.magic:.1f}/"
            f"{0.0 if action.max_magic is None else action.max_magic:.1f} "
            f"cost={0.0 if action.cost is None else action.cost:.1f} "
            f"reason={action.reason}"
        )

    def extract_state(self, snapshot, to_screen_point):
        if not snapshot or not isinstance(snapshot, dict):
            return None
        spellbook = snapshot.get("spellbook")
        if not isinstance(spellbook, dict):
            return None
        wrinklers = snapshot.get("wrinklers")
        if not isinstance(wrinklers, dict):
            wrinklers = {}

        spells = []
        for spell in spellbook.get("spells", []):
            if not isinstance(spell, dict):
                continue
            rect = spell.get("rect")
            screen_x = None
            screen_y = None
            if isinstance(rect, dict):
                center_x = rect.get("centerX")
                center_y = rect.get("centerY")
                if center_x is not None and center_y is not None:
                    mapped_x, mapped_y = to_screen_point(center_x, center_y)
                    screen_x = int(mapped_x)
                    screen_y = int(mapped_y)
            spells.append(
                {
                    "id": spell.get("id"),
                    "key": spell.get("key"),
                    "name": spell.get("name"),
                    "cost": None if spell.get("cost") is None else float(spell.get("cost")),
                    "fail_chance": None
                    if spell.get("failChance") is None
                    else float(spell.get("failChance")),
                    "ready": bool(spell.get("ready")),
                    "screen_x": screen_x,
                    "screen_y": screen_y,
                }
            )

        buffs = []
        for buff in spellbook.get("activeBuffs", []):
            if not isinstance(buff, dict):
                continue
            buffs.append(
                {
                    "key": buff.get("key"),
                    "name": buff.get("name") or buff.get("key"),
                    "type": buff.get("type"),
                    "building_id": buff.get("buildingId"),
                    "building_name": buff.get("buildingName"),
                    "mult_cps": None if buff.get("multCpS") is None else float(buff.get("multCpS")),
                    "time": None if buff.get("time") is None else float(buff.get("time")),
                    "max_time": None if buff.get("maxTime") is None else float(buff.get("maxTime")),
                }
            )

        return {
            "on_minigame": bool(spellbook.get("onMinigame")),
            "open_target": self._normalize_target(spellbook.get("openControl"), to_screen_point),
            "magic": float(spellbook.get("magic", 0.0)),
            "max_magic": float(spellbook.get("maxMagic", 0.0)),
            "spells_cast": None if spellbook.get("spellsCast") is None else int(spellbook.get("spellsCast")),
            "spells_cast_total": None
            if spellbook.get("spellsCastTotal") is None
            else int(spellbook.get("spellsCastTotal")),
            "spells": spells,
            "spells_by_key": {spell["key"]: spell for spell in spells if spell.get("key")},
            "buffs": buffs,
            "hand_of_fate_forecast": spellbook.get("handOfFateForecast")
            if isinstance(spellbook.get("handOfFateForecast"), dict)
            else None,
            "spell_forecasts": spellbook.get("spellForecasts")
            if isinstance(spellbook.get("spellForecasts"), list)
            else [],
            "elder_wrath": int(wrinklers.get("elderWrath") or 0),
            "wrinklers_active": int(wrinklers.get("active") or 0),
            "wrinklers_attached": int(wrinklers.get("attached") or 0),
            "wrinklers_max": int(wrinklers.get("max") or 0),
            "wrinklers_open_slots": int(wrinklers.get("openSlots") or 0),
        }

    def _should_open_grimoire(self, state, now, building_diag=None):
        if not isinstance(state, dict) or state.get("on_minigame"):
            return False
        return state.get("open_target") is not None

    def _normalize_target(self, rect, to_screen_point):
        if not isinstance(rect, dict):
            return None
        center_x = rect.get("centerX")
        center_y = rect.get("centerY")
        if center_x is None or center_y is None:
            return None
        screen_x, screen_y = to_screen_point(center_x, center_y)
        return {
            "screen_x": int(screen_x),
            "screen_y": int(screen_y),
        }

    def _can_cast_hand_of_fate(self, state, spell, now):
        if spell is None or not spell["ready"]:
            return False
        if self._recently_cast(spell["key"], now, cooldown=1.5):
            return False
        if not self._has_enough_magic(state, spell):
            return False
        return bool(self._get_long_running_buffs(state))

    def _has_enough_magic(self, state, spell):
        cost = spell.get("cost")
        if cost is None:
            return True
        return float(state.get("magic") or 0.0) + 1e-9 >= float(cost)

    def _get_long_running_buffs(self, state):
        long_buffs = []
        for buff in state.get("buffs") or []:
            remaining = buff.get("time")
            if remaining is None:
                continue
            if float(remaining) > 5.0:
                long_buffs.append(buff)
        return long_buffs

    def _can_cast_haggler_step(self, state, advance_plan, now):
        if self._has_click_combo_buff(state):
            return False
        if not (advance_plan and advance_plan.get("actionable")):
            return False
        spell = advance_plan.get("step_spell")
        if not isinstance(spell, dict) or not spell.get("ready"):
            return False
        if self._recently_cast(spell["key"], now, cooldown=1.5):
            return False
        return True

    def _can_cast_stretch_time(self, state, spell, now, defer_for_hand=False):
        if spell is None or not spell["ready"]:
            return False
        if self._recently_cast(spell["key"], now, cooldown=1.5):
            return False
        if defer_for_hand:
            return False
        return self._get_stretch_time_target(state) is not None

    def _can_cast_crafty_pixies(self, state, spell, plan, now):
        if spell is None or not spell["ready"] or not isinstance(plan, dict):
            return False
        if self._recently_cast(spell["key"], now, cooldown=1.5):
            return False
        if any(
            self._is_valuable_buff(buff["name"])
            for buff in state["buffs"]
            if buff.get("name") not in PRODUCTION_TRIGGER_BUFFS
        ):
            return False
        if self._has_reactive_combo_stack(state):
            if not plan.get("triggered_by_building_buff"):
                return False
        if self._has_click_combo_buff(state):
            return False
        return True

    def _is_valuable_buff(self, name):
        return bool(name) and name in VALUABLE_BUFF_KEYS

    def _has_reactive_combo_stack(self, state):
        buff_names = {buff["name"] for buff in state["buffs"]}
        production_buffs = buff_names & PRODUCTION_TRIGGER_BUFFS
        return bool(production_buffs)

    def _has_click_combo_buff(self, state):
        buff_names = {buff["name"] for buff in state["buffs"]}
        return bool(buff_names & {"Click frenzy", "Dragonflight"})

    def _is_stackable_hand_of_fate_combo(self, buff_names, outcome):
        active_production_buffs = set(buff_names) & PRODUCTION_TRIGGER_BUFFS
        if not active_production_buffs:
            return False
        target_buff = HAND_OF_FATE_STACKABLE_OUTCOME_BUFFS.get(outcome)
        if target_buff is None:
            return False
        if outcome == "dragonflight" and "Click frenzy" in buff_names:
            return False
        if outcome in {"click frenzy", "dragonflight"}:
            return True
        return target_buff not in buff_names

    def _get_crafty_pixies_plan(self, state, building_diag):
        if not isinstance(building_diag, dict):
            return None
        if int(building_diag.get("store_buy_mode") or 0) != 1:
            return None
        if int(building_diag.get("store_buy_bulk") or 0) != 1:
            return None
        building_name = building_diag.get("candidate")
        if not building_name:
            return None
        price = building_diag.get("candidate_price")
        if not isinstance(price, (int, float)) or float(price) <= 0:
            return None
        active_building_buffs = building_diag.get("active_building_buffs") or ()
        matched_building_buff = next(
            (
                buff
                for buff in active_building_buffs
                if isinstance(buff, dict)
                and buff.get("type") == "building buff"
                and buff.get("building_name") == building_name
            ),
            None,
        )
        reason = building_diag.get("reason")
        dragon_target = building_diag.get("dragon_target") or {}
        dragon_match = bool(
            reason == "dragon_building_floor_ready"
            and building_name == dragon_target.get("building_name")
        )
        if not dragon_match and matched_building_buff is None:
            return None
        cookies = max(0.0, float(building_diag.get("cookies") or 0.0))
        cookies_ps = max(0.0, float(building_diag.get("cookies_ps") or 0.0))
        minimum_price = max(
            cookies * CRAFTY_PIXIES_MIN_COOKIES_RATIO,
            cookies_ps * CRAFTY_PIXIES_MIN_CPS_SECONDS,
        )
        if float(price) < minimum_price:
            return None
        buff_names = {buff["name"] for buff in state["buffs"]}
        if CRAFTY_PIXIES_BUFF in buff_names or NASTY_GOBLINS_BUFF in buff_names:
            return None
        pixies_spell = state.get("spells_by_key", {}).get(CRAFTY_PIXIES_KEY)
        if pixies_spell is None:
            return None
        spell_cost = pixies_spell.get("cost")
        if not isinstance(spell_cost, (int, float)) or float(state.get("magic") or 0.0) + 1e-9 < float(spell_cost):
            return None
        fail_chance = float(pixies_spell.get("fail_chance") or 0.0)
        success_factor = self._crafty_pixies_success_factor(buff_names)
        failure_factor = self._crafty_pixies_failure_factor(buff_names)
        expected_modifier = ((1.0 - fail_chance) * success_factor) + (fail_chance * failure_factor)
        expected_savings = float(price) * max(0.0, 1.0 - expected_modifier)
        if expected_savings <= 0.0:
            return None
        return {
            "building_name": building_name,
            "price": float(price),
            "expected_savings": expected_savings,
            "triggered_by_building_buff": matched_building_buff is not None,
            "triggered_by_dragon_target": dragon_match,
            "buff_name": None if matched_building_buff is None else matched_building_buff.get("buff_name"),
        }

    def _is_positive_hand_of_fate_forecast(self, forecast):
        if not isinstance(forecast, dict):
            return False
        if forecast.get("backfire"):
            return False
        return str(forecast.get("outcome") or "").lower() in HAND_OF_FATE_ECONOMIC_OUTCOMES

    def _get_hand_of_fate_advance_plan(self, state, combo_eval):
        if not combo_eval.get("can_spawn_click_buff"):
            return None

        forecasts = state.get("spell_forecasts")
        if not isinstance(forecasts, list):
            return None

        step_candidates = self._get_step_spell_candidates(state)
        if not step_candidates:
            return None

        for entry in forecasts:
            if not isinstance(entry, dict):
                continue
            target_offset = int(entry.get("offset") or 0)
            if target_offset <= 0:
                continue
            hand_forecast = entry.get("handOfFate")
            if not isinstance(hand_forecast, dict):
                continue
            if hand_forecast.get("backfire"):
                continue
            target_outcome = hand_forecast.get("outcome")
            if target_outcome not in HAND_OF_FATE_CLICK_OUTCOMES:
                continue

            safe_steps = True
            for step in range(target_offset):
                prior_entry = forecasts[step] if step < len(forecasts) else None
                if not isinstance(prior_entry, dict):
                    safe_steps = False
                    break
                if self._choose_safe_step_spell(prior_entry, step_candidates) is None:
                    safe_steps = False
                    break
            if not safe_steps:
                continue

            step_spell = self._choose_safe_step_spell(forecasts[0], step_candidates)
            if step_spell is None:
                continue

            return {
                "target_offset": target_offset,
                "target_outcome": target_outcome,
                "actionable": True,
                "step_spell": step_spell,
            }

        return None

    def _get_step_spell_candidates(self, state):
        spells_by_key = state.get("spells_by_key") or {}
        candidates = []
        for key, spell in spells_by_key.items():
            if not self._is_step_spell_key(key):
                continue
            candidates.append(spell)
        if not candidates:
            forecasts = state.get("spell_forecasts")
            if isinstance(forecasts, list) and any(
                isinstance(entry, dict) and isinstance(entry.get("hagglersCharm"), dict)
                for entry in forecasts
            ):
                candidates.append(
                    {
                        "key": HAGGLERS_CHARM_KEY,
                        "name": "Haggler's Charm",
                        "cost": 0.0,
                        "ready": True,
                    }
                )
        candidates.sort(key=lambda spell: (float(spell.get("cost") or float("inf")), spell.get("name") or spell.get("key") or ""))
        return candidates

    def _is_step_spell_key(self, key):
        return (
            bool(key)
            and key not in RESERVED_STEP_SPELL_KEYS
            and key not in DISALLOWED_STEP_SPELL_KEYS
        )

    def _choose_safe_step_spell(self, forecast_entry, step_candidates):
        for spell in step_candidates:
            forecast = self._get_spell_forecast(forecast_entry, spell.get("key"))
            if not isinstance(forecast, dict):
                continue
            if forecast.get("backfire"):
                continue
            return spell
        return None

    def _get_spell_forecast(self, forecast_entry, spell_key):
        if not isinstance(forecast_entry, dict) or not spell_key:
            return None
        spells = forecast_entry.get("spells")
        if isinstance(spells, dict):
            forecast = spells.get(spell_key)
            if isinstance(forecast, dict):
                return forecast
        if spell_key == HAND_OF_FATE_KEY:
            forecast = forecast_entry.get("handOfFate")
            return forecast if isinstance(forecast, dict) else None
        if spell_key == HAGGLERS_CHARM_KEY:
            forecast = forecast_entry.get("hagglersCharm")
            return forecast if isinstance(forecast, dict) else None
        return None

    def _get_stretch_time_target(self, state):
        stacked_window = self._has_stretch_combo_window(state)
        best_name = None
        best_time = None
        for buff in state["buffs"]:
            name = buff.get("name")
            remaining = buff.get("time")
            if name not in STRETCH_TARGET_BUFFS or remaining is None:
                continue
            remaining = float(remaining)
            threshold = STRETCH_TIME_MIN_REMAINING
            if stacked_window:
                threshold = max(
                    threshold,
                    float(STACKED_STRETCH_TIME_REMAINING_BY_BUFF.get(name, STRETCH_TIME_MIN_REMAINING)),
                )
            if remaining > threshold:
                continue
            if best_time is None or remaining < best_time:
                best_time = remaining
                best_name = name
        return best_name

    def _has_stretch_combo_window(self, state):
        buff_names = {buff["name"] for buff in state["buffs"] if buff.get("name")}
        production_buffs = buff_names & PRODUCTION_TRIGGER_BUFFS
        click_buffs = buff_names & {"Click frenzy", "Dragonflight"}
        return bool(click_buffs and production_buffs) or len(production_buffs) >= 2

    def _crafty_pixies_success_factor(self, buff_names):
        if NASTY_GOBLINS_BUFF in buff_names:
            return CRAFTY_PIXIES_PRICE_FACTOR / NASTY_GOBLINS_PRICE_FACTOR
        return CRAFTY_PIXIES_PRICE_FACTOR

    def _crafty_pixies_failure_factor(self, buff_names):
        if NASTY_GOBLINS_BUFF in buff_names:
            return 1.0
        return NASTY_GOBLINS_PRICE_FACTOR

    def _recently_cast(self, key, now, cooldown):
        last = self.last_cast_by_key.get(key)
        return last is not None and (now - last) < cooldown

    def get_runtime_stats(self):
        return {
            "cast_count": self.cast_count,
            "last_spell": self.last_spell_summary,
            "pending_hand_cookie": None
            if self.pending_hand_cookie is None
            else self.pending_hand_cookie.get("expected_outcome"),
        }

    def get_pending_hand_shimmer(self, shimmers, now=None):
        now = time.monotonic() if now is None else now
        if self.pending_hand_cookie is None:
            return None
        if not isinstance(shimmers, list) or not shimmers:
            if (now - float(self.pending_hand_cookie.get("cast_at") or now)) > 5.0:
                self.pending_hand_cookie = None
            return None
        golden_shimmers = [
            item for item in shimmers
            if isinstance(item, dict) and str(item.get("type") or "golden") == "golden"
        ]
        if not golden_shimmers:
            return None
        target_id = self.pending_hand_cookie.get("target_shimmer_id")
        if target_id is not None:
            for shimmer in golden_shimmers:
                if int(shimmer.get("id")) == int(target_id):
                    return shimmer
        target = max(golden_shimmers, key=lambda item: int(item.get("id") or 0))
        self.pending_hand_cookie["target_shimmer_id"] = int(target["id"])
        return target

    def clear_pending_hand_shimmer(self, shimmer_id=None):
        if self.pending_hand_cookie is None:
            return
        if shimmer_id is None or self.pending_hand_cookie.get("target_shimmer_id") == shimmer_id:
            self.pending_hand_cookie = None
