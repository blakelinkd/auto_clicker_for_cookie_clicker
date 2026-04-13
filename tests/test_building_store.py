import unittest

from clicker_bot.features.building_store import BuildingStoreController


def _identity_point(x, y):
    return x, y


def _box(left, top, right, bottom):
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "centerX": (left + right) // 2,
        "centerY": (top + bottom) // 2,
    }


def _box_with_click(left, top, right, bottom, click_x, click_y):
    rect = _box(left, top, right, bottom)
    rect["clickX"] = click_x
    rect["clickY"] = click_y
    return rect


class BuildingStoreControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = BuildingStoreController()

    def test_scrolls_down_when_target_building_is_below_viewport(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "productsViewport": _box(100, 200, 400, 600),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 18,
                    "name": "You",
                    "canBuy": True,
                    "visible": False,
                    "target": _box(120, 760, 380, 840),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 18)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "scroll_store")
        self.assertLess(action.scroll_steps, 0)

    def test_scrolls_up_when_target_building_is_above_viewport(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "productsViewport": _box(100, 400, 400, 800),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 2,
                    "name": "Farm",
                    "canBuy": True,
                    "visible": False,
                    "target": _box(120, 120, 380, 220),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 2)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "scroll_store")
        self.assertGreater(action.scroll_steps, 0)

    def test_scrolls_when_target_is_marked_visible_but_bounds_are_outside_viewport(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "productsViewport": _box(100, 200, 400, 600),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 15,
                    "name": "Fractal engine",
                    "canBuy": True,
                    "visible": True,
                    "target": _box(120, 620, 380, 700),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 15)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "scroll_store")
        self.assertLess(action.scroll_steps, 0)

    def test_clicks_when_target_center_is_actionable_even_if_row_is_slightly_clipped(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "productsViewport": _box(100, 328, 400, 1440),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 0,
                    "name": "Cursor",
                    "canBuy": True,
                    "visible": True,
                    "target": _box(120, 320, 380, 384),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 0)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "click_building")

    def test_focus_building_reuses_scroll_plan(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "productsViewport": _box(100, 200, 400, 600),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 7,
                    "name": "Wizard tower",
                    "canBuy": True,
                    "visible": False,
                    "target": _box(120, 760, 380, 840),
                }
            ],
        }

        action = self.controller.plan_focus_building(snapshot, _identity_point, 7)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "scroll_store")

    def test_normalizes_bulk_before_scrolling_to_target_building(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 10,
                "productsViewport": _box(100, 200, 400, 600),
                "bulk1": _box(20, 20, 60, 60),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 18,
                    "name": "Cortex baker",
                    "canBuy": True,
                    "visible": False,
                    "target": _box(120, 760, 380, 840),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 18, quantity=1)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "set_store_bulk")
        self.assertEqual(action.store_bulk, 1)

    def test_scroll_uses_safe_interior_viewport_anchor_when_explicit_click_is_on_edge(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "productsViewport": _box_with_click(100, 200, 400, 600, 388, 580),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 18,
                    "name": "You",
                    "canBuy": True,
                    "visible": False,
                    "target": _box(120, 760, 380, 840),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 18)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "scroll_store")
        self.assertNotEqual((action.screen_x, action.screen_y), (388, 580))
        self.assertGreater(action.screen_x, 100)
        self.assertLess(action.screen_x, 400)
        self.assertGreater(action.screen_y, 200)
        self.assertLess(action.screen_y, 600)

    def test_scroll_uses_multiple_steps_for_large_delta(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "productsViewport": _box(100, 200, 400, 600),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 18,
                    "name": "You",
                    "canBuy": True,
                    "visible": False,
                    "target": _box(120, 760, 380, 840),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 18)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "scroll_store")
        self.assertLess(action.scroll_steps, -10)

    def test_chooses_safe_building_click_point_when_center_is_obstructed(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "modeBuy": _box(210, 230, 290, 320),
                "productsViewport": _box(100, 200, 400, 600),
                "sections": {
                    "products": {
                        "collapsed": False,
                    }
                },
            },
            "buildings": [
                {
                    "id": 3,
                    "name": "Mine",
                    "canBuy": True,
                    "visible": True,
                    "target": _box(120, 220, 380, 284),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 3)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "click_building")
        self.assertNotEqual((action.screen_x, action.screen_y), (250, 252))


if __name__ == "__main__":
    unittest.main()
