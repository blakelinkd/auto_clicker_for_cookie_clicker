from dataclasses import dataclass
import time
from enum import Enum

GARDEN_ACTION_COOLDOWN = 0.35


class GardenMode(Enum):
    OFF = "off"
    AUTO = "auto"
    SHIMMERLILLY = "shimmerlilly"

RECIPE_PLAN = [
    {"target": "cronerice", "parents": ("bakerWheat", "thumbcorn"), "pattern": "mixed_cross"},
    {"target": "gildmillet", "parents": ("cronerice", "thumbcorn"), "pattern": "mixed_cross"},
    {"target": "clover", "parents": ("bakerWheat", "gildmillet"), "pattern": "mixed_cross"},
    {"target": "shimmerlily", "parents": ("clover", "gildmillet"), "pattern": "mixed_cross"},
    {"target": "elderwort", "parents": ("shimmerlily", "cronerice"), "pattern": "mixed_cross"},
    {"target": "bakeberry", "parents": ("bakerWheat", "bakerWheat"), "pattern": "single_cross"},
    {"target": "meddleweed", "parents": (), "pattern": "neglect"},
]

FERTILIZER_KEY = "fertilizer"
WOODCHIPS_KEY = "woodchips"
CLAY_KEY = "clay"

BUFF_PRIORITY = {
    "goldenClover": 100.0,
    "clover": 70.0,
    "shimmerlily": 65.0,
    "gildmillet": 50.0,
    "elderwort": 45.0,
    "whiskerbloom": 40.0,
    "thumbcorn": 20.0,
    "bakerWheat": 15.0,
    "cronerice": 12.0,
}


@dataclass
class GardenAction:
    kind: str
    screen_x: int
    screen_y: int
    detail: str | None = None
    seed_key: str | None = None
    tile_x: int | None = None
    tile_y: int | None = None
    soil_key: str | None = None


