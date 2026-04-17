import unittest

from clicker_bot.features.godzamok_combo import GodzamokComboEngine


class _LogStub:
    def debug(self, message):
        pass

    def info(self, message):
        pass

    def warning(self, message):
        pass


class GodzamokSellFloorTests(unittest.TestCase):
    def setUp(self):
        self.engine = GodzamokComboEngine(_LogStub(), click_interval=0.05)

    def test_minigame_floor_blocks_farm_sell_below_garden_soil_threshold(self):
        state = {
            "ruin_bonus_per_sale": 0.01,
            "computed_mouse_cps": 1000.0,
            "combo_eval": {"should_fire_godzamok": True},
            "cookies": 1_000_000.0,
            "cookies_ps": 10.0,
            "sell_retain_floors": {"Farm": 300},
            "buildings": {
                2: {
                    "id": 2,
                    "name": "Farm",
                    "amount": 300,
                    "can_sell": True,
                    "can_buy": True,
                    "target": {"screen_x": 10, "screen_y": 10},
                    "price": 1000.0,
                    "sell_multiplier": 0.25,
                    "stored_cps": 10.0,
                }
            },
        }

        candidate = self.engine._find_candidate(state)

        self.assertIsNone(candidate)

    def test_dragon_floor_blocks_required_building_sell(self):
        state = {
            "ruin_bonus_per_sale": 0.01,
            "computed_mouse_cps": 1000.0,
            "combo_eval": {"should_fire_godzamok": True},
            "cookies": 1_000_000.0,
            "cookies_ps": 10.0,
            "sell_retain_floors": {"Cursor": 100},
            "buildings": {
                0: {
                    "id": 0,
                    "name": "Cursor",
                    "amount": 100,
                    "can_sell": True,
                    "can_buy": True,
                    "target": {"screen_x": 10, "screen_y": 10},
                    "price": 1000.0,
                    "sell_multiplier": 0.25,
                    "stored_cps": 10.0,
                }
            },
        }

        candidate = self.engine._find_candidate(state)

        self.assertIsNone(candidate)

    def test_parses_dragon_all_buildings_special_floor(self):
        floors = self.engine._build_sell_retain_floors(
            {
                "dragon": {
                    "nextCostType": "special",
                    "nextCostText": "50 of every building",
                }
            },
            {
                0: {"name": "Cursor"},
                2: {"name": "Farm"},
            },
        )

        self.assertEqual(floors["Cursor"], 50)
        self.assertEqual(floors["Farm"], 300)

    def test_opens_temple_when_godzamok_is_slotted_but_temple_is_closed(self):
        snapshot = {
            "cookies": 1_000_000.0,
            "cookiesPs": 10.0,
            "computedMouseCps": 1000.0,
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "products": [],
                "upgrades": [],
            },
            "temple": {
                "onMinigame": False,
                "openControl": {"centerX": 10, "centerY": 12},
                "ruinLevel": 1,
            },
            "spellbook": {
                "magic": 0.0,
                "maxMagic": 0.0,
                "spells": [],
            },
            "buffs": [],
            "buildings": [],
        }

        action = self.engine.get_action(snapshot, lambda x, y: (x, y), now=10.0)
        diag = self.engine.get_diagnostics(snapshot, lambda x, y: (x, y))

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "open_temple")
        self.assertEqual(action.detail, "open_temple")
        self.assertEqual(diag["reason"], "temple_closed_can_open")
        self.assertEqual(diag["combo_phase"], "idle")


if __name__ == "__main__":
    unittest.main()
