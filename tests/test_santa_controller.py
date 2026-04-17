import unittest

from clicker_bot.features.santa_controller import SantaController


class _LogStub:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def debug(self, message):
        self.messages.append(("debug", message))

    def warning(self, message):
        self.messages.append(("warning", message))


class SantaControllerTests(unittest.TestCase):
    def test_get_action_clicks_until_target_level(self):
        controller = SantaController(_LogStub())
        snapshot = {
            "santa": {
                "unlocked": True,
                "level": 0,
                "maxLevel": 14,
                "currentName": "Festive test tube",
                "nextName": "Festive ornament",
                "clickTarget": {"clickX": 12, "clickY": 34},
                "selectTarget": {"clickX": 40, "clickY": 50},
            }
        }

        action = controller.get_action(snapshot, lambda x, y: (x + 1, y + 2), now=100.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "click_santa")
        self.assertEqual((action.screen_x, action.screen_y), (13, 36))
        self.assertEqual(action.current_name, "Festive test tube")
        self.assertEqual(action.next_name, "Festive ornament")
        self.assertEqual(action.target_level, 14)

    def test_get_action_respects_target_level_and_cooldown(self):
        controller = SantaController(_LogStub(), target_level=1)
        snapshot = {
            "santa": {
                "unlocked": True,
                "level": 0,
                "maxLevel": 14,
                "currentName": "Festive test tube",
                "nextName": "Festive ornament",
                "clickTarget": {"clickX": 12, "clickY": 34},
            }
        }

        action = controller.get_action(snapshot, lambda x, y: (x, y), now=100.0)
        self.assertIsNotNone(action)
        controller.record_action(action)

        self.assertIsNone(controller.get_action(snapshot, lambda x, y: (x, y), now=100.1))
        snapshot["santa"]["level"] = 1
        self.assertIsNone(controller.get_action(snapshot, lambda x, y: (x, y), now=100.5))

    def test_get_action_uses_evolve_button_when_panel_is_open(self):
        controller = SantaController(_LogStub())
        snapshot = {
            "santa": {
                "unlocked": True,
                "level": 0,
                "maxLevel": 14,
                "currentName": "Festive test tube",
                "nextName": "Festive ornament",
                "open": True,
                "canEvolve": True,
                "evolveTarget": {"clickX": 40, "clickY": 50},
            }
        }

        action = controller.get_action(snapshot, lambda x, y: (x + 1, y + 2), now=100.0)

        self.assertIsNotNone(action)
        self.assertEqual((action.screen_x, action.screen_y), (41, 52))
        self.assertEqual(action.reason, "evolve_santa")
        self.assertFalse(any("Santa panel fallback" in message for _level, message in controller.log.messages))

    def test_get_action_waits_for_funds_when_evolve_button_is_unaffordable(self):
        controller = SantaController(_LogStub())
        snapshot = {
            "santa": {
                "unlocked": True,
                "level": 0,
                "maxLevel": 14,
                "currentName": "Festive test tube",
                "nextName": "Festive ornament",
                "open": True,
                "canEvolve": False,
                "nextCost": 1,
                "cookies": 1,
                "evolveTarget": {"clickX": 40, "clickY": 50},
            }
        }

        action = controller.get_action(snapshot, lambda x, y: (x + 1, y + 2), now=100.0)
        diagnostics = controller.get_diagnostics(snapshot, lambda x, y: (x, y))

        self.assertIsNone(action)
        self.assertTrue(diagnostics["available"])
        self.assertEqual(diagnostics["reason"], "santa_waiting_for_funds")
        self.assertEqual(diagnostics["next_cost"], 1)
        self.assertEqual(diagnostics["cookies"], 1)

    def test_get_action_clicks_panel_opener_when_evolve_button_is_missing(self):
        controller = SantaController(_LogStub())
        snapshot = {
            "santa": {
                "unlocked": True,
                "level": 0,
                "maxLevel": 14,
                "currentName": "Festive test tube",
                "nextName": "Festive ornament",
                "clickTarget": {"clickX": 40, "clickY": 50},
            }
        }

        action = controller.get_action(snapshot, lambda x, y: (x + 1, y + 2), now=100.0)

        self.assertIsNotNone(action)
        self.assertEqual((action.screen_x, action.screen_y), (41, 52))
        self.assertEqual(action.reason, "open_santa_panel")
        self.assertTrue(
            any(
                level == "info" and "Santa panel fallback" in message
                for level, message in controller.log.messages
            )
        )

    def test_get_diagnostics_reports_evolve_ready_when_panel_is_open(self):
        controller = SantaController(_LogStub())
        snapshot = {
            "santa": {
                "unlocked": True,
                "level": 0,
                "maxLevel": 14,
                "currentName": "Festive test tube",
                "nextName": "Festive ornament",
                "open": True,
                "canEvolve": True,
                "evolveTarget": {"clickX": 40, "clickY": 50},
            }
        }

        diagnostics = controller.get_diagnostics(snapshot, lambda x, y: (x, y))

        self.assertTrue(diagnostics["available"])
        self.assertEqual(diagnostics["reason"], "santa_evolve_ready")


if __name__ == "__main__":
    unittest.main()
