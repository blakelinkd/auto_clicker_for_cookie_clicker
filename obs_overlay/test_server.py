import json
import queue
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import server


class ServerEventTests(unittest.TestCase):
    def test_validate_spawn_event_clamps_target_and_duration(self):
        event = server.validate_spawn_event(
            {
                "type": "spawn_biden",
                "target": {"norm_x": 2, "norm_y": -1},
                "animation": {"duration_ms": 50},
            }
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["target"]["norm_x"], 1.0)
        self.assertEqual(event["target"]["norm_y"], 0.0)
        self.assertEqual(event["animation"]["duration_ms"], 100)

    def test_validate_spawn_event_rejects_missing_target(self):
        self.assertIsNone(server.validate_spawn_event({"type": "spawn_biden"}))

    def test_validate_play_sound_event(self):
        event = server.validate_spawn_event({"type": "play_sound", "sound": "dean"})

        self.assertEqual(event, {"version": 1, "type": "play_sound", "sound": "dean"})
        self.assertIsNone(server.validate_spawn_event({"type": "play_sound", "sound": "bad"}))

    def test_broadcast_event_queues_json_for_clients(self):
        client = queue.Queue()
        with server.CLIENTS_LOCK:
            server.CLIENTS.clear()
            server.CLIENTS.add(client)
        try:
            server.broadcast_event({"type": "spawn_biden", "target": {"norm_x": 0.5, "norm_y": 0.5}})
            payload = json.loads(client.get_nowait())
        finally:
            with server.CLIENTS_LOCK:
                server.CLIENTS.clear()

        self.assertEqual(payload["type"], "spawn_biden")
        self.assertEqual(payload["target"]["norm_x"], 0.5)

    def test_demo_event_is_valid_spawn_event(self):
        with patch("server.time.monotonic", return_value=10.0):
            event = server.validate_spawn_event(server.demo_event())

        self.assertIsNotNone(event)
        self.assertEqual(event["type"], "spawn_biden")

    def test_random_biden_event_is_valid_spawn_event(self):
        event = server.validate_spawn_event(server.random_biden_event())

        self.assertIsNotNone(event)
        self.assertEqual(event["type"], "spawn_biden")
        self.assertEqual(event["source"], "timer")

    def test_random_fruit_event_is_valid_spawn_event(self):
        event = server.validate_spawn_event(server.random_fruit_event())

        self.assertIsNotNone(event)
        self.assertEqual(event["type"], "spawn_fruit")
        self.assertEqual(event["fruit"]["kind"], "frenzy_cookie")

    def test_game_overlay_assets_exist_with_alpha(self):
        for name in ("cursor.png", "frenzy_cookie.png", "grandma_head.png", "grandma_head_smooth.png"):
            path = Path("obs_overlay/assets/game") / name
            self.assertTrue(path.is_file(), name)
            image = Image.open(path)
            self.assertEqual(image.mode, "RGBA")
            self.assertLess(image.getchannel("A").getextrema()[0], 255)

    def test_audio_assets_exist(self):
        for name in ("dean_scream.mp3", "grandma_cookie.mp3"):
            path = Path("obs_overlay/assets/audio") / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 1024)
            header = path.read_bytes()[:3]
            self.assertTrue(header == b"ID3" or header[:2] == b"\xff\xfb", name)


if __name__ == "__main__":
    unittest.main()
