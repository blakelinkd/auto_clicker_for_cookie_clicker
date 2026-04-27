import json
import socket
import time
from typing import Any


DEFAULT_HUD_MESSAGE_TTL_MS = 4000
MAX_HUD_MESSAGE_LENGTH = 500


class OverlayEventEmitter:
    """Best-effort UDP emitter for visual overlay events."""

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 47651,
        enabled: bool = True,
        log: Any = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.enabled = bool(enabled)
        self.log = log
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_shimmer_spawn(self, shimmer: dict[str, Any], *, mode: str, clicked_at: float) -> None:
        if not self.enabled:
            return
        norm_x = shimmer.get("target_norm_x")
        norm_y = shimmer.get("target_norm_y")
        if norm_x is None or norm_y is None:
            return
        viewport_width = shimmer.get("viewport_width")
        viewport_height = shimmer.get("viewport_height")
        payload = {
            "version": 1,
            "type": "spawn_biden",
            "event_id": f"shimmer:{shimmer.get('id')}:{mode}:{clicked_at:.6f}",
            "source": "shimmer",
            "mode": str(mode),
            "target": {
                "client_x": shimmer.get("client_x"),
                "client_y": shimmer.get("client_y"),
                "norm_x": float(norm_x),
                "norm_y": float(norm_y),
            },
            "game": {
                "viewport_width": viewport_width,
                "viewport_height": viewport_height,
                "device_pixel_ratio": shimmer.get("device_pixel_ratio", 1.0),
            },
            "shimmer": {
                "id": shimmer.get("id"),
                "type": shimmer.get("type"),
                "wrath": bool(shimmer.get("wrath")),
            },
            "animation": {"duration_ms": 3000},
        }
        self.send(payload)

    def send_hud_message(
        self,
        text: str,
        *,
        ttl_minutes: float | None = None,
        repeat_interval_minutes: float | None = None,
        submitted_at: float | None = None,
        event_id: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        message = str(text or "").strip()
        if not message:
            return
        message = message[:MAX_HUD_MESSAGE_LENGTH]
        submitted_at = time.time() if submitted_at is None else float(submitted_at)
        submitted_at_ms = int(round(submitted_at * 1000))
        payload: dict[str, Any] = {
            "version": 1,
            "type": "hud_message",
            "event_id": event_id or f"hud:{submitted_at_ms}",
            "source": "qt_hud",
            "text": message,
            "submitted_at_ms": submitted_at_ms,
            "ttl_ms": self._minutes_to_ms(ttl_minutes, default_ms=DEFAULT_HUD_MESSAGE_TTL_MS),
        }
        repeat_ms = self._minutes_to_ms(repeat_interval_minutes, default_ms=None)
        if repeat_ms is not None:
            payload["repeat_interval_ms"] = repeat_ms
        self.send(payload)

    def delete_hud_message(self, event_id: str) -> None:
        if not self.enabled:
            return
        event_id = str(event_id or "").strip()
        if not event_id:
            return
        self.send({
            "version": 1,
            "type": "hud_message_delete",
            "event_id": event_id,
            "source": "qt_hud",
        })

    def send_biden_timer(self, golden_diag: dict[str, Any] | None) -> None:
        if not self.enabled:
            return
        if not isinstance(golden_diag, dict) or not golden_diag.get("available"):
            self.send({
                "version": 1,
                "type": "biden_timer",
                "source": "golden_cookie_forecast",
                "available": False,
            })
            return
        remaining_seconds = golden_diag.get("median_remaining_seconds")
        if remaining_seconds is None:
            remaining_seconds = golden_diag.get("expected_remaining_seconds")
        try:
            remaining = max(0.0, float(remaining_seconds))
        except (TypeError, ValueError):
            remaining = None
        self.send({
            "version": 1,
            "type": "biden_timer",
            "source": "golden_cookie_forecast",
            "available": remaining is not None,
            "remaining_seconds": remaining,
            "on_screen": int(golden_diag.get("on_screen") or 0),
            "updated_at_ms": int(round(time.time() * 1000)),
        })

    def send_combat_log(self, text: str, *, channel: str = "say") -> None:
        if not self.enabled:
            return
        text = str(text or "").strip()
        if not text:
            return
        self.send({
            "version": 1,
            "type": "combat_log",
            "speaker": "gm",
            "text": text[:200],
            "channel": channel,
        })

    @staticmethod
    def _minutes_to_ms(value: float | None, *, default_ms: int | None) -> int | None:
        if value is None:
            return default_ms
        try:
            minutes = float(value)
        except (TypeError, ValueError):
            return default_ms
        if minutes <= 0:
            return default_ms
        return int(round(minutes * 60_000))

    def send(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self._socket.sendto(data, (self.host, self.port))
        except Exception as exc:
            if self.log is not None:
                try:
                    self.log.debug(f"Overlay UDP send failed: {exc}")
                except Exception:
                    pass
