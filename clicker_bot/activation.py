class BotActivationController:
    """Coordinates bot on/off transitions without owning loop internals."""

    def __init__(
        self,
        *,
        log,
        flip_active,
        set_runtime,
        log_mode_change,
        reset_shimmer_tracking,
        record_event,
        get_game_window,
        launch_game_if_needed,
        focus_game_window,
        get_main_cookie_clicking_enabled,
        get_lifecycle,
        set_click_thread,
        set_dom_thread,
        set_game_rect,
    ):
        self.log = log
        self.flip_active = flip_active
        self.set_runtime = set_runtime
        self.log_mode_change = log_mode_change
        self.reset_shimmer_tracking = reset_shimmer_tracking
        self.record_event = record_event
        self.get_game_window = get_game_window
        self.launch_game_if_needed = launch_game_if_needed
        self.focus_game_window = focus_game_window
        self.get_main_cookie_clicking_enabled = get_main_cookie_clicking_enabled
        self.get_lifecycle = get_lifecycle
        self.set_click_thread = set_click_thread
        self.set_dom_thread = set_dom_thread
        self.set_game_rect = set_game_rect

    def toggle(self, *, source="hotkey"):
        state = bool(self.flip_active())
        self.set_runtime(active=state)
        self.log_mode_change("Clicker", state, source=source)
        lifecycle = self.get_lifecycle()

        if state:
            self.reset_shimmer_tracking("bot_started", clear_click_state=True)
            self.log.info("Clicker ON")
            self.record_event("Clicker ON")
            game_rect = self.get_game_window()
            if game_rect is None:
                self.log.warning("Game window not found on toggle; attempting launch.")
                self.launch_game_if_needed()
                game_rect = self.get_game_window(log_missing=False)
                if game_rect is None:
                    self.log.warning("Game window still not found after launch attempt")
            else:
                self.focus_game_window()
            self.set_game_rect(game_rect)
            lifecycle.start(enable_click_loop=self.get_main_cookie_clicking_enabled())
            self.set_click_thread(lifecycle.state.click_thread)
            self.set_dom_thread(lifecycle.state.dom_thread)
            if self.get_main_cookie_clicking_enabled():
                self.log.info("Main cookie click loop enabled; using DOM feed for target coordinates.")
            else:
                self.log.info("Main cookie click loop disabled.")
            return state

        lifecycle.stop()
        self.reset_shimmer_tracking("bot_paused", clear_click_state=True)
        self.log.info("Clicker OFF")
        self.record_event("Clicker OFF")
        return state
