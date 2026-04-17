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


if __name__ == "__main__":
    unittest.main()
