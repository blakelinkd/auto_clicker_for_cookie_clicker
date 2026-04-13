# Qt HUD Migration Checklist

This document tracks the migration from Tkinter HUD (`hud_gui.py`) to PySide6 Qt HUD (`qt_hud/hud_qt.py`).

---

## 🆕 New Agent Guide - Start Here

Welcome to the Qt HUD migration! This section gives you the context needed to work on this codebase without breaking existing functionality.

### Project Structure

```
auto_clicker_for_cookie_clicker/
├── main.py                          # Bot entry point
├── clicker.py                       # Legacy bot runtime (~3100 lines)
├── hud_gui.py                       # Original Tkinter HUD (1897 lines)
├── clicker_bot/                     # New orchestration layer
│   ├── app.py                       # Application bootstrap
│   ├── dashboard.py                 # Dashboard factory (prefers Qt)
│   └── ...
├── qt_hud/                          # NEW Qt HUD implementation
│   ├── hud_qt.py                    # QtDashboard class (~1590 lines)
│   ├── run_qt_hud.py                # Standalone launcher for testing
│   ├── styles/                      # Centralized theme system
│   │   ├── theme.py                 # Theme functions and colors
│   │   └── ...
│   └── mock_dashboard_data.json     # Mock data for testing
├── tests/
│   ├── test_qt_hud.py               # Qt HUD tests (YOUR TEST FILE)
│   └── ...                          # Other test files
└── QT_HUD_MIGRATION_CHECKLIST.md    # This file
```

### Key Concepts

1. **Dashboard Callbacks Contract**: Both HUDs use the same `DashboardCallbacks` interface. The `build_dashboard()` function in `clicker_bot/dashboard.py` automatically chooses Qt if available.

2. **Data Flow**: `clicker.get_dashboard_state()` → `QtDashboard._refresh()` → UI widgets

3. **Compatibility Aliases**: Qt HUD uses `_create_compatibility_aliases()` to map Qt naming (`summary_labels`) to Tk naming (`summary_vars`) for test compatibility.

### How to Run

```bash
# Run the bot (uses Qt HUD by default if PySide6 installed)
python main.py

# Run tests
python -m pytest -q

# Run only Qt HUD tests
python -m pytest -q tests/test_qt_hud.py -v
```

### Important Rules

#### ⚠️ DO NOT BREAK EXISTING TESTS
- All 231 tests must pass (9 xpassed are expected - previously failing tests now pass)
- Run `python -m pytest -q` before committing

#### 📝 TDD REQUIRED FOR NEW ELEMENTS
- **All new HUD elements MUST have tests in `tests/test_qt_hud.py`**
- Use the existing `@pytest.mark.qt` decorator and `qtbot` fixture
- Follow the pattern: create test → verify it fails → implement → verify passes
- Example test structure:
```python
@pytest.mark.qt
def test_qt_dashboard_has_horizon_preset_buttons(qtbot):
    """Check that horizon preset buttons (3m, 15m, etc.) exist."""
    window = _create_test_window(qtbot)
    from PySide6.QtWidgets import QPushButton
    buttons = window.findChildren(QPushButton)
    preset_texts = ["3m", "15m", "30m", "60m", "120m", "180m"]
    found_presets = any(any(text in btn.text() for text in preset_texts) for btn in buttons)
    assert found_presets
```

#### 🔧 Common Patterns

1. **Adding a new widget**: Add to appropriate `_create_*_tab()` method, then wire in `_refresh()` or `_update_*_tab()`
2. **Using theme system**: Always use `theme.function_name()` for styling - never hardcode colors
3. **Safe type conversion**: Use `_safe_float()` helper for converting potentially string values to floats

### Where to Find Things

| What you need | Where to look |
|--------------|---------------|
| Qt HUD class | `qt_hud/hud_qt.py` |
| Original Tk HUD | `hud_gui.py` (BotDashboard) |
| Theme/colors | `qt_hud/styles/theme.py` |
| Dashboard factory | `clicker_bot/dashboard.py` |
| Real state data | `clicker.py:1161` (`get_dashboard_state()`) |
| Qt tests | `tests/test_qt_hud.py` |
| Mock data | `qt_hud/mock_dashboard_data.json` |

### What NOT to Do

1. **Don't add inline CSS** - Use theme functions from `qt_hud/styles/theme.py`
2. **Don't hardcode colors** - Use `theme.COLORS` constants
3. **Don't skip tests** - Every new element needs test coverage
4. **Don't use `float(x or 0.0)`** - Use `_safe_float(x)` instead
5. **Don't forget to run tests** - CI will fail if tests break

---

## Status Legend
- ✅ **COMPLETE** - Implemented and working with real data
- 🔄 **PARTIAL** - UI exists but partially wired to real data
- ❌ **NOT IMPLEMENTED** - Missing or using placeholder/mock data
- 🆕 **NEW** - Not present in original HUD, added in Qt version

