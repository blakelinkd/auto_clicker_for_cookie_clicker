#!/usr/bin/env python3
"""Serve a transparent OBS Browser Source overlay and bridge bot UDP events."""

from __future__ import annotations

import argparse
import json
import mimetypes
import queue
import random
import socket
import struct
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47651
CLIENTS: set[queue.Queue[str]] = set()
CLIENTS_LOCK = threading.Lock()
DEFAULT_HUD_MESSAGE_TTL_MS = 4000
MAX_HUD_MESSAGE_LENGTH = 500
MIN_HUD_MESSAGE_MS = 4000
MAX_HUD_MESSAGE_MS = 86_400_000


def ensure_worm_aseprite_exports() -> dict[str, Any] | None:
    """Export the worm/bones Aseprite layers into browser-ready PNG assets."""
    source = SPRITES_DIR / "worm_with_bones.ase"
    if not source.is_file():
        return None
    return export_aseprite_layers(
        source,
        {
            "worm": SPRITES_DIR / "worm_with_bones_worm.png",
            "bones": SPRITES_DIR / "worm_with_bones_bones.png",
        },
        SPRITES_DIR / "worm_with_bones.layers.json",
    )


def export_aseprite_layers(
    source: Path,
    layer_outputs: dict[str, Path],
    manifest_path: Path,
) -> dict[str, Any]:
    from PIL import Image

    data = source.read_bytes()
    if len(data) < 128 or data[4:6] != b"\xe0\xa5":
        raise ValueError(f"Unsupported Aseprite file: {source}")
    width = struct.unpack_from("<H", data, 8)[0]
    height = struct.unpack_from("<H", data, 10)[0]
    frames = struct.unpack_from("<H", data, 6)[0]
    color_depth = struct.unpack_from("<H", data, 12)[0]
    if color_depth != 32:
        raise ValueError(f"Only RGBA Aseprite files are supported: {source}")

    layers: list[dict[str, Any]] = []
    images: dict[str, Any] = {}
    offset = 128
    for _frame_index in range(frames):
        frame_bytes = struct.unpack_from("<I", data, offset)[0]
        old_chunk_count = struct.unpack_from("<H", data, offset + 6)[0]
        new_chunk_count = struct.unpack_from("<I", data, offset + 12)[0]
        chunk_count = new_chunk_count or old_chunk_count
        chunk_offset = offset + 16
        for _chunk_index in range(chunk_count):
            chunk_size, chunk_type = struct.unpack_from("<IH", data, chunk_offset)
            payload = chunk_offset + 6
            if chunk_type == 0x2004:
                name_length = struct.unpack_from("<H", data, payload + 16)[0]
                name = data[payload + 18:payload + 18 + name_length].decode("utf-8")
                layers.append({"name": name, "opacity": data[payload + 12]})
            elif chunk_type == 0x2005:
                _extract_aseprite_cel(data, payload, chunk_offset, chunk_size, layers, layer_outputs, images, width, height)
            chunk_offset += chunk_size
        offset += frame_bytes

    exported_layers: dict[str, str] = {}
    for layer_name, image in images.items():
        output_path = layer_outputs[layer_name]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        exported_layers[layer_name] = "/" + output_path.relative_to(BASE_DIR).as_posix()

    manifest = {
        "version": 1,
        "source": "/" + source.relative_to(BASE_DIR).as_posix(),
        "width": width,
        "height": height,
        "layers": exported_layers,
    }
    manifest_path.write_text(json.dumps(manifest, separators=(",", ":")) + "\n", encoding="utf-8")
    return manifest


def _extract_aseprite_cel(
    data: bytes,
    payload: int,
    chunk_offset: int,
    chunk_size: int,
    layers: list[dict[str, Any]],
    layer_outputs: dict[str, Path],
    images: dict[str, Any],
    width: int,
    height: int,
) -> None:
    from PIL import Image

    layer_index, x, y, cel_opacity, cel_type = struct.unpack_from("<HhhBH", data, payload)
    if layer_index >= len(layers):
        return
    layer_name = str(layers[layer_index]["name"])
    if layer_name not in layer_outputs or cel_type not in {0, 2}:
        return
    cel_width, cel_height = struct.unpack_from("<HH", data, payload + 16)
    pixel_offset = payload + 20
    pixel_length = cel_width * cel_height * 4
    if cel_type == 2:
        pixels = zlib.decompress(data[pixel_offset:chunk_offset + chunk_size])
    else:
        pixels = data[pixel_offset:pixel_offset + pixel_length]
    if len(pixels) < pixel_length:
        return
    layer_image = images.get(layer_name)
    if layer_image is None:
        layer_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        images[layer_name] = layer_image
    cel_image = Image.frombytes("RGBA", (cel_width, cel_height), pixels[:pixel_length])
    if cel_opacity < 255:
        alpha = cel_image.getchannel("A").point(lambda value: int(value * (cel_opacity / 255)))
        cel_image.putalpha(alpha)
    layer_image.alpha_composite(cel_image, (x, y))


