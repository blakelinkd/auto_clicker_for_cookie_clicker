import unittest

from clicker_bot.dashboard_state import DashboardStateBuilder
from clicker_bot.runtime import RuntimeConfig, RuntimeStore


class DashboardStateBuilderTests(unittest.TestCase):
    def _store(self):
        store = RuntimeStore(
            RuntimeConfig(
                hud_recent_events=2,
                gameplay_feed_size=5,
                upgrade_horizon_seconds=1.0,
                building_horizon_seconds=1.0,
                wrinkler_mode="hold",
                stock_trading_enabled=False,
                lucky_reserve_enabled=False,
                building_autobuy_enabled=False,
                upgrade_autobuy_enabled=True,
                ascension_prep_enabled=False,
                garden_automation_enabled=True,
            main_cookie_clicking_enabled=True,
            shimmer_autoclick_enabled=True,
            wrath_cookie_clicking_enabled=True,
        )
        )
        store.update(active=True, last_shimmer_telemetry={"blockedCount": 2, "lastChoice": "golden"})
        store.append_recent_event("one")
        store.append_recent_event("two")
        store.append_recent_event("three")
        store.append_feed_event({"message": "feed"})
        return store

    def test_build_returns_dashboard_payload(self):
        builder = DashboardStateBuilder(
            runtime_store=self._store(),
            hud_recent_events=2,
            get_trade_stats=lambda: {"trades": 1},
            get_building_stats=lambda: {"builds": 2},
            get_ascension_prep_stats=lambda: {"asc": 3},
            get_garden_stats=lambda: {"garden": 4},
            get_combo_stats=lambda: {"combo": 5},
            get_spell_stats=lambda: {"spell": 6},
            get_wrinkler_stats=lambda: {"wrinkler": 7},
            shimmer_seed_history=[
                {"classification": "positive", "seed": 11},
                {"classification": "negative"},
                {"classification": "neutral"},
            ],
            get_shimmer_reset_reason=lambda: "session_start",
        )

        payload = builder.build()

        self.assertEqual(payload["events"], ["two", "three"])
        self.assertEqual(payload["feed"], [{"message": "feed"}])
        self.assertEqual(payload["trade_stats"], {"trades": 1})
        self.assertEqual(payload["shimmer_stats"]["total"], 3)
        self.assertEqual(payload["shimmer_stats"]["seeds_captured"], 1)
        self.assertEqual(payload["shimmer_stats"]["blocked_total"], 2)
        self.assertEqual(payload["shimmer_stats"]["reset_reason"], "session_start")
