from dataclasses import dataclass
import time


VALUABLE_BUFF_KEYS = {
    "Frenzy",
    "Click frenzy",
    "Dragon Harvest",
    "Dragonflight",
    "Elder frenzy",
    "Building special",
}
WRINKLER_MODE_HOLD = "hold"
WRINKLER_MODE_SEASONAL_FARM = "seasonal_farm"
WRINKLER_MODE_SHINY_HUNT = "shiny_hunt"
SEASONAL_WRINKLER_SEASONS = {"halloween", "easter"}
WRINKLER_POP_CLICK_COOLDOWN = 0.16
WRINKLER_FOCUSED_POP_CLICK_COOLDOWN = 0.10
WRINKLER_MIN_CLOSE = 0.999


@dataclass
class WrinklerAction:
    wrinkler_id: int
    wrinkler_type: int
    screen_x: int
    screen_y: int
    clicks: int
    estimated_reward: float
    reason: str


class WrinklerController:
    def __init__(self, log, mode=WRINKLER_MODE_HOLD):
        self.log = log
        self.mode = mode
        self.last_click_by_id = {}
        self.goal_focus_wrinkler_id = None
        self.pop_clicks = 0
        self.last_wrinkler_summary = None

    def get_action(self, snapshot, to_screen_point, now=None, pop_goal=None):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None

        now = time.monotonic() if now is None else now
        candidate = self._pick_candidate(state, now, pop_goal=pop_goal)
        if candidate is None:
            return None

        return WrinklerAction(
            wrinkler_id=int(candidate["id"]),
            wrinkler_type=int(candidate.get("type") or 0),
            screen_x=int(candidate["screen_x"]),
            screen_y=int(candidate["screen_y"]),
            clicks=int(candidate.get("clicks") or 0),
            estimated_reward=float(candidate.get("estimated_reward") or 0.0),
            reason=str(state["reason"]),
        )

    def get_diagnostics(self, snapshot, to_screen_point, pop_goal=None):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return {"available": False, "reason": "no_wrinkler_data", "mode": self.mode}

        candidate = self._pick_candidate(state, time.monotonic(), pop_goal=pop_goal)
        bank = self._build_bank_summary(state, pop_goal=pop_goal)
        return {
            "available": True,
            "mode": self.mode,
            "reason": state["reason"],
            "season": state["season"],
            "elder_wrath": state["elder_wrath"],
            "active": state["active"],
            "attached": state["attached"],
            "max": state["max"],
            "open_slots": state["open_slots"],
            "shiny": state["shiny"],
            "valuable_buffs": tuple(state["valuable_buffs"]),
            "candidate_id": None if candidate is None else candidate["id"],
            "candidate_type": None if candidate is None else candidate["type"],
            "candidate_reward": None if candidate is None else candidate["estimated_reward"],
            "candidate_clicks": None if candidate is None else candidate["clicks"],
            "estimated_reward_total": bank["estimated_reward_total"],
            "estimated_reward_attached": bank["estimated_reward_attached"],
            "pop_goal_kind": bank["goal_kind"],
            "pop_goal_name": bank["goal_name"],
            "pop_goal_price": bank["goal_price"],
            "pop_goal_shortfall": bank["goal_shortfall"],
            "pop_goal_affordable_with_bank": bank["affordable_with_bank"],
        }

    def record_action(self, action):
        now = time.monotonic()
        self.last_click_by_id[action.wrinkler_id] = now
        if action.reason == "hold_mode":
            self.goal_focus_wrinkler_id = action.wrinkler_id
        else:
            self.goal_focus_wrinkler_id = None
        self.pop_clicks += 1
        wrinkler_kind = "shiny" if action.wrinkler_type == 1 else "normal"
        self.last_wrinkler_summary = f"{wrinkler_kind} #{action.wrinkler_id} ({action.reason})"
        self.log.info(
            f"Wrinkler click id={action.wrinkler_id} type={wrinkler_kind} "
            f"reward={action.estimated_reward:.1f} clicks={action.clicks} reason={action.reason}"
        )

    def get_runtime_stats(self):
        return {
            "pop_clicks": self.pop_clicks,
            "last_wrinkler": self.last_wrinkler_summary,
            "mode": self.mode,
        }

    def extract_state(self, snapshot, to_screen_point):
        if not snapshot or not isinstance(snapshot, dict):
            return None

        wrinklers = snapshot.get("wrinklers")
        if not isinstance(wrinklers, dict):
            return None

        raw_buffs = []
        spellbook = snapshot.get("spellbook")
        if isinstance(spellbook, dict):
            raw_buffs = spellbook.get("activeBuffs") or []

        valuable_buffs = []
        for buff in raw_buffs:
            if not isinstance(buff, dict):
                continue
            name = buff.get("name") or buff.get("key")
            if name in VALUABLE_BUFF_KEYS:
                valuable_buffs.append(name)

        parsed = []
        for item in wrinklers.get("wrinklers", []):
            if not isinstance(item, dict):
                continue
            client_x = item.get("clientX")
            client_y = item.get("clientY")
            if client_x is None or client_y is None:
                continue
            screen_x, screen_y = to_screen_point(client_x, client_y)
            parsed.append(
                {
                    "id": int(item.get("id") or 0),
                    "phase": int(item.get("phase") or 0),
                    "close": float(item.get("close") or 0.0),
                    "type": int(item.get("type") or 0),
                    "clicks": int(item.get("clicks") or 0),
                    "sucked": float(item.get("sucked") or 0.0),
                    "estimated_reward": float(item.get("estimatedReward") or 0.0),
                    "screen_x": int(screen_x),
                    "screen_y": int(screen_y),
                }
            )

        reason = "holding"
        season = snapshot.get("season")
        if self.mode == WRINKLER_MODE_HOLD:
            reason = "hold_mode"
        elif int(wrinklers.get("elderWrath") or 0) <= 0:
            reason = "elder_wrath_off"
        elif valuable_buffs:
            reason = "valuable_buff_active"
        elif self.mode == WRINKLER_MODE_SEASONAL_FARM and season not in SEASONAL_WRINKLER_SEASONS:
            reason = "season_not_farmable"
        elif self.mode == WRINKLER_MODE_SHINY_HUNT:
            reason = "shiny_hunt"
        elif self.mode == WRINKLER_MODE_SEASONAL_FARM:
            reason = "seasonal_farm"

        return {
            "mode": self.mode,
            "reason": reason,
            "season": season,
            "elder_wrath": int(wrinklers.get("elderWrath") or 0),
            "active": int(wrinklers.get("active") or 0),
            "attached": int(wrinklers.get("attached") or 0),
            "max": int(wrinklers.get("max") or 0),
            "open_slots": int(wrinklers.get("openSlots") or 0),
            "shiny": int(wrinklers.get("shiny") or 0),
            "valuable_buffs": valuable_buffs,
            "wrinklers": parsed,
        }

    def _pick_candidate(self, state, now, pop_goal=None):
        if state["elder_wrath"] <= 0:
            return None
        should_pop_for_goal = self._should_pop_for_goal(state, pop_goal=pop_goal)
        if state["valuable_buffs"] and not should_pop_for_goal:
            return None

        attached = [
            item
            for item in state["wrinklers"]
            if item["phase"] == 2 and item["close"] >= WRINKLER_MIN_CLOSE
        ]
        if not attached:
            return None

        if len(attached) > 1:
            normal_attached = [item for item in attached if int(item.get("type") or 0) != 1]
            if normal_attached:
                attached = normal_attached

        if not should_pop_for_goal:
            self.goal_focus_wrinkler_id = None
            if state["mode"] == WRINKLER_MODE_HOLD:
                return None
            if state["mode"] == WRINKLER_MODE_SEASONAL_FARM and state["season"] not in SEASONAL_WRINKLER_SEASONS:
                return None

        if state["mode"] == WRINKLER_MODE_SHINY_HUNT and not should_pop_for_goal:
            attached = [item for item in attached if item["type"] != 1]
            if not attached:
                return None

        candidates = []
        for item in attached:
            last_click = self.last_click_by_id.get(item["id"])
            item_cooldown = WRINKLER_POP_CLICK_COOLDOWN
            if should_pop_for_goal and item["id"] == self.goal_focus_wrinkler_id:
                item_cooldown = WRINKLER_FOCUSED_POP_CLICK_COOLDOWN
            if last_click is not None and (now - last_click) < item_cooldown:
                continue
            focus_bonus = 1 if should_pop_for_goal and item["id"] == self.goal_focus_wrinkler_id else 0
            if should_pop_for_goal:
                # During purchase funding, minimize time-to-liquidity and cursor travel.
                score = (
                    focus_bonus,
                    int(item.get("clicks") or 0),
                    float(item.get("estimated_reward") or 0.0),
                    -int(item["id"]),
                )
            else:
                score = (
                    float(item.get("estimated_reward") or 0.0),
                    int(item.get("clicks") or 0),
                    -int(item["id"]),
                )
            candidates.append((score, item))

        if not candidates:
            return None
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        return candidates[0][1]

    def _build_bank_summary(self, state, pop_goal=None):
        total_reward = sum(float(item.get("estimated_reward") or 0.0) for item in state["wrinklers"])
        attached_reward = sum(
            float(item.get("estimated_reward") or 0.0)
            for item in state["wrinklers"]
            if int(item.get("phase") or 0) == 2
        )
        cookies = 0.0
        goal_kind = None
        goal_name = None
        goal_price = None
        goal_shortfall = None
        affordable_with_bank = None
        if isinstance(pop_goal, dict):
            cookies = max(0.0, float(pop_goal.get("cookies") or 0.0))
            goal_kind = pop_goal.get("kind")
            goal_name = pop_goal.get("name")
            if isinstance(pop_goal.get("price"), (int, float)):
                goal_price = float(pop_goal["price"])
                goal_shortfall = max(0.0, goal_price - cookies)
                affordable_with_bank = (cookies + attached_reward) >= goal_price
        return {
            "estimated_reward_total": total_reward,
            "estimated_reward_attached": attached_reward,
            "goal_kind": goal_kind,
            "goal_name": goal_name,
            "goal_price": goal_price,
            "goal_shortfall": goal_shortfall,
            "affordable_with_bank": affordable_with_bank,
        }

    def _should_pop_for_goal(self, state, pop_goal=None):
        if not isinstance(pop_goal, dict):
            return False
        if pop_goal.get("force_wrinkler_liquidation"):
            attached_reward = sum(
                float(item.get("estimated_reward") or 0.0)
                for item in state["wrinklers"]
                if int(item.get("phase") or 0) == 2
            )
            return attached_reward > 0.0
        price = pop_goal.get("price")
        cookies = pop_goal.get("cookies")
        if not isinstance(price, (int, float)) or not isinstance(cookies, (int, float)):
            return False
        price = float(price)
        cookies = max(0.0, float(cookies))
        if price <= 0 or cookies >= price:
            return False
        attached_reward = sum(
            float(item.get("estimated_reward") or 0.0)
            for item in state["wrinklers"]
            if int(item.get("phase") or 0) == 2
        )
        return (cookies + attached_reward) >= price
