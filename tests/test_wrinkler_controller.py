import unittest

from wrinkler_controller import WrinklerController, WRINKLER_MODE_SHINY_HUNT


class _LogStub:
    def info(self, message):
        pass


def _identity_point(x, y):
    return x, y


class WrinklerControllerShinyProtectionTests(unittest.TestCase):
    def setUp(self):
        self.controller = WrinklerController(_LogStub(), mode=WRINKLER_MODE_SHINY_HUNT)

    def _snapshot(self, wrinklers):
        return {
            "season": "",
            "spellbook": {
                "activeBuffs": [],
            },
            "wrinklers": {
                "elderWrath": 1,
                "active": len(wrinklers),
                "attached": len(wrinklers),
                "max": 10,
                "openSlots": max(0, 10 - len(wrinklers)),
                "shiny": sum(1 for item in wrinklers if item.get("type") == 1),
                "wrinklers": wrinklers,
            },
        }

    def test_preserves_shiny_when_normal_wrinkler_exists(self):
        snapshot = self._snapshot(
            [
                {
                    "id": 1,
                    "phase": 2,
                    "close": 1.0,
                    "type": 1,
                    "clicks": 0,
                    "sucked": 100.0,
                    "estimatedReward": 330.0,
                    "clientX": 10,
                    "clientY": 10,
                },
                {
                    "id": 2,
                    "phase": 2,
                    "close": 1.0,
                    "type": 0,
                    "clicks": 0,
                    "sucked": 50.0,
                    "estimatedReward": 55.0,
                    "clientX": 20,
                    "clientY": 20,
                },
            ]
        )

        action = self.controller.get_action(snapshot, _identity_point, now=10.0)

        self.assertIsNotNone(action)
        self.assertEqual(action.wrinkler_id, 2)
        self.assertEqual(action.wrinkler_type, 0)

    def test_allows_shiny_when_it_is_last_attached_wrinkler_for_goal_funding(self):
        snapshot = self._snapshot(
            [
                {
                    "id": 1,
                    "phase": 2,
                    "close": 1.0,
                    "type": 1,
                    "clicks": 0,
                    "sucked": 100.0,
                    "estimatedReward": 330.0,
                    "clientX": 10,
                    "clientY": 10,
                }
            ]
        )

        action = self.controller.get_action(
            snapshot,
            _identity_point,
            now=10.0,
            pop_goal={
                "kind": "building",
                "name": "Farm",
                "price": 300.0,
                "cookies": 0.0,
                "can_buy": False,
                "shortfall": 300.0,
            },
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.wrinkler_id, 1)
        self.assertEqual(action.wrinkler_type, 1)

    def test_force_liquidation_overrides_valuable_buff_hold(self):
        snapshot = self._snapshot(
            [
                {
                    "id": 7,
                    "phase": 2,
                    "close": 1.0,
                    "type": 0,
                    "clicks": 0,
                    "sucked": 100.0,
                    "estimatedReward": 250.0,
                    "clientX": 15,
                    "clientY": 15,
                }
            ]
        )
        snapshot["spellbook"]["activeBuffs"] = [{"name": "Frenzy"}]

        action = self.controller.get_action(
            snapshot,
            _identity_point,
            now=10.0,
            pop_goal={
                "kind": "building",
                "name": "Mine",
                "price": 10_000.0,
                "cookies": 0.0,
                "can_buy": False,
                "shortfall": 10_000.0,
                "force_wrinkler_liquidation": True,
            },
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.wrinkler_id, 7)
        self.assertEqual(action.reason, "valuable_buff_active")


if __name__ == "__main__":
    unittest.main()
