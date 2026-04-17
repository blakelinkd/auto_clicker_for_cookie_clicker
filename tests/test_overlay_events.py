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


if __name__ == "__main__":
    unittest.main()
