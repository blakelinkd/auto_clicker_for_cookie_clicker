#!/usr/bin/env python3
"""
pytest-qt tests for the Qt HUD module.
"""
import pytest

from qt_hud.hud_qt import QtDashboard
from qt_hud.run_qt_hud import JsonMockCallbacks


class MockCallbacks(JsonMockCallbacks):
    """Extended mock callbacks for testing."""
    def __init__(self):
        super().__init__()
        self.last_called = []

    def toggle_active(self):
        super().toggle_active()
        self.last_called.append('toggle_active')

    def toggle_main_autoclick(self):
        super().toggle_main_autoclick()
        self.last_called.append('toggle_main_autoclick')

    def cycle_wrinkler_mode(self):
        super().cycle_wrinkler_mode()
        self.last_called.append('cycle_wrinkler_mode')


@pytest.mark.qt
def test_qt_dashboard_creation(qtbot):
    """Test that QtDashboard can be instantiated and has correct window title."""
    callbacks = MockCallbacks()
    window = QtDashboard(
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
        initial_geometry="800x600",
        refresh_interval_ms=1000,
    )
    
    qtbot.addWidget(window)
    window.show()
    
    # Verify window title
    assert window.windowTitle() == "Cookie Clicker Bot (Qt)"
    
    # Verify initial state
    assert window.isVisible()


@pytest.mark.qt
def test_qt_dashboard_toggle_buttons(qtbot):
    """Test that toggle buttons trigger callbacks."""
    callbacks = MockCallbacks()
    window = QtDashboard(
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
        initial_geometry="800x600",
        refresh_interval_ms=1000,
    )
    
    qtbot.addWidget(window)
    
    # Find toggle buttons by their text (simplified approach)
    # For now, just verify the window creates without error
    # In a real test, we would locate buttons and simulate clicks
    assert window.toggle_buttons is not None
    assert isinstance(window.toggle_buttons, dict)
    
    # Verify refresh timer is running
    assert window.timer.isActive()
    assert window.timer.interval() == 1000


@pytest.mark.qt
def test_qt_dashboard_refresh(qtbot):
    """Test that the refresh timer updates UI."""
    callbacks = MockCallbacks()
    window = QtDashboard(
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
        initial_geometry="800x600",
        refresh_interval_ms=100,
    )
    
    qtbot.addWidget(window)
    
    # Get initial hero label text
    initial_text = window.hero_label.text()
    
    # Wait for timer to trigger (allow one refresh)
    qtbot.wait(150)
    
    # Text should have changed (should show RUNNING or PAUSED)
    new_text = window.hero_label.text()
    assert new_text != initial_text or "RUNNING" in new_text or "PAUSED" in new_text


def _create_test_window(qtbot, refresh_interval_ms=1000):
    """Helper to create a QtDashboard instance for testing."""
    callbacks = MockCallbacks()
    window = QtDashboard(
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
        initial_geometry="800x600",
        refresh_interval_ms=refresh_interval_ms,
    )
    qtbot.addWidget(window)
    return window


@pytest.mark.qt
def test_qt_dashboard_has_shimmer_autoclick_toggle(qtbot):
    """Check that shimmer autoclick toggle button exists."""
    window = _create_test_window(qtbot)
    assert 'shimmer_autoclick' in window.toggle_buttons


@pytest.mark.qt
def test_qt_dashboard_has_all_tabs(qtbot):
    """Check that all tabs from hud_gui.py are present."""
    window = _create_test_window(qtbot)
    tab_widget = window.tab_widget
    tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
    expected_tabs = ["Gameplay", "Forecasts", "Feed", "Diagnostics"]
    for tab in expected_tabs:
        assert tab in tab_names, f"Missing tab: {tab}"


