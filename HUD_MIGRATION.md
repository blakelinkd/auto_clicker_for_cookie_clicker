# HUD Migration: Tkinter → PySide6

## Overview

This document outlines the migration of the Cookie Clicker bot's HUD from Tkinter to PySide6. The goal is to create a more modern, maintainable UI while preserving essential functionality and improving the user experience.

## Guiding Principles

1. **Backward Compatibility**: The new HUD must work with the existing `DashboardCallbacks` contract
2. **Incremental Migration**: Develop alongside existing Tkinter HUD, then switch
3. **Feature Parity**: Essential functionality must be preserved
4. **UX Improvements**: Address pain points in current UI where possible

## Current State Analysis

### Tkinter HUD Architecture

The current HUD (`hud_gui.py`):
- ~1900 lines of Tkinter code
- Uses `BotDashboard` class with extensive widget management
- Relies on `DashboardCallbacks` for bot interaction
- Updates via periodic refresh timer

### Key Contracts

#### DashboardCallbacks Interface
```python
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
    get_config: Optional[Any] = field(default=None)
    save_config: Optional[Any] = field(default=None)
```

#### Dashboard State Payload
Returned by `get_dashboard_state()`:
- `state`: Global bot state (active flags, counters, timestamps)
- `events`: Recent events feed
- `feed`: Gameplay feed
- `trade_stats`: Stock trading statistics
- `building_stats`: Building purchase statistics
- `ascension_prep_stats`: Ascension preparation stats
- `garden_stats`: Garden automation stats
- `combo_stats`: Combo execution stats
- `spell_stats`: Spell casting stats
- `wrinkler_stats`: Wrinkler handling stats
- `shimmer_stats`: Golden/Wrath cookie stats

## UI Element Inventory

Below is a comprehensive inventory of all UI elements in the current Tkinter HUD, organized by tab and panel. Each element is evaluated for its utility to average users.

### Tab Structure
The HUD uses a tabbed interface with 5 tabs:
1. **Gameplay** – Purchase progress, live status, trader performance
2. **Forecasts** – Sugar lump and golden cookie timers
3. **Feed** – Live game feed with categorized events
4. **Diagnostics** – Shimmer RNG data and building caps
5. **Settings** – Bot configuration and game path

### Header (Above tabs)
**Purpose**: Global bot status and quick toggles

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `hero_label` | `ttk.Label` (Hero.TLabel) | "RUNNING/PAUSED \| Uptime HH:MM:SS" | `state.active`, `state.started_at` | ✅ Yes | Critical status indicator |
| `meta_label` | `ttk.Label` (Data.TLabel) | Condensed feature flags (Feed age, Stocks ON/OFF, etc.) | Multiple `state.*_enabled` fields | ✅ Yes | At-a-glance overview |
| `last_actions_label` | `ttk.Label` (Muted.TLabel) | Last spell, trade, building, garden, wrinkler, lump actions | `state.last_*_action` and diagnostic `reason` fields | ✅ Yes | Quick activity visibility |
| Toggle button "Bot" | `tk.Button` (checkable) | Toggle bot active/inactive | `state.active` | ✅ Yes | Primary control |
| Toggle button "Stock Buy" | `tk.Button` (checkable) | Toggle stock trading | `state.stock_trading_enabled` | ✅ Yes | Common feature |
| Toggle button "Lucky Reserve" | `tk.Button` (checkable) | Toggle lucky cookie reserve | `state.lucky_reserve_enabled` | ✅ Yes | Important optimization |
| Toggle button "Building Buy" | `tk.Button` (checkable) | Toggle building purchases | `state.building_autobuy_enabled` | ✅ Yes | Core feature |
| Toggle button "Upgrade Buy" | `tk.Button` (checkable) | Toggle upgrade purchases | `state.upgrade_autobuy_enabled` | ✅ Yes | Core feature |
| Toggle button "Ascension Prep" | `tk.Button` (checkable) | Toggle ascension preparation | `state.ascension_prep_enabled` | ⚠️ Maybe | Niche feature |
| Action button "Autoclick" | `tk.Button` (checkable) | Toggle main cookie clicking | `state.main_cookie_clicking_enabled` | ✅ Yes | Core feature |
| Action button "GC/Wrath Click" | `tk.Button` (checkable) | Toggle golden/wrath cookie clicking | `state.shimmer_autoclick_enabled` | ✅ Yes | Core feature |
| "Wrinkler Mode" button | `ttk.Button` | Cycle wrinkler modes (auto/manual/off) | `state.wrinkler_mode` | ✅ Yes | Core control |
| "Exit" button | `ttk.Button` | Exit program | – | ✅ Yes | Required for clean exit |