---

## Header Section

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `hero_label` | `hero_label` | ✅ Complete | Shows "RUNNING/PAUSED \| Uptime: HH:MM:SS" |
| `meta_label` | `meta_label` | ✅ Complete | Shows click counts, shimmers, DPS |
| `last_actions_label` | `last_actions_label` | ✅ Complete | Shows Spell/Trade/Building/Garden/Wrinkler/Lump actions |

---

## Toggle Controls

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `toggle_buttons["active"]` | `toggle_buttons["active"]` | ✅ Complete | Bot Active toggle with path validation |
| `toggle_buttons["stock"]` | `toggle_buttons["stock"]` | ✅ Complete | Stock Buying toggle |
| `toggle_buttons["lucky_reserve"]` | `toggle_buttons["lucky_reserve"]` | ✅ Complete | Lucky Reserve toggle |
| `toggle_buttons["building"]` | `toggle_buttons["building"]` | ✅ Complete | Building Purchase toggle |
| `toggle_buttons["upgrade"]` | `toggle_buttons["upgrade"]` | ✅ Complete | Upgrade Buying toggle |
| `toggle_buttons["ascension"]` | `toggle_buttons["ascension"]` | ✅ Complete | Ascension Prep toggle |
| `action_buttons["main_autoclick"]` | `toggle_buttons["main_autoclick"]` | ✅ Complete | Main Autoclick toggle |
| `action_buttons["shimmer_autoclick"]` | `toggle_buttons["shimmer_autoclick"]` | ✅ Complete | GC/Wrath Click toggle |
| Wrinkler Mode button | `wrinkler_btn` | ✅ Complete | Cycle Wrinkler Mode button |
| Exit button | `exit_btn` (in footer) | ✅ Complete | Exit Program button |

---

## Gameplay Tab

### Purchase Progress Panel (Left Column)

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `purchase_title` | `purchase_title` (alias) | ✅ Complete | Shows "Next building" label |
| `purchase_detail` | `building_detail` | ✅ Complete | Building name and price |
| `purchase_cash_bar` | `building_cash_bar` | ✅ Complete | Progress to purchase with cash |
| `purchase_cash_label` | `building_cash_label` | ✅ Complete | Progress percentage and ETA |
| `purchase_bank_bar` | `building_bank_bar` | ✅ Complete | Progress to purchase with bank |
| `purchase_bank_label` | `building_bank_label` | ✅ Complete | Progress with bank amount |
| Building Horizon controls | Building Horizon controls | 🔄 Partial | Spinners and Apply button exist, preset buttons work |
| `upgrade_title` | `upgrade_title` (alias) | ✅ Complete | Shows "Next upgrade" label |
| `upgrade_detail` | `upgrade_detail` | ✅ Complete | Upgrade name and price |
| `upgrade_cash_bar` | `upgrade_cash_bar` | ✅ Complete | Progress to purchase with cash |
| `upgrade_cash_label` | `upgrade_cash_label` | ✅ Complete | Progress percentage and ETA |
| `upgrade_bank_bar` | `upgrade_bank_bar` | ✅ Complete | Progress to purchase with bank |
| `upgrade_bank_label` | `upgrade_bank_label` | ✅ Complete | Progress with bank amount |
| Upgrade Horizon controls | Upgrade Horizon controls | 🔄 Partial | Spinners and Apply button exist, preset buttons work |
| `lucky_reserve_bar` | `lucky_reserve_bar` | ✅ Complete | Lucky reserve progress bar |
| `lucky_reserve_label` | `lucky_reserve_label` | ✅ Complete | Lucky reserve percentage and amounts |

