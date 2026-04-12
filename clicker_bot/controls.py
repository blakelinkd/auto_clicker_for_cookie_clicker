from dataclasses import dataclass


@dataclass(frozen=True)
class ToggleBinding:
    feature_name: str
    runtime_key: str
    event_label: str
    on_label: str = "ON"
    off_label: str = "OFF"


class BotControls:
    """Control-surface helpers for mode toggles and config updates."""

    def __init__(
        self,
        *,
        log,
        set_runtime,
        record_event,
        log_mode_change,
        get_active,
        get_main_cookie_clicking_enabled,
        set_main_cookie_clicking_enabled,
        get_shimmer_autoclick_enabled,
        set_shimmer_autoclick_enabled,
        get_building_autobuy_enabled,
        set_building_autobuy_enabled,
        get_lucky_reserve_enabled,
        set_lucky_reserve_enabled,
        get_upgrade_autobuy_enabled,
        set_upgrade_autobuy_enabled,
        get_ascension_prep_enabled,
        set_ascension_prep_enabled,
        get_stock_trading_enabled,
        set_stock_trading_enabled,
        get_lifecycle,
        set_click_thread,
        building_autobuyer,
        set_upgrade_horizon_value,
        wrinkler_controller,
        wrinkler_modes,
    ):
        self.log = log
        self.set_runtime = set_runtime
        self.record_event = record_event
        self.log_mode_change = log_mode_change
        self.get_active = get_active
        self.get_main_cookie_clicking_enabled = get_main_cookie_clicking_enabled
        self.set_main_cookie_clicking_enabled = set_main_cookie_clicking_enabled
        self.get_shimmer_autoclick_enabled = get_shimmer_autoclick_enabled
        self.set_shimmer_autoclick_enabled = set_shimmer_autoclick_enabled
        self.get_building_autobuy_enabled = get_building_autobuy_enabled
        self.set_building_autobuy_enabled = set_building_autobuy_enabled
        self.get_lucky_reserve_enabled = get_lucky_reserve_enabled
        self.set_lucky_reserve_enabled = set_lucky_reserve_enabled
        self.get_upgrade_autobuy_enabled = get_upgrade_autobuy_enabled
        self.set_upgrade_autobuy_enabled = set_upgrade_autobuy_enabled
        self.get_ascension_prep_enabled = get_ascension_prep_enabled
        self.set_ascension_prep_enabled = set_ascension_prep_enabled
        self.get_stock_trading_enabled = get_stock_trading_enabled
        self.set_stock_trading_enabled = set_stock_trading_enabled
        self.get_lifecycle = get_lifecycle
        self.set_click_thread = set_click_thread
        self.building_autobuyer = building_autobuyer
        self.set_upgrade_horizon_value = set_upgrade_horizon_value
        self.wrinkler_controller = wrinkler_controller
        self.wrinkler_modes = tuple(wrinkler_modes)

    def _toggle_flag(self, current_value, set_value, binding: ToggleBinding, *, source: str):
        next_value = not bool(current_value)
        set_value(next_value)
        self.set_runtime(**{binding.runtime_key: next_value})
        self.record_event(f"{binding.event_label} {binding.on_label if next_value else binding.off_label}")
        self.log_mode_change(binding.feature_name, next_value, source=source)
        return next_value

    def toggle_main_autoclick(self, *, source="hud_button"):
        enabled = self._toggle_flag(
            self.get_main_cookie_clicking_enabled(),
            self.set_main_cookie_clicking_enabled,
            ToggleBinding(
                feature_name="Main autoclick",
                runtime_key="main_cookie_clicking_enabled",
                event_label="Main autoclick",
            ),
            source=source,
        )
        if self.get_active() and enabled:
            lifecycle = self.get_lifecycle()
            if lifecycle.ensure_click_loop():
                self.set_click_thread(lifecycle.state.click_thread)
            self.log.info("Main cookie click loop enabled; using DOM feed for target coordinates.")
        return enabled

    def toggle_shimmer_autoclick(self, *, source="hud_button"):
        return self._toggle_flag(
            self.get_shimmer_autoclick_enabled(),
            self.set_shimmer_autoclick_enabled,
            ToggleBinding(
                feature_name="Golden/wrath autoclick",
                runtime_key="shimmer_autoclick_enabled",
                event_label="Golden/wrath autoclick",
            ),
            source=source,
        )

    def toggle_building_autobuy(self, *, source="hotkey"):
        return self._toggle_flag(
            self.get_building_autobuy_enabled(),
            self.set_building_autobuy_enabled,
            ToggleBinding(
                feature_name="Building autobuy",
                runtime_key="building_autobuy_enabled",
                event_label="Building autobuy",
            ),
            source=source,
        )

    def toggle_lucky_reserve(self, *, source="hotkey"):
        return self._toggle_flag(
            self.get_lucky_reserve_enabled(),
            self.set_lucky_reserve_enabled,
            ToggleBinding(
                feature_name="Lucky reserve",
                runtime_key="lucky_reserve_enabled",
                event_label="Lucky reserve",
            ),
            source=source,
        )

    def toggle_upgrade_autobuy(self, *, source="hotkey"):
        return self._toggle_flag(
            self.get_upgrade_autobuy_enabled(),
            self.set_upgrade_autobuy_enabled,
            ToggleBinding(
                feature_name="Upgrade autobuy",
                runtime_key="upgrade_autobuy_enabled",
                event_label="Upgrade autobuy",
            ),
            source=source,
        )

    def toggle_ascension_prep(self, *, source="hotkey"):
        return self._toggle_flag(
            self.get_ascension_prep_enabled(),
            self.set_ascension_prep_enabled,
            ToggleBinding(
                feature_name="Ascension prep",
                runtime_key="ascension_prep_enabled",
                event_label="Ascension prep",
            ),
            source=source,
        )

    def toggle_stock_trading(self, *, source="hotkey"):
        next_value = self._toggle_flag(
            self.get_stock_trading_enabled(),
            self.set_stock_trading_enabled,
            ToggleBinding(
                feature_name="Stock buying",
                runtime_key="stock_trading_enabled",
                event_label="Stock buying",
                on_label="ON",
                off_label="OFF (sell exits stay active)",
            ),
            source=source,
        )
        return next_value

    def set_building_cap(self, building_name, cap):
        try:
            applied_cap = self.building_autobuyer.set_building_cap(building_name, cap)
        except Exception as exc:
            message = f"Building cap update failed for {building_name}: {exc}"
            self.record_event(message)
            self.log.warning(message)
            return False, str(exc)

        if cap is None:
            message = f"Building cap reset to default for {building_name} ({applied_cap})"
        else:
            message = f"Building cap set for {building_name}: {applied_cap}"
        self.record_event(message)
        self.log.info(message)
        return True, applied_cap

    def set_upgrade_horizon_seconds(self, horizon_seconds):
        try:
            horizon_seconds = float(horizon_seconds)
            if horizon_seconds <= 0:
                raise ValueError("horizon must be positive")
        except Exception as exc:
            message = f"Upgrade horizon update failed: {exc}"
            self.record_event(message)
            self.log.warning(message)
            return False, str(exc)

        self.set_upgrade_horizon_value(horizon_seconds)
        self.set_runtime(upgrade_horizon_seconds=horizon_seconds)
        message = f"Upgrade horizon set to {int(round(horizon_seconds / 60.0))}m"
        self.record_event(message)
        self.log.info(message)
        return True, horizon_seconds

    def set_building_horizon_seconds(self, horizon_seconds):
        try:
            applied = self.building_autobuyer.set_payback_horizon_seconds(horizon_seconds)
        except Exception as exc:
            message = f"Building horizon update failed: {exc}"
            self.record_event(message)
            self.log.warning(message)
            return False, str(exc)

        self.set_runtime(building_horizon_seconds=applied)
        message = f"Building horizon set to {int(round(applied / 60.0))}m"
        self.record_event(message)
        self.log.info(message)
        return True, applied

    def set_building_cap_ignored(self, building_name, ignored):
        try:
            active = self.building_autobuyer.set_building_cap_ignored(building_name, ignored)
        except Exception as exc:
            message = f"Building cap ignore update failed for {building_name}: {exc}"
            self.record_event(message)
            self.log.warning(message)
            return False, str(exc)

        message = f"Building cap {'ignored' if active else 'enforced'} for {building_name}"
        self.record_event(message)
        self.log.info(message)
        return True, active

    def cycle_wrinkler_mode(self):
        current = self.wrinkler_controller.mode
        try:
            index = self.wrinkler_modes.index(current)
        except ValueError:
            index = 0
        next_mode = self.wrinkler_modes[(index + 1) % len(self.wrinkler_modes)]
        self.wrinkler_controller.mode = next_mode
        self.set_runtime(wrinkler_mode=next_mode)
        self.record_event(f"Wrinkler mode {next_mode}")
        self.log.info(f"Wrinkler mode {next_mode}")
        return next_mode
