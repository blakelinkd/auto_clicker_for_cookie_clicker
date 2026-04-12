import unittest

from clicker_bot.stock_helpers import get_garden_cookie_reserve, has_cookies_after_reserve


class GardenReserveTests(unittest.TestCase):
    def test_reserve_only_applies_when_waiting_for_seed_funds(self):
        reserve = get_garden_cookie_reserve(
            {"cookies": 5000.0},
            {
                "plan_mode": "mutation",
                "planner_state": "waiting_for_seed_funds",
                "remaining_layout_cost": 12000.0,
            },
            garden_automation_enabled=True,
        )
        self.assertEqual(reserve, 0.0)

        reserve = get_garden_cookie_reserve(
            {"cookies": 15000.0},
            {
                "plan_mode": "mutation",
                "planner_state": "waiting_for_seed_funds",
                "remaining_layout_cost": 12000.0,
            },
            garden_automation_enabled=True,
        )
        self.assertEqual(reserve, 12000.0)

        reserve = get_garden_cookie_reserve(
            {"cookies": 5000.0},
            {
                "plan_mode": "mutation",
                "planner_state": "waiting_for_mutation",
                "remaining_layout_cost": 12000.0,
            },
            garden_automation_enabled=True,
        )
        self.assertEqual(reserve, 0.0)

    def test_reserve_zero_when_garden_automation_disabled(self):
        reserve = get_garden_cookie_reserve(
            {"cookies": 15000.0},
            {
                "plan_mode": "mutation",
                "planner_state": "waiting_for_seed_funds",
                "remaining_layout_cost": 12000.0,
            },
            garden_automation_enabled=False,
        )
        self.assertEqual(reserve, 0.0)

    def test_available_cookies_check_respects_reserve(self):
        has_cookies = has_cookies_after_reserve(
            {"cookies": 10000.0},
            3000.0,
            8000.0,
        )
        self.assertFalse(has_cookies)

        has_cookies = has_cookies_after_reserve(
            {"cookies": 10000.0},
            1500.0,
            8000.0,
        )
        self.assertTrue(has_cookies)


if __name__ == "__main__":
    unittest.main()
