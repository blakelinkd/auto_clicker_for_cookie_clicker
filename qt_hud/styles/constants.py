"""
Color constants for Qt HUD theme.
"""

# Color palette from hud_mockup.html
COLORS = {
    "bg_dark": "#1e1f23",
    "panel_bg": "#272930",
    "text_light": "#e0e0e0",
    "accent_green": "#4caf50",
    "accent_red": "#f44336",
    "border_color": "#3a3d41",
    "hover_bg": "#3c3f46",
    "info_blue": "#2979ff",
    "shimmer_yellow": "#f9a825",
}

# Additional colors used in progress bars
PROGRESSBAR_COLORS = {
    "info": COLORS["info_blue"],
    "accent": "#8fd3d1",
    "warn": "#ffb14a",
}

# Button style colors (hardcoded in _button_style)
BUTTON_PRIMARY_BG = "#4a5058"
BUTTON_PRIMARY_HOVER = "#5d636b"
BUTTON_SECONDARY_BG = "#3a3d41"
BUTTON_SECONDARY_HOVER = "#4a5058"
BUTTON_TOGGLE_BG = "#3a3d41"
BUTTON_TOGGLE_HOVER = "#3c3f46"
BUTTON_TOGGLE_CHECKED_BG = "#4caf50"
BUTTON_TOGGLE_CHECKED_TEXT = "#0f1e0c"