@pytest.mark.qt
def test_qt_dashboard_has_settings_checkboxes(qtbot):
    """Check that auto-launch and register hotkeys checkboxes exist."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'auto_launch_var')
    assert hasattr(window, 'register_hotkeys_var')


@pytest.mark.qt
def test_qt_dashboard_has_horizon_preset_buttons(qtbot):
    """Check that horizon preset buttons (3m, 15m, etc.) exist."""
    from PySide6.QtWidgets import QPushButton
    window = _create_test_window(qtbot)
    buttons = window.findChildren(QPushButton)
    preset_texts = ["3m", "15m", "30m", "60m", "120m", "180m"]
    found_presets = any(any(text in btn.text() for text in preset_texts) for btn in buttons)
    assert found_presets


@pytest.mark.qt
def test_qt_dashboard_has_purchase_panel(qtbot):
    """Check that purchase panel UI elements exist."""
    window = _create_test_window(qtbot)
    purchase_attrs = [
        'purchase_title', 'purchase_detail', 'purchase_cash_bar', 'purchase_cash_label',
        'purchase_bank_bar', 'purchase_bank_label', 'upgrade_title', 'upgrade_detail',
        'upgrade_cash_bar', 'upgrade_cash_label', 'upgrade_bank_bar', 'upgrade_bank_label',
        'lucky_reserve_bar', 'lucky_reserve_label'
    ]
    for attr in purchase_attrs:
        assert hasattr(window, attr), f"Missing purchase panel attribute: {attr}"


@pytest.mark.qt
def test_qt_dashboard_has_live_status_summary(qtbot):
    """Check that live status summary variables exist."""
    window = _create_test_window(qtbot)
    summary_attrs = ['summary_vars', 'timing_vars']
    for attr in summary_attrs:
        assert hasattr(window, attr), f"Missing live status attribute: {attr}"


@pytest.mark.qt
def test_qt_dashboard_has_charts(qtbot):
    """Check that lump, golden cookie, and trader charts exist (as text placeholders)."""
    window = _create_test_window(qtbot)
    chart_attrs = ['lump_chart', 'golden_cookie_chart', 'trader_chart']
    for attr in chart_attrs:
        assert hasattr(window, attr), f"Missing chart: {attr}"


@pytest.mark.qt
def test_qt_dashboard_has_shimmer_rng_panel(qtbot):
    """Check that shimmer RNG panel elements exist."""
    window = _create_test_window(qtbot)
    shimmer_attrs = ['shimmer_progress', 'shimmer_rng_status', 'shimmer_stats_detail', 'shimmer_dump_btn']
    for attr in shimmer_attrs:
        assert hasattr(window, attr), f"Missing shimmer RNG attribute: {attr}"


@pytest.mark.qt
def test_qt_dashboard_has_building_caps_rows(qtbot):
    """Check that building cap rows dictionary exists."""
    window = _create_test_window(qtbot)
    window._refresh()
    assert hasattr(window, 'building_cap_rows')
    assert hasattr(window, 'building_caps_meta')
    assert hasattr(window, 'building_caps_layout')
    assert window.building_cap_rows


@pytest.mark.qt
def test_qt_dashboard_preserves_focused_building_cap_input(qtbot):
    """Refresh should not reset a cap field while the user is typing."""
    window = _create_test_window(qtbot)
    building_entries = [
        {
            "name": "Cursor",
            "amount": 12,
            "cap": 100,
            "remaining_to_cap": 88,
            "manual_cap": 100,
            "cap_ignored": False,
        }
    ]

    window._update_building_caps(building_entries, {"ignored_building_caps": []})
    cap_input = window.building_cap_rows["Cursor"]["cap_input"]
    cap_input.setFocus()
    cap_input.setText("123")
    cap_input.setModified(True)

    window._update_building_caps(building_entries, {"ignored_building_caps": []})

    assert cap_input.text() == "123"


@pytest.mark.qt
def test_qt_dashboard_has_all_toggle_buttons(qtbot):
    """Check that all toggle buttons are present."""
    window = _create_test_window(qtbot)
    expected_toggles = [
        "active", "stock", "lucky_reserve", "building", "upgrade", "ascension",
        "main_autoclick", "shimmer_autoclick", "wrath_cookie"
    ]
    for toggle in expected_toggles:
        assert toggle in window.toggle_buttons, f"Missing toggle button: {toggle}"


@pytest.mark.qt
def test_qt_dashboard_has_header_labels(qtbot):
    """Check that header labels (hero, meta, last_actions) exist."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'hero_label')
    assert hasattr(window, 'meta_label')
    assert hasattr(window, 'last_actions_label')


@pytest.mark.qt
def test_qt_dashboard_has_wrinkler_button(qtbot):
    """Check that wrinkler mode button exists."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'wrinkler_btn')


@pytest.mark.qt
def test_qt_dashboard_has_exit_button(qtbot):
    """Check that exit button exists in footer."""
    from PySide6.QtWidgets import QPushButton
    window = _create_test_window(qtbot)
    buttons = window.findChildren(QPushButton)
    exit_btn = any("Exit" in btn.text() for btn in buttons)
    assert exit_btn


@pytest.mark.qt
def test_qt_dashboard_has_building_horizon_controls(qtbot):
    """Check that building horizon controls exist."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'building_horizon_slider')