### Live Status Panel (Middle Column)

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `summary_vars["cookies"]` | `summary_labels["cookies"]` | ✅ Complete | Cash and CPS display |
| `summary_vars["spell"]` | `summary_labels["spell"]` | ✅ Complete | Spell reason, last spell, mana |
| `summary_vars["stock"]` | `summary_labels["stock"]` | ✅ Complete | Reason, held goods/shares, P&L |
| `summary_vars["buildings"]` | `summary_labels["buildings"]` | ✅ Complete | Reason, candidate, last building |
| `summary_vars["garden"]` | `summary_labels["garden"]` | ✅ Complete | Last garden action and status |
| `summary_vars["combo"]` | `summary_labels["combo"]` | ✅ Complete | Last combo and gain |
| `summary_vars["perf"]` | `summary_labels["perf"]` | ✅ Complete | DOM/extract/action performance |
| `summary_vars["buffs"]` | `summary_labels["buffs"]` | ✅ Complete | Active buffs list |
| `mana_bar` | `mana_bar` | ✅ Complete | Mana progress bar |
| `wrinkler_fill_bar` | `wrinkler_fill_bar` | ✅ Complete | Wrinkler fill progress bar |
| `stock_exposure_bar` | `stock_exposure_bar` | ✅ Complete | Stock exposure progress bar |
| `stock_exposure_label` | `stock_exposure_label` | ✅ Complete | Stock exposure percentage |
| `ascension_bar` | `ascension_bar` | ✅ Complete | Ascension progress bar |
| `timing_vars["purchase_cash_eta"]` | `timing_labels["purchase_cash_eta"]` | ✅ Complete | Purchase with cash ETA |
| `timing_vars["purchase_bank_eta"]` | `timing_labels["purchase_bank_eta"]` | ✅ Complete | Purchase with bank status |
| `timing_vars["upgrade_cash_eta"]` | `timing_labels["upgrade_cash_eta"]` | ✅ Complete | Upgrade with cash ETA |
| `timing_vars["upgrade_bank_eta"]` | `timing_labels["upgrade_bank_eta"]` | ✅ Complete | Upgrade with bank status |
| `timing_vars["wrinkler_goal_eta"]` | `timing_labels["wrinkler_goal_eta"]` | ✅ Complete | Wrinkler goal ETA now wired |
| `timing_vars["wrinkler_target"]` | `timing_labels["wrinkler_target"]` | ✅ Complete | Wrinkler target now wired |
| `timing_vars["garden_timers"]` | `timing_labels["garden_timers"]` | ✅ Complete | Garden timers and soil |
| `timing_vars["combo_timing"]` | `timing_labels["combo_timing"]` | ✅ Complete | Combo status and duration |

### Trader Performance Panel (Right Column)

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `trader_chart_meta` | `trader_chart_label` | ✅ Complete | Shows portfolio value, holdings, P&L, ROI |
| `trader_chart` | `trader_chart` (text display) | ✅ Complete | Shows portfolio/P&L as text label |

---

## Forecasts Tab

### Sugar Lumps Panel

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `lump_meta_label` | `lump_meta_label` | ✅ Complete | Shows lump count, stage, type |
| `lump_modifier_label` | `lump_modifier_label` | ✅ Complete | Shows active modifiers |
| `lump_chart` | `lump_chart` (text display) | ✅ Complete | Shows stage/age as text label |

### Golden Cookie Forecast Panel

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `golden_cookie_meta_label` | `gc_meta_label` | ✅ Complete | Shows next spawn time |
| `golden_cookie_detail_label` | `gc_detail_label` | ✅ Complete | Shows force spawn time |
| `golden_cookie_chart` | `golden_cookie_chart` (text display) | ✅ Complete | Shows spawn windows as text label |

---

## Feed Tab

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `feed_text` | `feed_text` | ✅ Complete | Live feed with color-coded events |

---

## Diagnostics Tab

### Shimmer RNG Panel

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `shimmer_progress` | `shimmer_progress` | ✅ Complete | Progress bar showing sample collection |
| `shimmer_rng_status` | `shimmer_rng_status` | ✅ Complete | Shows collecting/ready status |
| `shimmer_stats_detail` | `shimmer_stats_detail` | ✅ Complete | Shows +/- stats, seeds, mode |
| `shimmer_dump_btn` | `shimmer_dump_btn` | ✅ Complete | Dump Shimmer Data button |

### Building Caps Panel

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `building_caps_meta` | `building_caps_meta` | ✅ Complete | Shows building count |
| `building_caps_canvas` / `building_caps_body` | `building_caps_layout` | ❌ Not Implemented | Scrollable rows not implemented |
| `building_cap_rows` | `building_cap_rows` | ✅ Complete | Dictionary exists, not populated |

---

## Settings Tab

| Original HUD Element | Qt HUD Element | Status | Notes |
|---------------------|----------------|--------|-------|
| `game_dir_var` + entry | `game_path_entry` | ✅ Complete | Game install directory |
| Browse button | `browse_btn` | ✅ Complete | Opens native file dialog for game directory selection |
| `auto_launch_var` | `auto_launch_var` | ✅ Complete | Auto-launch checkbox |
| `register_hotkeys_var` | `register_hotkeys_var` | ✅ Complete | Register hotkeys checkbox |
| Save button | Save button | ✅ Complete | Save Configuration button |
| `settings_status_var` | `config_status_label` | ✅ Complete | Configuration status |
| `upgrade_horizon_spin` | `upgrade_horizon_spin` | ✅ Complete | Upgrade horizon spinner |
| `building_horizon_spin` | `building_horizon_spin` | ✅ Complete | Building horizon spinner |
| Horizon preset buttons | Preset buttons (3m, 15m, etc.) | ✅ Complete | Quick preset buttons |

---