def clamp01(value: Any) -> float:
    return max(0.0, min(1.0, float(value)))


def _coerce_duration_ms(value: Any, *, default_ms: int, minimum_ms: int, maximum_ms: int) -> int:
    try:
        duration_ms = int(float(value))
    except (TypeError, ValueError):
        duration_ms = default_ms
    return max(minimum_ms, min(maximum_ms, duration_ms))


def _validate_hud_message_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    text = str(payload.get("text") or "").strip()
    if not text:
        return None
    text = text[:MAX_HUD_MESSAGE_LENGTH]
    event = dict(payload)
    event["version"] = 1
    event["type"] = "hud_message"
    event["source"] = str(payload.get("source") or "qt_hud")
    event["text"] = text
    event["ttl_ms"] = _coerce_duration_ms(
        payload.get("ttl_ms"),
        default_ms=DEFAULT_HUD_MESSAGE_TTL_MS,
        minimum_ms=MIN_HUD_MESSAGE_MS,
        maximum_ms=MAX_HUD_MESSAGE_MS,
    )
    repeat_ms = payload.get("repeat_interval_ms")
    if repeat_ms is not None:
        event["repeat_interval_ms"] = _coerce_duration_ms(
            repeat_ms,
            default_ms=MIN_HUD_MESSAGE_MS,
            minimum_ms=MIN_HUD_MESSAGE_MS,
            maximum_ms=MAX_HUD_MESSAGE_MS,
        )
    if "submitted_at_ms" in payload:
        try:
            event["submitted_at_ms"] = int(float(payload["submitted_at_ms"]))
        except (TypeError, ValueError):
            event.pop("submitted_at_ms", None)
    return event


def validate_spawn_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or payload.get("type") not in {"spawn_biden", "spawn_fruit", "play_sound", "hud_message", "hud_message_delete", "biden_timer"}:
        return None
    if payload.get("type") == "biden_timer":
        event = {
            "version": 1,
            "type": "biden_timer",
            "source": str(payload.get("source") or "golden_cookie_forecast"),
            "available": bool(payload.get("available")),
        }
        if event["available"]:
            try:
                event["remaining_seconds"] = max(0.0, float(payload["remaining_seconds"]))
            except (KeyError, TypeError, ValueError):
                event["available"] = False
        event["on_screen"] = int(payload.get("on_screen") or 0)
        return event
    if payload.get("type") == "hud_message_delete":
        event_id = str(payload.get("event_id") or "").strip()
        if not event_id:
            return None
        return {"version": 1, "type": "hud_message_delete", "event_id": event_id, "source": str(payload.get("source") or "qt_hud")}
    if payload.get("type") == "hud_message":
        return _validate_hud_message_event(payload)
    if payload.get("type") == "play_sound":
        sound = payload.get("sound")
        if sound not in {"dean", "grandma"}:
            return None
        return {"version": 1, "type": "play_sound", "sound": sound}
    if not isinstance(payload, dict):
        return None
    target = payload.get("target")
    if not isinstance(target, dict):
        return None
    try:
        norm_x = clamp01(target["norm_x"])
        norm_y = clamp01(target["norm_y"])
    except (KeyError, TypeError, ValueError):
        return None
    animation = payload.get("animation")
    duration_ms = 10000
    if isinstance(animation, dict):
        try:
            duration_ms = max(100, int(animation.get("duration_ms", duration_ms)))
        except (TypeError, ValueError):
            duration_ms = 10000
    event = dict(payload)
    event["target"] = dict(target)
    event["target"]["norm_x"] = norm_x
    event["target"]["norm_y"] = norm_y
    event["animation"] = {"duration_ms": duration_ms}
    return event


def broadcast_event(payload: dict[str, Any]) -> None:
    data = json.dumps(payload, separators=(",", ":"))
    with CLIENTS_LOCK:
        clients = list(CLIENTS)
    for client in clients:
        try:
            client.put_nowait(data)
        except queue.Full:
            pass


def demo_event() -> dict[str, Any]:
    phase = (time.monotonic() * 0.37) % 1.0
    return {
        "version": 1,
        "type": "spawn_biden",
        "source": "demo",
        "mode": "demo",
        "target": {
            "norm_x": 0.18 + 0.64 * phase,
            "norm_y": 0.22 + 0.45 * ((phase * 1.7) % 1.0),
        },
        "animation": {"duration_ms": 10000},
    }


def random_biden_event() -> dict[str, Any]:
    return {
        "version": 1,
        "type": "spawn_biden",
        "source": "timer",
        "mode": "periodic",
        "target": {
            "norm_x": random.uniform(0.12, 0.88),
            "norm_y": random.uniform(0.12, 0.88),
        },
        "animation": {"duration_ms": 10000},
    }


