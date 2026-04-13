# Qt HUD Style Guide

## Overview

This document outlines the styling architecture and conventions for the Qt HUD dashboard. The system uses a centralized theme approach to separate CSS styling from Python logic, following PySide6 best practices for maintainability and consistency.

## Architecture

### Core Principles

1. **Separation of Concerns**: All styling is defined in `qt_hud/styles/theme.py`, not inline in UI code
2. **Single Source of Truth**: Colors, spacing, and styles are defined once and reused everywhere
3. **Component-Based Styling**: Each UI component type has a dedicated styling function
4. **Runtime Theme Consistency**: All UI elements reference the same theme functions

### File Structure

```
qt_hud/
├── hud_qt.py              # Main HUD implementation (USES theme functions)
└── styles/
    ├── theme.py           # Central theme definitions (DEFINES styles)
    └── QT_HUD_STYLE_GUIDE.md  # This document
```

## Using the Theme System

### Importing the Theme

```python
from .styles import theme
```

### Applying Styles

**✅ DO: Use theme functions**
```python
button = QPushButton("Click Me")
button.setStyleSheet(theme.button_style("primary"))
```

**❌ DON'T: Write inline CSS**
```python
# BAD: Hardcoded colors and styles
button.setStyleSheet("""
    background-color: #4a5058;
    border: none;
    padding: 10px 20px;
    font-size: 14px;
""")
```

**❌ DON'T: Reference COLORS directly for styling**
```python
# BAD: Mixing color constants with inline CSS
button.setStyleSheet(f"color: {self.COLORS['text_light']}; font-size: 14px;")
```

### Available Theme Functions

#### Layout Components
- `panel_style()` - QGroupBox panels with titles
- `tab_widget_style()` - Tabbed widget styling
- `header_style()` - Header widget (top section)
- `footer_style()` - Footer widget (bottom section)
- `toggle_section_style()` - Toggle controls section
- `toggle_group_style()` - Grouped toggle buttons
- `scroll_area_style()` - Scrollable areas

#### Interactive Elements
- `button_style(style_type)` - Primary/secondary/toggle buttons
- `text_edit_style()` - Read-only text areas
- `line_edit_style()` - Editable text fields

#### Data Display
- `progressbar_style(style_type)` - Progress bars (info/accent/warn)
- `table_widget_style()` - Tabular data displays
- `metric_box_style()` - Metric display boxes
- `metric_value_style(color)` - Large metric values
- `metric_title_style()` - Metric description labels
- `chart_label_style(min_height=150, margin_top=0)` - Placeholder charts