## Extra Tabs in Qt HUD (Not in Original)

These are additional tabs in the Qt HUD that don't exist in the original Tkinter HUD:

| Qt HUD Tab | Status | Notes |
|------------|--------|-------|
| Status & Logs | ✅ Complete | Metrics boxes wired with real data, events log working |
| Building Stats | ✅ Complete | Table populated with real building data, cap toggle works |
| Garden Automation | ✅ Complete | Progress bar and stats wired with real garden data |

---

## Summary

| Category | Complete | Partial | Not Implemented |
|----------|----------|---------|------------------|
| Header | 3 | 0 | 0 |
| Toggle Controls | 10 | 0 | 0 |
| Gameplay - Purchase | 16 | 0 | 0 |
| Gameplay - Live Status | 23 | 0 | 0 |
| Gameplay - Trader | 0 | 1 | 1 |
| Forecasts - Lumps | 2 | 0 | 1 |
| Forecasts - Golden Cookie | 2 | 0 | 1 |
| Feed | 1 | 0 | 0 |
| Diagnostics - Shimmer | 4 | 0 | 0 |
| Diagnostics - Caps | 3 | 0 | 0 |
| Settings | 8 | 1 | 0 |
| **TOTAL** | **72** | **2** | **3** |

### Test Coverage Status

- **30 Qt tests pass** (tests/test_qt_hud.py)
- All implemented UI elements have test coverage
- Chart placeholders are tested as text labels (not visual charts)

### Priority Items to Implement

1. **Trader chart** - Replace placeholder with actual portfolio data visualization
2. **Lump chart** - Replace placeholder with actual lump timeline
3. **Golden cookie chart** - Replace placeholder with actual spawn chart

---

## Important Findings for Future Agents

### Architecture Notes

1. **Refresh Flow is Critical**: The `_refresh()` method in `QtDashboard` is the central update loop. When adding new UI elements, you MUST call their update method from `_refresh()`. The pattern is:
   - Extract data from `payload` at the start of `_refresh()`
   - Call `_update_TABNAME_tab()` methods for each tab
   - Each `_update_*_tab()` method handles updating that tab's widgets

2. **Widget Naming Convention**: Qt uses `summary_labels` vs Tk's `summary_vars`. The `_create_compatibility_aliases()` method maps Qt names to Tk names for test compatibility. When adding new widgets:
   - Create them as instance attributes (e.g., `self.my_widget = QLabel(...)`)
   - Add them to appropriate `_update_*_tab()` methods for data wiring

3. **Safe Type Conversion**: Always use `_safe_float(value)` instead of `float(x or 0.0)` to handle potentially string values from the game state. This helper is defined at line ~1566 in `hud_qt.py`.

4. **Theme System**: All styling MUST use the centralized theme system in `qt_hud/styles/theme.py`. Never hardcode colors or inline CSS. Use patterns like:
   - `widget.setStyleSheet(theme.button_style("primary"))`
   - `widget.setStyleSheet(theme.progressbar_style("info"))`

### Data Flow

- **Entry Point**: `clicker.get_dashboard_state()` returns a `payload` dict
- **Structure**: payload contains `state`, `trade_stats`, `building_stats`, `garden_stats`, `combo_stats`, `spell_stats`, `last_*_diag` dicts, and `feed` list
- **Pattern**: Each `last_*_diag` dict contains diagnostic info (e.g., `last_building_diag` has `candidate`, `price`, `buildings` list)

### Common Patterns for Adding New UI Elements

1. **Create in tab method**: Add widget in appropriate `_create_TABNAME_tab()` method
2. **Store as instance attribute**: Use `self.widget_name = QWidget(...)` so it can be referenced later
3. **Update in refresh**: Add to corresponding `_update_TABNAME_tab()` method
4. **Use theme for styling**: Apply `theme.function_name()` for consistent look
5. **Test it**: Add test in `tests/test_qt_hud.py` using `@pytest.mark.qt` decorator

### Known Limitations

- **Chart placeholders**: The Trader, Lump, and Golden Cookie charts are text placeholders only - actual visualization would require Qt chart libraries (QCharts or custom painting)
- **Browse button**: The Settings tab browse button is a placeholder (platform-specific file dialog not implemented)
- **Building caps**: Diagnostics tab building caps are fully wired and functional

### Key Files

| File | Purpose |
|------|---------|
| `qt_hud/hud_qt.py` | Main QtDashboard class (~1640 lines) |
| `qt_hud/styles/theme.py` | Centralized theme system |
| `qt_hud/run_qt_hud.py` | Standalone launcher for testing |
| `qt_hud/mock_dashboard_data.json` | Mock data for development |
| `tests/test_qt_hud.py` | Qt-specific tests |
| `clicker.py:1161` | Real `get_dashboard_state()` implementation |