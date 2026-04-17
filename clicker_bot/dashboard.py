from dataclasses import dataclass, field
from typing import Optional, Any

from clicker_bot.legacy.hud_gui import BotDashboard

try:
    from qt_hud.hud_qt import QtDashboard
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QtDashboard = None


@dataclass(frozen=True)
class DashboardCallbacks:
    get_dashboard_state: object
    toggle_active: object
    toggle_main_autoclick: object
    toggle_shimmer_autoclick: object
    toggle_stock_buying: object
    toggle_lucky_reserve: object
    toggle_building_buying: object
    toggle_upgrade_buying: object
    toggle_ascension_prep: object
    toggle_garden_automation: object
    set_upgrade_horizon_seconds: object
    set_building_horizon_seconds: object
    set_building_cap: object
    set_building_cap_ignored: object
    cycle_wrinkler_mode: object
    exit_program: object
    dump_shimmer_data: object
    get_config: Optional[Any] = field(default=None)
    save_config: Optional[Any] = field(default=None)
    toggle_wrath_cookie_clicking: Optional[Any] = field(default=None)


def build_dashboard(*, callbacks: DashboardCallbacks, initial_geometry, refresh_interval_ms: int, use_qt_hud: bool = True):
    """Build a dashboard. Prefers PySide6 if available, falls back to Tkinter."""
    if use_qt_hud and QT_AVAILABLE:
        return build_qt_dashboard(
            callbacks=callbacks,
            initial_geometry=initial_geometry,
            refresh_interval_ms=refresh_interval_ms,
        )
    # Fallback to Tk
    return BotDashboard(
        get_dashboard_state=callbacks.get_dashboard_state,
        toggle_active=callbacks.toggle_active,
        toggle_main_autoclick=callbacks.toggle_main_autoclick,
        toggle_shimmer_autoclick=callbacks.toggle_shimmer_autoclick,
        toggle_stock_buying=callbacks.toggle_stock_buying,
        toggle_lucky_reserve=callbacks.toggle_lucky_reserve,
        toggle_building_buying=callbacks.toggle_building_buying,
        toggle_upgrade_buying=callbacks.toggle_upgrade_buying,
        toggle_ascension_prep=callbacks.toggle_ascension_prep,
        toggle_garden_automation=callbacks.toggle_garden_automation,
        set_upgrade_horizon_seconds=callbacks.set_upgrade_horizon_seconds,
        set_building_horizon_seconds=callbacks.set_building_horizon_seconds,
        set_building_cap=callbacks.set_building_cap,
        set_building_cap_ignored=callbacks.set_building_cap_ignored,
        cycle_wrinkler_mode=callbacks.cycle_wrinkler_mode,
        exit_program=callbacks.exit_program,
        dump_shimmer_data=callbacks.dump_shimmer_data,
        get_config=callbacks.get_config,
        save_config=callbacks.save_config,
        initial_geometry=initial_geometry,
        refresh_interval_ms=int(refresh_interval_ms),
    )


def build_qt_dashboard(*, callbacks: DashboardCallbacks, initial_geometry, refresh_interval_ms: int):
    """Build a PySide6-based dashboard (requires PySide6 installed)."""
    if not QT_AVAILABLE:
        raise RuntimeError(
            "PySide6 is not available. Install it via 'pip install PySide6'."
        )
    # Ensure QApplication exists before creating Qt widgets
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        import sys
        app = QApplication(sys.argv)
    return QtDashboard(
        get_dashboard_state=callbacks.get_dashboard_state,
        toggle_active=callbacks.toggle_active,
        toggle_main_autoclick=callbacks.toggle_main_autoclick,
        toggle_shimmer_autoclick=callbacks.toggle_shimmer_autoclick,
        toggle_wrath_cookie_clicking=callbacks.toggle_wrath_cookie_clicking,
        toggle_stock_buying=callbacks.toggle_stock_buying,
        toggle_lucky_reserve=callbacks.toggle_lucky_reserve,
        toggle_building_buying=callbacks.toggle_building_buying,
        toggle_upgrade_buying=callbacks.toggle_upgrade_buying,
        toggle_ascension_prep=callbacks.toggle_ascension_prep,
        toggle_garden_automation=callbacks.toggle_garden_automation,
        set_upgrade_horizon_seconds=callbacks.set_upgrade_horizon_seconds,
        set_building_horizon_seconds=callbacks.set_building_horizon_seconds,
        set_building_cap=callbacks.set_building_cap,
        set_building_cap_ignored=callbacks.set_building_cap_ignored,
        cycle_wrinkler_mode=callbacks.cycle_wrinkler_mode,
        exit_program=callbacks.exit_program,
        dump_shimmer_data=callbacks.dump_shimmer_data,
        get_config=callbacks.get_config,
        save_config=callbacks.save_config,
        initial_geometry=initial_geometry,
        refresh_interval_ms=int(refresh_interval_ms),
    )
