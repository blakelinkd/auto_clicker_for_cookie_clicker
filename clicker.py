import ctypes
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from json import JSONDecodeError
from pathlib import Path

import keyboard
import pyautogui
import win32gui
import win32process
from clicker_bot.dashboard import DashboardCallbacks, build_dashboard
from clicker_bot.dashboard_state import DashboardStateBuilder
from clicker_bot.dom_loop import (
    DomLoopBuildOptions,
)
from clicker_bot.dom_loop_services import build_default_dom_loop_service_factory
from clicker_bot.activation import BotActivationController
from clicker_bot.controls import BotControls
from clicker_bot.events import BotEventRecorder
from clicker_bot.lifecycle import BotLifecycle, BotLifecycleState
from clicker_bot.minigame_access import plan_minigame_store_access
from clicker_bot.dragon_diagnostics import build_dragon_diag
from clicker_bot.reserve_policy import ReservePolicy, apply_building_burst_purchase_goal
from clicker_bot.pause_policy import (
    GARDEN_LONG_BUFF_THRESHOLD_FRAMES,
    get_active_click_buff_names,
    has_buff_only_non_click_pause,
    has_long_positive_active_buff,
    has_positive_active_buffs,
    should_allow_garden_action,
    should_allow_non_click_actions_during_pause,
)
from clicker_bot.runtime import RuntimeConfig, RuntimeStore
from clicker_bot.snapshot_extractors import (
    extract_big_cookie,
    extract_buffs,
    extract_shimmers,
    extract_spell,
    normalize_snapshot_target,
)
from clicker_bot.startup_policy import (
    ATTACH_STARTUP_DELAY,
    GAME_ATTACH_WAIT_SECONDS,
    STARTUP_DELAY,
    should_launch_new_game_process,
)
from clicker_bot.stock_helpers import (
    build_disabled_bank_diag,
    get_garden_cookie_reserve,
    get_stock_buy_controls,
    has_cookies_after_reserve,
    should_defer_stock_actions_for_upgrade,
    should_pause_stock_trading,
    stock_trade_management_active,
)
from clicker_bot.upgrade_diagnostics import build_upgrade_diag

from ascension_prep import AscensionPrepController
from building_autobuyer import BuildingAutobuyer
from building_store import BuildingStoreController
from combo_evaluator import PRODUCTION_STACK_BUFF_KEYS, VALUABLE_BUFF_KEYS, evaluate_combo_buffs
from garden_controller import GardenController
from godzamok_combo import GodzamokComboEngine
from spell_autocaster import SpellAutocaster, CRAFTY_PIXIES_BUFF
from stock_db import StockDatabase
from stock_trader import StockTrader
from upgrade_store import UpgradeStoreController
from wrinkler_controller import (
    WrinklerController,
    WRINKLER_MODE_HOLD,
    WRINKLER_MODE_SEASONAL_FARM,
    WRINKLER_MODE_SHINY_HUNT,
)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


MAIN_CLICK_INTERVAL = 0.100
FEED_POLL_INTERVAL = 0.080
FEED_MAX_AGE_SECONDS = 1.0
MAIN_CLICK_HOLD = 0.01
BONUS_CLICK_HOLD = 0.035
SPELL_CLICK_HOLD = 0.02
TRADE_CLICK_HOLD = 0.02
BUILDING_CLICK_HOLD = 0.02
MAIN_CLICK_SUPPRESS_SECONDS = 0.30
STORE_SCROLL_WHEEL_MULTIPLIER = 12
SHIMMER_CLICK_COOLDOWN = 0.12
SHIMMER_CLICK_DELAY_SECONDS = 1.2
SPELL_CLICK_COOLDOWN = 1.50
TRADE_ACTION_COOLDOWN = 0.35
BUILDING_ACTION_COOLDOWN = 0.35
UPGRADE_ACTION_COOLDOWN = 0.35
DRAGON_ACTION_COOLDOWN = 0.50
DRAGON_AURA_ACTION_COOLDOWN = 15.0
UPGRADE_STUCK_ATTEMPT_LIMIT = 4
UPGRADE_STUCK_BACKOFF_SECONDS = 15.0
UPGRADE_STUCK_SIGNATURE_SUPPRESS_SECONDS = 60.0
BUILDING_STUCK_ATTEMPT_LIMIT = 4
BUILDING_STUCK_SIGNATURE_SUPPRESS_SECONDS = 30.0
COMBO_ACTION_COOLDOWN = 0.20
WRINKLER_ACTION_COOLDOWN = 0.12
NOTE_DISMISS_COOLDOWN = 0.35
LUMP_ACTION_COOLDOWN = 1.0
MINIGAME_OPEN_RETRY_SECONDS = 2.0
UI_OWNER_LOCK_SECONDS = 1.25
UPGRADE_AFFORD_HORIZON_SECONDS = 30 * 60
UPGRADE_AUTO_BUY_PAYBACK_SECONDS = 3 * 60
CHEAP_UPGRADE_SWEEP_RATIO = 0.10
POST_UPGRADE_WRINKLER_COOLDOWN_SECONDS = 3.0
AUTO_CAST_HAND_OF_FATE = True
ENABLE_MAIN_COOKIE_CLICKING = True
ENABLE_SHIMMER_AUTOCLICK = True
ENABLE_STOCK_TRADING = False
ENABLE_BUILDING_AUTOBUY = False
ENABLE_GARDEN_AUTOMATION = True
WRINKLER_MODE = WRINKLER_MODE_HOLD

FEED_PATH = Path(
    r"D:\SteamLibrary\steamapps\common\Cookie Clicker\resources\app\file_outputs\shimmers.txt"
)
GAME_EXE_PATH = Path(r"D:\SteamLibrary\steamapps\common\Cookie Clicker\Cookie Clicker.exe")
DB_PATH = Path("clicker.sqlite3")
MOD_SOURCE_DIR = Path("cookie_shimmer_bridge_mod")
MOD_INSTALL_DIR = Path(r"D:\SteamLibrary\steamapps\common\Cookie Clicker\resources\app\mods\local\shimmerBridge")
MOD_SYNC_FILES = ("main.js", "info.txt")
HUD_REFRESH_INTERVAL = 0.50
HUD_RECENT_EVENTS = 10
FEED_DEBUG_LOG_INTERVAL = 2.0
PROFILE_EMA_ALPHA = 0.20
STOCK_DIAG_REFRESH_INTERVAL = 3.0
COMBO_ACTIVE_STAGES = {"spawn_click_buff", "execute_click_combo"}
COOKIE_CLICKER_FPS = 30.0
UPGRADE_BUFF_WINDOW_PAYBACK_THRESHOLD = 1.0
COMBO_STAGE_RANK = {
    "idle": 0,
    "build_combo": 1,
    "spawn_click_buff": 2,
    "execute_click_combo": 3,
}
LUCKY_RESERVE_CPS_SECONDS = 600.0
BUILDING_BUFF_BURST_MIN_REMAINING_SECONDS = 8.0
KNOWN_NEGATIVE_BUFFS = {
    "Clot",
    "Ruin cookies",
    "Cursed finger",
}
KNOWN_POSITIVE_SHIMMER_OUTCOMES = {
    "Building special",
    "Click frenzy",
    "Cookie storm",
    "Cookie storm drop",
    "Dragon Harvest",
    "Dragonflight",
    "Elder frenzy",
    "Frenzy",
    "Lucky",
    "multiply cookies",
}
SKIP_WRATH_DURING_CLICK_BUFFS = False
STOCK_BUILDING_RUNWAY_FULL_PAYBACK_SECONDS = 15 * 60
STOCK_BUILDING_RUNWAY_HALF_PAYBACK_SECONDS = 60 * 60
DRAGON_AUTOMATION_MAX_COOKIE_LEVEL = 4
DRAGON_AURA_NAME_TO_ID = {
    "No aura": 0,
    "Breath of Milk": 1,
    "Dragon Cursor": 2,
    "Reaper of Fields": 4,
    "Arcane Aura": 9,
    "Dragonflight": 10,
    "Radiant Appetite": 15,
}


