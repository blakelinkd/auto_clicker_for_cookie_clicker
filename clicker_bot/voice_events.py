import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_VOICE_SERVER_URL = "http://127.0.0.1:8765"
DEFAULT_HISTORY_PATH = Path.home() / ".codex" / "history.jsonl"


class VoiceEventEmitter:
    """Best-effort sender for manual HUD messages to the local TTS server."""

    def __init__(
        self,
        *,
        server_url: str | None = None,
        enabled: bool = True,
        timeout_seconds: float = 0.75,
        history_fallback_path: Path | None = DEFAULT_HISTORY_PATH,
        log: Any = None,
    ) -> None:
        self.server_url = (server_url or os.environ.get("COOKIE_TTS_SERVER_URL") or DEFAULT_VOICE_SERVER_URL).rstrip("/")
        self.enabled = bool(enabled)
        self.timeout_seconds = float(timeout_seconds)
        self.history_fallback_path = history_fallback_path
        self.log = log

    def send_message(self, text: str, *, submitted_at: float | None = None, event_id: str | None = None) -> bool:
        if not self.enabled:
            return False
        message = str(text or "").strip()
        if not message:
            return False
        submitted_at = time.time() if submitted_at is None else float(submitted_at)
        payload = {
            "version": 1,
            "type": "speak",
            "source": "qt_hud",
            "text": message,
            "submitted_at_ms": int(round(submitted_at * 1000)),
            "event_id": event_id,
        }
        if self._post_to_server(payload):
            return True
        return self._append_history_fallback(message, submitted_at=submitted_at, event_id=event_id)

    def _post_to_server(self, payload: dict[str, Any]) -> bool:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = request.Request(
            f"{self.server_url}/speak",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return 200 <= int(response.status) < 300
        except error.HTTPError as exc:
            self._debug(f"Voice server rejected message: HTTP {exc.code}")
            return False
        except Exception as exc:
            self._debug(f"Voice server send failed: {exc}")
            return False

    def _append_history_fallback(self, text: str, *, submitted_at: float, event_id: str | None) -> bool:
        if self.history_fallback_path is None:
            return False
        try:
            self.history_fallback_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "text": text,
                "source": "qt_hud",
                "event_id": event_id,
                "timestamp": submitted_at,
            }
            with self.history_fallback_path.open("a", encoding="utf-8") as history:
                history.write(json.dumps(payload, separators=(",", ":")) + "\n")
            return True
        except Exception as exc:
            self._debug(f"Voice history fallback failed: {exc}")
            return False

    def _debug(self, message: str) -> None:
        if self.log is None:
            return
        try:
            self.log.debug(message)
        except Exception:
            pass
