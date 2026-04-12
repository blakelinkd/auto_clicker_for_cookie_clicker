import threading
from dataclasses import dataclass


@dataclass
class BotLifecycleState:
    active: bool = False
    click_thread: object = None
    dom_thread: object = None


class BotLifecycle:
    """Owns loop-thread startup/shutdown decisions without feature policy."""

    def __init__(self, *, state: BotLifecycleState, click_loop, dom_loop):
        self.state = state
        self.click_loop = click_loop
        self.dom_loop = dom_loop

    def start(self, *, enable_click_loop: bool):
        self.state.active = True
        if enable_click_loop:
            self.state.click_thread = threading.Thread(target=self.click_loop, daemon=True)
            self.state.click_thread.start()
        else:
            self.state.click_thread = None
        self.state.dom_thread = threading.Thread(target=self.dom_loop, daemon=True)
        self.state.dom_thread.start()

    def stop(self):
        self.state.active = False

    def ensure_click_loop(self):
        thread = self.state.click_thread
        if thread is not None and thread.is_alive():
            return False
        self.state.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.state.click_thread.start()
        return True