class HudBufferHandler(logging.Handler):
    def __init__(self, sink, level=logging.INFO):
        super().__init__(level=level)
        self.sink = sink

    def emit(self, record):
        try:
            message = self.format(record)
            self.sink(record.levelname, message)
        except Exception:
            pass


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
file_handler = logging.FileHandler("clicker.log", mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

log = logging.getLogger(__name__)


active = False
active_lock = threading.Lock()
click_lock = threading.Lock()
click_thread = None
dom_thread = None
hud_thread = None
bot_lifecycle = None
bot_controls = None
bot_activation = None
bot_event_recorder = None
dashboard_state_builder = None
dom_loop_services = None
game_hwnd = None
game_rect = None
suppress_main_click_until = 0.0
recent_shimmer_clicks = {}
shimmer_first_seen = {}
shimmer_click_attempts = {}
pending_shimmer_results = {}
shimmer_seed_history = []
shimmer_tracking_reset_reason = "session_start"
last_seen_golden_decision = None
last_spell_click = 0.0
last_trade_action = 0.0
last_building_action = 0.0
last_upgrade_action = 0.0
last_upgrade_skip_signature = None
last_upgrade_focus_signature = None
last_upgrade_focus_at = 0.0
last_upgrade_focus_point = None
upgrade_attempt_tracker = {
    "candidate_id": None,
    "attempts": 0,
    "blocked_until": 0.0,
    "candidate_signature": None,
    "blocked_signature": None,
}
building_attempt_tracker = {
    "candidate_id": None,
    "attempts": 0,
    "blocked_until": 0.0,
    "candidate_signature": None,
    "blocked_signature": None,
}
MINIGAME_BUILDING_IDS = {
    "garden": 2,
    "bank": 5,
    "grimoire": 7,
}
last_combo_action_click = 0.0
last_wrinkler_action = 0.0
last_dragon_action = 0.0
last_note_dismiss_action = 0.0
last_lump_action = 0.0
post_upgrade_wrinkler_cooldown_until = 0.0
last_ui_open_action = {}
ui_owner_lock = {"owner": None, "until": 0.0}
building_autobuy_enabled = ENABLE_BUILDING_AUTOBUY
stock_trading_enabled = ENABLE_STOCK_TRADING
lucky_reserve_enabled = False
upgrade_autobuy_enabled = True
ascension_prep_enabled = False
garden_automation_enabled = ENABLE_GARDEN_AUTOMATION
main_cookie_clicking_enabled = ENABLE_MAIN_COOKIE_CLICKING
shimmer_autoclick_enabled = ENABLE_SHIMMER_AUTOCLICK
stock_db = StockDatabase(DB_PATH, log)
stock_trader = StockTrader(log, stock_db)
building_autobuyer = BuildingAutobuyer(log)
building_store = BuildingStoreController()
upgrade_store = UpgradeStoreController()
ascension_prep = AscensionPrepController(log)
godzamok_combo = GodzamokComboEngine(log, MAIN_CLICK_INTERVAL)
spell_autocaster = SpellAutocaster(log)
wrinkler_controller = WrinklerController(log, mode=WRINKLER_MODE)
garden_controller = GardenController(log)
_last_lucky_multiplier = 1.0
_last_lucky_multiplier_logged_at = 0.0
reserve_policy = ReservePolicy(
    lucky_reserve_cps_seconds=LUCKY_RESERVE_CPS_SECONDS,
    crafty_pixies_buff=CRAFTY_PIXIES_BUFF,
    building_buff_burst_min_remaining_seconds=BUILDING_BUFF_BURST_MIN_REMAINING_SECONDS,
    cookie_clicker_fps=COOKIE_CLICKER_FPS,
    log=log,
    monotonic=time.monotonic,
    last_lucky_multiplier=_last_lucky_multiplier,
    last_lucky_multiplier_logged_at=_last_lucky_multiplier_logged_at,
)
combo_run_tracker = {
    "active": False,
    "started_at": None,
    "started_cookies": None,
    "peak_cookies": None,
    "start_stage": None,
    "max_stage": None,
    "start_buffs": (),
    "max_buffs": (),
    "godzamok_start": 0,
    "spell_cast_start": 0,
}
runtime_store = RuntimeStore(
    RuntimeConfig(
        hud_recent_events=HUD_RECENT_EVENTS,
        gameplay_feed_size=120,
        upgrade_horizon_seconds=UPGRADE_AFFORD_HORIZON_SECONDS,
        building_horizon_seconds=building_autobuyer.payback_horizon_seconds,
        wrinkler_mode=WRINKLER_MODE,
        stock_trading_enabled=ENABLE_STOCK_TRADING,
        lucky_reserve_enabled=False,
        building_autobuy_enabled=ENABLE_BUILDING_AUTOBUY,
        upgrade_autobuy_enabled=True,
        ascension_prep_enabled=False,
        garden_automation_enabled=ENABLE_GARDEN_AUTOMATION,
        main_cookie_clicking_enabled=ENABLE_MAIN_COOKIE_CLICKING,
        shimmer_autoclick_enabled=ENABLE_SHIMMER_AUTOCLICK,
    )
)
runtime_lock = runtime_store.lock
snapshot_lock = runtime_store.snapshot_lock
runtime_state = runtime_store.state
recent_events = runtime_store.recent_events
gameplay_feed = runtime_store.gameplay_feed
feed_parse_failures = 0
profile_last_log_at = {}
last_focus_warning_at = 0.0
last_focus_attempt_at = 0.0
last_game_window_missing_warning_at = 0.0


def _hud_event(_level, message):
    runtime_store.append_recent_event(message)


hud_handler = HudBufferHandler(_hud_event, level=logging.INFO)
hud_handler.setFormatter(logging.Formatter(LOG_FORMAT))
root_logger.addHandler(hud_handler)


def _set_runtime(**kwargs):
    runtime_store.update(**kwargs)


def _infer_feed_category(message):
    text = str(message or "").lower()
    if any(token in text for token in ("note", "notification", "close_all_notes", "close_note", "dismiss")):
        return "ui"
    if any(token in text for token in ("shimmer", "golden", "wrath", "reindeer")):
        return "shimmer"
    if any(token in text for token in ("spell", "pixies", "hand of fate", "stretch time")):
        return "spell"
    if any(token in text for token in ("upgrade buy", "building buy", "ascension prep", "dragon ")):
        return "purchase"
    if any(token in text for token in ("garden", "seed", "harvest")):
        return "garden"
    if "wrinkler" in text:
        return "wrinkler"
    if any(token in text for token in ("sugar lump", "lump")):
        return "lump"
    if any(token in text for token in ("trade", "stock")):
        return "trade"
    if any(token in text for token in ("clicker ", "autobuy", "mode ", "horizon")):
        return "system"
    return "event"


def _record_feed_event(message, category=None):
    _get_event_recorder().record_feed_event(message, category=category)


def _record_event(message):
    _get_event_recorder().record_event(message)


def _record_shimmer_click_runtime(shimmer_id, mode):
    with runtime_lock:
        runtime_state["shimmer_clicks"] = int(runtime_state.get("shimmer_clicks", 0)) + 1
        runtime_state["last_shimmer"] = f"id={shimmer_id} {mode}"


def _record_shimmer_collect_runtime(shimmer_kind, shimmer_id, outcome, decision_blocked):
    with runtime_lock:
        runtime_state["shimmer_collected"] = int(runtime_state.get("shimmer_collected", 0)) + 1
        runtime_state["last_shimmer"] = f"{shimmer_kind} id={shimmer_id}"
        runtime_state["last_shimmer_effect"] = (
            f"blocked {outcome}" if decision_blocked else outcome
        )


def _format_shimmer_id_list(ids, limit=8):
    values = []
    for value in ids or ():
        try:
            values.append(str(int(value)))
        except Exception:
            continue
    if not values:
        return "-"
    if len(values) <= limit:
        return ",".join(values)
    return ",".join(values[:limit]) + f",+{len(values) - limit}"


def _should_throttle_ui_action(kind, screen_x, screen_y, now, cooldown=MINIGAME_OPEN_RETRY_SECONDS):
    signature = (kind, int(screen_x), int(screen_y))
    last_at = last_ui_open_action.get(signature)
    if last_at is not None and (now - last_at) < cooldown:
        return True
    last_ui_open_action[signature] = now
    for key, value in list(last_ui_open_action.items()):
        if (now - value) >= max(cooldown * 4.0, 10.0):
            last_ui_open_action.pop(key, None)
    return False


def _ui_owner_conflicts(owner, now):
    if not owner:
        return False
    active_owner = ui_owner_lock.get("owner")
    until = float(ui_owner_lock.get("until") or 0.0)
    return bool(active_owner and active_owner != owner and now < until)


def _claim_ui_owner(owner, now, duration=UI_OWNER_LOCK_SECONDS):
    if not owner:
        return
    ui_owner_lock["owner"] = owner
    ui_owner_lock["until"] = max(float(ui_owner_lock.get("until") or 0.0), float(now) + float(duration))


def _release_ui_owner(owner):
    if owner and ui_owner_lock.get("owner") == owner:
        ui_owner_lock["owner"] = None
        ui_owner_lock["until"] = 0.0


def _wrinkler_purchase_funding_active():
    with runtime_lock:
        wrinkler_diag = runtime_state.get("last_wrinkler_diag") or {}
    return bool(
        wrinkler_diag.get("candidate_id") is not None
        and wrinkler_diag.get("pop_goal_affordable_with_bank")
    )


def _record_profile_ms(prefix, elapsed_ms, spike_ms=None):
    avg_key = f"{prefix}_avg_ms"
    max_key = f"{prefix}_max_ms"
    elapsed_ms = float(elapsed_ms)
    with runtime_lock:
        current_avg = runtime_state.get(avg_key)
        runtime_state[avg_key] = (
            elapsed_ms
            if current_avg is None
            else ((1.0 - PROFILE_EMA_ALPHA) * float(current_avg)) + (PROFILE_EMA_ALPHA * elapsed_ms)
        )
        current_max = runtime_state.get(max_key)
        runtime_state[max_key] = elapsed_ms if current_max is None else max(float(current_max), elapsed_ms)
    if spike_ms is not None:
        last_logged = float(profile_last_log_at.get(prefix, 0.0))
        now = time.monotonic()
        if elapsed_ms >= float(spike_ms) and (now - last_logged) >= 5.0:
            profile_last_log_at[prefix] = now
            log.warning(f"Profiler spike op={prefix} elapsed_ms={elapsed_ms:.1f}")


def _track_combo_run(snapshot, buffs, spell_stats, combo_stats):
    if not isinstance(snapshot, dict):
        return

    buff_names = tuple(buff.get("name") for buff in buffs if isinstance(buff, dict) and buff.get("name"))
    combo_eval = evaluate_combo_buffs(buff_names)
    stage = combo_eval.get("stage") or "idle"
    cookies = float(snapshot.get("cookies") or 0.0)
    now = time.monotonic()

    if combo_run_tracker["active"]:
        combo_run_tracker["peak_cookies"] = max(float(combo_run_tracker["peak_cookies"] or cookies), cookies)
        if COMBO_STAGE_RANK.get(stage, 0) >= COMBO_STAGE_RANK.get(combo_run_tracker["max_stage"], 0):
            combo_run_tracker["max_stage"] = stage
            combo_run_tracker["max_buffs"] = buff_names
        if stage not in COMBO_ACTIVE_STAGES:
            started_cookies = float(combo_run_tracker["started_cookies"] or cookies)
            peak_cookies = float(combo_run_tracker["peak_cookies"] or cookies)
            gain = cookies - started_cookies
            peak_gain = peak_cookies - started_cookies
            duration = now - float(combo_run_tracker["started_at"] or now)
            godzamok_uses = int(combo_stats.get("fire_count", 0)) - int(combo_run_tracker["godzamok_start"] or 0)
            spell_casts = int(spell_stats.get("cast_count", 0)) - int(combo_run_tracker["spell_cast_start"] or 0)
            with runtime_lock:
                runtime_state["combo_run_count"] = int(runtime_state.get("combo_run_count", 0)) + 1
                runtime_state["last_combo_run_gain"] = gain
                runtime_state["last_combo_run_peak_gain"] = peak_gain
                runtime_state["last_combo_run_duration"] = duration
                runtime_state["last_combo_run_stage"] = combo_run_tracker["max_stage"]
            log.info(
                f"Combo run complete stage={combo_run_tracker['max_stage']} "
                f"duration={duration:.2f}s gain={gain:.1f} peak_gain={peak_gain:.1f} "
                f"spells={spell_casts} godzamok={godzamok_uses} "
                f"start_buffs={combo_run_tracker['start_buffs']} "
                f"max_buffs={combo_run_tracker['max_buffs']}"
            )
            combo_run_tracker.update(
                {
                    "active": False,
                    "started_at": None,
                    "started_cookies": None,
                    "peak_cookies": None,
                    "start_stage": None,
                    "max_stage": None,
                    "start_buffs": (),
                    "max_buffs": (),
                    "godzamok_start": 0,
                    "spell_cast_start": 0,
                }
            )

    if (not combo_run_tracker["active"]) and stage in COMBO_ACTIVE_STAGES:
        combo_run_tracker.update(
            {
                "active": True,
                "started_at": now,
                "started_cookies": cookies,
                "peak_cookies": cookies,
                "start_stage": stage,
                "max_stage": stage,
                "start_buffs": buff_names,
                "max_buffs": buff_names,
                "godzamok_start": int(combo_stats.get("fire_count", 0)),
                "spell_cast_start": int(spell_stats.get("cast_count", 0)),
            }
        )
        log.info(
            f"Combo run started stage={stage} cookies={cookies:.1f} buffs={buff_names}"
        )


def _should_pause_non_click_actions(buffs, spell_diag=None, combo_diag=None):
    return bool(_get_non_click_pause_reasons(buffs, spell_diag=spell_diag, combo_diag=combo_diag))


def _has_named_buff(buffs, name):
    for buff in buffs or ():
        if isinstance(buff, dict) and buff.get("name") == name:
            return True
    return False


KNOWN_CLICK_VALUE_BUFFS = {
    "Click frenzy",
    "Dragonflight",
    "Cursed finger",
}


def _get_active_click_buff_names(buffs):
    return get_active_click_buff_names(
        buffs,
        production_stack_buff_keys=PRODUCTION_STACK_BUFF_KEYS,
        known_click_value_buffs=KNOWN_CLICK_VALUE_BUFFS,
    )


def _should_pause_value_actions_during_clot(buffs):
    return False


def _should_pause_stock_trading(buffs):
    return should_pause_stock_trading(buffs)


def _classify_shimmer_outcome(outcome):
    if isinstance(outcome, str):
        name = outcome.strip()
        mult_cps = None
        mult_click = None
    elif isinstance(outcome, dict):
        name = str(outcome.get("name") or outcome.get("outcome") or "").strip()
        mult_cps = outcome.get("mult_cpS") or outcome.get("multCpS")
        mult_click = outcome.get("mult_click") or outcome.get("multClick")
    else:
        return "unknown"
    if not name and mult_cps is None and mult_click is None:
        return "unknown"
    lowered = name.lower()
    mult_cps_val = float(mult_cps) if mult_cps is not None else 1.0
    mult_click_val = float(mult_click) if mult_click is not None else 1.0
    if mult_cps_val > 1.0 or mult_click_val > 1.0:
        return "positive"
    if name in KNOWN_POSITIVE_SHIMMER_OUTCOMES:
        return "positive"
    if name in KNOWN_NEGATIVE_BUFFS:
        return "negative"
    if lowered in {"blab", "free sugar lump", "no_new_buff", "unknown"}:
        return "neutral"
    if mult_cps_val < 1.0 or mult_click_val < 1.0:
        return "negative"
    return "neutral"


def _should_skip_wrath_shimmer(buffs, combo_diag=None):
    if not SKIP_WRATH_DURING_CLICK_BUFFS:
        return False
    buff_names = {buff.get("name") for buff in buffs if isinstance(buff, dict) and buff.get("name")}
    click_buff_names = _get_active_click_buff_names(buffs)
    if click_buff_names:
        return True
    combo_eval = evaluate_combo_buffs(buff_names)
    if combo_eval.get("stage") in COMBO_ACTIVE_STAGES:
        return True
    return False


def _should_defer_stock_actions_for_upgrade(
    snapshot,
    upgrade_diag,
    *,
    upgrade_autobuy_enabled,
    pause_non_click_actions=False,
    allow_upgrade_during_pause=False,
    global_cookie_reserve=0.0,
    shimmers_present=False,
    combo_pending=False,
    upgrade_signature_blocked=False,
    now=0.0,
    upgrade_blocked_until=0.0,
):
    return should_defer_stock_actions_for_upgrade(
        snapshot,
        upgrade_diag,
        upgrade_autobuy_enabled=upgrade_autobuy_enabled,
        pause_non_click_actions=pause_non_click_actions,
        allow_upgrade_during_pause=allow_upgrade_during_pause,
        global_cookie_reserve=global_cookie_reserve,
        shimmers_present=shimmers_present,
        combo_pending=combo_pending,
        upgrade_signature_blocked=upgrade_signature_blocked,
        now=now,
        upgrade_blocked_until=upgrade_blocked_until,
    )


def _get_non_click_pause_reasons(buffs, spell_diag=None, combo_diag=None):
    reasons = []
    buff_names = {buff.get("name") for buff in buffs if isinstance(buff, dict) and buff.get("name")}
    click_buff_names = _get_active_click_buff_names(buffs)
    if click_buff_names:
        reasons.append(f"click_buffs={click_buff_names}")
    combo_eval = evaluate_combo_buffs(buff_names)
    if combo_eval.get("stage") in COMBO_ACTIVE_STAGES:
        reasons.append(f"combo_stage={combo_eval.get('stage')}")
    combo_reason = None if not isinstance(combo_diag, dict) else combo_diag.get("reason")
    if combo_reason in {
        "combo_ready",
        "await_sell_confirm",
        "buffing",
        "cast_pixies",
        "rebuy_setup",
        "rebuy",
    }:
        reasons.append(f"combo_reason={combo_reason}")
    return reasons


def _find_upgrade_snapshot_entry(snapshot, upgrade_id):
    if not isinstance(snapshot, dict):
        return None
    raw_upgrades = snapshot.get("upgrades")
    if not isinstance(raw_upgrades, list):
        return None
    for item in raw_upgrades:
        if not isinstance(item, dict):
            continue
        if item.get("id") == upgrade_id:
            return item
    return None


def _find_building_snapshot_entry(snapshot, building_name=None, building_id=None):
    if not isinstance(snapshot, dict):
        return None
    raw_buildings = snapshot.get("buildings")
    if not isinstance(raw_buildings, list):
        return None
    for item in raw_buildings:
        if not isinstance(item, dict):
            continue
        if building_id is not None and item.get("id") == building_id:
            return item
        if building_name and item.get("name") == building_name:
            return item
    return None


def _estimate_conservative_buff_window_seconds(buffs):
    positive_windows = []
    for buff in buffs:
        if not isinstance(buff, dict):
            continue
        mult_cps = buff.get("multCpS")
        time_left = buff.get("time")
        if not isinstance(mult_cps, (int, float)) or float(mult_cps) <= 1.0:
            continue
        if not isinstance(time_left, (int, float)) or float(time_left) <= 0:
            continue
        positive_windows.append(float(time_left) / COOKIE_CLICKER_FPS)
    if not positive_windows:
        return 0.0
    return max(0.0, min(positive_windows))


def _estimate_upgrade_live_delta_cps(snapshot, upgrade_id):
    upgrade = _find_upgrade_snapshot_entry(snapshot, upgrade_id)
    if not isinstance(upgrade, dict):
        return None
    cookies_ps = None if not isinstance(snapshot, dict) else (
        snapshot.get("cookiesPs") if snapshot.get("cookiesPs") is not None else snapshot.get("cookiesPsRawHighest")
    )
    if not isinstance(cookies_ps, (int, float)) or float(cookies_ps) <= 0:
        return None

    power = upgrade.get("power")
    pool = upgrade.get("pool")
    tier = upgrade.get("tier")
    if pool == "cookie" and isinstance(power, (int, float)) and float(power) > 0:
        return float(cookies_ps) * (float(power) / 100.0)
    if bool(upgrade.get("kitten")) and isinstance(power, (int, float)) and float(power) > 0:
        milk_progress = snapshot.get("milkProgress") if isinstance(snapshot, dict) else None
        if isinstance(milk_progress, (int, float)) and float(milk_progress) > 0:
            return float(cookies_ps) * float(milk_progress) * float(power)

    building_tie_name = upgrade.get("buildingTieName")
    building_tie_id = upgrade.get("buildingTieId")
    if building_tie_name or building_tie_id is not None:
        building = _find_building_snapshot_entry(snapshot, building_name=building_tie_name, building_id=building_tie_id)
        stored_total_cps = None if not isinstance(building, dict) else building.get("storedTotalCps")
        global_cps_mult = snapshot.get("globalCpsMult") if isinstance(snapshot, dict) else None
        if isinstance(stored_total_cps, (int, float)) and isinstance(global_cps_mult, (int, float)):
            live_building_cps = float(stored_total_cps) * float(global_cps_mult)
            if tier == "fortune":
                return live_building_cps * 0.07
            if isinstance(tier, int) or (isinstance(tier, str) and str(tier).isdigit()):
                return live_building_cps
    return None


def _estimate_attached_wrinkler_bank(snapshot):
    if not isinstance(snapshot, dict):
        return 0.0
    wrinklers = snapshot.get("wrinklers")
    if not isinstance(wrinklers, dict):
        return 0.0
    total = 0.0
    for item in wrinklers.get("wrinklers", []):
        if not isinstance(item, dict):
            continue
        if int(item.get("phase") or 0) != 2:
            continue
        total += float(item.get("estimatedReward") or 0.0)
    return max(0.0, total)


def _resolve_upgrade_candidate_metrics(snapshot, upgrade):
    if not isinstance(upgrade, dict):
        return None

    price = upgrade.get("price")
    if not isinstance(price, (int, float)) or float(price) <= 0:
        return None
    price = float(price)

    delta_cps = upgrade.get("deltaCps")
    if not isinstance(delta_cps, (int, float)) or float(delta_cps) <= 0:
        upgrade_id = upgrade.get("id")
        if isinstance(upgrade_id, int):
            delta_cps = _estimate_upgrade_live_delta_cps(snapshot, upgrade_id)
    if not isinstance(delta_cps, (int, float)) or float(delta_cps) <= 0:
        return None
    delta_cps = float(delta_cps)

    payback_seconds = upgrade.get("paybackSeconds")
    if not isinstance(payback_seconds, (int, float)) or float(payback_seconds) <= 0:
        payback_seconds = price / delta_cps
    if not isinstance(payback_seconds, (int, float)) or float(payback_seconds) <= 0:
        return None

    candidate = dict(upgrade)
    candidate["price"] = price
    candidate["deltaCps"] = delta_cps
    candidate["paybackSeconds"] = float(payback_seconds)
    return candidate


def _evaluate_upgrade_buff_window(snapshot, buffs, upgrade_diag, pause_reasons):
    price = None if not isinstance(upgrade_diag, dict) else upgrade_diag.get("candidate_price")
    upgrade_id = None if not isinstance(upgrade_diag, dict) else upgrade_diag.get("candidate_id")
    if not isinstance(price, (int, float)) or not isinstance(upgrade_id, int):
        return {
            "allow_during_pause": False,
            "buff_window_seconds": 0.0,
            "estimated_delta_cps": None,
            "estimated_window_gain": None,
            "reason": "missing_candidate",
        }

    if not pause_reasons or any(not str(reason).startswith("valuable_buffs=") for reason in pause_reasons):
        return {
            "allow_during_pause": False,
            "buff_window_seconds": 0.0,
            "estimated_delta_cps": None,
            "estimated_window_gain": None,
            "reason": "pause_not_buff_only",
        }

    buff_window_seconds = _estimate_conservative_buff_window_seconds(buffs)
    if buff_window_seconds <= 0:
        return {
            "allow_during_pause": False,
            "buff_window_seconds": 0.0,
            "estimated_delta_cps": None,
            "estimated_window_gain": None,
            "reason": "no_positive_cps_buff_window",
        }

    estimated_delta_cps = _estimate_upgrade_live_delta_cps(snapshot, upgrade_id)
    if not isinstance(estimated_delta_cps, (int, float)) or float(estimated_delta_cps) <= 0:
        return {
            "allow_during_pause": False,
            "buff_window_seconds": buff_window_seconds,
            "estimated_delta_cps": None,
            "estimated_window_gain": None,
            "reason": "delta_not_estimable",
        }

    estimated_window_gain = float(estimated_delta_cps) * buff_window_seconds
    allow_during_pause = estimated_window_gain >= (float(price) * UPGRADE_BUFF_WINDOW_PAYBACK_THRESHOLD)
    return {
        "allow_during_pause": allow_during_pause,
        "buff_window_seconds": buff_window_seconds,
        "estimated_delta_cps": float(estimated_delta_cps),
        "estimated_window_gain": estimated_window_gain,
        "reason": "window_pays_back" if allow_during_pause else "window_below_threshold",
    }


def _has_positive_active_buffs(snapshot):
    return has_positive_active_buffs(snapshot, known_negative_buffs=KNOWN_NEGATIVE_BUFFS)


def _has_long_positive_active_buff(snapshot):
    return has_long_positive_active_buff(
        snapshot,
        known_negative_buffs=KNOWN_NEGATIVE_BUFFS,
        long_buff_threshold_frames=GARDEN_LONG_BUFF_THRESHOLD_FRAMES,
    )


def _has_buff_only_non_click_pause(pause_reasons):
    return has_buff_only_non_click_pause(pause_reasons)


def _should_allow_non_click_actions_during_pause(snapshot, pause_reasons):
    return should_allow_non_click_actions_during_pause(snapshot, pause_reasons)


def _should_allow_garden_action(snapshot, garden_diag):
    return should_allow_garden_action(
        snapshot,
        garden_diag,
        production_stack_buff_keys=PRODUCTION_STACK_BUFF_KEYS,
        known_click_value_buffs=KNOWN_CLICK_VALUE_BUFFS,
    )


def _format_number(value):
    if value is None:
        return "-"
    abs_value = abs(float(value))
    if abs_value >= 1e12:
        return f"{value/1e12:.3f}T"
    if abs_value >= 1e9:
        return f"{value/1e9:.3f}B"
    if abs_value >= 1e6:
        return f"{value/1e6:.3f}M"
    if abs_value >= 1e3:
        return f"{value/1e3:.3f}K"
    return f"{float(value):.2f}"


def _format_percent(value):
    if value is None:
        return "-"
    return f"{100.0 * float(value):.0f}%"


def _format_duration_compact(seconds):
    if seconds is None:
        return "-"
    seconds = max(0, int(round(float(seconds))))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _extract_lump_diag(snapshot, to_screen_point):
    if not isinstance(snapshot, dict):
        return {}
    lump_state = snapshot.get("lump")
    if not isinstance(lump_state, dict):
        return {}

    target = lump_state.get("target")
    target_rect = target if isinstance(target, dict) else None
    center_x = None if target_rect is None else target_rect.get("clickX", target_rect.get("centerX"))
    center_y = None if target_rect is None else target_rect.get("clickY", target_rect.get("centerY"))
    if center_x is not None and center_y is not None:
        screen_x, screen_y = to_screen_point(center_x, center_y)
    else:
        screen_x = None
        screen_y = None

    modifiers = tuple(
        str(item)
        for item in (lump_state.get("modifiers") or ())
        if isinstance(item, str) and item.strip()
    )
    ripe_seconds = None
    if isinstance(lump_state.get("timeToRipeMs"), (int, float)):
        ripe_seconds = max(0.0, float(lump_state.get("timeToRipeMs")) / 1000.0)
    overripe_seconds = None
    if isinstance(lump_state.get("timeToOverripeMs"), (int, float)):
        overripe_seconds = max(0.0, float(lump_state.get("timeToOverripeMs")) / 1000.0)

    unlocked = bool(lump_state.get("unlocked"))
    is_ripe = bool(lump_state.get("isRipe"))
    stage = str(lump_state.get("stage") or ("locked" if not unlocked else "unknown"))
    if not unlocked:
        reason = "locked"
    elif center_x is None or center_y is None:
        reason = "missing_target"
    elif is_ripe:
        reason = "ripe_ready"
    else:
        reason = f"waiting_{stage}"

    return {
        "reason": reason,
        "unlocked": unlocked,
        "stage": stage,
        "is_mature": bool(lump_state.get("isMature")),
        "is_ripe": is_ripe,
        "lumps": lump_state.get("lumps"),
        "lumps_total": lump_state.get("lumpsTotal"),
        "current_type": lump_state.get("currentType"),
        "current_type_name": lump_state.get("currentTypeName") or "normal",
        "age_ms": lump_state.get("ageMs"),
        "mature_age_ms": lump_state.get("matureAgeMs"),
        "ripe_age_ms": lump_state.get("ripeAgeMs"),
        "overripe_age_ms": lump_state.get("overripeAgeMs"),
        "time_to_mature_seconds": None
        if not isinstance(lump_state.get("timeToMatureMs"), (int, float))
        else max(0.0, float(lump_state.get("timeToMatureMs")) / 1000.0),
        "time_to_ripe_seconds": ripe_seconds,
        "time_to_overripe_seconds": overripe_seconds,
        "screen_x": None if screen_x is None else int(screen_x),
        "screen_y": None if screen_y is None else int(screen_y),
        "has_target": screen_x is not None and screen_y is not None,
        "can_click": is_ripe and screen_x is not None and screen_y is not None,
        "modifiers": modifiers,
        "grandmas": lump_state.get("grandmas"),
        "refill": lump_state.get("refill"),
        "can_refill": lump_state.get("canRefill"),
    }


def _estimate_golden_cookie_spawn_distribution(current_time, min_time, max_time, *, horizon_seconds=60, step_frames=30):
    if not all(isinstance(value, (int, float)) for value in (current_time, min_time, max_time)):
        return None
    current_time = max(0.0, float(current_time))
    min_time = max(0.0, float(min_time))
    max_time = max(min_time, float(max_time))
    if max_time <= 0.0:
        return None
    step_frames = max(1, int(step_frames))
    horizon_seconds = max(1, int(horizon_seconds))

    curve = []
    survival = 1.0
    frame_cursor = current_time
    median_seconds = None
    expected_seconds = 0.0
    chance_10 = 0.0
    chance_30 = 0.0
    chance_60 = 0.0

    for second in range(1, horizon_seconds + 1):
        second_spawn = 0.0
        for _ in range(step_frames):
            frame_cursor += COOKIE_CLICKER_FPS / step_frames
            if max_time <= min_time:
                progress = 1.0 if frame_cursor >= max_time else 0.0
            else:
                progress = max(0.0, min(1.0, (frame_cursor - min_time) / (max_time - min_time)))
            per_tick = progress ** 5
            spawn_now = survival * per_tick
            second_spawn += spawn_now
            survival *= max(0.0, 1.0 - per_tick)
            if survival <= 1e-12:
                survival = 0.0
                break
        cumulative = max(0.0, min(1.0, 1.0 - survival))
        curve.append({"second": second, "cumulative": cumulative})
        expected_seconds += survival
        if chance_10 == 0.0 and second >= 10:
            chance_10 = cumulative
        if chance_30 == 0.0 and second >= 30:
            chance_30 = cumulative
        if chance_60 == 0.0 and second >= 60:
            chance_60 = cumulative
        if median_seconds is None and cumulative >= 0.5:
            median_seconds = float(second)
        if survival <= 0.0:
            for tail_second in range(second + 1, horizon_seconds + 1):
                curve.append({"second": tail_second, "cumulative": 1.0})
            break

    if chance_10 == 0.0 and curve:
        chance_10 = curve[min(len(curve), 10) - 1]["cumulative"]
    if chance_30 == 0.0 and curve:
        chance_30 = curve[min(len(curve), 30) - 1]["cumulative"]
    if chance_60 == 0.0 and curve:
        chance_60 = curve[min(len(curve), 60) - 1]["cumulative"]

    return {
        "curve": tuple(curve),
        "chance_within_10s": chance_10,
        "chance_within_30s": chance_30,
        "chance_within_60s": chance_60,
        "median_remaining_seconds": median_seconds,
        "expected_remaining_seconds": expected_seconds,
    }


def _extract_golden_cookie_diag(snapshot):
    if not isinstance(snapshot, dict):
        return {"available": False, "reason": "no_snapshot"}
    golden = snapshot.get("goldenCookie")
    if not isinstance(golden, dict):
        return {"available": False, "reason": "no_golden_cookie_data"}
    time_frames = golden.get("time")
    min_frames = golden.get("minTime")
    max_frames = golden.get("maxTime")
    on_screen = int(golden.get("onScreen") or 0)
    if not all(isinstance(value, (int, float)) for value in (time_frames, min_frames, max_frames)):
        return {
            "available": True,
            "reason": "missing_timer",
            "on_screen": on_screen,
            "time_frames": time_frames,
            "min_time_frames": min_frames,
            "max_time_frames": max_frames,
        }

    time_frames = max(0.0, float(time_frames))
    min_frames = max(0.0, float(min_frames))
    max_frames = max(min_frames, float(max_frames))
    if max_frames <= min_frames:
        progress = 1.0 if time_frames >= max_frames else 0.0
    else:
        progress = max(0.0, min(1.0, (time_frames - min_frames) / (max_frames - min_frames)))
    per_tick_spawn_probability = progress ** 5
    distribution = _estimate_golden_cookie_spawn_distribution(time_frames, min_frames, max_frames)
    return {
        "available": True,
        "reason": "tracking_spawn_window",
        "on_screen": on_screen,
        "time_frames": time_frames,
        "min_time_frames": min_frames,
        "max_time_frames": max_frames,
        "elapsed_seconds": time_frames / COOKIE_CLICKER_FPS,
        "min_seconds": min_frames / COOKIE_CLICKER_FPS,
        "max_seconds": max_frames / COOKIE_CLICKER_FPS,
        "progress": progress,
        "spawn_pressure": per_tick_spawn_probability,
        "spawn_curve": () if not isinstance(distribution, dict) else distribution["curve"],
        "chance_within_10s": None if not isinstance(distribution, dict) else distribution["chance_within_10s"],
        "chance_within_30s": None if not isinstance(distribution, dict) else distribution["chance_within_30s"],
        "chance_within_60s": None if not isinstance(distribution, dict) else distribution["chance_within_60s"],
        "median_remaining_seconds": None if not isinstance(distribution, dict) else distribution["median_remaining_seconds"],
        "expected_remaining_seconds": None if not isinstance(distribution, dict) else distribution["expected_remaining_seconds"],
    }


def get_dashboard_state():
    return _get_dashboard_state_builder().build()


def _render_hud():
    state, events, _feed = runtime_store.snapshot_state()
    trade_stats = stock_trader.get_runtime_stats()
    building_stats = building_autobuyer.get_runtime_stats()
    garden_stats = garden_controller.get_runtime_stats()
    combo_stats = godzamok_combo.get_runtime_stats()
    spell_stats = spell_autocaster.get_runtime_stats()
    wrinkler_stats = wrinkler_controller.get_runtime_stats()
    uptime = time.monotonic() - state["started_at"]
    uptime_text = time.strftime("%H:%M:%S", time.gmtime(max(0, int(uptime))))
    shimmer_per_hour = 0.0 if uptime <= 0 else (state["shimmer_collected"] * 3600.0 / uptime)
    candidate_payback = state["last_building_diag"].get("candidate_payback_seconds")
    candidate_payback_text = "-" if candidate_payback is None else f"{float(candidate_payback):.1f}s"
    upgrade_payback = state["last_upgrade_diag"].get("candidate_payback_seconds")
    upgrade_payback_text = "-" if upgrade_payback is None else f"{float(upgrade_payback):.1f}s"
    feed_load_text = "-" if state["feed_load_ms"] is None else f"{float(state['feed_load_ms']):.1f}ms"
    feed_parse_text = "-" if state["feed_parse_ms"] is None else f"{float(state['feed_parse_ms']):.1f}ms"
    click_loop_text = "-" if state["click_loop_avg_ms"] is None else f"{float(state['click_loop_avg_ms']):.1f}/{float(state['click_loop_max_ms']):.1f}ms"
    click_action_text = "-" if state["click_action_avg_ms"] is None else f"{float(state['click_action_avg_ms']):.1f}/{float(state['click_action_max_ms']):.1f}ms"
    dom_loop_text = "-" if state["dom_loop_avg_ms"] is None else f"{float(state['dom_loop_avg_ms']):.1f}/{float(state['dom_loop_max_ms']):.1f}ms"
    dom_extract_text = "-" if state["dom_extract_avg_ms"] is None else f"{float(state['dom_extract_avg_ms']):.1f}/{float(state['dom_extract_max_ms']):.1f}ms"
    dom_diag_text = "-" if state["dom_diag_avg_ms"] is None else f"{float(state['dom_diag_avg_ms']):.1f}/{float(state['dom_diag_max_ms']):.1f}ms"
    dom_shimmer_text = "-" if state["dom_shimmer_avg_ms"] is None else f"{float(state['dom_shimmer_avg_ms']):.1f}/{float(state['dom_shimmer_max_ms']):.1f}ms"
    dom_action_text = "-" if state["dom_action_avg_ms"] is None else f"{float(state['dom_action_avg_ms']):.1f}/{float(state['dom_action_max_ms']):.1f}ms"
    snapshot_profile = state.get("snapshot_profile") or {}
    snapshot_total_text = "-" if snapshot_profile.get("totalMs") is None else f"{float(snapshot_profile['totalMs']):.1f}ms"
    snapshot_upgrade_text = "-" if snapshot_profile.get("upgradesMs") is None else f"{float(snapshot_profile['upgradesMs']):.1f}ms"
    snapshot_spellbook_text = "-" if snapshot_profile.get("spellbookMs") is None else f"{float(snapshot_profile['spellbookMs']):.1f}ms"
    snapshot_garden_text = "-" if snapshot_profile.get("gardenMs") is None else f"{float(snapshot_profile['gardenMs']):.1f}ms"
    stock_profile = state.get("stock_profile") or {}
    db_profile = state.get("db_profile") or {}
    stock_diag_text = "-" if "get_diagnostics" not in stock_profile else f"{float(stock_profile['get_diagnostics']['avg_ms']):.1f}/{float(stock_profile['get_diagnostics']['max_ms']):.1f}ms"
    stock_extract_text = "-" if "extract_state" not in stock_profile else f"{float(stock_profile['extract_state']['avg_ms']):.1f}/{float(stock_profile['extract_state']['max_ms']):.1f}ms"
    db_range_text = "-" if "get_recent_range_stats" not in db_profile else f"{float(db_profile['get_recent_range_stats']['avg_ms']):.1f}/{float(db_profile['get_recent_range_stats']['max_ms']):.1f}ms"
    db_series_text = "-" if "get_price_series" not in db_profile else f"{float(db_profile['get_price_series']['avg_ms']):.1f}/{float(db_profile['get_price_series']['max_ms']):.1f}ms"
    spell_magic = state["last_spell_diag"].get("magic")
    spell_max_magic = state["last_spell_diag"].get("max_magic")
    spell_mana_text = (
        "-"
        if spell_magic is None or spell_max_magic is None
        else f"{float(spell_magic):.1f}/{float(spell_max_magic):.1f}"
    )
    trade_exposure_ratio = state["last_bank_diag"].get("portfolio_exposure_ratio")
    trade_exposure_pct = _format_percent(trade_exposure_ratio)
    trade_total_funds = None
    if (
        state["last_bank_diag"].get("portfolio_exposure") is not None
        and state["last_bank_diag"].get("cookies") is not None
    ):
        trade_total_funds = (
            float(state["last_bank_diag"].get("portfolio_exposure"))
            + float(state["last_bank_diag"].get("cookies"))
        )
    trade_hold_text = "-"
    portfolio_cap = state["last_bank_diag"].get("portfolio_cap")
    buy_reserve = state["last_bank_diag"].get("buy_reserve_cookies")
    trade_hold_parts = []
    if isinstance(portfolio_cap, (int, float)):
        trade_hold_parts.append(f"cap={_format_number(portfolio_cap)}")
    if isinstance(buy_reserve, (int, float)) and float(buy_reserve) > 0:
        trade_hold_parts.append(f"reserve={_format_number(buy_reserve)}")
    if trade_hold_parts:
        trade_hold_text = ", ".join(trade_hold_parts)
    upgrade_hold_text = "-"
    upgrade_garden_reserve = state["last_upgrade_diag"].get("garden_cookie_reserve")
    upgrade_lucky_reserve = state["last_upgrade_diag"].get("lucky_cookie_reserve")
    upgrade_hold_parts = []
    if isinstance(upgrade_garden_reserve, (int, float)) and float(upgrade_garden_reserve) > 0:
        upgrade_hold_parts.append(f"garden reserve={_format_number(upgrade_garden_reserve)}")
    if isinstance(upgrade_lucky_reserve, (int, float)) and float(upgrade_lucky_reserve) > 0:
        upgrade_hold_parts.append(f"lucky reserve={_format_number(upgrade_lucky_reserve)}")
    if upgrade_hold_parts:
        upgrade_hold_text = ", ".join(upgrade_hold_parts)
    building_hold_text = "-"
    building_hold_parts = []
    building_garden_reserve = state["last_building_diag"].get("garden_cookie_reserve")
    building_lucky_reserve = state["last_building_diag"].get("lucky_cookie_reserve")
    autobuyer_reserve = state["last_building_diag"].get("autobuyer_reserve")
    if isinstance(building_garden_reserve, (int, float)) and float(building_garden_reserve) > 0:
        building_hold_parts.append(f"garden reserve={_format_number(building_garden_reserve)}")
    if isinstance(building_lucky_reserve, (int, float)) and float(building_lucky_reserve) > 0:
        building_hold_parts.append(f"lucky reserve={_format_number(building_lucky_reserve)}")
    if isinstance(autobuyer_reserve, (int, float)) and float(autobuyer_reserve) > 0:
        building_hold_parts.append(f"autobuyer reserve={_format_number(autobuyer_reserve)}")
    cap_floor = state["last_building_diag"].get("cap_floor")
    spendable = state["last_building_diag"].get("spendable")
    if isinstance(cap_floor, (int, float)) and float(cap_floor) > 0:
        building_hold_parts.append(f"cap floor={_format_number(cap_floor)}")
    if isinstance(spendable, (int, float)):
        building_hold_parts.append(f"spendable={_format_number(spendable)}")
    if building_hold_parts:
        building_hold_text = ", ".join(building_hold_parts)
    lump_diag = state.get("last_lump_diag") or {}
    lump_modifiers = ", ".join(lump_diag.get("modifiers", ())) or "-"
    lump_stage_text = (
        f"{lump_diag.get('stage', '-')} {lump_diag.get('current_type_name', '-')}"
        if lump_diag.get("unlocked")
        else "locked"
    )
    lump_timer_text = _format_duration_compact(lump_diag.get("time_to_ripe_seconds"))
    lump_overripe_text = _format_duration_compact(lump_diag.get("time_to_overripe_seconds"))

    lines = [
        "Cookie Clicker Bot HUD",
        "=" * 72,
        (
            f"State: {'ON' if state['active'] else 'OFF'}"
            f" | Uptime: {uptime_text}"
            f" | Feed age: {state['last_feed_age'] if state['last_feed_age'] is not None else '-'}"
            f" | Feed load: {feed_load_text}"
            f" | Parse: {feed_parse_text}"
            f" | Stock trading: {'ON' if state['stock_trading_enabled'] else 'OFF'}"
            f" | Lucky reserve: {'ON' if state.get('lucky_reserve_enabled') else 'OFF'}"
            f" | Building autobuy: {'ON' if state['building_autobuy_enabled'] else 'OFF'}"
            f" | Upgrade autobuy: {'ON' if state['upgrade_autobuy_enabled'] else 'OFF'}"
            f" | Ascension prep: {'ON' if state.get('ascension_prep_enabled') else 'OFF'}"
            f" | Garden: {'ON' if state['garden_automation_enabled'] else 'OFF'}"
            f" | Wrinklers: {state['wrinkler_mode']}"
        ),
        (
            f"Clicks: main={state['main_clicks']} shimmer={state['shimmer_clicks']}"
            f" | Collected: {state['shimmer_collected']}"
            f" | Shimmers/h: {shimmer_per_hour:.1f}"
            f" | Last shimmer: {state['last_shimmer'] or '-'}"
        ),
        (
            f"Click loop: idle_misses={state['click_idle_misses']}"
            f" | suppressed={state['click_suppressed_loops']}"
            f" | Last cookie: {state['last_big_cookie'] or '-'}"
        ),
        (
            f"Perf: click loop={click_loop_text}"
            f" | click action={click_action_text}"
            f" | dom loop={dom_loop_text}"
        ),
        (
            f"Perf split: extract={dom_extract_text}"
            f" | diag={dom_diag_text}"
            f" | shimmer={dom_shimmer_text}"
            f" | action={dom_action_text}"
        ),
        (
            f"Snapshot perf: total={snapshot_total_text}"
            f" | upgrades={snapshot_upgrade_text}"
            f" | spellbook={snapshot_spellbook_text}"
            f" | garden={snapshot_garden_text}"
        ),
        (
            f"Stock perf: diag={stock_diag_text}"
            f" | extract={stock_extract_text}"
            f" | db range={db_range_text}"
            f" | db series={db_series_text}"
        ),
        (
            f"Shimmer effect: {state['last_shimmer_effect'] or '-'}"
            f" | Buffs: {', '.join(state['last_buffs'][:4]) if state['last_buffs'] else '-'}"
        ),
        (
            f"Spell: {spell_stats['cast_count']} casts"
            f" | Last: {spell_stats['last_spell'] or '-'}"
            f" | Mana: {spell_mana_text}"
            f" | Candidate: {state['last_spell_diag'].get('candidate', '-')}"
        ),
        (
            f"Spell state: {state['last_spell_diag'].get('reason', '-')}"
            f" | Buffs: {', '.join(state['last_spell_diag'].get('valuable_buffs', ())) or '-'}"
            f" | Wrinklers: {state['last_spell_diag'].get('wrinklers_active', '-')}/"
            f"{state['last_spell_diag'].get('wrinklers_max', '-')}"
        ),
        (
            f"Spell ready: {state['last_spell_diag'].get('ready_spells', '-')}"
            f" / {state['last_spell_diag'].get('spells_total', '-')}"
            f" | Open slots: {state['last_spell_diag'].get('wrinklers_open_slots', '-')}"
            f" | Last cast: {state['last_spell_cast'] or '-'}"
        ),
        (
            f"Wrinklers: mode={state['last_wrinkler_diag'].get('mode', wrinkler_stats['mode'])}"
            f" | clicks={wrinkler_stats['pop_clicks']}"
            f" | Last: {wrinkler_stats['last_wrinkler'] or '-'}"
            f" | State: {state['last_wrinkler_diag'].get('reason', '-')}"
        ),
        (
            f"Wrinkler fill: {state['last_wrinkler_diag'].get('attached', '-')}/"
            f"{state['last_wrinkler_diag'].get('max', '-')}"
            f" attached | Active: {state['last_wrinkler_diag'].get('active', '-')}"
            f" | Open: {state['last_wrinkler_diag'].get('open_slots', '-')}"
            f" | Shiny: {state['last_wrinkler_diag'].get('shiny', '-')}"
        ),
        (
            f"Wrinkler next: id={state['last_wrinkler_diag'].get('candidate_id', '-')}"
            f" | Type: {state['last_wrinkler_diag'].get('candidate_type', '-')}"
            f" | Reward: {_format_number(state['last_wrinkler_diag'].get('candidate_reward'))}"
            f" | Clicks: {state['last_wrinkler_diag'].get('candidate_clicks', '-')}"
        ),
        (
            f"Godzamok: fires={combo_stats['fire_count']}"
            f" | Last: {combo_stats['last_combo'] or '-'}"
            f" | State: {state['last_combo_diag'].get('reason', '-')}"
        ),
        (
            f"Godzamok next: {state['last_combo_diag'].get('candidate_building', '-')}"
            f" x{state['last_combo_diag'].get('candidate_quantity', '-')}"
            f" | Gain: {_format_number(state['last_combo_diag'].get('candidate_gain'))}"
            f" | Net: {_format_number(state['last_combo_diag'].get('candidate_net'))}"
            f" | Pixies: {'YES' if state['last_combo_diag'].get('candidate_uses_pixies') else 'NO'}"
        ),
        (
            f"Combo runs: {state['combo_run_count']}"
            f" | Last gain: {_format_number(state['last_combo_run_gain'])}"
            f" | Peak: {_format_number(state['last_combo_run_peak_gain'])}"
            f" | Duration: "
            f"{'-' if state['last_combo_run_duration'] is None else format(float(state['last_combo_run_duration']), '.2f') + 's'}"
        ),
        (
            f"Combo result: {state['last_combo_run_stage'] or '-'}"
            f" | Active: {'YES' if combo_run_tracker.get('active') else 'NO'}"
            f" | Start: {combo_run_tracker.get('start_stage') or '-'}"
        ),
        (
            f"Trading: pnl={_format_number(trade_stats['realized_pnl'])}"
            f" | buys={trade_stats['buy_confirms']}/{trade_stats['buy_clicks']}"
            f" | sells={trade_stats['sell_confirms']}/{trade_stats['sell_clicks']}"
            f" | held={trade_stats['held_goods']} goods / {trade_stats['held_shares']} shares"
        ),
        (
            f"Trade exposure: {_format_number(state['last_bank_diag'].get('portfolio_exposure'))}"
            f" / {_format_number(trade_total_funds)}"
            f" ({trade_exposure_pct} deployed)"
            f" | Cash: {_format_number(state['last_bank_diag'].get('cookies'))}"
        ),
        (
            f"Trade last: {trade_stats['last_trade'] or '-'}"
            f" | Brokers: {state['last_bank_diag'].get('brokers', '-')}"
            f" | State: {state['last_bank_diag'].get('reason', '-')}"
            f" | Hold: {trade_hold_text}"
        ),
        (
            f"Trade picks: buy={state['last_bank_diag'].get('buy_candidate', '-')}"
            f" | Candidate sell: {state['last_bank_diag'].get('sell_candidate', '-')}"
        ),
        (
            f"Trade bands: buy<={_format_number(state['last_bank_diag'].get('buy_threshold'))}"
            f" | sell>={_format_number(state['last_bank_diag'].get('sell_threshold'))}"
            f" | Learned goods: {state['last_bank_diag'].get('goods_with_thresholds', '-')}"
        ),
        (
            f"Garden: state={state['last_garden_diag'].get('reason', '-')}"
            f" | Open: {'YES' if state['last_garden_diag'].get('has_open_target') else 'NO'}"
            f" | On minigame: {'YES' if state['last_garden_diag'].get('on_minigame') else 'NO'}"
            f" | Farm lvl: {state['last_garden_diag'].get('farm_level', '-')}"
            f" | Actions: {garden_stats['action_count']}"
        ),
        (
            f"Garden soil: {state['last_garden_diag'].get('soil', '-')}"
            f" | Freeze: {'YES' if state['last_garden_diag'].get('freeze') else 'NO'}"
            f" | Next tick: {state['last_garden_diag'].get('next_tick', '-')}"
            f" | Next soil: {state['last_garden_diag'].get('next_soil', '-')}"
        ),
        (
            f"Garden plot: {state['last_garden_diag'].get('plot_width', '-')}"
            f"x{state['last_garden_diag'].get('plot_height', '-')}"
            f" | Tiles: {state['last_garden_diag'].get('plot_tile_count', '-')}"
            f" | Occupied: {state['last_garden_diag'].get('plot_occupied', '-')}"
            f" | Mature: {state['last_garden_diag'].get('plot_mature', '-')}"
        ),
        (
            f"Garden seeds: {state['last_garden_diag'].get('plants_unlocked', '-')}/"
            f"{state['last_garden_diag'].get('plants_total', '-')}"
            f" unlocked | Selected: {state['last_garden_diag'].get('selected_seed', '-')}"
            f" | Next lock: {state['last_garden_diag'].get('next_locked_seed', '-')}"
        ),
        (
            f"Garden last: {garden_stats['last_garden'] or '-'}"
            f" | Mode: {state['last_garden_diag'].get('plan_mode', '-')}"
            f" | Tile targets: {state['last_garden_diag'].get('plots_with_targets', '-')}"
            f" | Seed count: {state['last_garden_diag'].get('seeds_total', '-')}"
            f" | Plan: {state['last_garden_diag'].get('plan_target', '-')}"
        ),
        (
            f"Garden plan: {state['last_garden_diag'].get('planner_state', '-')}"
            f" | Parents: {', '.join(state['last_garden_diag'].get('plan_parents', ())) or '-'}"
            f" | Last action: {state['last_garden_action'] or '-'}"
        ),
        (
            f"Garden target: {'YES' if state['last_garden_diag'].get('target_present') else 'NO'}"
            f" | Mature: {'YES' if state['last_garden_diag'].get('target_mature') else 'NO'}"
            f" | Tiles: {state['last_garden_diag'].get('target_tiles', '-')}"
        ),
        (
            f"Garden funds: cash={_format_number(state['last_garden_diag'].get('cookies'))}"
            f" | Need={_format_number(state['last_garden_diag'].get('remaining_layout_cost'))}"
            f" | Affordable: {'YES' if state['last_garden_diag'].get('can_afford_layout') else 'NO'}"
        ),
        (
            f"Sugar lump: count={_format_number(lump_diag.get('lumps'))}"
            f" | Total={_format_number(lump_diag.get('lumps_total'))}"
            f" | State: {lump_diag.get('reason', '-')}"
            f" | Last action: {state.get('last_lump_action') or '-'}"
        ),
        (
            f"Lump next: {lump_stage_text}"
            f" | Ripe in: {lump_timer_text}"
            f" | Overripe in: {lump_overripe_text}"
            f" | Ready: {'YES' if lump_diag.get('can_click') else 'NO'}"
        ),
        (
            f"Lump modifiers: {lump_modifiers}"
            f" | Grandmas: {lump_diag.get('grandmas', '-')}"
            f" | Refill: {'YES' if lump_diag.get('can_refill') else 'NO'}"
        ),
        (
            f"Upgrades: in store={state['last_upgrade_diag'].get('upgrades_total', '-')}"
            f" | Affordable: {state['last_upgrade_diag'].get('affordable', '-')}"
            f" | Candidate: {state['last_upgrade_diag'].get('candidate', '-')}"
        ),
        (
            f"Upgrade next: {_format_number(state['last_upgrade_diag'].get('candidate_price'))}"
            f" | Delta cps: {_format_number(state['last_upgrade_diag'].get('candidate_delta_cps'))}"
            f" | Payback: {upgrade_payback_text}"
        ),
        (
            f"Upgrade state: {state['last_upgrade_diag'].get('reason', '-')}"
            f" | Pool: {state['last_upgrade_diag'].get('candidate_pool', '-')}"
            f" | Hold: {upgrade_hold_text}"
        ),
        (
            f"Dragon: state={state['last_dragon_diag'].get('reason', '-')}"
            f" | Level: {state['last_dragon_diag'].get('level', '-')}/"
            f"{state['last_dragon_diag'].get('max_level', '-')}"
            f" | Current: {state['last_dragon_diag'].get('current_name', '-')}"
        ),
        (
            f"Dragon next: {state['last_dragon_diag'].get('next_action', '-')}"
            f" | Cost: {state['last_dragon_diag'].get('next_cost_text', '-')}"
            f" | Aura: {state['last_dragon_diag'].get('aura_primary', '-')}"
            f" | Last action: {state['last_dragon_action'] or '-'}"
        ),
        (
            f"Dragon floor: {state['last_dragon_diag'].get('next_required_building_name', '-')}"
            f" {state['last_dragon_diag'].get('next_required_building_owned', '-')}/"
            f"{state['last_dragon_diag'].get('next_required_building_amount', '-')}"
            f" | Type: {state['last_dragon_diag'].get('next_cost_type', '-')}"
        ),
        (
            f"Buildings: clicks={building_stats['buy_clicks']}"
            f" | Last: {building_stats['last_building'] or '-'}"
            f" | Candidate: {state['last_building_diag'].get('candidate', '-')}"
            f" | Reserve: { _format_number(state['last_building_diag'].get('reserve')) }"
        ),
        (
            f"Building next: {_format_number(state['last_building_diag'].get('candidate_price'))}"
            f" | Delta cps: {_format_number(state['last_building_diag'].get('candidate_delta_cps'))}"
            f" | Payback: {candidate_payback_text}"
        ),
        (
            f"Building state: {state['last_building_diag'].get('reason', '-')}"
            f" | Last action: {state['last_building_action'] or '-'}"
            f" | Affordable: {state['last_building_diag'].get('affordable', '-')}"
            f" | Hold: {building_hold_text}"
        ),
        (
            f"Building total: {state['last_building_diag'].get('total_buildings', '-')}"
            f" | Temple align: {'YES' if state['last_building_diag'].get('temple_aligned') else 'NO'}"
            f" | Buys to x{state['last_building_diag'].get('temple_modulus', '-')}: "
            f"{state['last_building_diag'].get('buys_to_alignment', '-')}"
        ),
        (
            f"Building cap: keep {_format_number(state['last_building_diag'].get('cap_floor'))}"
            f" ({100.0 * float(state['last_building_diag'].get('spend_cap_ratio', 0.0)):.0f}% spend)"
            f" | Spendable: {_format_number(state['last_building_diag'].get('spendable'))}"
        ),
        "-" * 72,
        "Recent events:",
    ]
    if events:
        lines.extend(events[-HUD_RECENT_EVENTS:])
    else:
        lines.append("(none)")
    return "\x1b[2J\x1b[H" + "\n".join(lines[:40])


def hud_loop():
    while True:
        try:
            sys.stdout.write(_render_hud())
            sys.stdout.flush()
            time.sleep(HUD_REFRESH_INTERVAL)
        except Exception:
            time.sleep(1.0)


def start_dashboard():
    dashboard_geometry = _get_dashboard_geometry()
    callbacks = DashboardCallbacks(
        get_dashboard_state=get_dashboard_state,
        toggle_active=lambda: toggle(source="hud_button"),
        toggle_main_autoclick=lambda: toggle_main_autoclick(source="hud_button"),
        toggle_shimmer_autoclick=lambda: toggle_shimmer_autoclick(source="hud_button"),
        toggle_stock_buying=lambda: toggle_stock_trading(source="hud_button"),
        toggle_lucky_reserve=lambda: toggle_lucky_reserve(source="hud_button"),
        toggle_building_buying=lambda: toggle_building_autobuy(source="hud_button"),
        toggle_upgrade_buying=lambda: toggle_upgrade_autobuy(source="hud_button"),
        toggle_ascension_prep=lambda: toggle_ascension_prep(source="hud_button"),
        set_upgrade_horizon_seconds=set_upgrade_horizon_seconds,
        set_building_horizon_seconds=set_building_horizon_seconds,
        set_building_cap=set_building_cap,
        set_building_cap_ignored=set_building_cap_ignored,
        cycle_wrinkler_mode=cycle_wrinkler_mode,
        exit_program=exit_program,
        dump_shimmer_data=_dump_shimmer_seed_history,
    )
    return build_dashboard(
        callbacks=callbacks,
        initial_geometry=dashboard_geometry,
        refresh_interval_ms=max(100, int(HUD_REFRESH_INTERVAL * 1000.0)),
    )


def _log_automation_mode_change(feature, enabled, *, source="unknown"):
    log.info(
        f"{feature} {'ON' if enabled else 'OFF'} source={source} "
        f"active={int(bool(active))} "
        f"building_autobuy={int(bool(building_autobuy_enabled))} "
        f"upgrade_autobuy={int(bool(upgrade_autobuy_enabled))} "
        f"stock_buying={int(bool(stock_trading_enabled))} "
        f"lucky_reserve={int(bool(lucky_reserve_enabled))} "
        f"ascension_prep={int(bool(ascension_prep_enabled))}"
    )


def _file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sync_mod_files():
    try:
        MOD_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        log.exception(f"Failed to create mod install dir: {MOD_INSTALL_DIR}")
        return

    for filename in MOD_SYNC_FILES:
        source = MOD_SOURCE_DIR / filename
        dest = MOD_INSTALL_DIR / filename

        if not source.exists():
            log.warning(f"Mod sync skipped missing source file: {source}")
            continue

        should_copy = not dest.exists()
        source_hash = None
        dest_hash = None
        if not should_copy:
            try:
                source_hash = _file_sha256(source)
                dest_hash = _file_sha256(dest)
                should_copy = source_hash != dest_hash
            except Exception:
                log.exception(f"Failed hashing mod file pair source={source} dest={dest}")
                should_copy = True

        if not should_copy:
            log.debug(f"Mod sync up-to-date: {filename}")
            continue

        try:
            shutil.copy2(source, dest)
            if source_hash is None:
                source_hash = _file_sha256(source)
            log.info(
                f"Mod sync copied {filename} to game folder "
                f"source_hash={source_hash[:12]} dest={dest}"
            )
        except Exception:
            log.exception(f"Failed to copy mod file source={source} dest={dest}")


def _click(x, y, hold=0.01, debug=False, move_duration=0):
    target = (int(x), int(y))
    pyautogui.moveTo(target[0], target[1], duration=max(0, float(move_duration)), _pause=False)
    if debug:
        actual_pos = pyautogui.position()
        actual = (int(actual_pos.x), int(actual_pos.y))
        try:
            hwnd = win32gui.WindowFromPoint(actual)
            title = win32gui.GetWindowText(hwnd) if hwnd else ""
            cls = win32gui.GetClassName(hwnd) if hwnd else ""
        except Exception:
            hwnd = None
            title = ""
            cls = ""
        log.debug(
            f"_click: target={target} actual={actual} "
            f"hwnd={hwnd} class='{cls}' title='{title}'"
        )
    pyautogui.mouseDown(x=target[0], y=target[1], button="left", _pause=False)
    time.sleep(hold)
    pyautogui.mouseUp(x=target[0], y=target[1], button="left", _pause=False)


def _move_mouse(x, y):
    target = (int(x), int(y))
    pyautogui.moveTo(target[0], target[1], duration=0, _pause=False)


def _click_shimmer(x, y, hold=BONUS_CLICK_HOLD):
    _click(x, y, hold=hold)


def _scroll(x, y, steps):
    target = (int(x), int(y))
    pyautogui.moveTo(target[0], target[1], duration=0, _pause=False)
    pyautogui.scroll(int(steps) * STORE_SCROLL_WHEEL_MULTIPLIER, _pause=False)


def _format_store_planner_context(context):
    if not isinstance(context, dict):
        return ""
    return (
        f" planner_reason={context.get('reason')} "
        f"building_visible={int(bool(context.get('building_visible')))} "
        f"fully_visible={int(bool(context.get('fully_visible')))} "
        f"center_in_view={int(bool(context.get('center_within_viewport')))} "
        f"delta_y={context.get('delta_y')} "
        f"padding={context.get('padding')} "
        f"viewport=({context.get('viewport_left')},{context.get('viewport_top')})-"
        f"({context.get('viewport_right')},{context.get('viewport_bottom')}) "
        f"target=({context.get('target_left')},{context.get('target_top')})-"
        f"({context.get('target_right')},{context.get('target_bottom')}) "
        f"target_center=({context.get('target_center_x')},{context.get('target_center_y')})"
    )


def _format_upgrade_planner_context(context):
    if not isinstance(context, dict):
        return ""
    return (
        f" planner_reason={context.get('reason')} "
        f"upgrade_visible={int(bool(context.get('upgrade_visible')))} "
        f"row_in_view={int(bool(context.get('row_within_viewport')))} "
        f"center_in_view={int(bool(context.get('center_within_viewport')))} "
        f"actionable={int(bool(context.get('actionable')))} "
        f"padding={context.get('padding')} "
        f"viewport=({context.get('viewport_left')},{context.get('viewport_top')})-"
        f"({context.get('viewport_right')},{context.get('viewport_bottom')}) "
        f"target=({context.get('target_left')},{context.get('target_top')})-"
        f"({context.get('target_right')},{context.get('target_bottom')}) "
        f"target_center=({context.get('target_center_x')},{context.get('target_center_y')})"
    )


def _get_note_dismiss_target(snapshot, to_screen_point):
    if not isinstance(snapshot, dict):
        return None
    notes_state = snapshot.get("notes")
    if not isinstance(notes_state, dict):
        return None
    close_all = notes_state.get("closeAll")
    if isinstance(close_all, dict):
        x = close_all.get("clickX", close_all.get("centerX"))
        y = close_all.get("clickY", close_all.get("centerY"))
        if x is not None and y is not None:
            screen_x, screen_y = to_screen_point(x, y)
            return {
                "kind": "close_all_notes",
                "count": int(notes_state.get("count") or 0),
                "title": None,
                "screen_x": int(screen_x),
                "screen_y": int(screen_y),
            }
    notes = notes_state.get("notes")
    if not isinstance(notes, list) or not notes:
        return None
    first_note = next((note for note in notes if isinstance(note, dict)), None)
    if not isinstance(first_note, dict):
        return None
    close_rect = first_note.get("close")
    if not isinstance(close_rect, dict):
        return None
    x = close_rect.get("clickX", close_rect.get("centerX"))
    y = close_rect.get("clickY", close_rect.get("centerY"))
    if x is None or y is None:
        return None
    screen_x, screen_y = to_screen_point(x, y)
    return {
        "kind": "close_note",
        "count": int(notes_state.get("count") or 0),
        "title": first_note.get("title"),
        "screen_x": int(screen_x),
        "screen_y": int(screen_y),
    }


def _update_latest_snapshot(snapshot):
    big_cookie = _extract_big_cookie(snapshot)
    runtime_store.set_snapshot(snapshot, big_cookie)


def _get_window_process_image(hwnd):
    try:
        _thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)
        if not process_id:
            return None
        process_handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(process_id))
        if not process_handle:
            return None
        try:
            buffer_size = ctypes.c_ulong(32768)
            buffer = ctypes.create_unicode_buffer(buffer_size.value)
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(
                process_handle,
                0,
                buffer,
                ctypes.byref(buffer_size),
            ):
                return buffer.value
        finally:
            ctypes.windll.kernel32.CloseHandle(process_handle)
    except Exception:
        return None
    return None