### Tab 1: Gameplay
Contains three panels side‑by‑side.

#### Panel 1A: Purchase Progress (`_build_purchase_panel`)
**Purpose**: Visualize building/upgrade affordability and horizon settings.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `purchase_title` | `ttk.Label` (Value.TLabel) | "Next building" | – | ✅ Yes | Section heading |
| `purchase_detail` | `ttk.Label` (Data.TLabel) | Building candidate name and price | `last_building_diag.candidate`, `.price` | ✅ Yes | Clear target |
| Building horizon controls | `ttk.Frame` with `ttk.Spinbox` | Hours/minutes input for building horizon | `state.building_horizon_seconds` | ⚠️ Maybe | Advanced tuning |
| `purchase_cash_bar` | `ttk.Progressbar` | Progress toward building price with cash only | `cookies` vs `next_candidate_price` | ✅ Yes | Visual affordability |
| `purchase_cash_label` | `ttk.Label` (Muted.TLabel) | Cash shortfall/ETA text | `cookies`, `cookies_ps`, `next_candidate_price` | ✅ Yes | Concrete timing |
| `purchase_bank_bar` | `ttk.Progressbar` | Progress toward building price including wrinkler bank | `cookies + wrinkler_bank` vs `next_candidate_price` | ✅ Yes | Visual bank‑inclusive affordability |
| `purchase_bank_label` | `ttk.Label` (Muted.TLabel) | Bank‑inclusive shortfall/readiness text | Same as above | ✅ Yes | Useful for planning |
| `upgrade_title` | `ttk.Label` (Value.TLabel) | "Next upgrade" | – | ✅ Yes | Section heading |
| `upgrade_detail` | `ttk.Label` (Data.TLabel) | Upgrade candidate name and price | `last_upgrade_diag.candidate`, `.price` | ✅ Yes | Clear target |
| Upgrade horizon controls | `ttk.Frame` with `ttk.Spinbox` | Hours/minutes input for upgrade horizon | `state.upgrade_horizon_seconds` | ⚠️ Maybe | Advanced tuning |
| `upgrade_cash_bar` | `ttk.Progressbar` | Progress toward upgrade price with cash only | `cookies` vs `candidate_price` | ✅ Yes | Visual affordability |
| `upgrade_cash_label` | `ttk.Label` (Muted.TLabel) | Cash shortfall/ETA text | `cookies`, `cookies_ps`, `candidate_price` | ✅ Yes | Concrete timing |
| `upgrade_bank_bar` | `ttk.Progressbar` | Progress toward upgrade price including wrinkler bank | `cookies + wrinkler_bank` vs `candidate_price` | ✅ Yes | Visual bank‑inclusive affordability |
| `upgrade_bank_label` | `ttk.Label` (Muted.TLabel) | Bank‑inclusive shortfall/readiness text | Same as above | ✅ Yes | Useful for planning |
| `lucky_reserve_bar` | `ttk.Progressbar` | Progress toward hard lucky reserve target | `cookies` vs `hard_lucky_cookie_reserve` | ✅ Yes | Visual reserve status |
| `lucky_reserve_label` | `ttk.Label` (Muted.TLabel) | Detailed reserve breakdown (hard/live/global/garden) | Multiple reserve fields | ✅ Yes | Advanced but helpful |

