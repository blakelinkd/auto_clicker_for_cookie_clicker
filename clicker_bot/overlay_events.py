import json
import socket
from typing import Any


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
