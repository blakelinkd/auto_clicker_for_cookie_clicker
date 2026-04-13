#!/usr/bin/env python3
"""
Standalone script to launch the PySide6 HUD for testing.
This does NOT start the bot; it uses mock data from JSON.
"""
import sys
import json
import time
import logging
from typing import Any
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .hud_qt import QtDashboard

logging.basicConfig(level=logging.INFO)


class JsonMockCallbacks:
    def __init__(self):
        # Load mock data from JSON file
        json_path = Path(__file__).parent / "mock_dashboard_data.json"
        with open(json_path, 'r', encoding='utf-8') as f:
            self.mock_data = json.load(f)
        
        # Ensure state dict exists and update with current time
        self.state = self.mock_data.get("state", {})
        self.state["started_at"] = time.monotonic()
        
        # Initialize other required fields if missing
        self.state.setdefault("active", True)
        self.state.setdefault("stock_trading_enabled", True)
        self.state.setdefault("lucky_reserve_enabled", True)
        self.state.setdefault("building_autobuy_enabled", True)
        self.state.setdefault("upgrade_autobuy_enabled", True)
        self.state.setdefault("ascension_prep_enabled", False)
        self.state.setdefault("garden_automation_enabled", True)
        self.state.setdefault("main_cookie_clicking_enabled", True)
        self.state.setdefault("shimmer_autoclick_enabled", True)
        self.state.setdefault("wrinkler_mode", "auto")

    def get_dashboard_state(self):
        """Return complete dashboard state with updated state dict."""
        # Create a deep copy of mock data to avoid mutation of original
        import copy
        payload = copy.deepcopy(self.mock_data)
        # Update the state in payload with current state (which may have been toggled)
        payload["state"] = copy.deepcopy(self.state)
        # Update uptime
        payload["state"]["started_at"] = self.state["started_at"]
        return payload

    def toggle_active(self):
        self.state["active"] = not self.state["active"]
        print(f"Toggle active -> {self.state['active']}")

    def toggle_main_autoclick(self):
        self.state["main_cookie_clicking_enabled"] = not self.state["main_cookie_clicking_enabled"]
        print(f"Toggle main autoclick -> {self.state['main_cookie_clicking_enabled']}")

    def toggle_shimmer_autoclick(self):
        self.state["shimmer_autoclick_enabled"] = not self.state["shimmer_autoclick_enabled"]
        print(f"Toggle shimmer autoclick -> {self.state['shimmer_autoclick_enabled']}")

    def toggle_stock_buying(self):
        self.state["stock_trading_enabled"] = not self.state["stock_trading_enabled"]
        print(f"Toggle stock buying -> {self.state['stock_trading_enabled']}")

    def toggle_lucky_reserve(self):
        self.state["lucky_reserve_enabled"] = not self.state["lucky_reserve_enabled"]
        print(f"Toggle lucky reserve -> {self.state['lucky_reserve_enabled']}")

    def toggle_building_buying(self):
        self.state["building_autobuy_enabled"] = not self.state["building_autobuy_enabled"]
        print(f"Toggle building buying -> {self.state['building_autobuy_enabled']}")

    def toggle_upgrade_buying(self):
        self.state["upgrade_autobuy_enabled"] = not self.state["upgrade_autobuy_enabled"]
        print(f"Toggle upgrade buying -> {self.state['upgrade_autobuy_enabled']}")

    def toggle_ascension_prep(self):
        self.state["ascension_prep_enabled"] = not self.state["ascension_prep_enabled"]
        print(f"Toggle ascension prep -> {self.state['ascension_prep_enabled']}")

    def set_upgrade_horizon_seconds(self, value):
        print(f"Set upgrade horizon seconds -> {value}")

    def set_building_horizon_seconds(self, value):
        print(f"Set building horizon seconds -> {value}")

    def set_building_cap(self, name, cap):
        print(f"Set building cap {name} -> {cap}")

    def set_building_cap_ignored(self, name, ignored):
        print(f"Set building cap ignored {name} -> {ignored}")

    def cycle_wrinkler_mode(self):
        modes = ["auto", "manual", "off"]
        current = self.state.get("wrinkler_mode", "auto")
        idx = (modes.index(current) + 1) % len(modes) if current in modes else 0
        self.state["wrinkler_mode"] = modes[idx]
        print(f"Cycle wrinkler mode -> {self.state['wrinkler_mode']}")

    def exit_program(self):
        print("Exit program requested")
        QApplication.instance().quit()

    def dump_shimmer_data(self):
        print("Dump shimmer data")

    def get_config(self):
        return {"game_install_dir": "C:/Steam/..."}

    def save_config(self, config):
        print(f"Save config: {config}")


def main():
    app = QApplication(sys.argv)
    callbacks = JsonMockCallbacks()
    window = QtDashboard(
        get_dashboard_state=callbacks.get_dashboard_state,
        toggle_active=callbacks.toggle_active,
        toggle_main_autoclick=callbacks.toggle_main_autoclick,
        toggle_shimmer_autoclick=callbacks.toggle_shimmer_autoclick,
        toggle_stock_buying=callbacks.toggle_stock_buying,
        toggle_lucky_reserve=callbacks.toggle_lucky_reserve,
        toggle_building_buying=callbacks.toggle_building_buying,
        toggle_upgrade_buying=callbacks.toggle_upgrade_buying,
        toggle_ascension_prep=callbacks.toggle_ascension_prep,
        set_upgrade_horizon_seconds=callbacks.set_upgrade_horizon_seconds,
        set_building_horizon_seconds=callbacks.set_building_horizon_seconds,
        set_building_cap=callbacks.set_building_cap,
        set_building_cap_ignored=callbacks.set_building_cap_ignored,
        cycle_wrinkler_mode=callbacks.cycle_wrinkler_mode,
        exit_program=callbacks.exit_program,
        dump_shimmer_data=callbacks.dump_shimmer_data,
        get_config=callbacks.get_config,
        save_config=callbacks.save_config,
        initial_geometry="800x600",
        refresh_interval_ms=1000,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()