#### Panel 1B: Live Status (`_build_status_panel`)
**Purpose**: Snapshot of all subsystems and timing estimates.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `summary_vars["cookies"]` | `ttk.Label` via `StringVar` | Cash and CPS | `last_building_diag.cookies`, `.cookies_ps` | ✅ Yes | Core economy metric |
| `summary_vars["spell"]` | `ttk.Label` via `StringVar` | Spell status, last spell, mana | `last_spell_diag.reason`, `spell_stats.last_spell`, `.magic` | ✅ Yes | Spellcasting overview |
| `summary_vars["stock"]` | `ttk.Label` via `StringVar` | Stock reason, held goods/shares, P&L | `last_bank_diag.reason`, `trade_stats` | ✅ Yes | Trading overview |
| `summary_vars["buildings"]` | `ttk.Label` via `StringVar` | Building reason, next candidate, prep status | `last_building_diag.reason`, `.candidate`, `ascension_prep_diag` | ✅ Yes | Building overview |
| `summary_vars["garden"]` | `ttk.Label` via `StringVar` | Garden reason, last action | `last_garden_diag.reason`, `garden_stats.last_garden` | ✅ Yes | Garden overview |
| `summary_vars["combo"]` | `ttk.Label` via `StringVar` | Combo reason, last combo | `last_combo_diag.reason`, `combo_stats.last_combo` | ✅ Yes | Combo overview |
| `summary_vars["perf"]` | `ttk.Label` via `StringVar` | Loop performance timings (dom/extract/action) | `state.dom_*_avg_ms`, `.dom_*_max_ms` | ❌ No | Developer‑only |
| `summary_vars["buffs"]` | `ttk.Label` via `StringVar` | Active buff list (truncated) | `state.last_buffs` | ✅ Yes | Useful buff awareness |
| `mana_bar` | `ttk.Progressbar` | Magic mana fill | `last_spell_diag.magic`, `.max_magic` | ✅ Yes | Visual spell readiness |
| `wrinkler_fill_bar` | `ttk.Progressbar` | Attached wrinkler fill | `last_wrinkler_diag.attached`, `.max` | ✅ Yes | Visual wrinkler status |
| `stock_exposure_bar` | `ttk.Progressbar` | Portfolio exposure ratio | `last_bank_diag.portfolio_exposure_ratio` | ⚠️ Maybe | Advanced trading metric |
| `stock_exposure_label` | `ttk.Label` (Muted.TLabel) | Exposure/cap numbers | `last_bank_diag.portfolio_exposure`, `.portfolio_cap` | ⚠️ Maybe | Advanced trading detail |
| `ascension_bar` | `ttk.Progressbar` | Ascension meter percentage | `last_ascension.legacyMeterPercent` | ⚠️ Maybe | Niche, but visible |
| `timing_vars["purchase_cash_eta"]` | `ttk.Label` via `StringVar` | Purchase ETA with cash only | `cookies`, `cookies_ps`, `next_candidate_price` | ✅ Yes | Concrete timing |
| `timing_vars["purchase_bank_eta"]` | `ttk.Label` via `StringVar` | Purchase readiness with wrinkler bank | `cookies + wrinkler_bank`, `next_candidate_price` | ✅ Yes | Useful for planning |
| `timing_vars["upgrade_cash_eta"]` | `ttk.Label` via `StringVar` | Upgrade ETA with cash only | `cookies`, `cookies_ps`, `candidate_price` | ✅ Yes | Concrete timing |
| `timing_vars["upgrade_bank_eta"]` | `ttk.Label` via `StringVar` | Upgrade readiness with wrinkler bank | `cookies + wrinkler_bank`, `candidate_price` | ✅ Yes | Useful for planning |
| `timing_vars["wrinkler_goal_eta"]` | `ttk.Label` via `StringVar` | Wrinkler pop goal affordability and gap | `last_wrinkler_diag.pop_goal_*` | ⚠️ Maybe | Niche, but helpful |
| `timing_vars["wrinkler_target"]` | `ttk.Label` via `StringVar` | Wrinkler target name and candidate reward | `last_wrinkler_diag.pop_goal_*`, `.candidate_reward` | ⚠️ Maybe | Niche detail |
| `timing_vars["garden_timers"]` | `ttk.Label` via `StringVar` | Next tick and next soil change timers | `last_garden_diag.next_tick`, `.next_soil` | ✅ Yes | Useful garden planning |
| `timing_vars["combo_timing"]` | `ttk.Label` via `StringVar` | Combo reason and last run duration | `last_combo_diag.reason`, `state.last_combo_run_duration` | ✅ Yes | Combo timing insight |