def _is_game_process_running():
    exe_name = GAME_EXE_PATH.name.lower()
    try:
        process_ids = win32process.EnumProcesses()
    except Exception:
        return False
    for process_id in process_ids or ():
        if not process_id:
            continue
        process_handle = None
        try:
            process_handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(process_id))
            if not process_handle:
                continue
            buffer_size = ctypes.c_ulong(32768)
            buffer = ctypes.create_unicode_buffer(buffer_size.value)
            if not ctypes.windll.kernel32.QueryFullProcessImageNameW(
                process_handle,
                0,
                buffer,
                ctypes.byref(buffer_size),
            ):
                continue
            process_name = Path(buffer.value).name.lower()
            if process_name == exe_name:
                return True
        except Exception:
            continue
        finally:
            if process_handle:
                try:
                    ctypes.windll.kernel32.CloseHandle(process_handle)
                except Exception:
                    pass
    return False


def _should_launch_new_game_process(existing_rect):
    return should_launch_new_game_process(existing_rect)


def _get_latest_big_cookie():
    return runtime_store.get_latest_big_cookie()


def get_game_window(log_missing=True):
    global game_hwnd, last_game_window_missing_warning_at
    found = []
    fallback_found = []
    target_exe_name = GAME_EXE_PATH.name.lower()

    def check(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            lowered = title.lower()
            if "bot dashboard" in lowered or "file explorer" in lowered:
                return
            process_image = _get_window_process_image(hwnd)
            process_name = None if not process_image else Path(process_image).name.lower()
            if process_name != target_exe_name:
                return
            try:
                window_rect = win32gui.GetWindowRect(hwnd)
                width = max(0, int(window_rect[2]) - int(window_rect[0]))
                height = max(0, int(window_rect[3]) - int(window_rect[1]))
            except Exception:
                width = 0
                height = 0
            candidate = (hwnd, title, process_image)
            if "cookie clicker" in lowered:
                found.append(candidate)
            elif width >= 640 and height >= 480:
                fallback_found.append(candidate)

    win32gui.EnumWindows(check, None)
    if not found and fallback_found:
        found = fallback_found
    if not found:
        if log_missing and (time.monotonic() - last_game_window_missing_warning_at) >= 2.0:
            last_game_window_missing_warning_at = time.monotonic()
            log.warning("Cookie Clicker window not found")
        return None

    hwnd, title, process_image = found[0]
    game_hwnd = hwnd
    window_rect = win32gui.GetWindowRect(hwnd)
    try:
        client_rect = win32gui.GetClientRect(hwnd)
        client_left, client_top = win32gui.ClientToScreen(hwnd, (0, 0))
        client_right, client_bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))
        rect = (client_left, client_top, client_right, client_bottom)
    except Exception:
        rect = window_rect

    log.info(
        f"Game window found: '{title}' process='{process_image}' "
        f"client={rect} window={window_rect}"
    )
    return rect


