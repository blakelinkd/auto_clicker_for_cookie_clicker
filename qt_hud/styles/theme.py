"""
Centralized theme system for Qt HUD dashboard.

## IMPORTANT: STYLE GUIDE
All developers MUST read and follow the style guide before modifying this module:
See: `QT_HUD_STYLE_GUIDE.md` in the parent directory.

## ARCHITECTURE OVERVIEW
This module implements a separation of concerns: CSS styling is defined here,
while UI logic resides in `hud_qt.py`. This ensures:
1. Single source of truth for colors and styles
2. Consistent styling across all UI components
3. Easy theme customization and maintenance
4. Clean separation of styling from business logic

## USAGE GUIDELINES
✅ DO:
- Import this module: `from .styles import theme`
- Use theme functions: `widget.setStyleSheet(theme.button_style("primary"))`
- Add new theme functions for new UI component types
- Update colors here, not in hud_qt.py

❌ DO NOT:
- Write inline CSS in hud_qt.py
- Reference self.COLORS directly for styling
- Create helper styling methods in hud_qt.py
- Hardcode colors or style values outside this module

## COLOR SYSTEM
Colors are defined in the COLORS dictionary, sourced from hud_mockup.html.
Specialized color groups (PROGRESSBAR_COLORS, BUTTON_* constants) provide
semantic names for specific use cases.

## ADDING NEW STYLES
When adding new UI components:
1. Check if an existing theme function can be used or extended
2. Create new function with descriptive name: `{component}_{style}_style()`
3. Add comprehensive docstring with usage example
4. Add parameters for configurability when appropriate
5. Update all usages in hud_qt.py to use the new function
"""
import logging
from .constants import (
    COLORS,
    PROGRESSBAR_COLORS,
    BUTTON_PRIMARY_BG,
    BUTTON_PRIMARY_HOVER,
    BUTTON_SECONDARY_BG,
    BUTTON_SECONDARY_HOVER,
    BUTTON_TOGGLE_BG,
    BUTTON_TOGGLE_HOVER,
    BUTTON_TOGGLE_CHECKED_BG,
    BUTTON_TOGGLE_CHECKED_TEXT,
)
from .template_loader import render_template

log = logging.getLogger(__name__)




def panel_style(colors=COLORS):
    """Return CSS style for QGroupBox panels."""
    return render_template("panel_style", **colors)


def progressbar_style(style_type, colors=COLORS):
    """Return CSS style for QProgressBar."""
    bar_colors = PROGRESSBAR_COLORS.copy()
    color = bar_colors.get(style_type, colors["info_blue"])
    return render_template("progressbar_style", **colors, color=color)


def button_style(style_type):
    """Return CSS style for QPushButton.
    
    style_type: "primary", "secondary", or "toggle"
    """
    if style_type == "primary":
        return render_template("button_primary", **COLORS)
    elif style_type == "secondary":
        return render_template("button_secondary", **COLORS)
    elif style_type == "toggle":
        return render_template("button_toggle", **COLORS)
    return ""


def checkbox_style(colors=COLORS):
    """Return CSS style for QCheckBox."""
    return f"""
        QCheckBox {{
            color: {colors['text_light']};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors['accent_green']};
            border: 1px solid {colors['accent_green']};
        }}
        QCheckBox::indicator:unchecked {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
        }}
    """


def tab_widget_style(colors=COLORS):
    """Return CSS style for QTabWidget."""
    return render_template("tab_widget_style", **colors)


def header_style(colors=COLORS):
    """Return CSS style for header widget."""
    return render_template("header_style", **colors)
def toggle_section_style(colors=COLORS):
    """Return CSS style for toggle section."""
    return render_template("toggle_section_style", **colors)
def toggle_group_style(colors=COLORS):
    """Return CSS style for toggle group widget."""
    return render_template("toggle_group_style", **colors)
def toggle_group_label_style(colors=COLORS):
    """Return CSS style for toggle group label."""
    return render_template("toggle_group_label_style", **colors)
def footer_style(colors=COLORS):
    """Return CSS style for footer widget."""
    return render_template("footer_style", **colors)
def scroll_area_style(colors=COLORS):
    """Return CSS style for QScrollArea."""
    return render_template("scroll_area_style", **colors)
def text_edit_style(colors=COLORS, min_height=None):
    """Return CSS style for QTextEdit.
    
    Args:
        colors: Color dictionary.
        min_height: Optional minimum height in pixels.
    """
    style = f"""
        background-color: {colors['bg_dark']};
        color: {colors['text_light']};
        border: 1px solid {colors['border_color']};
        border-radius: 4px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        padding: 10px;
    """
    if min_height is not None:
        style += f" min-height: {min_height}px;"
    return style