#### Panel 1C: Trader Performance (`_build_trader_panel`)
**Purpose**: Visual chart of stock portfolio value over time.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `trader_chart_meta` | `ttk.Label` (Muted.TLabel) | Chart description text | – | ⚠️ Maybe | Context label |
| `trader_chart` | `tk.Canvas` | Line chart of portfolio value | `trade_stats.portfolio_history` | ⚠️ Maybe | Visual trend, but not critical |

### Tab 2: Forecasts
Two vertical panels for sugar lumps and golden cookies.

#### Panel 2A: Sugar Lumps (`_build_lump_panel`)
**Purpose**: Sugar lump stage timeline and modifiers.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `lump_meta_label` | `ttk.Label` (Data.TLabel) | Current lump count, next stage, ripe/overripe timers | `last_lump_diag.lumps`, `.stage`, `.time_to_ripe_seconds`, etc. | ✅ Yes | Clear lump status |
| `lump_modifier_label` | `ttk.Label` (Muted.TLabel) | Active ripening modifiers | `last_lump_diag.modifiers` | ✅ Yes | Useful modifier awareness |
| `lump_chart` | `tk.Canvas` | Visual timeline from now → mature → ripe → overripe | `last_lump_diag.age_ms`, `.mature_age_ms`, etc. | ✅ Yes | Excellent visual timeline |

#### Panel 2B: Golden Cookie Forecast (`_build_golden_cookie_panel`)
**Purpose**: Golden cookie spawn timer and classification.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `golden_cookie_meta_label` | `ttk.Label` (Data.TLabel) | Timer status and next spawn estimate | `last_golden_diag.available`, `.next_spawn_seconds`, etc. | ✅ Yes | Clear GC timing |
| `golden_cookie_detail_label` | `ttk.Label` (Muted.TLabel) | Additional details (force‑spawn, wrath, etc.) | `last_golden_diag` fields | ✅ Yes | Useful detail |
| `golden_cookie_chart` | `tk.Canvas` | Visual timeline of spawn windows | `last_golden_diag.spawn_windows` | ⚠️ Maybe | Visual but not critical |

### Tab 3: Feed (`_build_feed_panel`)
**Purpose**: Live, color‑coded game feed.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `feed_text` | `scrolledtext.ScrolledText` | Chronologically reversed feed entries with colored categories | `payload.feed` | ✅ Yes | Essential for debugging and awareness |

### Tab 4: Diagnostics
Two vertical panels for shimmer RNG and building caps.

#### Panel 4A: Shimmer RNG Data (`_build_shimmer_rng_panel`)
**Purpose**: Golden/wrath cookie predictor sampling progress.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `shimmer_progress` | `ttk.Progressbar` | Overall sampling progress (samples & seeds) | `shimmer_stats.total`, `.seeds_captured` | ⚠️ Maybe | Useful for predictor readiness |
| `shimmer_rng_status` | `ttk.Label` (Muted.TLabel) | Readiness status with color coding | `shimmer_stats.tracking_active`, `.total`, etc. | ⚠️ Maybe | Status indicator |
| `shimmer_stats_detail` | `ttk.Label` (Muted.TLabel) | Detailed counts (+/-/=, seeds, mode, blocked, reset reason) | `shimmer_stats` fields | ⚠️ Maybe | Detailed debug info |
| `shimmer_dump_btn` | `ttk.Button` | Export shimmer data to file | – | ❌ No | Debug feature only |