def _get_monitor_workareas():
    user32 = ctypes.windll.user32
    monitors = []

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", ctypes.c_ulong),
        ]

    monitor_enum_proc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.POINTER(RECT),
        ctypes.c_double,
    )

    def _callback(hmonitor, _hdc, _lprect, _lparam):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            monitors.append(
                {
                    "left": int(info.rcWork.left),
                    "top": int(info.rcWork.top),
                    "right": int(info.rcWork.right),
                    "bottom": int(info.rcWork.bottom),
                    "width": int(info.rcWork.right - info.rcWork.left),
                    "height": int(info.rcWork.bottom - info.rcWork.top),
                    "monitor_left": int(info.rcMonitor.left),
                    "monitor_top": int(info.rcMonitor.top),
                    "monitor_right": int(info.rcMonitor.right),
                    "monitor_bottom": int(info.rcMonitor.bottom),
                    "monitor_width": int(info.rcMonitor.right - info.rcMonitor.left),
                    "monitor_height": int(info.rcMonitor.bottom - info.rcMonitor.top),
                    "primary": bool(info.dwFlags & 1),
                }
            )
        return 1

    user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(_callback), 0)
    monitors.sort(key=lambda item: (item["left"], item["top"]))
    return monitors


def _rect_center(rect):
    if not rect:
        return None
    return (
        int((int(rect[0]) + int(rect[2])) / 2),
        int((int(rect[1]) + int(rect[3])) / 2),
    )


