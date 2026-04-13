import unittest

from clicker_bot.features.upgrade_store import UpgradeStoreController


def _identity_point(x, y):
    return x, y


def _rect(x, y):
    return {
        "centerX": x,
        "centerY": y,
    }


def _box(left, top, right, bottom):
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "centerX": (left + right) // 2,
        "centerY": (top + bottom) // 2,
    }


class UpgradeStoreControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = UpgradeStoreController()

    def test_expands_upgrades_section_before_clicking(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "sections": {
                    "upgrades": {
                        "collapsed": True,
                        "toggle": _rect(10, 10),
                    }
                },
            },
            "upgrades": [
                {
                    "id": 7,
                    "displayName": "Test Upgrade",
                    "canBuy": True,
                    "target": _rect(20, 20),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 7)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "expand_upgrades_section")

    def test_clicks_upgrade_when_visible_and_affordable(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "sections": {
                    "upgrades": {
                        "collapsed": False,
                        "toggle": _rect(10, 10),
                        "rect": _rect(20, 20),
                    }
                },
            },
            "upgrades": [
                {
                    "id": 7,
                    "displayName": "Test Upgrade",
                    "canBuy": True,
                    "visible": True,
                    "target": _rect(20, 20),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 7)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "click_upgrade")
        self.assertEqual(action.upgrade_id, 7)

    def test_focuses_store_when_upgrade_is_offscreen(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "productsViewport": _rect(20, 200),
                "sections": {
                    "upgrades": {
                        "collapsed": False,
                        "toggle": _rect(10, 10),
                        "rect": _rect(20, 20),
                    }
                },
            },
            "upgrades": [
                {
                    "id": 7,
                    "displayName": "Test Upgrade",
                    "canBuy": True,
                    "visible": False,
                    "target": _rect(20, 600),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 7)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "focus_store_section")
        self.assertEqual(action.section_name, "upgrades")

    def test_clicks_upgrade_when_flagged_not_visible_but_target_is_inside_viewport(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "sections": {
                    "upgrades": {
                        "collapsed": False,
                        "toggle": _rect(10, 10),
                        "rect": _box(2243, 218, 2543, 320),
                    }
                },
            },
            "upgrades": [
                {
                    "id": 761,
                    "displayName": "Thoughts & prayers",
                    "canBuy": True,
                    "visible": False,
                    "row": _box(2249, 218, 2297, 266),
                    "target": _box(2249, 218, 2297, 266),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 761)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "click_upgrade")
        self.assertEqual(action.upgrade_id, 761)

    def test_avoids_store_controls_when_upgrade_rect_overlaps_them(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "modeBuy": _box(2243, 212, 2303, 228),
                "modeSell": _box(2243, 227, 2303, 243),
                "bulk1": _box(2303, 212, 2363, 244),
                "bulk10": _box(2363, 212, 2423, 244),
                "bulk100": _box(2423, 212, 2483, 244),
                "bulkMax": _box(2483, 212, 2543, 244),
                "sections": {
                    "upgrades": {
                        "collapsed": False,
                        "toggle": _rect(10, 10),
                        "rect": _rect(20, 20),
                    }
                },
            },
            "upgrades": [
                {
                    "id": 11,
                    "displayName": "Fertilizer",
                    "canBuy": True,
                    "visible": True,
                    "target": _box(2249, 202, 2297, 250),
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 11)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "click_upgrade")
        self.assertEqual(action.screen_x, 2273)
        self.assertEqual(action.screen_y, 208)

    def test_prefers_explicit_click_point_from_feed(self):
        snapshot = {
            "store": {
                "buyMode": 1,
                "buyBulk": 1,
                "modeBuy": _box(120, 220, 160, 236),
                "modeSell": _box(120, 236, 160, 252),
                "sections": {
                    "upgrades": {
                        "collapsed": False,
                        "toggle": _rect(10, 10),
                        "rect": _rect(20, 20),
                    }
                },
            },
            "upgrades": [
                {
                    "id": 11,
                    "displayName": "Fertilizer",
                    "canBuy": True,
                    "visible": True,
                    "target": {
                        "left": 100,
                        "top": 200,
                        "right": 160,
                        "bottom": 260,
                        "centerX": 130,
                        "centerY": 210,
                        "clickX": 142,
                        "clickY": 248,
                    },
                }
            ],
        }

        action = self.controller.plan_buy(snapshot, _identity_point, 11)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, "click_upgrade")
        self.assertEqual(action.screen_x, 142)
        self.assertEqual(action.screen_y, 248)


if __name__ == "__main__":
    unittest.main()