def random_fruit_event() -> dict[str, Any]:
    return {
        "version": 1,
        "type": "spawn_fruit",
        "source": "timer",
        "mode": "periodic",
        "target": {
            "norm_x": random.uniform(0.12, 0.88),
            "norm_y": random.uniform(0.12, 0.88),
        },
        "fruit": {
            "kind": "frenzy_cookie",
        },
    }


def udp_listener(host: str, port: int, stop_event: threading.Event) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(0.2)
    while not stop_event.is_set():
        try:
            data, _addr = sock.recvfrom(65535)
        except TimeoutError:
            continue
        except OSError:
            break
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        event = validate_spawn_event(payload)
        if event is not None:
            broadcast_event(event)
    sock.close()


class OverlayRequestHandler(BaseHTTPRequestHandler):
    server_version = "CookieBidenOverlay/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        if getattr(self.server, "quiet", False):
            return
        super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        path = urlparse(self.path).path.split("?")[0]
        if path in {"", "/"}:
            self._send_file(BASE_DIR / "web" / "index.html", "text/html; charset=utf-8")
            return
        if path == "/config.js":
            self._send_config()
            return
        if path == "/events":
            self._serve_events()
            return
        if path.startswith("/test-sound/"):
            self._serve_test_sound(path.rsplit("/", 1)[-1])
            return
        if path.startswith("/assets/"):
            asset_path = (BASE_DIR / path.lstrip("/")).resolve()
            if not str(asset_path).startswith(str(ASSETS_DIR.resolve())):
                self.send_error(403)
                return
            self._send_file(asset_path)
            return
        if path.startswith("/web/"):
            web_path = (BASE_DIR / path.lstrip("/")).resolve()
            web_dir = (BASE_DIR / "web").resolve()
            if not str(web_path).startswith(str(web_dir)):
                self.send_error(403)
                return
            self._send_file(web_path)
            return
        self.send_error(404)

    def _serve_test_sound(self, sound: str) -> None:
        event = validate_spawn_event({"type": "play_sound", "sound": sound})
        if event is None:
            self.send_error(404)
            return
        broadcast_event(event)
        data = f"queued {sound}\n".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        if urlparse(self.path).path != "/event":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400)
            return
        event = validate_spawn_event(payload)
        if event is None:
            self.send_error(400)
            return
        broadcast_event(event)
        self.send_response(204)
        self.end_headers()

    def _send_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        if content_type is None:
            content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _send_config(self) -> None:
        payload = {
            "snakeEnabled": bool(getattr(self.server, "snake_enabled", True)),
        }
        data = ("window.OVERLAY_CONFIG = " + json.dumps(payload, separators=(",", ":")) + ";\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _serve_events(self) -> None:
        client_queue: queue.Queue[str] = queue.Queue(maxsize=100)
        with CLIENTS_LOCK:
            CLIENTS.add(client_queue)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    data = client_queue.get(timeout=15.0)
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with CLIENTS_LOCK:
                CLIENTS.discard(client_queue)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_demo_loop(stop_event: threading.Event, interval_seconds: float) -> None:
    while not stop_event.is_set():
        broadcast_event(demo_event())
        stop_event.wait(interval_seconds)


def run_periodic_fruit_loop(stop_event: threading.Event, interval_seconds: float) -> None:
    while not stop_event.wait(interval_seconds):
        event = validate_spawn_event(random_fruit_event())
        if event is not None:
            broadcast_event(event)


def run_periodic_biden_loop(stop_event: threading.Event, interval_seconds: float) -> None:
    while not stop_event.wait(interval_seconds):
        event = validate_spawn_event(random_biden_event())
        if event is not None:
            broadcast_event(event)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the OBS Browser Source overlay.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--udp-host", default=DEFAULT_HOST)
    parser.add_argument("--udp-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--demo-clicks", action="store_true")
    parser.add_argument("--no-snake", action="store_true")
    parser.add_argument("--bidens", type=float, default=0.0, metavar="SECONDS")
    parser.add_argument("--fruit-interval-seconds", type=float, default=20.0)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_worm_aseprite_exports()
    stop_event = threading.Event()
    udp_thread = threading.Thread(
        target=udp_listener,
        args=(args.udp_host, args.udp_port, stop_event),
        daemon=True,
    )
    udp_thread.start()
    if args.demo_clicks:
        threading.Thread(target=run_demo_loop, args=(stop_event, 0.9), daemon=True).start()

    server = ReusableThreadingHTTPServer((args.host, args.port), OverlayRequestHandler)
    server.quiet = args.quiet
    server.snake_enabled = not args.no_snake
    if args.bidens > 0:
        threading.Thread(
            target=run_periodic_biden_loop,
            args=(stop_event, float(args.bidens)),
            daemon=True,
        ).start()
    if server.snake_enabled and args.fruit_interval_seconds > 0:
        threading.Thread(
            target=run_periodic_fruit_loop,
            args=(stop_event, float(args.fruit_interval_seconds)),
            daemon=True,
        ).start()
    print(f"OBS Browser Source URL: http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