def _monitor_for_point(monitors, point):
    if point is None:
        return None
    x, y = point
    for monitor in monitors:
        if monitor["left"] <= x < monitor["right"] and monitor["top"] <= y < monitor["bottom"]:
            return monitor
    return None


def _get_dashboard_geometry():
    monitors = _get_monitor_workareas()
    default_width = 1320
    default_height = 840
    if not monitors:
        return f"{default_width}x{default_height}"
    if len(monitors) == 1 or game_rect is None:
        monitor = monitors[0]
    else:
        game_monitor = _monitor_for_point(monitors, _rect_center(game_rect))
        monitor = next((item for item in monitors if item is not game_monitor), monitors[0])
    width = min(default_width, max(1100, monitor["width"] - 40))
    height = min(default_height, max(720, monitor["height"] - 80))
    x = monitor["left"] + max(0, int((monitor["width"] - width) / 2))
    y = monitor["top"] + max(0, int((monitor["height"] - height) / 2))
    return f"{width}x{height}+{x}+{y}"


def _get_game_launch_monitor():
    monitors = _get_monitor_workareas()
    if not monitors:
        return None
    primary = next((item for item in monitors if item.get("primary")), None)
    if primary is not None:
        return primary
    return monitors[0]


def _move_game_window_to_monitor(hwnd, monitor):
    if hwnd is None or monitor is None:
        return False
    try:
        if win32gui.IsIconic(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, 9)
        win32gui.MoveWindow(
            hwnd,
            int(monitor["monitor_left"]),
            int(monitor["monitor_top"]),
            int(monitor["monitor_width"]),
            int(monitor["monitor_height"]),
            True,
        )
        return True
    except Exception:
        log.exception("Failed to move Cookie Clicker window to target monitor")
        return False