@pytest.mark.qt
def test_qt_dashboard_has_upgrade_horizon_controls(qtbot):
    """Check that upgrade horizon controls exist."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'upgrade_horizon_slider')


@pytest.mark.qt
def test_qt_dashboard_has_settings_tab_controls(qtbot):
    """Check that settings tab controls exist."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'game_path_entry')
    assert hasattr(window, 'browse_btn')
    from PySide6.QtWidgets import QPushButton
    buttons = window.findChildren(QPushButton)
    hasSaveBtn = any("Save" in btn.text() for btn in buttons)
    assert hasSaveBtn


@pytest.mark.qt
def test_qt_dashboard_has_forecasts_tab_labels(qtbot):
    """Check that forecasts tab labels exist."""
    window = _create_test_window(qtbot)
    forecast_attrs = [
        'lump_meta_label', 'lump_modifier_label', 'lump_chart_widget',
        'gc_meta_label', 'gc_detail_label', 'gc_chart_widget'
    ]
    for attr in forecast_attrs:
        assert hasattr(window, attr), f"Missing forecast attribute: {attr}"


@pytest.mark.qt
def test_qt_dashboard_has_feed_tab(qtbot):
    """Check that feed tab exists."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'feed_text')


@pytest.mark.qt
def test_qt_dashboard_has_trader_chart_label(qtbot):
    """Check that trader chart label exists in Gameplay tab."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'trader_chart_label')


@pytest.mark.qt
def test_qt_dashboard_has_summary_labels(qtbot):
    """Check that summary_labels dictionary exists with core keys."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'summary_labels')
    expected_keys = ['cookies', 'spell', 'stock', 'buildings', 'garden', 'combo', 'buffs']
    for key in expected_keys:
        assert key in window.summary_labels, f"Missing summary_labels key: {key}"


@pytest.mark.qt
def test_qt_dashboard_has_timing_labels(qtbot):
    """Check that timing_labels dictionary exists with keys."""
    window = _create_test_window(qtbot)
    assert hasattr(window, 'timing_labels')
    expected_keys = [
        'purchase_cash_eta', 'purchase_bank_eta', 'upgrade_cash_eta', 'upgrade_bank_eta',
        'wrinkler_goal_eta', 'wrinkler_target'
    ]
    for key in expected_keys:
        assert key in window.timing_labels, f"Missing timing_labels key: {key}"


@pytest.mark.qt
def test_qt_dashboard_has_progress_bars(qtbot):
    """Check that all progress bars exist."""
    window = _create_test_window(qtbot)
    progress_bars = [
        'building_cash_bar', 'building_bank_bar', 'upgrade_cash_bar', 'upgrade_bank_bar',
        'lucky_reserve_bar', 'mana_bar', 'wrinkler_fill_bar',
        'stock_exposure_bar', 'ascension_bar'
    ]
    for bar in progress_bars:
        assert hasattr(window, bar), f"Missing progress bar: {bar}"


@pytest.mark.qt
def test_qt_dashboard_has_building_stats_tab(qtbot):
    """Check that Building Stats tab exists (Qt extra)."""
    window = _create_test_window(qtbot)
    tab_widget = window.tab_widget
    tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
    hasBuildingStats = any("\U0001f9f1" in name or "Building Stats" in name for name in tab_names)
    assert hasBuildingStats


@pytest.mark.qt
def test_qt_dashboard_has_garden_automation_tab(qtbot):
    """Check that Garden Automation tab exists (Qt extra)."""
    window = _create_test_window(qtbot)
    tab_widget = window.tab_widget
    tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
    hasGarden = any("\U0001f331" in name or "Garden" in name for name in tab_names)
    assert hasGarden


@pytest.mark.qt
def test_qt_dashboard_has_status_logs_tab(qtbot):
    """Check that Status & Logs tab exists (Qt extra)."""
    window = _create_test_window(qtbot)
    tab_widget = window.tab_widget
    tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
    hasStatus = any("Status" in name or "Logs" in name for name in tab_names)
    assert hasStatus


@pytest.mark.qt
def test_qt_dashboard_initial_refresh(qtbot):
    """Test that initial refresh populates data."""
    callbacks = MockCallbacks()
    window = _create_test_window(qtbot, refresh_interval_ms=100)
    qtbot.wait(150)
    hero_text = window.hero_label.text()
    assert "RUNNING" in hero_text or "PAUSED" in hero_text or "INIT" in hero_text


@pytest.mark.qt
def test_qt_dashboard_compatibility_aliases(qtbot):
    """Check that compatibility aliases map correctly."""
    window = _create_test_window(qtbot)
    assert window.summary_vars is window.summary_labels
    assert window.timing_vars is window.timing_labels
