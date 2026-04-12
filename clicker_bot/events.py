import time


class BotEventRecorder:
    """Owns feed/recent-event recording against the runtime store."""

    def __init__(self, *, runtime_store, infer_feed_category):
        self.runtime_store = runtime_store
        self.infer_feed_category = infer_feed_category

    def record_feed_event(self, message, category=None):
        entry = {
            "timestamp": time.strftime("%H:%M:%S", time.localtime()),
            "message": str(message),
            "category": str(category or self.infer_feed_category(message)),
        }
        self.runtime_store.append_feed_event(entry)
        return entry

    def record_event(self, message):
        self.record_feed_event(message)
        self.runtime_store.append_recent_event(message)
        return message