def _set_game_fullscreen():
    try:
        pyautogui.press("f11", _pause=False)
        return True
    except Exception:
        log.exception("Failed to send fullscreen hotkey to Cookie Clicker")
        return False


def _launch_game_if_needed():
    global game_rect
    existing_rect = get_game_window(log_missing=False)
    game_process_running = _is_game_process_running()
    if existing_rect is not None:
        game_rect = existing_rect
        return False
    if game_process_running:
        log.info("Cookie Clicker process detected without a window; retrying attach before launching a new instance.")
        deadline = time.monotonic() + GAME_ATTACH_WAIT_SECONDS
        while time.monotonic() < deadline:
            rect = get_game_window(log_missing=False)
            if rect is not None:
                game_rect = rect
                return False
            time.sleep(0.25)
        log.warning("Cookie Clicker process is running but no game window was found; launching a new instance.")
    if not _should_launch_new_game_process(existing_rect):
        return False
    if not GAME_EXE_PATH.exists():
        log.warning(f"Cookie Clicker executable not found: {GAME_EXE_PATH}")
        return False

    launch_monitor = _get_game_launch_monitor()
    try:
        subprocess.Popen([str(GAME_EXE_PATH)], cwd=str(GAME_EXE_PATH.parent))
        log.info(f"Launched Cookie Clicker executable: {GAME_EXE_PATH}")
    except Exception:
        log.exception(f"Failed to launch Cookie Clicker executable: {GAME_EXE_PATH}")
        return False

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        rect = get_game_window(log_missing=False)
        if rect is not None and game_hwnd is not None:
            game_rect = rect
            break
        time.sleep(0.25)
    else:
        log.warning("Timed out waiting for Cookie Clicker window after launch")
        return False

    if launch_monitor is not None:
        _move_game_window_to_monitor(game_hwnd, launch_monitor)
        time.sleep(0.25)
        game_rect = get_game_window(log_missing=False) or game_rect

    if _focus_game_window():
        time.sleep(0.20)
        _set_game_fullscreen()
        time.sleep(0.40)
        game_rect = get_game_window(log_missing=False) or game_rect
    return True


def _focus_game_window():
    global game_hwnd
    if game_hwnd is None or not win32gui.IsWindow(game_hwnd):
        get_game_window()
    hwnd = game_hwnd
    if hwnd is None:
        return False
    try:
        if win32gui.IsIconic(hwnd):
            ctypes.windll.user32.ShowWindow(hwnd, 9)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        if hwnd is not None and not win32gui.IsWindow(hwnd):
            game_hwnd = None
        return False


def _is_game_foreground():
    global game_hwnd
    if game_hwnd is None or not win32gui.IsWindow(game_hwnd):
        get_game_window()
    hwnd = game_hwnd
    if hwnd is None:
        return False
    try:
        return int(win32gui.GetForegroundWindow() or 0) == int(hwnd)
    except Exception:
        return False


def _can_interact_with_game(now=None):
    global last_focus_warning_at, last_focus_attempt_at
    now = time.monotonic() if now is None else float(now)
    if _is_game_foreground():
        return True
    if (now - last_focus_attempt_at) >= 0.75:
        last_focus_attempt_at = now
        _focus_game_window()
        time.sleep(0.05)
        if _is_game_foreground():
            return True
    if (now - last_focus_warning_at) >= 2.0:
        last_focus_warning_at = now
        log.warning("Skipping input because Cookie Clicker is not the foreground window")
    return False


def _load_feed_snapshot():
    global feed_parse_failures
    started = time.perf_counter()
    try:
        stat = FEED_PATH.stat()
    except (FileNotFoundError, OSError):
        _set_runtime(feed_load_ms=None, feed_parse_ms=None)
        return None

    age = time.time() - stat.st_mtime
    if age > FEED_MAX_AGE_SECONDS:
        _set_runtime(feed_load_ms=(time.perf_counter() - started) * 1000.0, feed_parse_ms=None)
        return None

    text = None
    parse_started = None
    for _attempt in range(2):
        try:
            text = FEED_PATH.read_text(encoding="utf-8")
        except OSError:
            _set_runtime(feed_load_ms=(time.perf_counter() - started) * 1000.0, feed_parse_ms=None)
            return None
        if text and text.strip():
            try:
                parse_started = time.perf_counter()
                payload = json.loads(text)
                feed_parse_failures = 0
                _set_runtime(
                    feed_load_ms=(time.perf_counter() - started) * 1000.0,
                    feed_parse_ms=(time.perf_counter() - parse_started) * 1000.0,
                )
                break
            except JSONDecodeError:
                time.sleep(0.01)
                continue
        time.sleep(0.01)
    else:
        feed_parse_failures += 1
        if feed_parse_failures in (1, 10) or (feed_parse_failures % 100) == 0:
            size = 0 if text is None else len(text)
            log.warning(f"Feed snapshot unavailable or partial; skipping read failures={feed_parse_failures} size={size}")
        _set_runtime(feed_load_ms=(time.perf_counter() - started) * 1000.0, feed_parse_ms=None)
        return None

    if not isinstance(payload, dict):
        return None
    payload["_age"] = age
    return payload


def _client_to_screen(x, y):
    global game_hwnd, game_rect
    if game_hwnd is not None and win32gui.IsWindow(game_hwnd):
        try:
            screen_x, screen_y = win32gui.ClientToScreen(
                game_hwnd,
                (int(round(x)), int(round(y))),
            )
            return int(screen_x), int(screen_y)
        except Exception:
            pass
    if game_rect is None:
        return int(round(x)), int(round(y))
    return game_rect[0] + int(round(x)), game_rect[1] + int(round(y))


def _extract_big_cookie(snapshot):
    return extract_big_cookie(snapshot, to_screen_point=_client_to_screen)


def _extract_spell(snapshot):
    return extract_spell(snapshot, to_screen_point=_client_to_screen)


def _extract_upgrade_target_debug(snapshot, upgrade_id):
    if not isinstance(snapshot, dict):
        return None
    upgrades = snapshot.get("upgrades")
    if not isinstance(upgrades, list):
        return None
    try:
        target_id = int(upgrade_id)
    except Exception:
        return None
    for raw in upgrades:
        if not isinstance(raw, dict):
            continue
        try:
            raw_id = int(raw.get("id"))
        except Exception:
            continue
        if raw_id != target_id:
            continue
        target = raw.get("target") if isinstance(raw.get("target"), dict) else {}
        row = raw.get("row") if isinstance(raw.get("row"), dict) else {}
        return {
            "id": raw_id,
            "name": raw.get("displayName") or raw.get("name"),
            "target_click": (
                target.get("clickX"),
                target.get("clickY"),
            ),
            "target_center": (
                target.get("centerX"),
                target.get("centerY"),
            ),
            "target_raw_center": (
                target.get("rawCenterX"),
                target.get("rawCenterY"),
            ),
            "target_bounds": (
                target.get("left"),
                target.get("top"),
                target.get("right"),
                target.get("bottom"),
            ),
            "row_click": (
                row.get("clickX"),
                row.get("clickY"),
            ),
            "row_center": (
                row.get("centerX"),
                row.get("centerY"),
            ),
            "row_raw_center": (
                row.get("rawCenterX"),
                row.get("rawCenterY"),
            ),
        }
    return None


def _build_upgrade_attempt_signature(snapshot, upgrade_diag):
    if not isinstance(upgrade_diag, dict):
        return None
    candidate_id = upgrade_diag.get("candidate_id")
    if candidate_id is None:
        return None
    try:
        candidate_id = int(candidate_id)
    except Exception:
        return None
    target_debug = _extract_upgrade_target_debug(snapshot, candidate_id) or {}
    return (
        candidate_id,
        upgrade_diag.get("candidate_price"),
        target_debug.get("target_bounds"),
        target_debug.get("target_click"),
        target_debug.get("row_click"),
    )


def _extract_building_target_debug(snapshot, building_id):
    if not isinstance(snapshot, dict):
        return None
    raw_buildings = snapshot.get("buildings")
    if not isinstance(raw_buildings, list):
        return None
    for building in raw_buildings:
        if not isinstance(building, dict):
            continue
        if building.get("id") != building_id:
            continue
        target = building.get("target") if isinstance(building.get("target"), dict) else {}
        row = building.get("row") if isinstance(building.get("row"), dict) else {}
        return {
            "id": int(building.get("id")),
            "name": building.get("name"),
            "amount": int(building.get("amount") or 0),
            "price": None if building.get("price") is None else float(building.get("price")),
            "target_bounds": (
                target.get("left"),
                target.get("top"),
                target.get("right"),
                target.get("bottom"),
            ),
            "target_click": (
                target.get("clickX"),
                target.get("clickY"),
            ),
            "target_center": (
                target.get("centerX"),
                target.get("centerY"),
            ),
            "target_raw_center": (
                target.get("rawCenterX"),
                target.get("rawCenterY"),
            ),
            "row_click": (
                row.get("clickX"),
                row.get("clickY"),
            ),
            "row_center": (
                row.get("centerX"),
                row.get("centerY"),
            ),
            "row_raw_center": (
                row.get("rawCenterX"),
                row.get("rawCenterY"),
            ),
        }
    return None


def _build_building_attempt_signature(snapshot, building_action):
    if building_action is None:
        return None
    building_id = getattr(building_action, "building_id", None)
    if building_id is None:
        return None
    try:
        building_id = int(building_id)
    except Exception:
        return None
    target_debug = _extract_building_target_debug(snapshot, building_id) or {}
    return (
        building_id,
        target_debug.get("amount"),
        target_debug.get("price"),
        getattr(building_action, "quantity", None),
    )


def _update_building_attempt_tracking(snapshot, building_action, now):
    candidate_id = getattr(building_action, "building_id", None)
    candidate_signature = _build_building_attempt_signature(snapshot, building_action)
    _get_dom_attempt_tracker().sync_tracker(
        building_attempt_tracker,
        candidate_id=candidate_id,
        candidate_signature=candidate_signature,
        now=now,
    )


def _update_upgrade_attempt_tracking(snapshot, upgrade_diag, now):
    candidate_id = upgrade_diag.get("candidate_id") if isinstance(upgrade_diag, dict) else None
    candidate_can_buy = bool(upgrade_diag.get("candidate_can_buy")) if isinstance(upgrade_diag, dict) else False
    candidate_signature = _build_upgrade_attempt_signature(snapshot, upgrade_diag)
    _get_dom_attempt_tracker().sync_tracker(
        upgrade_attempt_tracker,
        candidate_id=(candidate_id if candidate_can_buy else None),
        candidate_signature=(candidate_signature if candidate_can_buy else None),
        now=now,
    )


def _plan_minigame_store_access(snapshot, spell_diag, bank_diag, garden_diag):
    return plan_minigame_store_access(
        snapshot,
        spell_diag=spell_diag,
        bank_diag=bank_diag,
        garden_diag=garden_diag,
        minigame_building_ids=MINIGAME_BUILDING_IDS,
        plan_focus_building=building_store.plan_focus_building,
        to_screen_point=_client_to_screen,
    )


def _extract_shimmers(snapshot):
    return extract_shimmers(snapshot, to_screen_point=_client_to_screen)


def _record_shimmer_outcome(shimmer_result):
    global shimmer_seed_history
    new_buffs = shimmer_result.get("new_buffs", [])
    outcome = str(shimmer_result.get("outcome") or ",".join(sorted(new_buffs)) or "unknown")
    classification = _classify_shimmer_outcome(outcome)
    if classification in {"neutral", "unknown"} and new_buffs:
        for buff in new_buffs:
            cls = _classify_shimmer_outcome({"name": buff})
            if cls == "positive":
                classification = "positive"
                break
            if cls == "negative":
                classification = "negative"
    if classification == "unknown":
        classification = "neutral"
    entry = {
        "timestamp": time.time(),
        "id": shimmer_result.get("id"),
        "type": shimmer_result.get("type"),
        "wrath": bool(shimmer_result.get("wrath")),
        "outcome": outcome,
        "classification": classification,
        "seed": shimmer_result.get("seed_at_click"),
        "new_buffs": new_buffs,
    }
    shimmer_seed_history.append(entry)
    if len(shimmer_seed_history) > 1000:
        shimmer_seed_history = shimmer_seed_history[-500:]


def _reset_shimmer_tracking(reason, *, clear_click_state=False):
    global shimmer_seed_history, shimmer_tracking_reset_reason, last_seen_golden_decision
    shimmer_seed_history = []
    shimmer_tracking_reset_reason = str(reason or "reset")
    if shimmer_tracking_reset_reason != "untracked_shimmer_resolution":
        last_seen_golden_decision = None
    if clear_click_state:
        recent_shimmer_clicks.clear()
        shimmer_first_seen.clear()
        shimmer_click_attempts.clear()
        pending_shimmer_results.clear()
    with runtime_lock:
        runtime_state["last_shimmer"] = None
        runtime_state["last_shimmer_effect"] = None
    _record_event(f"Shimmer predictor reset: {shimmer_tracking_reset_reason}")
    log.info(f"Shimmer predictor reset: {shimmer_tracking_reset_reason}")


