#!/usr/bin/env python3
"""Serve a transparent OBS Browser Source overlay and bridge bot UDP events."""

from __future__ import annotations

import argparse
import json
import mimetypes
import queue
import random
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47651
CLIENTS: set[queue.Queue[str]] = set()
CLIENTS_LOCK = threading.Lock()


def clamp01(value: Any) -> float:
    return max(0.0, min(1.0, float(value)))


def validate_spawn_event(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or payload.get("type") not in {"spawn_biden", "spawn_fruit", "play_sound"}:
        return None
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
