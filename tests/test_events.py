import unittest

from clicker_bot.events import BotEventRecorder
from clicker_bot.runtime import RuntimeConfig, RuntimeStore


class BotEventRecorderTests(unittest.TestCase):
    def _store(self):
        return RuntimeStore(
            RuntimeConfig(
                hud_recent_events=5,
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

    def test_record_event_appends_feed_and_recent(self):
        store = self._store()
        recorder = BotEventRecorder(runtime_store=store, infer_feed_category=lambda message: "system")

        recorder.record_event("hello")

        _state, events, feed = store.snapshot_state()
        self.assertEqual(events, ["hello"])
        self.assertEqual(feed[0]["message"], "hello")
        self.assertEqual(feed[0]["category"], "system")