class GardenController:
    def __init__(self, log):
        self.log = log
        self.last_action_time = 0.0
        self.action_count = 0
        self.last_garden_summary = None
        self.pending_mutation_deadline = {"signature": None, "deadline_ms": None}
        self.mode = GardenMode.AUTO

    def extract_state(self, snapshot, to_screen_point):
        if not isinstance(snapshot, dict):
            return None
        garden = snapshot.get("garden")
        if not isinstance(garden, dict):
            return None

        seeds = []
        for seed in garden.get("seeds", []):
            if not isinstance(seed, dict):
                continue
            target = self._normalize_target(seed.get("target"), to_screen_point)
            seeds.append(
                {
                    "id": None if seed.get("id") is None else int(seed.get("id")),
                    "key": seed.get("key"),
                    "name": seed.get("name") or seed.get("key"),
                    "unlocked": bool(seed.get("unlocked")),
                    "plantable": bool(seed.get("plantable")),
                    "selected": bool(seed.get("selected")),
                    "mature_age": None if seed.get("matureAge") is None else float(seed.get("matureAge")),
                    "cost": None if seed.get("cost") is None else float(seed.get("cost")),
                    "target": target,
                }
            )

        soils = []
        for soil in garden.get("soils", []):
            if not isinstance(soil, dict):
                continue
            target = self._normalize_target(soil.get("target"), to_screen_point)
            soils.append(
                {
                    "id": None if soil.get("id") is None else int(soil.get("id")),
                    "key": soil.get("key"),
                    "name": soil.get("name") or soil.get("key"),
                    "tick_minutes": None if soil.get("tickMinutes") is None else float(soil.get("tickMinutes")),
                    "selected": bool(soil.get("selected")),
                    "available": bool(soil.get("available")),
                    "target": target,
                }
            )

        plot = []
        for tile in garden.get("plot", []):
            if not isinstance(tile, dict):
                continue
            target = self._normalize_target(tile.get("target"), to_screen_point)
            plot.append(
                {
                    "x": int(tile.get("x") or 0),
                    "y": int(tile.get("y") or 0),
                    "unlocked": bool(tile.get("unlocked")),
                    "plant_id": tile.get("plantId"),
                    "plant_key": tile.get("plantKey"),
                    "plant_name": tile.get("plantName"),
                    "age": float(tile.get("age") or 0.0),
                    "mature_age": None if tile.get("matureAge") is None else float(tile.get("matureAge")),
                    "is_mature": bool(tile.get("isMature")),
                    "is_dying": bool(tile.get("isDying")),
                    "immortal": bool(tile.get("immortal")),
                    "target": target,
                }
            )

        soil = garden.get("soil")
        if not isinstance(soil, dict):
            soil = None

        open_target = self._normalize_target(garden.get("openControl"), to_screen_point)

        return {
            "snapshot_timestamp": None if snapshot.get("timestamp") is None else float(snapshot.get("timestamp")),
            "on_minigame": bool(garden.get("onMinigame")),
            "open_target": open_target,
            "farm_level": int(garden.get("farmLevel") or 0),
            "farm_amount": int(garden.get("farmAmount") or 0),
            "cookies": float(snapshot.get("cookies") or 0.0),
            "soil": None
            if soil is None
            else {
                "id": soil.get("id"),
                "key": soil.get("key"),
                "name": soil.get("name") or soil.get("key"),
                "tick_minutes": None if soil.get("tickMinutes") is None else float(soil.get("tickMinutes")),
            },
            "freeze": bool(garden.get("freeze")),
            "next_step_at": None if garden.get("nextStepAt") is None else float(garden.get("nextStepAt")),
            "next_soil_at": None if garden.get("nextSoilAt") is None else float(garden.get("nextSoilAt")),
            "plot_width": int(garden.get("plotWidth") or 0),
            "plot_height": int(garden.get("plotHeight") or 0),
            "plot_tile_count": int(garden.get("plotTileCount") or 0),
            "plot_occupied": int(garden.get("plotOccupied") or 0),
            "plot_mature": int(garden.get("plotMature") or 0),
            "plants_unlocked": int(garden.get("plantsUnlocked") or 0),
            "plants_total": int(garden.get("plantsTotal") or 0),
            "seed_selected": None if garden.get("seedSelected") is None else int(garden.get("seedSelected")),
            "seeds": seeds,
            "soils": soils,
            "plot": plot,
        }

    def get_diagnostics(self, snapshot, to_screen_point):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return {"available": False, "reason": "no_garden_data"}
        has_garden_access = self._has_garden_access(state)

        selected_seed = None
        next_locked_seed = None
        for seed in state["seeds"]:
            if seed["selected"]:
                selected_seed = seed["name"]
            if next_locked_seed is None and not seed["unlocked"]:
                next_locked_seed = seed["name"]

        plan = self._choose_plan(state)
        buff_plan = None if plan is not None else self._choose_buff_plan(state)
        remaining_cost = None if plan is None else self._remaining_layout_cost(state, plan)
        if plan is None and buff_plan is not None:
            remaining_cost = self._remaining_layout_cost(state, buff_plan)
        target_tiles = [] if plan is None else [
            tile for tile in state["plot"] if tile["unlocked"] and tile["plant_key"] == plan["target"]
        ]
        if plan is None and buff_plan is not None:
            target_tiles = [
                tile for tile in state["plot"] if tile["unlocked"] and tile["plant_key"] == buff_plan["target"]
            ]
        now_ms = state.get("snapshot_timestamp")
        active_plan = plan if plan is not None else buff_plan
        mutation_window = self._mutation_window_status(state, plan, target_tiles)
        refresh_cost = None if plan is None else self._refresh_layout_cost(state, plan)
        return {
            "available": True,
            "reason": (
                "garden_unavailable"
                if not has_garden_access
                else (
                    "garden_open"
                    if state["on_minigame"]
                    else ("garden_closed_can_open" if state["open_target"] is not None else "garden_closed_missing_open_control")
                )
            ),
            "on_minigame": state["on_minigame"],
            "has_open_target": state["open_target"] is not None,
            "has_garden_access": has_garden_access,
            "farm_level": state["farm_level"],
            "farm_amount": state["farm_amount"],
            "soil": "-" if state["soil"] is None else state["soil"]["name"],
            "freeze": state["freeze"],
            "next_tick": self._format_countdown_ms(state["next_step_at"], now_ms),
            "next_soil": self._format_countdown_ms(state["next_soil_at"], now_ms),
            "plot_width": state["plot_width"],
            "plot_height": state["plot_height"],
            "plot_tile_count": state["plot_tile_count"],
            "plot_occupied": state["plot_occupied"],
            "plot_mature": state["plot_mature"],
            "plot_unlocked": sum(1 for tile in state["plot"] if tile["unlocked"]),
            "plots_with_targets": sum(1 for tile in state["plot"] if tile["unlocked"] and tile["target"] is not None),
            "plants_unlocked": state["plants_unlocked"],
            "plants_total": state["plants_total"],
            "selected_seed": selected_seed,
            "next_locked_seed": next_locked_seed,
            "plan_target": None if active_plan is None else active_plan["target"],
            "plan_parents": () if active_plan is None else tuple(active_plan.get("parents", ())),
            "plan_mode": "mutation" if plan is not None else ("buffs" if buff_plan is not None else "idle"),
            "controller_mode": self.mode.value,
            "planner_state": self._describe_plan_state(state, active_plan),
            "target_present": bool(target_tiles),
            "target_mature": any(tile["is_mature"] for tile in target_tiles),
            "target_tiles": tuple((tile["x"], tile["y"]) for tile in target_tiles),
            "mutation_deadline": self._format_countdown_ms(mutation_window["deadline_ms"], now_ms),
            "mutation_window_expired": mutation_window["expired"],
            "refresh_layout_cost": refresh_cost,
            "can_afford_refresh": None if refresh_cost is None else state["cookies"] >= refresh_cost,
            "cookies": state["cookies"],
            "remaining_layout_cost": remaining_cost,
            "can_afford_layout": None if remaining_cost is None else state["cookies"] >= remaining_cost,
            "seeds_total": len(state["seeds"]),
            "seeds_unlocked": sum(1 for seed in state["seeds"] if seed["unlocked"]),
        }

    def get_action(self, snapshot, to_screen_point, now=None):
        state = self.extract_state(snapshot, to_screen_point)
        if state is None:
            return None
        if not self._has_garden_access(state):
            return None

        now = time.monotonic() if now is None else now
        if (now - self.last_action_time) < GARDEN_ACTION_COOLDOWN:
            return None

        if not state["on_minigame"]:
            if not self._should_open_garden(state):
                return None
            target = state["open_target"]
            if target is None:
                return None
            return GardenAction(
                kind="open_garden",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                detail="open garden minigame",
            )

        if not self._garden_targets_ready(state):
            target = state["open_target"]
            if target is None:
                return None
            return GardenAction(
                kind="focus_garden",
                screen_x=target["screen_x"],
                screen_y=target["screen_y"],
                detail="focus garden minigame",
            )

        harvestable_locked_seed_tile = self._find_mature_locked_seed_tile(state)
        if harvestable_locked_seed_tile is not None:
            return GardenAction(
                kind="harvest_target",
                screen_x=harvestable_locked_seed_tile["target"]["screen_x"],
                screen_y=harvestable_locked_seed_tile["target"]["screen_y"],
                detail=f"harvest mature {harvestable_locked_seed_tile['plant_key']}",
                tile_x=harvestable_locked_seed_tile["x"],
                tile_y=harvestable_locked_seed_tile["y"],
            )

        plan = self._choose_plan(state)
        if plan is None:
            plan = self._choose_buff_plan(state)
        if plan is None:
            return None

        target_key = plan["target"]
        target_tiles = [
            tile for tile in state["plot"] if tile["unlocked"] and tile["plant_key"] == target_key
        ]
        mutation_window = self._update_mutation_window(state, plan, target_tiles)
        if plan.get("mode") == "buffs":
            target_tiles = []
        locked_target_present = any(target_tiles)
        locked_target_mature = any(tile["is_mature"] for tile in target_tiles)
        if locked_target_mature:
            target_tile = next(tile for tile in target_tiles if tile["is_mature"] and tile["target"] is not None)
            return GardenAction(
                kind="harvest_target",
                screen_x=target_tile["target"]["screen_x"],
                screen_y=target_tile["target"]["screen_y"],
                detail=f"harvest mature {target_key}",
                tile_x=target_tile["x"],
                tile_y=target_tile["y"],
            )

        desired_soil = self._choose_desired_soil(state, plan)
        current_soil_key = None if state["soil"] is None else state["soil"]["key"]
        if desired_soil is not None and current_soil_key != desired_soil["key"] and self._soil_ready(state):
            return GardenAction(
                kind="set_soil",
                screen_x=desired_soil["target"]["screen_x"],
                screen_y=desired_soil["target"]["screen_y"],
                detail=f"switch soil to {desired_soil['name']}",
                soil_key=desired_soil["key"],
            )

        if mutation_window["expired"]:
            refresh_cost = self._refresh_layout_cost(state, plan)
            if refresh_cost is not None and state["cookies"] < refresh_cost:
                return None
            refresh_action = self._plan_refresh_action(state, plan)
            if refresh_action is not None:
                return refresh_action

        remaining_cost = self._remaining_layout_cost(state, plan)
        if remaining_cost is not None and state["cookies"] < remaining_cost:
            return None

        layout_action = self._plan_layout_action(state, plan, preserve_target=locked_target_present)
        if layout_action is not None:
            return layout_action
        return None

    def record_action(self, action):
        self.last_action_time = time.monotonic()
        self.action_count += 1
        self.last_garden_summary = action.detail or action.kind
        self.log.info(
            f"Garden action kind={action.kind} detail={action.detail or '-'} "
            f"screen=({action.screen_x},{action.screen_y})"
        )

    def _has_garden_access(self, state):
        return int(state.get("farm_amount") or 0) > 0

    def get_runtime_stats(self):
        return {
            "action_count": self.action_count,
            "last_garden": self.last_garden_summary,
            "mode": self.mode.value,
        }
    
    def cycle_mode(self):
        modes = list(GardenMode)
        current_index = modes.index(self.mode)
        next_index = (current_index + 1) % len(modes)
        self.mode = modes[next_index]
        self.log.info(f"Garden mode changed to {self.mode.value}")
        return self.mode

    def _choose_plan(self, state):
        if self.mode == GardenMode.OFF:
            return None
        if self.mode == GardenMode.SHIMMERLILLY:
            unlocked = {seed["key"] for seed in state["seeds"] if seed["unlocked"] and seed["key"]}
            if "shimmerlily" in unlocked:
                return None
            if all(parent in unlocked for parent in ("clover", "gildmillet")):
                return {"target": "shimmerlily", "parents": ("clover", "gildmillet"), "pattern": "mixed_cross"}
            return None
        
        unlocked = {seed["key"] for seed in state["seeds"] if seed["unlocked"] and seed["key"]}
        for item in RECIPE_PLAN:
            if item["target"] in unlocked:
                continue
            if all(parent in unlocked for parent in item["parents"]):
                return item
        return None

    def _garden_targets_ready(self, state):
        if not state["on_minigame"]:
            return False
        visible_plot_targets = sum(1 for tile in state["plot"] if tile["unlocked"] and tile["target"] is not None)
        visible_seed_targets = sum(1 for seed in state["seeds"] if seed["unlocked"] and seed["target"] is not None)
        return visible_plot_targets > 0 and visible_seed_targets > 0

    def _should_open_garden(self, state):
        if state.get("open_target") is None:
            return False
        plan = self._choose_plan(state)
        if plan is None:
            plan = self._choose_buff_plan(state)
        if plan is None:
            return False
        required_keys = (plan.get("parents") or ()) if plan.get("mode") != "buffs" else (plan.get("target"),)
        for seed_key in required_keys:
            if not seed_key:
                continue
            seed = self._seed_by_key(state, seed_key)
            if seed is None or seed["cost"] is None:
                return False
        remaining_cost = self._remaining_layout_cost(state, plan)
        if remaining_cost is None:
            return False
        if remaining_cost is not None and state["cookies"] < remaining_cost:
            return False
        return True

    def _choose_buff_plan(self, state):
        if self.mode == GardenMode.OFF:
            return None
        if self.mode == GardenMode.SHIMMERLILLY:
            unlocked_keys = {seed["key"] for seed in state["seeds"] if seed["unlocked"] and seed["key"]}
            if "shimmerlily" in unlocked_keys:
                return {
                    "target": "shimmerlily",
                    "parents": (),
                    "pattern": "fill_all",
                    "mode": "buffs",
                }
            return None
        
        unlocked_keys = {seed["key"] for seed in state["seeds"] if seed["unlocked"] and seed["key"]}
        candidates = [
            (score, key)
            for key, score in BUFF_PRIORITY.items()
            if key in unlocked_keys
        ]
        if not candidates:
            return None
        candidates.sort(reverse=True)
        best_key = candidates[0][1]
        return {
            "target": best_key,
            "parents": (),
            "pattern": "fill_all",
            "mode": "buffs",
        }

    def _describe_plan_state(self, state, plan):
        if plan is None:
            return "no_supported_plan"
        if plan.get("mode") == "buffs":
            remaining_cost = self._remaining_layout_cost(state, plan)
            if remaining_cost is not None and state["cookies"] < remaining_cost:
                return "waiting_for_buff_funds"
            layout_action = self._plan_layout_action(state, plan)
            if layout_action is None:
                return "holding_buff_layout"
            return layout_action.kind
        target_tiles = [
            tile for tile in state["plot"] if tile["unlocked"] and tile["plant_key"] == plan["target"]
        ]
        if any(tile["is_mature"] for tile in target_tiles):
            return "harvest_target"
        if target_tiles:
            layout_action = self._plan_layout_action(state, plan, preserve_target=True)
            if layout_action is None:
                return "hold_target_to_mature"
            return f"support_{layout_action.kind}"
        if plan["pattern"] == "neglect":
            cleanup_action = self._plan_neglect_cleanup(state)
            if cleanup_action is not None:
                return cleanup_action.kind
            return "waiting_for_target_spawn"
        mutation_window = self._mutation_window_status(state, plan, target_tiles)
        if mutation_window["expired"]:
            refresh_cost = self._refresh_layout_cost(state, plan)
            if refresh_cost is not None and state["cookies"] < refresh_cost:
                return "waiting_for_refresh_funds"
            refresh_action = self._plan_refresh_action(state, plan)
            if refresh_action is None:
                return "refresh_layout_complete"
            return refresh_action.kind
        remaining_cost = self._remaining_layout_cost(state, plan)
        if remaining_cost is not None and state["cookies"] < remaining_cost:
            return "waiting_for_seed_funds"
        desired_soil = self._choose_desired_soil(state, plan)
        current_soil_key = None if state["soil"] is None else state["soil"]["key"]
        if desired_soil is not None and current_soil_key != desired_soil["key"] and self._soil_ready(state):
            return "set_mutation_soil"
        layout_action = self._plan_layout_action(state, plan)
        if layout_action is None:
            return "waiting_for_mutation"
        return layout_action.kind

    def _choose_desired_soil(self, state, plan):
        soils_by_key = {soil["key"]: soil for soil in state["soils"] if soil.get("key")}
        
        if self.mode == GardenMode.SHIMMERLILLY:
            if CLAY_KEY in soils_by_key and soils_by_key[CLAY_KEY]["available"] and soils_by_key[CLAY_KEY]["target"] is not None:
                return soils_by_key[CLAY_KEY]
            if FERTILIZER_KEY in soils_by_key and soils_by_key[FERTILIZER_KEY]["available"] and soils_by_key[FERTILIZER_KEY]["target"] is not None:
                return soils_by_key[FERTILIZER_KEY]
            return None
        
        if plan.get("mode") == "buffs":
            if CLAY_KEY in soils_by_key and soils_by_key[CLAY_KEY]["available"] and soils_by_key[CLAY_KEY]["target"] is not None:
                return soils_by_key[CLAY_KEY]
            if FERTILIZER_KEY in soils_by_key and soils_by_key[FERTILIZER_KEY]["available"] and soils_by_key[FERTILIZER_KEY]["target"] is not None:
                return soils_by_key[FERTILIZER_KEY]
            return None
        if WOODCHIPS_KEY in soils_by_key and soils_by_key[WOODCHIPS_KEY]["available"] and soils_by_key[WOODCHIPS_KEY]["target"] is not None:
            return soils_by_key[WOODCHIPS_KEY]
        if FERTILIZER_KEY in soils_by_key and soils_by_key[FERTILIZER_KEY]["available"] and soils_by_key[FERTILIZER_KEY]["target"] is not None:
            return soils_by_key[FERTILIZER_KEY]
        return None

    def _soil_ready(self, state):
        now_ms = state.get("snapshot_timestamp")
        if now_ms is None:
            now_ms = time.time() * 1000.0
        return state["next_soil_at"] is None or state["next_soil_at"] <= now_ms

    def _is_layout_ready(self, state, plan):
        if plan.get("mode") == "buffs":
            desired = self._desired_layout(state, plan["pattern"], (plan["target"],))
            for coord, plant_key in desired.items():
                tile = self._tile_by_coord(state, coord[0], coord[1])
                if tile is None or tile["plant_key"] != plant_key:
                    return False
            return True
        desired = self._desired_layout(state, plan["pattern"], plan["parents"])
        for coord, plant_key in desired.items():
            tile = self._tile_by_coord(state, coord[0], coord[1])
            if tile is None or tile["plant_key"] != plant_key or not tile["is_mature"]:
                return False
        for tile in state["plot"]:
            if not tile["unlocked"]:
                continue
            if (tile["x"], tile["y"]) in desired:
                continue
            if tile["plant_key"] == plan["target"]:
                return False
        return True

    def _plan_layout_action(self, state, plan, preserve_target=False):
        if plan["pattern"] == "neglect":
            return self._plan_neglect_cleanup(state)
        parents = plan["parents"] if plan.get("mode") != "buffs" else (plan["target"],)
        desired = self._desired_layout(state, plan["pattern"], parents)
        for tile in state["plot"]:
            if not tile["unlocked"] or tile["target"] is None:
                continue
            if preserve_target and tile["plant_key"] == plan["target"]:
                continue
            coord = (tile["x"], tile["y"])
            desired_key = desired.get(coord)
            if desired_key is not None:
                if tile["plant_key"] == desired_key:
                    continue
                if tile["plant_key"] is not None:
                    return GardenAction(
                        kind="clear_tile",
                        screen_x=tile["target"]["screen_x"],
                        screen_y=tile["target"]["screen_y"],
                        detail=f"clear tile {tile['x']},{tile['y']} for {desired_key}",
                        tile_x=tile["x"],
                        tile_y=tile["y"],
                    )
                seed = self._seed_by_key(state, desired_key)
                if seed is None or seed["target"] is None:
                    continue
                if not seed["selected"]:
                    return GardenAction(
                        kind="select_seed",
                        screen_x=seed["target"]["screen_x"],
                        screen_y=seed["target"]["screen_y"],
                        detail=f"select {desired_key}",
                        seed_key=desired_key,
                    )
                return GardenAction(
                    kind="plant_seed",
                    screen_x=tile["target"]["screen_x"],
                    screen_y=tile["target"]["screen_y"],
                    detail=f"plant {desired_key} at {tile['x']},{tile['y']}",
                    seed_key=desired_key,
                    tile_x=tile["x"],
                    tile_y=tile["y"],
                )
            if tile["plant_key"] is not None and tile["plant_key"] != plan["target"]:
                return GardenAction(
                    kind="clear_tile",
                    screen_x=tile["target"]["screen_x"],
                    screen_y=tile["target"]["screen_y"],
                    detail=f"clear non-layout tile {tile['x']},{tile['y']}",
                    tile_x=tile["x"],
                    tile_y=tile["y"],
                )
        return None

    def _plan_neglect_cleanup(self, state):
        for tile in state["plot"]:
            if not tile["unlocked"] or tile["target"] is None:
                continue
            if tile["plant_key"] is None:
                continue
            return GardenAction(
                kind="clear_tile",
                screen_x=tile["target"]["screen_x"],
                screen_y=tile["target"]["screen_y"],
                detail=f"clear tile {tile['x']},{tile['y']} for neglect",
                tile_x=tile["x"],
                tile_y=tile["y"],
            )
        return None

    def _plan_refresh_action(self, state, plan):
        parents = plan["parents"] if plan.get("mode") != "buffs" else (plan["target"],)
        desired = self._desired_layout(state, plan["pattern"], parents)
        for coord, desired_key in desired.items():
            tile = self._tile_by_coord(state, coord[0], coord[1])
            if tile is None or tile["target"] is None:
                continue
            if tile["plant_key"] is None:
                continue
            return GardenAction(
                kind="clear_tile",
                screen_x=tile["target"]["screen_x"],
                screen_y=tile["target"]["screen_y"],
                detail=f"refresh tile {tile['x']},{tile['y']} for {desired_key}",
                tile_x=tile["x"],
                tile_y=tile["y"],
            )
        return self._plan_layout_action(state, plan)

    def _remaining_layout_cost(self, state, plan):
        if plan["pattern"] == "neglect":
            return 0.0
        parents = plan["parents"] if plan.get("mode") != "buffs" else (plan["target"],)
        desired = self._desired_layout(state, plan["pattern"], parents)
        total_cost = 0.0
        missing_any = False
        for coord, desired_key in desired.items():
            tile = self._tile_by_coord(state, coord[0], coord[1])
            if tile is None:
                continue
            if tile["plant_key"] == desired_key:
                continue
            seed = self._seed_by_key(state, desired_key)
            if seed is None or seed["cost"] is None:
                return None
            if tile["plant_key"] is None:
                total_cost += float(seed["cost"])
                missing_any = True
        return total_cost if missing_any else 0.0

    def _refresh_layout_cost(self, state, plan):
        if plan["pattern"] == "neglect":
            return 0.0
        parents = plan["parents"] if plan.get("mode") != "buffs" else (plan["target"],)
        desired = self._desired_layout(state, plan["pattern"], parents)
        total_cost = 0.0
        for desired_key in desired.values():
            seed = self._seed_by_key(state, desired_key)
            if seed is None or seed["cost"] is None:
                return None
            total_cost += float(seed["cost"])
        return total_cost

    def _plan_signature(self, plan):
        if not isinstance(plan, dict):
            return None
        return (
            plan.get("target"),
            tuple(plan.get("parents", ())),
            plan.get("pattern"),
            plan.get("mode"),
        )

    def _mutation_window_status(self, state, plan, target_tiles):
        if not isinstance(plan, dict) or plan.get("mode") == "buffs" or plan.get("pattern") == "neglect":
            return {"deadline_ms": None, "expired": False}
        if target_tiles:
            return {"deadline_ms": None, "expired": False}
        signature = self._plan_signature(plan)
        pending_signature = self.pending_mutation_deadline.get("signature")
        deadline_ms = self.pending_mutation_deadline.get("deadline_ms")
        expired = (
            signature is not None
            and signature == pending_signature
            and deadline_ms is not None
            and state.get("snapshot_timestamp") is not None
            and float(state["snapshot_timestamp"]) >= float(deadline_ms)
        )
        if expired:
            return {"deadline_ms": deadline_ms, "expired": True}
        if not self._is_layout_ready(state, plan):
            return {"deadline_ms": None, "expired": False}
        parents = plan["parents"] if plan.get("mode") != "buffs" else (plan["target"],)
        desired = self._desired_layout(state, plan["pattern"], parents)
        for coord in desired:
            tile = self._tile_by_coord(state, coord[0], coord[1])
            if tile is None or tile["plant_key"] is None:
                return {"deadline_ms": None, "expired": False}
            if tile["is_dying"]:
                return {"deadline_ms": state.get("next_step_at"), "expired": False}
        return {"deadline_ms": None, "expired": False}

    def _update_mutation_window(self, state, plan, target_tiles):
        status = self._mutation_window_status(state, plan, target_tiles)
        signature = self._plan_signature(plan)
        if status["expired"]:
            return status
        if signature is None or status["deadline_ms"] is None:
            self.pending_mutation_deadline = {"signature": None, "deadline_ms": None}
            return status
        self.pending_mutation_deadline = {
            "signature": signature,
            "deadline_ms": status["deadline_ms"],
        }
        return status

    def _desired_layout(self, state, pattern, parents):
        unlocked = [(tile["x"], tile["y"]) for tile in state["plot"] if tile["unlocked"]]
        if not unlocked:
            return {}
        min_x = min(coord[0] for coord in unlocked)
        min_y = min(coord[1] for coord in unlocked)
        max_x = max(coord[0] for coord in unlocked)
        max_y = max(coord[1] for coord in unlocked)
        center_x = min_x + 1
        center_y = min_y + 1
        is_three_by_three = (max_x - min_x + 1) == 3 and (max_y - min_y + 1) == 3 and len(unlocked) == 9
        if pattern == "fill_all":
            return {coord: parents[0] for coord in unlocked}
        if is_three_by_three and pattern == "single_cross":
            return {
                (min_x, min_y): parents[0],
                (min_x + 1, min_y): parents[0],
                (min_x, min_y + 1): parents[0],
                (min_x + 2, min_y + 1): parents[0],
                (min_x + 1, min_y + 2): parents[0],
                (min_x + 2, min_y + 2): parents[0],
            }
        if is_three_by_three and pattern == "mixed_cross":
            return {
                (min_x, min_y): parents[0],
                (min_x + 1, min_y): parents[1],
                (min_x, min_y + 1): parents[1],
                (min_x + 2, min_y + 1): parents[0],
                (min_x + 1, min_y + 2): parents[0],
                (min_x + 2, min_y + 2): parents[1],
            }
        if pattern == "single_cross":
            return {
                (center_x, min_y): parents[0],
                (min_x, center_y): parents[0],
                (min_x + 2, center_y): parents[0],
                (center_x, min_y + 2): parents[0],
            }
        return {
            (center_x, min_y): parents[0],
            (min_x, center_y): parents[1],
            (min_x + 2, center_y): parents[1],
            (center_x, min_y + 2): parents[0],
        }

    def _seed_by_key(self, state, key):
        for seed in state["seeds"]:
            if seed["key"] == key:
                return seed
        return None

    def _find_mature_locked_seed_tile(self, state):
        locked_seed_keys = {
            seed["key"]
            for seed in state["seeds"]
            if seed.get("key") and not seed.get("unlocked")
        }
        if not locked_seed_keys:
            return None
        for tile in state["plot"]:
            if (
                tile["unlocked"]
                and tile["target"] is not None
                and tile["is_mature"]
                and tile["plant_key"] in locked_seed_keys
            ):
                return tile
        return None

    def _tile_by_coord(self, state, x, y):
        for tile in state["plot"]:
            if tile["x"] == x and tile["y"] == y and tile["unlocked"]:
                return tile
        return None

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

    def _format_countdown_ms(self, target_ms, now_ms):
        if target_ms is None or now_ms is None:
            return "-"
        remaining_ms = max(0.0, float(target_ms) - float(now_ms))
        if remaining_ms <= 0:
            return "ready"
        remaining_seconds = remaining_ms / 1000.0
        if remaining_seconds >= 3600:
            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)
            return f"{hours}h{minutes:02d}m"
        if remaining_seconds >= 60:
            minutes = int(remaining_seconds // 60)
            seconds = int(remaining_seconds % 60)
            return f"{minutes}m{seconds:02d}s"
        return f"{remaining_seconds:.1f}s"
