from dataclasses import dataclass

from hud_gui import BotDashboard


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
    set_upgrade_horizon_seconds: object
    set_building_horizon_seconds: object
    set_building_cap: object
    set_building_cap_ignored: object
    cycle_wrinkler_mode: object
    exit_program: object
    dump_shimmer_data: object


def build_dashboard(*, callbacks: DashboardCallbacks, initial_geometry, refresh_interval_ms: int):
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
        set_upgrade_horizon_seconds=callbacks.set_upgrade_horizon_seconds,
        set_building_horizon_seconds=callbacks.set_building_horizon_seconds,
        set_building_cap=callbacks.set_building_cap,
        set_building_cap_ignored=callbacks.set_building_cap_ignored,
        cycle_wrinkler_mode=callbacks.cycle_wrinkler_mode,
        exit_program=callbacks.exit_program,
        dump_shimmer_data=callbacks.dump_shimmer_data,
        initial_geometry=initial_geometry,
        refresh_interval_ms=int(refresh_interval_ms),
    )
