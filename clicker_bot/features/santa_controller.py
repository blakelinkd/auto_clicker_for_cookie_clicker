from dataclasses import dataclass
import threading
import time

from clicker_bot.snapshot_extractors import normalize_snapshot_target


SANTA_ACTION_COOLDOWN_SECONDS = 0.35


@dataclass
class SantaAction:
    kind: str
    screen_x: int
    screen_y: int
    level: int
    max_level: int
    target_level: int
    current_name: str | None = None
    next_name: str | None = None
    reason: str | None = None


class SantaController:
    def __init__(self, log, target_level: int | None = None):
        self.log = log
        self.target_level = target_level
        self.lock = threading.Lock()
        self.last_action_time = 0.0
        self.action_count = 0
        self.last_action_summary = None

    def extract_state(self, snapshot, to_screen_point):
        if not isinstance(snapshot, dict):
            return None
        santa = snapshot.get("santa")
        if not isinstance(santa, dict):
            return None

        levels = santa.get("levels")
        if not isinstance(levels, list):
            levels = []

        level = int(santa.get("level") or 0)
        max_level = int(santa.get("maxLevel") or max(0, len(levels) - 1))
        target_level = max_level if self.target_level is None else min(max(0, int(self.target_level)), max_level)
        current_name = santa.get("currentName") or (levels[level] if level < len(levels) else None)
        next_name = santa.get("nextName") or (levels[level + 1] if level < len(levels) - 1 else None)
        open = bool(santa.get("open"))
        next_cost = santa.get("nextCost")
        cookies = santa.get("cookies")
        can_evolve = bool(santa.get("canEvolve"))
        click_target = normalize_snapshot_target(santa.get("clickTarget"), to_screen_point)
        select_target = normalize_snapshot_target(santa.get("selectTarget"), to_screen_point)
        evolve_target = normalize_snapshot_target(santa.get("evolveTarget"), to_screen_point)

        return {
            "unlocked": bool(santa.get("unlocked")) or click_target is not None or evolve_target is not None,
            "open": open,
            "level": level,
            "max_level": max_level,
            "target_level": target_level,
            "current_name": current_name,
            "next_name": next_name,
            "next_cost": next_cost,
            "cookies": cookies,
            "can_evolve": can_evolve,
            "click_target": click_target,
            "select_target": select_target,
            "evolve_target": evolve_target,
        }

    def get_action(self, snapshot, to_screen_point, now=None):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None

        now = time.monotonic() if now is None else float(now)
        with self.lock:
            if (now - self.last_action_time) < SANTA_ACTION_COOLDOWN_SECONDS:
                return None

        if not state["unlocked"]:
            return None
        if state["level"] >= state["target_level"]:
            return None

        if state["evolve_target"] is not None:
            if not state["can_evolve"]:
                return None
            if not state["open"]:
                self.log.info(
                    f"Santa evolve target present before panel open current={state['current_name']} "
                    f"next={state['next_name']} level={state['level']}/{state['max_level']} "
                    f"target={state['target_level']}"
                )
            return SantaAction(
                kind="click_santa",
                screen_x=int(state["evolve_target"]["screen_x"]),
                screen_y=int(state["evolve_target"]["screen_y"]),
                level=state["level"],
                max_level=state["max_level"],
                target_level=state["target_level"],
                current_name=state["current_name"],
                next_name=state["next_name"],
                reason="evolve_santa",
            )

        if state["open"]:
            return None

        if state["click_target"] is None:
            return None

        self.log.info(
            f"Santa panel fallback current={state['current_name']} "
            f"next={state['next_name']} level={state['level']}/{state['max_level']} "
            f"target={state['target_level']}"
        )
        return SantaAction(
            kind="click_santa",
            screen_x=int(state["click_target"]["screen_x"]),
            screen_y=int(state["click_target"]["screen_y"]),
            level=state["level"],
            max_level=state["max_level"],
            target_level=state["target_level"],
            current_name=state["current_name"],
            next_name=state["next_name"],
            reason="open_santa_panel",
        )

    def get_diagnostics(self, snapshot, to_screen_point):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return {
                "available": False,
                "reason": "no_santa_data",
            }
        if not state["unlocked"]:
            return {
                "available": False,
                "reason": "santa_locked",
                **state,
            }
        if state["level"] >= state["target_level"]:
            return {
                "available": True,
                "reason": "santa_target_reached",
                **state,
            }
        if state["evolve_target"] is not None:
            if not state["can_evolve"]:
                return {
                    "available": True,
                    "reason": "santa_waiting_for_funds",
                    **state,
                }
            return {
                "available": True,
                "reason": "santa_evolve_ready",
                **state,
            }
        if state["open"]:
            return {
                "available": True,
                "reason": "santa_panel_open_no_evolve",
                **state,
            }
        if state["click_target"] is None:
            return {
                "available": True,
                "reason": "santa_panel_unavailable",
                **state,
            }
        return {
            "available": True,
            "reason": "santa_panel_ready",
            **state,
        }

    def record_action(self, action):
        with self.lock:
            self.last_action_time = time.monotonic()
            self.action_count += 1
            self.last_action_summary = (
                f"{action.current_name or 'Santa'} -> {action.next_name or action.target_level}"
            )
        self.log.info(
            f"Santa level action level={action.level}/{action.max_level} "
            f"current={action.current_name} next={action.next_name} "
            f"target={action.target_level} reason={action.reason}"
        )

    def get_runtime_stats(self):
        with self.lock:
            return {
                "action_count": self.action_count,
                "last_action": self.last_action_summary,
            }