#### Labels & Text
- `hero_label_style()` - Large hero text (24px, bold)
- `meta_label_style()` - Medium metadata text (14px)
- `secondary_label_style()` - Small secondary text (12px, #aaa)
- `summary_label_style()` - Summary labels (13px)
- `large_label_style()` - Large values (20px, bold)
- `text_light_color_style()` - Just text_light color
- `accent_green_color_style()` - Just accent_green color
- `accent_red_color_style()` - Just accent_red color
- `accent_green_medium_label_style()` - Medium green text
- `accent_red_hero_label_style()` - Large red hero text
- `accent_green_small_label_style()` - Small green text

#### Application
- `apply_dark_palette(app)` - Apply dark theme to QApplication

## Color System

### Core Colors (from hud_mockup.html)
```python
COLORS = {
    "bg_dark": "#1e1f23",      # Main background
    "panel_bg": "#272930",     # Panel backgrounds
    "text_light": "#e0e0e0",   # Primary text
    "accent_green": "#4caf50", # Success/active states
    "accent_red": "#f44336",   # Error/inactive states
    "border_color": "#3a3d41", # Borders and separators
    "hover_bg": "#3c3f46",     # Hover states
    "info_blue": "#2979ff",    # Informational elements
    "shimmer_yellow": "#f9a825", # Shimmer-specific
}
```

### Specialized Color Groups
```python
PROGRESSBAR_COLORS = {
    "info": COLORS["info_blue"],
    "accent": "#8fd3d1",   # Cyan for building progress
    "warn": "#ffb14a",     # Orange for upgrade progress
}

BUTTON_PRIMARY_BG = "#4a5058"
BUTTON_PRIMARY_HOVER = "#5d636b"
BUTTON_SECONDARY_BG = "#3a3d41"
BUTTON_SECONDARY_HOVER = "#4a5058"
BUTTON_TOGGLE_BG = "#3a3d41"
BUTTON_TOGGLE_HOVER = "#3c3f46"
BUTTON_TOGGLE_CHECKED_BG = "#4caf50"
BUTTON_TOGGLE_CHECKED_TEXT = "#0f1e0c"
```

## Adding New Styles

### When to Add a New Theme Function

Add a new function to `theme.py` when:

1. **New UI Component Type**: A new kind of widget not covered by existing functions
2. **Variant with Parameters**: Existing style needs configurable parameters (like `chart_label_style()`)
3. **Repeated Pattern**: Same CSS pattern appears 3+ times in `hud_qt.py`

### Creating a New Theme Function

1. **Define at appropriate abstraction level**:
   ```python
   def list_widget_style(colors=COLORS):
       """Return CSS style for QListWidget."""
       return f"""
           QListWidget {{
               background-color: {colors['bg_dark']};
               color: {colors['text_light']};
               border: 1px solid {colors['border_color']};
           }}
       """
   ```

2. **Add parameters for configurability**:
   ```python
   def custom_label_style(color, font_size=12, bold=False):
       """Return CSS style for custom labels."""
       weight = "bold" if bold else "normal"
       return f"color: {color}; font-size: {font_size}px; font-weight: {weight};"
   ```

3. **Update imports in `hud_qt.py`** (already imported via `from .styles import theme`)

## Common Patterns

### Combining Styles
```python
# Add extra styling to a base style
label.setStyleSheet(theme.secondary_label_style() + " margin-top: 10px;")
```

### Conditional Styling
```python
# Use Python logic, not CSS logic
color = theme.COLORS['accent_green'] if active else theme.COLORS['accent_red']
label.setStyleSheet(f"color: {color}; font-size: 14px;")
```

### Dynamic Content with Static Styling
```python
# Good: Style stays in theme, content changes
label.setText(f"Value: {dynamic_value}")
label.setStyleSheet(theme.secondary_label_style())

# Bad: Mixing content and styling
label.setStyleSheet(f"color: #aaa; content: 'Value: {dynamic_value}';")
```

## Maintenance Guidelines

### When Modifying Styles

1. **Change in One Place**: Update `theme.py`, not `hud_qt.py`
2. **Test All Usages**: Use `grep` to find all usages of the function
3. **Consider Backward Compatibility**: Add parameters instead of breaking changes

### When Adding UI Components

1. **Check for Existing Functions**: Don't reinvent the wheel
2. **Follow Naming Conventions**: `{component}_{style}_style()`
3. **Add Documentation**: Include docstring with example usage

### Code Review Checklist

- [ ] No inline `setStyleSheet()` with hardcoded colors
- [ ] No direct `self.COLORS` references in styling
- [ ] Theme functions used consistently
- [ ] New styles added to `theme.py` not `hud_qt.py`
- [ ] Function names follow conventions

## Migration from Legacy Code

If you encounter legacy inline CSS:

1. **Extract to `theme.py`**: Create appropriate function
2. **Replace All Instances**: Update all usages in `hud_qt.py`
3. **Remove Helper Methods**: Delete `_button_style()`, `_panel_style()` etc.
4. **Test Thoroughly**: Ensure visual appearance unchanged

## Testing

Run the Qt HUD tests to ensure styling works:
```bash
python -m pytest -q tests/ -k qt
```

Check for syntax errors:
```bash
python -m py_compile qt_hud/hud_qt.py
```

## References

- [PySide6 Style Sheets Reference](https://doc.qt.io/qt-6/stylesheet-reference.html)
- [Original HUD Mockup](hud_mockup.html) - Color source
- [REFACTOR_LOG.md](../REFACTOR_LOG.md) - Refactoring history

---

*Last Updated: April 12, 2026*  
*Maintainer: Qt HUD Development Team*