def _dump_shimmer_seed_history():
    import json
    if not shimmer_seed_history:
        log.info("No shimmer seed history captured")
        return
    positive = sum(1 for e in shimmer_seed_history if e.get("classification") == "positive")
    negative = sum(1 for e in shimmer_seed_history if e.get("classification") == "negative")
    neutral = sum(1 for e in shimmer_seed_history if e.get("classification") == "neutral")
    seeds_with_data = [e for e in shimmer_seed_history if e.get("seed")]
    log.info(f"Shimmer outcomes: {len(shimmer_seed_history)} total | +:{positive} -:{negative} =:{neutral}")
    log.info(f"Seeds captured: {len(seeds_with_data)}/{len(shimmer_seed_history)}")
    data_file = "shimmer_seed_data.json"
    with open(data_file, "w") as f:
        json.dump(shimmer_seed_history, f, indent=2)
    log.info(f"Dumped to {data_file}")


def _extract_buffs(snapshot):
    return extract_buffs(snapshot)


def _extract_upgrade_diag(snapshot):
    return build_upgrade_diag(
        snapshot,
        resolve_candidate_metrics=_resolve_upgrade_candidate_metrics,
        estimate_attached_wrinkler_bank=_estimate_attached_wrinkler_bank,
        afford_horizon_seconds=UPGRADE_AFFORD_HORIZON_SECONDS,
        auto_buy_payback_seconds=UPGRADE_AUTO_BUY_PAYBACK_SECONDS,
        cheap_upgrade_sweep_ratio=CHEAP_UPGRADE_SWEEP_RATIO,
    )


def _normalize_snapshot_target(rect, to_screen_point):
    return normalize_snapshot_target(rect, to_screen_point)


def _extract_dragon_diag(snapshot, to_screen_point):
    return build_dragon_diag(
        snapshot,
        to_screen_point=to_screen_point,
        normalize_target=_normalize_snapshot_target,
    )


def _get_desired_dragon_auras(combo_diag, spell_diag=None):
    stage = None if not isinstance(combo_diag, dict) else combo_diag.get("combo_stage")
    combo_click_buffs = tuple(combo_diag.get("click_buffs") or ()) if isinstance(combo_diag, dict) else ()
    combo_production_buffs = (
        tuple(combo_diag.get("production_buffs") or ()) if isinstance(combo_diag, dict) else ()
    )
    spell_valuable_buffs = (
        tuple(spell_diag.get("valuable_buffs") or ()) if isinstance(spell_diag, dict) else ()
    )
    has_click_window = bool(combo_click_buffs)
    has_setup_window = bool(
        combo_production_buffs
        or tuple(buff for buff in spell_valuable_buffs if buff in PRODUCTION_STACK_BUFF_KEYS)
        or stage in {"build_combo", "spawn_click_buff"}
    )
    if stage == "execute_click_combo" or has_click_window:
        return {
            "reason": "combo_execute",
            "primary_name": "Dragon Cursor",
            "primary_id": DRAGON_AURA_NAME_TO_ID["Dragon Cursor"],
            "secondary_name": "Radiant Appetite",
            "secondary_id": DRAGON_AURA_NAME_TO_ID["Radiant Appetite"],
        }
    if has_setup_window:
        return {
            "reason": "combo_setup",
            "primary_name": "Dragonflight",
            "primary_id": DRAGON_AURA_NAME_TO_ID["Dragonflight"],
            "secondary_name": "Reaper of Fields",
            "secondary_id": DRAGON_AURA_NAME_TO_ID["Reaper of Fields"],
        }
    return None


def _is_dragon_aura_unlocked(dragon_level, aura_id):
    try:
        level = int(dragon_level or 0)
        aura = int(aura_id or 0)
    except (TypeError, ValueError):
        return False
    if aura <= 0:
        return True
    return level >= (aura + 3)


def _plan_dragon_aura_action(dragon_diag, combo_diag, spell_diag=None):
    if not isinstance(dragon_diag, dict) or not dragon_diag.get("available"):
        return None
    desired = _get_desired_dragon_auras(combo_diag, spell_diag=spell_diag)
    if desired is None:
        return None
    dragon_level = int(dragon_diag.get("level") or 0)
    primary_unlocked = _is_dragon_aura_unlocked(dragon_level, desired["primary_id"])
    secondary_slot_available = dragon_level >= 27
    secondary_unlocked = secondary_slot_available and _is_dragon_aura_unlocked(
        dragon_level, desired["secondary_id"]
    )
    if not primary_unlocked and not secondary_unlocked:
        return None
    if not bool(dragon_diag.get("aura_swap_cost_free")):
        if int(dragon_diag.get("aura_swap_cost_building_amount") or 0) <= 1:
            return None
    if bool(dragon_diag.get("aura_prompt_open")):
        prompt_slot = int(dragon_diag.get("aura_prompt_slot") or 0)
        if prompt_slot == 1:
            if not secondary_unlocked:
                return None
            desired_id = desired["secondary_id"]
            desired_name = desired["secondary_name"]
        else:
            if not primary_unlocked:
                return None
            desired_id = desired["primary_id"]
            desired_name = desired["primary_name"]
        selected_id = dragon_diag.get("aura_prompt_selected_id")
        current_id = dragon_diag.get("aura_prompt_current_id")
        choice = (dragon_diag.get("aura_prompt_choices") or {}).get(int(desired_id))
        if selected_id != desired_id and isinstance(choice, dict) and isinstance(choice.get("target"), dict):
            target = choice["target"]
            return {
                "kind": "select_dragon_aura",
                "screen_x": target["screen_x"],
                "screen_y": target["screen_y"],
                "detail": f"slot={prompt_slot} aura={desired_name}",
            }
        if current_id != desired_id and isinstance(dragon_diag.get("aura_prompt_confirm"), dict):
            target = dragon_diag["aura_prompt_confirm"]
            return {
                "kind": "confirm_dragon_aura",
                "screen_x": target["screen_x"],
                "screen_y": target["screen_y"],
                "detail": f"slot={prompt_slot} aura={desired_name}",
            }
        return None

    primary_matches = (not primary_unlocked) or dragon_diag.get("aura_primary_id") == desired["primary_id"]
    secondary_matches = (not secondary_unlocked) or dragon_diag.get("aura_secondary_id") == desired["secondary_id"]
    if primary_unlocked and not primary_matches and isinstance(dragon_diag.get("aura_primary_control"), dict):
        target = dragon_diag["aura_primary_control"]
        return {
            "kind": "open_dragon_aura_primary",
            "screen_x": target["screen_x"],
            "screen_y": target["screen_y"],
            "detail": desired["primary_name"],
        }
    if secondary_unlocked and not secondary_matches and isinstance(dragon_diag.get("aura_secondary_control"), dict):
        target = dragon_diag["aura_secondary_control"]
        return {
            "kind": "open_dragon_aura_secondary",
            "screen_x": target["screen_x"],
            "screen_y": target["screen_y"],
            "detail": desired["secondary_name"],
        }
    return None


def _get_next_purchase_goal(snapshot, building_diag=None, upgrade_diag=None):
    if not isinstance(snapshot, dict):
        return None

    cookies = max(0.0, float(snapshot.get("cookies") or 0.0))
    choices = []

    if isinstance(upgrade_diag, dict):
        price = upgrade_diag.get("candidate_price")
        payback = upgrade_diag.get("candidate_payback_seconds")
        name = upgrade_diag.get("candidate")
        if isinstance(price, (int, float)) and isinstance(payback, (int, float)) and name:
            choices.append(
                {
                    "kind": "upgrade",
                    "name": str(name),
                    "price": float(price),
                    "payback_seconds": float(payback),
                    "cookies": cookies,
                    "can_buy": bool(upgrade_diag.get("candidate_can_buy")),
                }
            )

    if isinstance(building_diag, dict):
        price = building_diag.get("next_candidate_price")
        payback = building_diag.get("next_candidate_payback_seconds")
        name = building_diag.get("next_candidate")
        if isinstance(price, (int, float)) and isinstance(payback, (int, float)) and name:
            choices.append(
                {
                    "kind": "building",
                    "name": str(name),
                    "price": float(price),
                    "payback_seconds": float(payback),
                    "cookies": cookies,
                    "can_buy": bool(building_diag.get("next_candidate_can_buy")),
                }
            )

    if not choices:
        return None

    choices.sort(key=lambda item: (item["payback_seconds"], item["price"], item["kind"], item["name"]))
    winner = dict(choices[0])
    winner["shortfall"] = max(0.0, winner["price"] - cookies)
    return winner


def _apply_building_burst_purchase_goal(snapshot, building_diag, purchase_goal, burst_window):
    return apply_building_burst_purchase_goal(snapshot, building_diag, purchase_goal, burst_window)


def _get_garden_cookie_reserve(snapshot, garden_diag):
    return get_garden_cookie_reserve(
        snapshot,
        garden_diag,
        garden_automation_enabled=garden_automation_enabled,
    )


def _get_lucky_reserve_multiplier(snapshot):
    global _last_lucky_multiplier, _last_lucky_multiplier_logged_at
    multiplier = reserve_policy.get_lucky_reserve_multiplier(snapshot)
    _last_lucky_multiplier = reserve_policy.last_lucky_multiplier
    _last_lucky_multiplier_logged_at = reserve_policy.last_lucky_multiplier_logged_at
    return multiplier


def _get_lucky_cookie_reserve(snapshot, use_live_cps=False):
    return reserve_policy.get_lucky_cookie_reserve(snapshot, use_live_cps=use_live_cps)


def _get_building_buff_burst_window(snapshot, building_diag=None, spell_diag=None):
    return reserve_policy.get_building_buff_burst_window(snapshot, building_diag, spell_diag)


def _get_global_cookie_reserve(snapshot, garden_diag, building_diag=None, spell_diag=None):
    return reserve_policy.get_global_cookie_reserve(
        snapshot,
        garden_diag,
        get_garden_cookie_reserve=_get_garden_cookie_reserve,
        lucky_reserve_enabled=bool(globals().get("lucky_reserve_enabled", True)),
        building_diag=building_diag,
        spell_diag=spell_diag,
    )


def _has_cookies_after_reserve(snapshot, price, reserve_cookies):
    return has_cookies_after_reserve(snapshot, price, reserve_cookies)


def _get_stock_buy_controls(building_diag, enabled, reserve_cookies):
    return get_stock_buy_controls(building_diag, enabled, reserve_cookies)


def _extract_bank_diag_disabled(snapshot):
    return build_disabled_bank_diag(snapshot, held_positions=stock_trader.positions)


def _stock_trade_management_active():
    return stock_trade_management_active(
        stock_trading_enabled=stock_trading_enabled,
        held_positions=stock_trader.positions,
        pending_actions=stock_trader.pending_actions,
    )


def click_loop():
    global suppress_main_click_until
    log.info("click_loop started")
    while active:
        loop_started = time.perf_counter()
        try:
            if not main_cookie_clicking_enabled:
                time.sleep(MAIN_CLICK_INTERVAL)
                _record_profile_ms("click_loop", (time.perf_counter() - loop_started) * 1000.0, spike_ms=30.0)
                continue

            now = time.monotonic()
            if now < suppress_main_click_until:
                with runtime_lock:
                    runtime_state["click_suppressed_loops"] += 1
                time.sleep(0.01)
                _record_profile_ms("click_loop", (time.perf_counter() - loop_started) * 1000.0, spike_ms=30.0)
                continue
            if _wrinkler_purchase_funding_active():
                with runtime_lock:
                    runtime_state["click_suppressed_loops"] += 1
                time.sleep(0.01)
                _record_profile_ms("click_loop", (time.perf_counter() - loop_started) * 1000.0, spike_ms=30.0)
                continue

            big_cookie = _get_latest_big_cookie()
            if big_cookie is None:
                with runtime_lock:
                    runtime_state["click_idle_misses"] += 1
                time.sleep(0.01)
                _record_profile_ms("click_loop", (time.perf_counter() - loop_started) * 1000.0, spike_ms=30.0)
                continue
            if not _can_interact_with_game(now):
                time.sleep(0.05)
                _record_profile_ms("click_loop", (time.perf_counter() - loop_started) * 1000.0, spike_ms=30.0)
                continue

            action_started = time.perf_counter()
            with click_lock:
                _click(big_cookie["screen_x"], big_cookie["screen_y"], hold=MAIN_CLICK_HOLD)
            _record_profile_ms("click_action", (time.perf_counter() - action_started) * 1000.0, spike_ms=20.0)
            with runtime_lock:
                runtime_state["main_clicks"] += 1
            time.sleep(MAIN_CLICK_INTERVAL)
        except Exception:
            log.exception("click_loop: unhandled exception")
            time.sleep(1.0)
        finally:
            _record_profile_ms("click_loop", (time.perf_counter() - loop_started) * 1000.0, spike_ms=30.0)

    log.info("click_loop stopped")


def dom_loop():
    global suppress_main_click_until, last_spell_click, last_trade_action, last_building_action, last_upgrade_action, last_combo_action_click, last_wrinkler_action, last_dragon_action, last_note_dismiss_action, last_lump_action, last_upgrade_skip_signature, post_upgrade_wrinkler_cooldown_until, last_upgrade_focus_signature, last_upgrade_focus_at, last_upgrade_focus_point, last_seen_golden_decision
    log.info("dom_loop started")
    state = _get_dom_loop_state_bridge().create_state(
        suppress_main_click_until=suppress_main_click_until,
        last_spell_click=last_spell_click,
        last_trade_action=last_trade_action,
        last_building_action=last_building_action,
        last_upgrade_action=last_upgrade_action,
        last_combo_action_click=last_combo_action_click,
        last_wrinkler_action=last_wrinkler_action,
        last_dragon_action=last_dragon_action,
        last_note_dismiss_action=last_note_dismiss_action,
        last_lump_action=last_lump_action,
        last_upgrade_skip_signature=last_upgrade_skip_signature,
        post_upgrade_wrinkler_cooldown_until=post_upgrade_wrinkler_cooldown_until,
        last_upgrade_focus_signature=last_upgrade_focus_signature,
        last_upgrade_focus_at=last_upgrade_focus_at,
        last_upgrade_focus_point=last_upgrade_focus_point,
        last_seen_golden_decision=last_seen_golden_decision,
    )

    while active:
        loop_started = time.perf_counter()
        try:
            state = _get_dom_loop_state_bridge().sync_before_cycle(
                state,
                suppress_main_click_until=suppress_main_click_until,
            )
            build_options = DomLoopBuildOptions(
                building_autobuy_enabled=building_autobuy_enabled,
                lucky_reserve_enabled=lucky_reserve_enabled,
                stock_trading_enabled=stock_trading_enabled,
                upgrade_autobuy_enabled=upgrade_autobuy_enabled,
                ascension_prep_enabled=ascension_prep_enabled,
                garden_automation_enabled=garden_automation_enabled,
                stock_diag_refresh_interval=STOCK_DIAG_REFRESH_INTERVAL,
            )
            state = _get_dom_loop_coordinator().run_cycle(
                state=state,
                build_options=build_options,
                upgrade_attempt_tracker=upgrade_attempt_tracker,
                building_attempt_tracker=building_attempt_tracker,
                shimmer_autoclick_enabled=shimmer_autoclick_enabled,
                auto_cast_hand_of_fate=AUTO_CAST_HAND_OF_FATE,
            )
            legacy_updates = _get_dom_loop_state_bridge().export_state(
                state,
                suppress_main_click_until=suppress_main_click_until,
            )
            suppress_main_click_until = legacy_updates["suppress_main_click_until"]
            last_seen_golden_decision = legacy_updates["last_seen_golden_decision"]
            last_spell_click = legacy_updates["last_spell_click"]
            last_trade_action = legacy_updates["last_trade_action"]
            last_building_action = legacy_updates["last_building_action"]
            last_upgrade_action = legacy_updates["last_upgrade_action"]
            last_combo_action_click = legacy_updates["last_combo_action_click"]
            last_wrinkler_action = legacy_updates["last_wrinkler_action"]
            last_dragon_action = legacy_updates["last_dragon_action"]
            last_note_dismiss_action = legacy_updates["last_note_dismiss_action"]
            last_lump_action = legacy_updates["last_lump_action"]
            last_upgrade_skip_signature = legacy_updates["last_upgrade_skip_signature"]
            post_upgrade_wrinkler_cooldown_until = legacy_updates["post_upgrade_wrinkler_cooldown_until"]
            last_upgrade_focus_signature = legacy_updates["last_upgrade_focus_signature"]
            last_upgrade_focus_at = legacy_updates["last_upgrade_focus_at"]
            last_upgrade_focus_point = legacy_updates["last_upgrade_focus_point"]
        except Exception:
            log.exception("dom_loop: unhandled exception")
            time.sleep(1.0)
        finally:
            _record_profile_ms("dom_loop", (time.perf_counter() - loop_started) * 1000.0, spike_ms=40.0)

    log.info("dom_loop stopped")


