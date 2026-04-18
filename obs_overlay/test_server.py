import json
import queue
import shutil
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

    def test_validate_reload_overlay_event(self):
        event = server.validate_spawn_event({"type": "reload_overlay"})

        self.assertEqual(event, {
            "version": 1,
            "type": "reload_overlay",
            "source": "overlay_server",
        })

    def test_overlay_reload_event_uses_source(self):
        event = server.overlay_reload_event("overlay_file_watch")

        self.assertEqual(event, {
            "version": 1,
            "type": "reload_overlay",
            "source": "overlay_file_watch",
        })

    def test_watched_file_snapshot_tracks_size_and_mtime(self):
        temp_dir = Path("obs_overlay/.test_tmp")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        try:
            temp_dir.mkdir()
            watched_path = temp_dir / "overlay.js"
            watched_path.write_text("one", encoding="utf-8")

            first = server.watched_file_snapshot((watched_path,))
            watched_path.write_text("two two", encoding="utf-8")
            second = server.watched_file_snapshot((watched_path,))
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

        self.assertIn(watched_path, first)
        self.assertIn(watched_path, second)
        self.assertNotEqual(first[watched_path], second[watched_path])

    def test_watched_file_snapshot_handles_missing_files(self):
        missing_path = Path("__missing_overlay_file__.js")

        snapshot = server.watched_file_snapshot((missing_path,))

        self.assertIsNone(snapshot[missing_path])

    def test_validate_hud_message_event(self):
        event = server.validate_spawn_event(
            {
                "type": "hud_message",
                "source": "qt_hud",
                "text": " Hello overlay ",
                "ttl_ms": 120000,
                "repeat_interval_ms": 300000,
                "submitted_at_ms": "123456",
            }
        )

        self.assertIsNotNone(event)
        self.assertEqual(event["version"], 1)
        self.assertEqual(event["type"], "hud_message")
        self.assertEqual(event["text"], "Hello overlay")
        self.assertEqual(event["ttl_ms"], 120000)
        self.assertEqual(event["repeat_interval_ms"], 300000)
        self.assertEqual(event["submitted_at_ms"], 123456)

    def test_validate_hud_message_rejects_empty_text_and_clamps_durations(self):
        self.assertIsNone(server.validate_spawn_event({"type": "hud_message", "text": "   "}))

        event = server.validate_spawn_event(
            {
                "type": "hud_message",
                "text": "Short",
                "ttl_ms": 1,
                "repeat_interval_ms": 999999999,
            }
        )

        self.assertEqual(event["ttl_ms"], 4000)
        self.assertEqual(event["repeat_interval_ms"], 86400000)

    def test_validate_hud_message_delete_event(self):
        event = server.validate_spawn_event({"type": "hud_message_delete", "event_id": " hud:test "})

        self.assertEqual(event, {
            "version": 1,
            "type": "hud_message_delete",
            "event_id": "hud:test",
            "source": "qt_hud",
        })
        self.assertIsNone(server.validate_spawn_event({"type": "hud_message_delete"}))

    def test_validate_biden_timer_event(self):
        event = server.validate_spawn_event(
            {"type": "biden_timer", "available": True, "remaining_seconds": "12.5", "on_screen": 1}
        )

        self.assertEqual(event["type"], "biden_timer")
        self.assertTrue(event["available"])
        self.assertEqual(event["remaining_seconds"], 12.5)
        self.assertEqual(event["on_screen"], 1)

        unavailable = server.validate_spawn_event({"type": "biden_timer", "available": True})
        self.assertFalse(unavailable["available"])

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

    def test_random_worm_event_is_valid_spawn_event(self):
        event = server.validate_spawn_event(server.random_worm_event())

        self.assertIsNotNone(event)
        self.assertEqual(event["type"], "spawn_worm")
        self.assertEqual(event["source"], "timer")

    def test_game_overlay_assets_exist_with_alpha(self):
        for name in ("cursor.png", "frenzy_cookie.png", "grandma_head.png", "grandma_head_smooth.png"):
            path = Path("obs_overlay/assets/game") / name
            self.assertTrue(path.is_file(), name)
            image = Image.open(path)
            self.assertEqual(image.mode, "RGBA")
            self.assertLess(image.getchannel("A").getextrema()[0], 255)

    def test_audio_assets_exist(self):
        for name in ("dean_scream.mp3", "grandma_cookie.mp3", "farting_sound.mp3", "chomp_sound_effect.mp3"):
            path = Path("obs_overlay/assets/audio") / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 1024)
            header = path.read_bytes()[:3]
            self.assertTrue(header == b"ID3" or header[:2] == b"\xff\xfb", name)

    def test_poop_sprite_sheet_exists_with_six_horizontal_frames(self):
        path = Path("obs_overlay/assets/sprites/poop.png")
        self.assertTrue(path.is_file())
        image = Image.open(path)
        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.width % 6, 0)
        self.assertEqual(image.width // 6, image.height)

    def test_worm_aseprite_asset_exists(self):
        path = Path("obs_overlay/assets/sprites/worm_with_bones.ase")
        self.assertTrue(path.is_file())
        data = path.read_bytes()
        self.assertGreater(len(data), 128)
        self.assertEqual(data[4:6], b"\xe0\xa5")
        self.assertEqual(int.from_bytes(data[8:10], "little"), 128)
        self.assertEqual(int.from_bytes(data[10:12], "little"), 128)

    def test_worm_aseprite_exports_browser_ready_layers(self):
        manifest = server.ensure_worm_aseprite_exports()

        self.assertIsNotNone(manifest)
        self.assertLess(manifest["width"], 128)
        self.assertLess(manifest["height"], 128)
        self.assertIn("worm", manifest["layers"])
        self.assertIn("bones", manifest["layers"])
        for name in ("worm", "bones"):
            path = Path("obs_overlay") / manifest["layers"][name].lstrip("/")
            self.assertIn("assets/generated/sprites", path.as_posix())
            self.assertTrue(path.is_file(), name)
            image = Image.open(path)
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.size, (manifest["width"], manifest["height"]))


if __name__ == "__main__":
    unittest.main()
