import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from clicker_bot.voice_events import VoiceEventEmitter


class VoiceEventEmitterTests(unittest.TestCase):
    def test_send_message_posts_to_voice_server(self):
        response = MagicMock()
        response.status = 204
        response.__enter__.return_value = response

        with patch("clicker_bot.voice_events.request.urlopen", return_value=response) as urlopen:
            emitter = VoiceEventEmitter(history_fallback_path=None)
            sent = emitter.send_message(" Hello voice ", submitted_at=123.456, event_id="hud:test")

        self.assertTrue(sent)
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:8765/speak")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["type"], "speak")
        self.assertEqual(payload["source"], "qt_hud")
        self.assertEqual(payload["text"], "Hello voice")
        self.assertEqual(payload["submitted_at_ms"], 123456)
        self.assertEqual(payload["event_id"], "hud:test")

    def test_send_message_does_not_clip_long_text(self):
        response = MagicMock()
        response.status = 202
        response.__enter__.return_value = response
        long_text = "x" * 1200

        with patch("clicker_bot.voice_events.request.urlopen", return_value=response) as urlopen:
            emitter = VoiceEventEmitter(history_fallback_path=None)
            sent = emitter.send_message(long_text, submitted_at=1.0)

        self.assertTrue(sent)
        payload = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["text"], long_text)

    def test_send_message_falls_back_to_history_jsonl(self):
        temp_dir = Path(".test_tmp") / "voice_events"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        try:
            history_path = temp_dir / "history.jsonl"
            with patch("clicker_bot.voice_events.request.urlopen", side_effect=OSError("down")):
                emitter = VoiceEventEmitter(history_fallback_path=history_path)
                sent = emitter.send_message("Fallback voice", submitted_at=1.25, event_id="hud:fallback")

            self.assertTrue(sent)
            payload = json.loads(history_path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["text"], "Fallback voice")
            self.assertEqual(payload["source"], "qt_hud")
            self.assertEqual(payload["event_id"], "hud:fallback")
            self.assertEqual(payload["timestamp"], 1.25)
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def test_send_message_skips_empty(self):
        with patch("clicker_bot.voice_events.request.urlopen") as urlopen:
            emitter = VoiceEventEmitter(history_fallback_path=None)
            sent = emitter.send_message("   ")

        self.assertFalse(sent)
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
