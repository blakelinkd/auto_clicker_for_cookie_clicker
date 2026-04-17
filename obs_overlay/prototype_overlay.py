#!/usr/bin/env python3
"""OBS overlay prototype that spawns a pointing Biden sticker from UDP events."""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPixmap
from PySide6.QtNetwork import QHostAddress, QUdpSocket
from PySide6.QtWidgets import QApplication, QWidget


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SPRITE = BASE_DIR / "assets" / "biden_i_did_that.png"
CORNFLOWER_BLUE = QColor(100, 149, 237)
FINGER_ANCHOR_NORM = QPointF(0.0071, 0.1389)


@dataclass
class BidenSpawn:
    target_norm_x: float
    target_norm_y: float
    started_at: float
    duration_ms: int


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def sprite_top_left_for_target(
    *,
    target_x: float,
    target_y: float,
    sprite_width: float,
    sprite_height: float,
    scale: float,
    anchor_norm_x: float = FINGER_ANCHOR_NORM.x(),
    anchor_norm_y: float = FINGER_ANCHOR_NORM.y(),
) -> QPointF:
    return QPointF(
        target_x - (sprite_width * scale * anchor_norm_x),
        target_y - (sprite_height * scale * anchor_norm_y),
    )


class BidenOverlayWindow(QWidget):
    def __init__(
        self,
        *,
        sprite_path: Path,
        size: QSize,
        sprite_height: int,
        listen_port: int,
        frameless: bool,
        demo_clicks: bool,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Cookie Clicker Biden OBS Overlay")
        self.resize(size)
        self.setMinimumSize(320, 180)
        self.setAutoFillBackground(False)

        if frameless:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        source = QPixmap(str(sprite_path))
        if source.isNull():
            raise FileNotFoundError(f"Could not load sprite: {sprite_path}")

        self.sprite = source.scaledToHeight(
            sprite_height,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.spawns: list[BidenSpawn] = []
        self.paused = False

        self.udp = QUdpSocket(self)
        if not self.udp.bind(QHostAddress(socket.gethostbyname("127.0.0.1")), int(listen_port)):
            raise OSError(f"Could not bind UDP listener on 127.0.0.1:{listen_port}")
        self.udp.readyRead.connect(self.read_udp_events)

        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.tick)
        self.frame_timer.start(16)

        self.demo_timer: QTimer | None = None
        if demo_clicks:
            self.demo_timer = QTimer(self)
            self.demo_timer.timeout.connect(self.spawn_demo)
            self.demo_timer.start(900)
            self.spawn_demo()

    def read_udp_events(self) -> None:
        while self.udp.hasPendingDatagrams():
            datagram = self.udp.receiveDatagram()
            try:
                payload = json.loads(bytes(datagram.data()).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            self.handle_event(payload)

    def handle_event(self, payload: dict[str, Any]) -> bool:
        if not isinstance(payload, dict) or payload.get("type") != "spawn_biden":
            return False
        target = payload.get("target")
        if not isinstance(target, dict):
            return False
        try:
            norm_x = clamp01(float(target["norm_x"]))
            norm_y = clamp01(float(target["norm_y"]))
        except (KeyError, TypeError, ValueError):
            return False
        animation = payload.get("animation")
        duration_ms = 10000
        if isinstance(animation, dict):
            try:
                duration_ms = max(100, int(animation.get("duration_ms", duration_ms)))
            except (TypeError, ValueError):
        duration_ms = 10000
        self.spawns.append(
            BidenSpawn(
                target_norm_x=norm_x,
                target_norm_y=norm_y,
                started_at=time.monotonic(),
                duration_ms=duration_ms,
            )
        )
        self.update()
        return True

    def spawn_demo(self) -> None:
        if self.paused:
            return
        phase = (time.monotonic() * 0.37) % 1.0
        self.handle_event(
            {
                "type": "spawn_biden",
                "target": {
                    "norm_x": 0.18 + 0.64 * phase,
                    "norm_y": 0.22 + 0.45 * ((phase * 1.7) % 1.0),
                },
                "animation": {"duration_ms": 10000},
            }
        )

    def tick(self) -> None:
        if self.paused:
            return
        now = time.monotonic()
        self.spawns = [
            spawn
            for spawn in self.spawns
            if ((now - spawn.started_at) * 1000.0) <= spawn.duration_ms
        ]
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API name
        painter = QPainter(self)
        painter.fillRect(self.rect(), CORNFLOWER_BLUE)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        now = time.monotonic()
        for spawn in self.spawns:
            elapsed_ms = (now - spawn.started_at) * 1000.0
            progress = clamp01(elapsed_ms / spawn.duration_ms)
            opacity = 1.0 - progress
            scale = 1.0 - (0.45 * progress)
            target_x = spawn.target_norm_x * self.width()
            target_y = spawn.target_norm_y * self.height()
            top_left = sprite_top_left_for_target(
                target_x=target_x,
                target_y=target_y,
                sprite_width=self.sprite.width(),
                sprite_height=self.sprite.height(),
                scale=scale,
            )

            painter.save()
            painter.setOpacity(opacity)
            painter.translate(top_left)
            painter.scale(scale, scale)
            painter.drawPixmap(QPointF(0.0, 0.0), self.sprite)
            painter.restore()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt API name
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()
            return
        if event.key() == Qt.Key.Key_Space:
            self.paused = not self.paused
            return
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
            return
        super().keyPressEvent(event)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview the OBS Biden overlay.")
    parser.add_argument("--sprite", type=Path, default=DEFAULT_SPRITE)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--sprite-height", type=int, default=320)
    parser.add_argument("--listen-port", type=int, default=47651)
    parser.add_argument("--demo-clicks", action="store_true")
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--framed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    window = BidenOverlayWindow(
        sprite_path=args.sprite,
        size=QSize(args.width, args.height),
        sprite_height=args.sprite_height,
        listen_port=args.listen_port,
        frameless=not args.framed,
        demo_clicks=args.demo_clicks,
    )
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