#### Panel 4B: Building Caps (`_build_building_caps_panel`)
**Purpose**: Per‑building cap management with ignore toggles and manual overrides.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `building_caps_meta` | `ttk.Label` (Muted.TLabel) | Summary line (count, ignored, instructions) | `building_entries` length, `ignored` set | ⚠️ Maybe | Context label |
| `building_caps_body` | `ttk.Frame` inside `tk.Canvas` | Scrollable list of building rows | `last_building_diag.buildings` | ⚠️ Maybe | Advanced configuration |
| Per‑building row | `ttk.Frame` with multiple widgets | Building name, summary, ignore checkbox, cap entry, apply/reset buttons | `entry.name`, `.amount`, `.cap`, etc. | ⚠️ Maybe | Advanced configuration |

### Tab 5: Settings (`_build_settings_panel`)
**Purpose**: Game path configuration and config persistence.

| Element | Widget Type | Description | Data Source | Essential? | User Value |
|---------|-------------|-------------|-------------|------------|------------|
| `game_path_entry` | `ttk.Entry` | Cookie Clicker installation directory | `config.game_install_dir` | ✅ Yes | Required for operation |
| `browse_button` | `ttk.Button` | Open directory browser | – | ✅ Yes | Usability improvement |
| `save_config_button` | `ttk.Button` | Save current configuration | – | ✅ Yes | Required for persistence |
| `settings_status_var` | `tk.StringVar` | Status message after save/error | – | ✅ Yes | Feedback important |
| Config‑dependent widgets | Various | Only shown if `get_config`/`save_config` are provided | – | ✅ Yes | Graceful fallback |

### Global UI Patterns
**Design Patterns Used**:
- **Card‑style panels**: Each panel is a `ttk.LabelFrame` with consistent padding and styling
- **Color‑coded progress bars**: Different styles (Info, Accent, Warn) for different metrics
- **Toggle buttons**: Custom `tk.Button` with red/green/blue background states
- **Canvas‑based charts**: Custom‑drawn timelines for lumps, golden cookies, and stock portfolio
- **Scrollable canvas**: For building caps list with manual scrollbar
- **Tagged text widget**: Feed with syntax‑highlighting‑like category colors

## Proposed PySide6 Implementation

Based on the inventory above, we prioritize elements by user value and complexity.

### Phase 1: Core UI (Essential – ✅ Yes)
**Target**: Fully functional bot with all critical controls and status.
- **Header**: hero label, meta label, last actions label, all toggle/action buttons, wrinkler mode button, exit button.
- **Gameplay tab – Purchase Progress panel**: building/upgrade titles, details, cash/bank progress bars and labels, lucky reserve bar and label. (Horizon controls deferred to Phase 3.)
- **Gameplay tab – Live Status panel**: summary_vars for cookies, spell, stock, buildings, garden, combo, buffs; mana bar, wrinkler fill bar, garden timers, combo timing, purchase/upgrade cash/bank ETAs. (Performance metrics and stock exposure deferred.)
- **Feed tab**: feed_text with category coloring.
- **Settings tab**: game path entry, browse button, save button, status feedback.
- **Forecasts tab – Sugar Lumps panel**: meta label, modifier label, lump chart.
- **Forecasts tab – Golden Cookie Forecast panel**: meta label, detail label. (Chart deferred.)

### Phase 2: Enhanced Visualization (⚠️ Maybe – high value)
**Target**: Add visual charts and advanced status panels.
- **Gameplay tab – Trader Performance panel**: trader chart (canvas) with meta label.
- **Forecasts tab – Golden Cookie Forecast panel**: chart (canvas).
- **Gameplay tab – Live Status panel**: stock exposure bar/label, ascension bar, wrinkler goal/target timing.
- **Diagnostics tab – Shimmer RNG Data panel**: progress bar, status label, detail label. (Dump button deferred.)
- **Diagnostics tab – Building Caps panel**: meta label, scrollable building list with ignore toggles and cap entries. (Apply/reset buttons included.)

