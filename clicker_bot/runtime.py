from collections import deque
from dataclasses import dataclass
import threading
import time


@dataclass(frozen=True)
class RuntimeConfig:
    hud_recent_events: int
    gameplay_feed_size: int
    upgrade_horizon_seconds: float
    building_horizon_seconds: float
    wrinkler_mode: str
    stock_trading_enabled: bool
    lucky_reserve_enabled: bool
    building_autobuy_enabled: bool
    upgrade_autobuy_enabled: bool
    ascension_prep_enabled: bool
    garden_automation_enabled: bool
    main_cookie_clicking_enabled: bool
    shimmer_autoclick_enabled: bool
    wrath_cookie_clicking_enabled: bool


class RuntimeStore:
    """Owns dashboard/runtime state and lightweight feed buffers."""

    def __init__(self, config: RuntimeConfig):
        self.lock = threading.Lock()
        self.snapshot_lock = threading.Lock()
        self.state = {
            "started_at": time.monotonic(),
            "shimmer_collected": 0,
            "shimmer_clicks": 0,
            "main_clicks": 0,
            "last_shimmer": None,
            "last_shimmer_effect": None,
            "last_feed_age": None,
            "last_big_cookie": None,
            "last_buffs": (),
            "last_spell_diag": {},
            "last_bank_diag": {},
            "last_garden_diag": {},
            "last_building_diag": {},
            "last_upgrade_diag": {},
            "last_ascension_prep_diag": {},
            "last_ascension": {},
            "last_lump_diag": {},
            "last_golden_diag": {},
            "last_purchase_goal": None,
            "last_shimmer_telemetry": {},
            "upgrade_horizon_seconds": config.upgrade_horizon_seconds,
            "building_horizon_seconds": config.building_horizon_seconds,
            "last_combo_diag": {},
            "last_wrinkler_diag": {},
            "last_dragon_diag": {},
            "last_spell_cast": None,
            "last_trade_action": None,
            "last_garden_action": None,
            "last_building_action": None,
            "last_ascension_prep_action": None,
            "last_combo_action": None,
            "last_wrinkler_action": None,
            "last_dragon_action": None,
            "last_note_action": None,
            "last_lump_action": None,
            "wrinkler_mode": config.wrinkler_mode,
            "stock_trading_enabled": config.stock_trading_enabled,
            "lucky_reserve_enabled": config.lucky_reserve_enabled,
            "building_autobuy_enabled": config.building_autobuy_enabled,
            "upgrade_autobuy_enabled": config.upgrade_autobuy_enabled,
            "ascension_prep_enabled": config.ascension_prep_enabled,
            "garden_automation_enabled": config.garden_automation_enabled,
            "main_cookie_clicking_enabled": config.main_cookie_clicking_enabled,
            "shimmer_autoclick_enabled": config.shimmer_autoclick_enabled,
            "wrath_cookie_clicking_enabled": config.wrath_cookie_clicking_enabled,
            "active": False,
            "feed_load_ms": None,
            "feed_parse_ms": None,
            "click_idle_misses": 0,
            "click_suppressed_loops": 0,
            "click_loop_avg_ms": None,
            "click_loop_max_ms": None,
            "click_action_avg_ms": None,
            "click_action_max_ms": None,
            "dom_loop_avg_ms": None,
            "dom_loop_max_ms": None,
            "dom_extract_avg_ms": None,
            "dom_extract_max_ms": None,
            "dom_diag_avg_ms": None,
            "dom_diag_max_ms": None,
            "dom_shimmer_avg_ms": None,
            "dom_shimmer_max_ms": None,
            "dom_action_avg_ms": None,
            "dom_action_max_ms": None,
            "snapshot_profile": {},
            "stock_profile": {},
            "db_profile": {},
            "combo_run_count": 0,
            "last_combo_run_gain": None,
            "last_combo_run_peak_gain": None,
            "last_combo_run_duration": None,
            "last_combo_run_stage": None,
        }
        self.recent_events = deque(maxlen=config.hud_recent_events)
        self.gameplay_feed = deque(maxlen=config.gameplay_feed_size)
        self.latest_snapshot = None
        self.latest_big_cookie = None

    def update(self, **kwargs):
        with self.lock:
            self.state.update(kwargs)

    def append_recent_event(self, message):
        with self.lock:
            self.recent_events.append(message)

    def append_feed_event(self, entry):
        with self.lock:
            self.gameplay_feed.append(entry)

    def snapshot_state(self):
        with self.lock:
            return dict(self.state), list(self.recent_events), list(self.gameplay_feed)

    def set_snapshot(self, snapshot, big_cookie):
        with self.snapshot_lock:
            self.latest_snapshot = snapshot
            self.latest_big_cookie = big_cookie

    def get_latest_big_cookie(self):
        with self.snapshot_lock:
            if self.latest_big_cookie is None:
                return None
            return dict(self.latest_big_cookie)