def line_edit_style(colors=COLORS):
    """Return CSS style for QLineEdit."""
    return render_template("line_edit_style", **colors)
def metric_value_style(color):
    """Return CSS style for metric value label."""
    return f"""
        font-size: 24px;
        font-weight: bold;
        color: {color};
        margin-bottom: 5px;
    """


def metric_title_style():
    """Return CSS style for metric title label."""
    return """
        font-size: 12px;
        color: #aaa;
    """

def metric_box_style(colors=COLORS):
    """Return CSS style for metric box."""
    return render_template("metric_box_style", **colors)

def table_widget_style(colors=COLORS):
    """Return CSS style for QTableWidget."""
    return render_template("table_widget_style", **colors)
def hero_label_style(colors=COLORS):
    """Return CSS style for hero label (large, bold, green)."""
    return render_template("hero_label_style", **colors)
def meta_label_style(colors=COLORS):
    """Return CSS style for meta label."""
    return render_template("meta_label_style", **colors)
def secondary_label_style():
    """Return CSS style for secondary label (small, muted)."""
    return """
        font-size: 12px;
        color: #aaa;
    """

def chart_label_style(colors=COLORS, min_height=None, margin_top=None):
    """Return CSS style for chart label."""
    return render_template("chart_label_style", **colors, min_height=min_height, margin_css=f"margin-top: {margin_top}px;" if margin_top else "")

def text_light_color_style(colors=COLORS):
    """Return CSS style for text light color."""
    return f"color: {colors['text_light']};"


def accent_green_color_style(colors=COLORS):
    """Return CSS style for accent green color."""
    return render_template("accent_green_color_style", **colors)
def medium_label_style(colors=COLORS, margin_top=None):
    """Return CSS style for medium-sized label (14px, text light).
    
    Args:
        colors: Color dictionary.
        margin_top: Optional top margin in pixels.
    """
    style = f"color: {colors['text_light']}; font-size: 14px;"
    if margin_top is not None:
        style += f" margin-top: {margin_top}px;"
    return style
def accent_green_medium_label_style(colors=COLORS, margin_top=None):
    """Return CSS style for medium-sized label with accent green.
    
    Args:
        colors: Color dictionary.
        margin_top: Optional top margin in pixels.
    """
    style = f"color: {colors['accent_green']}; font-size: 14px;"
    if margin_top is not None:
        style += f" margin-top: {margin_top}px;"
    return style
def summary_label_style(colors=COLORS):
    """Return CSS style for summary label (13px, text light)."""
    return f"color: {colors['text_light']}; font-size: 13px;"


def large_label_style(colors=COLORS):
    """Return CSS style for large label (20px, bold, text light)."""
    return render_template("large_label_style", **colors)
def accent_red_color_style(colors=COLORS):
    """Return CSS style for accent red color."""
    return f"color: {colors['accent_red']};"


def accent_red_hero_label_style(colors=COLORS):
    """Return CSS style for hero label with accent red."""
    return render_template("accent_red_hero_label_style", **colors)
def accent_green_small_label_style(colors=COLORS):
    """Return CSS style for small label with accent green."""
    return f"color: {colors['accent_green']}; font-size: 12px;"


def shimmer_yellow_color_style(colors=COLORS):
    """Return CSS style for shimmer yellow color."""
    return render_template("shimmer_yellow_color_style", **colors)
def shimmer_yellow_small_label_style(colors=COLORS):
    """Return CSS style for small label with shimmer yellow."""
    return f"color: {colors['shimmer_yellow']}; font-size: 12px;"


def apply_dark_palette(app, colors=COLORS):
    """Apply dark color palette to the QApplication."""
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtCore import Qt
    
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(colors["bg_dark"]))
    palette.setColor(QPalette.WindowText, QColor(colors["text_light"]))
    palette.setColor(QPalette.Base, QColor(colors["panel_bg"]))
    palette.setColor(QPalette.AlternateBase, QColor(colors["bg_dark"]))
    palette.setColor(QPalette.ToolTipBase, QColor(colors["panel_bg"]))
    palette.setColor(QPalette.ToolTipText, QColor(colors["text_light"]))
    palette.setColor(QPalette.Text, QColor(colors["text_light"]))
    palette.setColor(QPalette.Button, QColor(colors["panel_bg"]))
    palette.setColor(QPalette.ButtonText, QColor(colors["text_light"]))
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(colors["info_blue"]))
    palette.setColor(QPalette.Highlight, QColor(colors["info_blue"]))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)