### Phase 3: Advanced Configuration & Debug (⚠️ Maybe – niche / ❌ No)
**Target**: Fine‑tuning controls and developer features.
- **Gameplay tab – Purchase Progress panel**: building/upgrade horizon controls (hours/minutes spinboxes).
- **Gameplay tab – Live Status panel**: performance metrics (dom/extract/action timings).
- **Diagnostics tab – Shimmer RNG Data panel**: dump shimmer data button.
- (Optional) Dark/light theme toggle, tooltips for all controls.

## Design Guidelines for PySide6

### Layout Strategy
- **Main Window**: `QMainWindow` with central widget
- **Tabbed Interface**: `QTabWidget` for organization
- **Grid Layouts**: `QGridLayout` for structured panels
- **Scroll Areas**: `QScrollArea` for content-heavy sections

### Widget Mapping
- `tk.Label` → `QLabel`
- `tk.Button` → `QPushButton` (checkable for toggles)
- `tk.scrolledtext.ScrolledText` → `QTextEdit` (read-only)
- `tk.ttk.Progressbar` → `QProgressBar`
- `tk.Entry` → `QLineEdit`
- `tk.Scale` → `QSlider` or `QSpinBox`

### Thread Safety
- All UI updates must happen in GUI thread
- Use `QTimer` for periodic refresh
- Signal/slot for callback integration

## Migration Plan

### Current Status (2026‑04‑12)
- ✅ **Bootstrap**: `qt_hud/hud_qt.py` exists with `QtDashboard` class implementing the `DashboardCallbacks` contract.
- ✅ **Standalone test**: `qt_hud/run_qt_hud.py` launches a Qt window with dummy callbacks.
- ✅ **Factory function**: `clicker_bot/dashboard.py` exports `build_qt_dashboard()` (optional).
- 🚧 **Basic UI**: Current `QtDashboard` has a simple header, toggle buttons, status text, and events log.
- ❌ **Missing**: Tabbed interface, purchase/status/forecasts/feed/diagnostics/settings panels, charts, building caps.

### Next Steps

1. **Phase 1A: Tabbed Interface & Gameplay Tab** 🚧 Next
   - Create `QTabWidget` with tabs: Gameplay, Forecasts, Feed, Diagnostics, Settings.
   - Implement **Purchase Progress panel** (building/upgrade progress bars, lucky reserve).
   - Implement **Live Status panel** (summary_vars, mana/wrinkler bars, timing ETAs).
   - Keep existing header and toggle buttons.

2. **Phase 1B: Remaining Essential Panels**
   - **Feed tab**: `QTextEdit` with syntax‑like coloring (reuse `feed_text` logic).
   - **Settings tab**: Game path entry, browse button, save button, status feedback.
   - **Forecasts tab – Sugar Lumps**: meta label, modifier label, lump chart (canvas).
   - **Forecasts tab – Golden Cookie**: meta label, detail label (chart deferred).

3. **Phase 2: Enhanced Visualization**
   - **Trader Performance panel**: Portfolio value chart (`QPainter` or `QChart`).
   - **Golden Cookie chart**: Spawn timeline canvas.
   - **Shimmer RNG panel**: Progress bar, status/detail labels.
   - **Building Caps panel**: Scrollable list with ignore toggles and cap entries.

4. **Phase 3: Advanced Configuration**
   - Horizon controls (spinboxes for hours/minutes).
   - Performance metrics display.
   - Dump shimmer data button.
   - Optional: tooltips, dark/light theme.

5. **Integration & Production**
   - Replace Tkinter dashboard in test environment.
   - Verify no regression in bot behavior.
   - Update `build_dashboard()` to use Qt by default, keep Tkinter as fallback.
   - Update documentation and `REFACTOR_LOG.md`.

## Success Criteria

1. All essential functionality preserved
2. No regression in user workflow
3. Improved visual clarity and organization
4. Responsive layout for common window sizes
5. Clear error feedback and status indication
6. Settings persistence works correctly

## Open Questions

1. Should we maintain Tkinter as a fallback for systems without Qt?
2. How to handle per-building cap configuration more intuitively?
3. Should we add tooltips for all controls?
4. Is there value in a dark/light theme toggle?