def _get_bot_lifecycle():
    global bot_lifecycle
    if bot_lifecycle is None:
        state = BotLifecycleState(active=active, click_thread=click_thread, dom_thread=dom_thread)
        bot_lifecycle = BotLifecycle(state=state, click_loop=click_loop, dom_loop=dom_loop)
    return bot_lifecycle


def _get_bot_controls():
    global bot_controls
    if bot_controls is None:
        bot_controls = BotControls(
            log=log,
            set_runtime=_set_runtime,
            record_event=_record_event,
            log_mode_change=_log_automation_mode_change,
            get_active=lambda: active,
            get_main_cookie_clicking_enabled=lambda: main_cookie_clicking_enabled,
            set_main_cookie_clicking_enabled=lambda value: globals().__setitem__("main_cookie_clicking_enabled", value),
            get_shimmer_autoclick_enabled=lambda: shimmer_autoclick_enabled,
            set_shimmer_autoclick_enabled=lambda value: globals().__setitem__("shimmer_autoclick_enabled", value),
            get_building_autobuy_enabled=lambda: building_autobuy_enabled,
            set_building_autobuy_enabled=lambda value: globals().__setitem__("building_autobuy_enabled", value),
            get_lucky_reserve_enabled=lambda: lucky_reserve_enabled,
            set_lucky_reserve_enabled=lambda value: globals().__setitem__("lucky_reserve_enabled", value),
            get_upgrade_autobuy_enabled=lambda: upgrade_autobuy_enabled,
            set_upgrade_autobuy_enabled=lambda value: globals().__setitem__("upgrade_autobuy_enabled", value),
            get_ascension_prep_enabled=lambda: ascension_prep_enabled,
            set_ascension_prep_enabled=lambda value: globals().__setitem__("ascension_prep_enabled", value),
            get_stock_trading_enabled=lambda: stock_trading_enabled,
            set_stock_trading_enabled=lambda value: globals().__setitem__("stock_trading_enabled", value),
            get_lifecycle=_get_bot_lifecycle,
            set_click_thread=lambda value: globals().__setitem__("click_thread", value),
            building_autobuyer=building_autobuyer,
            set_upgrade_horizon_value=lambda value: globals().__setitem__("UPGRADE_AFFORD_HORIZON_SECONDS", value),
            wrinkler_controller=wrinkler_controller,
            wrinkler_modes=(
                WRINKLER_MODE_HOLD,
                WRINKLER_MODE_SEASONAL_FARM,
                WRINKLER_MODE_SHINY_HUNT,
            ),
        )
    return bot_controls


def _flip_active_state():
    global active
    with active_lock:
        active = not active
        return active


def _get_bot_activation():
    global bot_activation
    if bot_activation is None:
        bot_activation = BotActivationController(
            log=log,
            flip_active=_flip_active_state,
            set_runtime=_set_runtime,
            log_mode_change=_log_automation_mode_change,
            reset_shimmer_tracking=_reset_shimmer_tracking,
            record_event=_record_event,
            get_game_window=get_game_window,
            launch_game_if_needed=_launch_game_if_needed,
            focus_game_window=_focus_game_window,
            get_main_cookie_clicking_enabled=lambda: main_cookie_clicking_enabled,
            get_lifecycle=_get_bot_lifecycle,
            set_click_thread=lambda value: globals().__setitem__("click_thread", value),
            set_dom_thread=lambda value: globals().__setitem__("dom_thread", value),
            set_game_rect=lambda value: globals().__setitem__("game_rect", value),
        )
    return bot_activation


def _get_event_recorder():
    global bot_event_recorder
    if bot_event_recorder is None:
        bot_event_recorder = BotEventRecorder(
            runtime_store=runtime_store,
            infer_feed_category=_infer_feed_category,
        )
    return bot_event_recorder


def _get_dom_loop_services():
    global dom_loop_services
    if dom_loop_services is None:
        dom_loop_services = build_default_dom_loop_service_factory(
            load_feed_snapshot=_load_feed_snapshot,
            update_latest_snapshot=_update_latest_snapshot,
            extract_shimmers=_extract_shimmers,
            extract_buffs=_extract_buffs,
            extract_spell=_extract_spell,
            get_latest_big_cookie=_get_latest_big_cookie,
            to_screen_point=_client_to_screen,
            monotonic=time.monotonic,
            garden_get_diagnostics=garden_controller.get_diagnostics,
            extract_lump_diag=_extract_lump_diag,
            building_get_diagnostics=building_autobuyer.get_diagnostics,
            ascension_get_diagnostics=ascension_prep.get_diagnostics,
            extract_upgrade_diag=_extract_upgrade_diag,
            extract_dragon_diag=_extract_dragon_diag,
            extract_golden_cookie_diag=_extract_golden_cookie_diag,
            spell_get_diagnostics=spell_autocaster.get_diagnostics,
            get_global_cookie_reserve=_get_global_cookie_reserve,
            get_next_purchase_goal=_get_next_purchase_goal,
            apply_building_burst_purchase_goal=_apply_building_burst_purchase_goal,
            get_stock_buy_controls=_get_stock_buy_controls,
            stock_trade_management_active=_stock_trade_management_active,
            stock_get_diagnostics=stock_trader.get_diagnostics,
            extract_bank_diag_disabled=_extract_bank_diag_disabled,
            wrinkler_get_diagnostics=wrinkler_controller.get_diagnostics,
            combo_get_diagnostics=godzamok_combo.get_diagnostics,
            stock_get_runtime_stats=stock_trader.get_runtime_stats,
            spell_get_runtime_stats=spell_autocaster.get_runtime_stats,
            combo_get_runtime_stats=godzamok_combo.get_runtime_stats,
            track_combo_run=_track_combo_run,
            get_non_click_pause_reasons=_get_non_click_pause_reasons,
            should_pause_stock_trading=_should_pause_stock_trading,
            should_allow_non_click_actions_during_pause=_should_allow_non_click_actions_during_pause,
            evaluate_upgrade_buff_window=_evaluate_upgrade_buff_window,
            should_defer_stock_actions_for_upgrade=_should_defer_stock_actions_for_upgrade,
            set_runtime=_set_runtime,
            should_pause_value_actions_during_clot=_should_pause_value_actions_during_clot,
            perf_counter=time.perf_counter,
            record_profile_ms=_record_profile_ms,
            feed_debug_log_interval=FEED_DEBUG_LOG_INTERVAL,
            log=log,
            click_lock=click_lock,
            click=_click,
            scroll=_scroll,
            can_interact_with_game=_can_interact_with_game,
            ui_owner_conflicts=_ui_owner_conflicts,
            should_throttle_ui_action=_should_throttle_ui_action,
            claim_ui_owner=_claim_ui_owner,
            move_mouse=_move_mouse,
            record_event=_record_event,
            time_monotonic=time.monotonic,
            sleep=time.sleep,
            building_click_hold=BUILDING_CLICK_HOLD,
            spell_click_hold=SPELL_CLICK_HOLD,
            feed_poll_interval=FEED_POLL_INTERVAL,
            main_click_suppress_seconds=MAIN_CLICK_SUPPRESS_SECONDS,
            suppress_main_click_until_getter=lambda: suppress_main_click_until,
            suppress_main_click_until_setter=lambda value: globals().__setitem__("suppress_main_click_until", value),
            plan_reset_store_to_default=building_store.plan_reset_to_default,
            plan_upgrade_buy=upgrade_store.plan_buy,
            get_wrinkler_action=wrinkler_controller.get_action,
            get_desired_dragon_auras=_get_desired_dragon_auras,
            plan_dragon_aura_action=_plan_dragon_aura_action,
            is_dragon_aura_unlocked=_is_dragon_aura_unlocked,
            get_ascension_action=ascension_prep.get_action,
            plan_building_buy=building_store.plan_buy,
            plan_building_sell=building_store.plan_sell,
            get_trade_action=stock_trader.get_action,
            get_building_action=building_autobuyer.get_action,
            has_cookies_after_reserve=_has_cookies_after_reserve,
            plan_minigame_store_access=_plan_minigame_store_access,
            update_upgrade_attempt_tracking=_update_upgrade_attempt_tracking,
            build_upgrade_attempt_signature=_build_upgrade_attempt_signature,
            upgrade_action_cooldown=UPGRADE_ACTION_COOLDOWN,
            note_target_getter=_get_note_dismiss_target,
            should_allow_garden_action=_should_allow_garden_action,
            update_building_attempt_tracking=_update_building_attempt_tracking,
            build_building_attempt_signature=_build_building_attempt_signature,
            extract_building_target_debug=_extract_building_target_debug,
            format_store_planner_context=_format_store_planner_context,
            extract_upgrade_target_debug=_extract_upgrade_target_debug,
            format_upgrade_planner_context=_format_upgrade_planner_context,
            combo_controller=godzamok_combo,
            spell_controller=spell_autocaster,
            garden_controller=garden_controller,
            wrinkler_controller=wrinkler_controller,
            ascension_controller=ascension_prep,
            stock_trader=stock_trader,
            building_autobuyer=building_autobuyer,
            lump_action_cooldown=LUMP_ACTION_COOLDOWN,
            note_dismiss_cooldown=NOTE_DISMISS_COOLDOWN,
            combo_action_cooldown=COMBO_ACTION_COOLDOWN,
            spell_click_cooldown=SPELL_CLICK_COOLDOWN,
            wrinkler_action_cooldown=WRINKLER_ACTION_COOLDOWN,
            trade_action_cooldown=TRADE_ACTION_COOLDOWN,
            building_action_cooldown=BUILDING_ACTION_COOLDOWN,
            dragon_action_cooldown=DRAGON_ACTION_COOLDOWN,
            dragon_aura_action_cooldown=DRAGON_AURA_ACTION_COOLDOWN,
            post_upgrade_wrinkler_cooldown_seconds=POST_UPGRADE_WRINKLER_COOLDOWN_SECONDS,
            bonus_click_hold=BONUS_CLICK_HOLD,
            trade_click_hold=TRADE_CLICK_HOLD,
            building_stuck_attempt_limit=BUILDING_STUCK_ATTEMPT_LIMIT,
            building_stuck_signature_suppress_seconds=BUILDING_STUCK_SIGNATURE_SUPPRESS_SECONDS,
            upgrade_stuck_attempt_limit=UPGRADE_STUCK_ATTEMPT_LIMIT,
            upgrade_stuck_signature_suppress_seconds=UPGRADE_STUCK_SIGNATURE_SUPPRESS_SECONDS,
            store_scroll_wheel_multiplier=STORE_SCROLL_WHEEL_MULTIPLIER,
            click_shimmer=_click_shimmer,
            should_skip_wrath_shimmer=_should_skip_wrath_shimmer,
            format_shimmer_id_list=_format_shimmer_id_list,
            reset_shimmer_tracking=_reset_shimmer_tracking,
            record_shimmer_outcome=_record_shimmer_outcome,
            record_shimmer_click_runtime=_record_shimmer_click_runtime,
            record_shimmer_collect_runtime=_record_shimmer_collect_runtime,
            get_pending_hand_shimmer=spell_autocaster.get_pending_hand_shimmer,
            clear_pending_hand_shimmer=spell_autocaster.clear_pending_hand_shimmer,
            recent_shimmer_clicks=recent_shimmer_clicks,
            shimmer_first_seen=shimmer_first_seen,
            shimmer_click_attempts=shimmer_click_attempts,
            pending_shimmer_results=pending_shimmer_results,
            shimmer_click_delay_seconds=SHIMMER_CLICK_DELAY_SECONDS,
            shimmer_click_cooldown=SHIMMER_CLICK_COOLDOWN,
            combo_pending_getter=godzamok_combo.has_pending,
        )
    return dom_loop_services


def _get_dom_attempt_tracker():
    return _get_dom_loop_services().attempt_tracker()


def _get_dom_loop_coordinator():
    return _get_dom_loop_services().coordinator()


def _get_dom_loop_state_bridge():
    return _get_dom_loop_services().state_bridge()


def _get_dashboard_state_builder():
    global dashboard_state_builder
    if dashboard_state_builder is None:
        dashboard_state_builder = DashboardStateBuilder(
            runtime_store=runtime_store,
            hud_recent_events=HUD_RECENT_EVENTS,
            get_trade_stats=stock_trader.get_runtime_stats,
            get_building_stats=building_autobuyer.get_runtime_stats,
            get_ascension_prep_stats=ascension_prep.get_runtime_stats,
            get_garden_stats=garden_controller.get_runtime_stats,
            get_combo_stats=godzamok_combo.get_runtime_stats,
            get_spell_stats=spell_autocaster.get_runtime_stats,
            get_wrinkler_stats=wrinkler_controller.get_runtime_stats,
            shimmer_seed_history=shimmer_seed_history,
            get_shimmer_reset_reason=lambda: shimmer_tracking_reset_reason,
        )
    return dashboard_state_builder


def toggle(e=None, source="hotkey"):
    _get_bot_activation().toggle(source=source)


def toggle_main_autoclick(e=None, source="hud_button"):
    _get_bot_controls().toggle_main_autoclick(source=source)


def toggle_shimmer_autoclick(e=None, source="hud_button"):
    _get_bot_controls().toggle_shimmer_autoclick(source=source)


def toggle_building_autobuy(e=None, source="hotkey"):
    _get_bot_controls().toggle_building_autobuy(source=source)


def toggle_lucky_reserve(e=None, source="hotkey"):
    _get_bot_controls().toggle_lucky_reserve(source=source)


def toggle_upgrade_autobuy(e=None, source="hotkey"):
    _get_bot_controls().toggle_upgrade_autobuy(source=source)


def toggle_ascension_prep(e=None, source="hotkey"):
    _get_bot_controls().toggle_ascension_prep(source=source)


def set_building_cap(building_name, cap):
    return _get_bot_controls().set_building_cap(building_name, cap)


def set_upgrade_horizon_seconds(horizon_seconds):
    return _get_bot_controls().set_upgrade_horizon_seconds(horizon_seconds)


def set_building_horizon_seconds(horizon_seconds):
    return _get_bot_controls().set_building_horizon_seconds(horizon_seconds)


def set_building_cap_ignored(building_name, ignored):
    return _get_bot_controls().set_building_cap_ignored(building_name, ignored)


def toggle_stock_trading(e=None, source="hotkey"):
    _get_bot_controls().toggle_stock_trading(source=source)


def cycle_wrinkler_mode(e=None):
    _get_bot_controls().cycle_wrinkler_mode()


def exit_program():
    log.info("Exit hotkey pressed - shutting down.")
    os._exit(0)


def main():
    from clicker_bot.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
