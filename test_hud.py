#!/usr/bin/env python3
"""
Quick test of QtDashboard to check tab orientation and any errors.
"""
import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Import the mock callbacks
from qt_hud.run_qt_hud import JsonMockCallbacks
from qt_hud.hud_qt import QtDashboard

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
    
    # Close after 2 seconds
    QTimer.singleShot(2000, window.close)
    QTimer.singleShot(2100, app.quit)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()