## Appendix: Actual UI Structure (from hud_gui.py)

```
BotDashboard
├── Header (above tabs)
│   ├── hero_label (RUNNING/PAUSED | Uptime)
│   ├── meta_label (condensed status flags)
│   ├── last_actions_label (last spell/trade/building/etc.)
│   ├── toggle_buttons (active, stock, lucky_reserve, building, upgrade, ascension)
│   ├── action_buttons (main_autoclick, shimmer_autoclick)
│   ├── wrinkler_mode_button
│   └── exit_button
├── Tabbed interface (ttk.Notebook)
│   ├── Gameplay tab
│   │   ├── Purchase Progress panel (left column)
│   │   │   ├── purchase_title, purchase_detail
│   │   │   ├── building horizon controls (hours/minutes spinboxes)
│   │   │   ├── purchase_cash_bar, purchase_cash_label
│   │   │   ├── purchase_bank_bar, purchase_bank_label
│   │   │   ├── upgrade_title, upgrade_detail
│   │   │   ├── upgrade horizon controls
│   │   │   ├── upgrade_cash_bar, upgrade_cash_label
│   │   │   ├── upgrade_bank_bar, upgrade_bank_label
│   │   │   ├── lucky_reserve_bar, lucky_reserve_label
│   │   ├── Live Status panel (middle column)
│   │   │   ├── summary_vars (cookies, spell, stock, buildings, garden, combo, perf, buffs)
│   │   │   ├── mana_bar
│   │   │   ├── wrinkler_fill_bar
│   │   │   ├── stock_exposure_bar, stock_exposure_label
│   │   │   ├── ascension_bar
│   │   │   ├── timing_vars (purchase_cash_eta, purchase_bank_eta, upgrade_cash_eta,
│   │   │       upgrade_bank_eta, wrinkler_goal_eta, wrinkler_target, garden_timers, combo_timing)
│   │   └── Trader Performance panel (right column)
│   │       ├── trader_chart_meta
│   │       └── trader_chart (canvas)
│   ├── Forecasts tab
│   │   ├── Sugar Lumps panel (top)
│   │   │   ├── lump_meta_label
│   │   │   ├── lump_modifier_label
│   │   │   └── lump_chart (canvas)
│   │   └── Golden Cookie Forecast panel (bottom)
│   │       ├── golden_cookie_meta_label
│   │       ├── golden_cookie_detail_label
│   │       └── golden_cookie_chart (canvas)
│   ├── Feed tab
│   │   └── feed_text (scrolledtext with category coloring)
│   ├── Diagnostics tab
│   │   ├── Shimmer RNG Data panel (top)
│   │   │   ├── shimmer_progress (progress bar)
│   │   │   ├── shimmer_rng_status
│   │   │   ├── shimmer_stats_detail
│   │   │   └── shimmer_dump_btn
│   │   └── Building Caps panel (bottom, scrollable)
│   │       ├── building_caps_meta
│   │       ├── building_caps_canvas (scrollable)
│   │       │   └── building_caps_body (dynamic rows)
│   │       │       └── per‑building row:
│   │       │           ├── building name label
│   │       │           ├── summary StringVar label
│   │       │           ├── ignore checkbutton
│   │       │           ├── cap entry field
│   │       │           ├── apply button
│   │       │           └── reset button
│   └── Settings tab
│       ├── game_path_entry
│       ├── browse_button
│       ├── save_config_button
│       └── settings_status_var (status label)
└── (No separate footer; exit button is in header)
```

**Notes**:
- The old inventory incorrectly listed separate tabs for Stocks, Buildings, Garden, Spells, Wrinklers, Combo. Those are actually **panels inside the Gameplay tab** or **summaries in the Live Status panel**.
- There is no separate "Status Area" or "Footer". The header contains all global controls.
- The feed tab is purely a log viewer; there is no separate "events log" tab.
- The diagnostics tab contains shimmer RNG and building caps, not general debug info.