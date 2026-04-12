import unittest

from clicker_bot.runtime import RuntimeConfig, RuntimeStore


class RuntimeStoreTests(unittest.TestCase):
    def _store(self):
        return RuntimeStore(
            RuntimeConfig(
                hud_recent_events=3,
                gameplay_feed_size=2,
                upgrade_horizon_seconds=1800.0,
                building_horizon_seconds=1200.0,
                wrinkler_mode="hold",
                stock_trading_enabled=False,
                lucky_reserve_enabled=False,
                building_autobuy_enabled=False,
                upgrade_autobuy_enabled=True,
                ascension_prep_enabled=False,
                garden_automation_enabled=True,
                main_cookie_clicking_enabled=True,
                shimmer_autoclick_enabled=True,
            )
        )

    def test_snapshot_state_returns_copies(self):
        store = self._store()
        store.update(active=True)
        store.append_recent_event("one")
        store.append_feed_event({"message": "alpha"})

        state, events, feed = store.snapshot_state()

        self.assertTrue(state["active"])
        self.assertEqual(events, ["one"])
        self.assertEqual(feed, [{"message": "alpha"}])

        events.append("mutated")
        feed.append({"message": "beta"})
        self.assertEqual(list(store.recent_events), ["one"])
        self.assertEqual(list(store.gameplay_feed), [{"message": "alpha"}])

    def test_latest_big_cookie_is_returned_as_copy(self):
        store = self._store()
        store.set_snapshot({"cookies": 1}, {"screen_x": 10, "screen_y": 20})

        big_cookie = store.get_latest_big_cookie()

        self.assertEqual(big_cookie, {"screen_x": 10, "screen_y": 20})
        big_cookie["screen_x"] = 99
        self.assertEqual(store.get_latest_big_cookie()["screen_x"], 10)
