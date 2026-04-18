import unittest
from unittest.mock import patch

from clicker_bot.dashboard import DashboardCallbacks, build_dashboard, QT_AVAILABLE


class DashboardFactoryTests(unittest.TestCase):
    def test_build_dashboard_passes_callbacks_through(self):
        callbacks = DashboardCallbacks(
            get_dashboard_state=lambda: None,
            toggle_active=lambda: None,
            toggle_main_autoclick=lambda: None,
            toggle_shimmer_autoclick=lambda: None,
            toggle_stock_buying=lambda: None,
            toggle_lucky_reserve=lambda: None,
            toggle_building_buying=lambda: None,
            toggle_upgrade_buying=lambda: None,
            toggle_ascension_prep=lambda: None,
            toggle_garden_automation=lambda: None,
            set_upgrade_horizon_seconds=lambda value: value,
            set_building_horizon_seconds=lambda value: value,
            set_building_cap=lambda name, cap: (name, cap),
            set_building_cap_ignored=lambda name, ignored: (name, ignored),
            cycle_wrinkler_mode=lambda: None,
            cycle_garden_mode=lambda: None,
            exit_program=lambda: None,
            dump_shimmer_data=lambda: None,
            send_overlay_message=lambda *args, **kwargs: None,
            delete_overlay_message=lambda *args, **kwargs: None,
            send_biden_timer=lambda *args, **kwargs: None,
            send_voice_message=lambda *args, **kwargs: None,
        )

        # Since we prefer Qt when available, patch QtDashboard
        with patch("clicker_bot.dashboard.QtDashboard") as dashboard_cls:
            build_dashboard(
                callbacks=callbacks,
                initial_geometry="800x600",
                refresh_interval_ms=500,
            )

        dashboard_cls.assert_called_once()
        kwargs = dashboard_cls.call_args.kwargs
        self.assertIs(kwargs["get_dashboard_state"], callbacks.get_dashboard_state)
        self.assertIs(kwargs["send_overlay_message"], callbacks.send_overlay_message)
        self.assertIs(kwargs["delete_overlay_message"], callbacks.delete_overlay_message)
        self.assertIs(kwargs["send_biden_timer"], callbacks.send_biden_timer)
        self.assertIs(kwargs["send_voice_message"], callbacks.send_voice_message)
        self.assertEqual(kwargs["initial_geometry"], "800x600")
        self.assertEqual(kwargs["refresh_interval_ms"], 500)
