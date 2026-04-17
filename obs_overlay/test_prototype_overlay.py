import unittest

from overlay_math import sprite_top_left_for_target


class PrototypeOverlayMathTests(unittest.TestCase):
    def test_sprite_top_left_places_finger_anchor_on_target(self):
        top_left = sprite_top_left_for_target(
            target_x=640,
            target_y=180,
            sprite_width=226,
            sprite_height=320,
            scale=1.0,
        )

        self.assertAlmostEqual(top_left[0] + (226 * 0.0071), 640, places=3)
        self.assertAlmostEqual(top_left[1] + (320 * 0.1389), 180, places=3)


if __name__ == "__main__":
    unittest.main()
