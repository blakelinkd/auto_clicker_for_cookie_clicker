import json
import unittest
from unittest.mock import patch

from clicker_bot.overlay_events import OverlayEventEmitter


class FakeSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, data, address):
        self.sent.append((data, address))


class OverlayEventEmitterTests(unittest.TestCase):
    def test_send_shimmer_spawn_emits_udp_payload(self):
        fake_socket = FakeSocket()
        with patch("clicker_bot.overlay_events.socket.socket", return_value=fake_socket):
            emitter = OverlayEventEmitter()
            emitter.send_shimmer_spawn(
                {
                    "id": 7,
                    "type": "golden",
                    "wrath": False,
                    "client_x": 640,
                    "client_y": 180,
                    "target_norm_x": 0.5,
                    "target_norm_y": 0.25,
                    "viewport_width": 1280,
                    "viewport_height": 720,
                    "device_pixel_ratio": 1.0,
                },
                mode="planned",
                clicked_at=12.345,
            )

        self.assertEqual(len(fake_socket.sent), 1)
        data, address = fake_socket.sent[0]
        self.assertEqual(address, ("127.0.0.1", 47651))
        payload = json.loads(data.decode("utf-8"))
        self.assertEqual(payload["type"], "spawn_biden")
        self.assertEqual(payload["source"], "shimmer")
        self.assertEqual(payload["mode"], "planned")
        self.assertEqual(payload["target"]["norm_x"], 0.5)
        self.assertEqual(payload["game"]["viewport_width"], 1280)

    def test_send_shimmer_spawn_skips_without_normalized_target(self):
        fake_socket = FakeSocket()
        with patch("clicker_bot.overlay_events.socket.socket", return_value=fake_socket):
            emitter = OverlayEventEmitter()
            emitter.send_shimmer_spawn({"id": 7}, mode="clicked", clicked_at=1.0)

        self.assertEqual(fake_socket.sent, [])

    def test_send_hud_message_emits_udp_payload(self):
        fake_socket = FakeSocket()
        with patch("clicker_bot.overlay_events.socket.socket", return_value=fake_socket):
            emitter = OverlayEventEmitter()
            emitter.send_hud_message(
                " Hello stream ",
                ttl_minutes=2,
                repeat_interval_minutes=5,
                submitted_at=123.456,
                event_id="hud:test",
            )

        self.assertEqual(len(fake_socket.sent), 1)
        data, address = fake_socket.sent[0]
        self.assertEqual(address, ("127.0.0.1", 47651))
        payload = json.loads(data.decode("utf-8"))
        self.assertEqual(payload["type"], "hud_message")
        self.assertEqual(payload["source"], "qt_hud")
        self.assertEqual(payload["text"], "Hello stream")
        self.assertEqual(payload["event_id"], "hud:test")
        self.assertEqual(payload["submitted_at_ms"], 123456)
        self.assertEqual(payload["ttl_ms"], 120000)
        self.assertEqual(payload["repeat_interval_ms"], 300000)

    def test_send_hud_message_defaults_ttl_and_skips_empty(self):
        fake_socket = FakeSocket()
        with patch("clicker_bot.overlay_events.socket.socket", return_value=fake_socket):
            emitter = OverlayEventEmitter()
            emitter.send_hud_message("   ", submitted_at=1.0)
            emitter.send_hud_message("One shot", submitted_at=1.0)

        self.assertEqual(len(fake_socket.sent), 1)
        payload = json.loads(fake_socket.sent[0][0].decode("utf-8"))
        self.assertEqual(payload["ttl_ms"], 4000)
        self.assertNotIn("repeat_interval_ms", payload)

    def test_delete_hud_message_emits_udp_payload(self):
        fake_socket = FakeSocket()
        with patch("clicker_bot.overlay_events.socket.socket", return_value=fake_socket):
            emitter = OverlayEventEmitter()
            emitter.delete_hud_message("hud:test")

        payload = json.loads(fake_socket.sent[0][0].decode("utf-8"))
        self.assertEqual(payload, {
            "version": 1,
            "type": "hud_message_delete",
            "event_id": "hud:test",
            "source": "qt_hud",
        })

    def test_send_biden_timer_emits_forecast_payload(self):
        fake_socket = FakeSocket()
        with patch("clicker_bot.overlay_events.socket.socket", return_value=fake_socket):
            emitter = OverlayEventEmitter()
            emitter.send_biden_timer({"available": True, "median_remaining_seconds": 12.5, "on_screen": 0})

        payload = json.loads(fake_socket.sent[0][0].decode("utf-8"))
        self.assertEqual(payload["type"], "biden_timer")
        self.assertEqual(payload["source"], "golden_cookie_forecast")
        self.assertTrue(payload["available"])
        self.assertEqual(payload["remaining_seconds"], 12.5)

    def test_send_biden_timer_emits_unavailable_without_diag(self):
        fake_socket = FakeSocket()
        with patch("clicker_bot.overlay_events.socket.socket", return_value=fake_socket):
            emitter = OverlayEventEmitter()
            emitter.send_biden_timer(None)

        payload = json.loads(fake_socket.sent[0][0].decode("utf-8"))
        self.assertEqual(payload["type"], "biden_timer")
        self.assertFalse(payload["available"])


if __name__ == "__main__":
    unittest.main()
