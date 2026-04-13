"""
Template loader for Qt HUD CSS templates.

Loads .qss template files from the 'qss' directory and substitutes color placeholders.
"""
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# Import theme colors
from .constants import COLORS, PROGRESSBAR_COLORS, BUTTON_PRIMARY_BG, BUTTON_PRIMARY_HOVER, BUTTON_SECONDARY_BG, BUTTON_SECONDARY_HOVER, BUTTON_TOGGLE_BG, BUTTON_TOGGLE_HOVER, BUTTON_TOGGLE_CHECKED_BG, BUTTON_TOGGLE_CHECKED_TEXT

if getattr(sys, 'frozen', False):
    TEMPLATES_DIR = Path(sys._MEIPASS) / "qt_hud" / "styles" / "qss"
else:
    TEMPLATES_DIR = Path(__file__).parent / "qss"

# Cache loaded templates
_template_cache = {}

def load_template(template_name):
    """Load a template file, cache it, and return raw content."""
    if template_name in _template_cache:
        return _template_cache[template_name]
    
    template_path = TEMPLATES_DIR / f"{template_name}.qss"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    _template_cache[template_name] = content
    log.debug("Loaded template %s (%d chars)", template_name, len(content))
    return content

def render_template(template_name, **kwargs):
    """Load template and substitute placeholders with provided values.
    
    Placeholders are in the format %key%. Missing keys will be looked up
    from the theme color dictionaries.
    """
    template = load_template(template_name)
    
    # Prepare substitution dictionary
    subs = {}
    subs.update(COLORS)
    subs.update(PROGRESSBAR_COLORS)
    # Add button constants
    subs.update({
        "BUTTON_PRIMARY_BG": BUTTON_PRIMARY_BG,
        "BUTTON_PRIMARY_HOVER": BUTTON_PRIMARY_HOVER,
        "BUTTON_SECONDARY_BG": BUTTON_SECONDARY_BG,
        "BUTTON_SECONDARY_HOVER": BUTTON_SECONDARY_HOVER,
        "BUTTON_TOGGLE_BG": BUTTON_TOGGLE_BG,
        "BUTTON_TOGGLE_HOVER": BUTTON_TOGGLE_HOVER,
        "BUTTON_TOGGLE_CHECKED_BG": BUTTON_TOGGLE_CHECKED_BG,
        "BUTTON_TOGGLE_CHECKED_TEXT": BUTTON_TOGGLE_CHECKED_TEXT,
    })
    # Override with kwargs
    subs.update(kwargs)
    
    # Perform substitution
    result = template
    for key, value in subs.items():
        placeholder = f"%{key}%"
        if placeholder in result:
            result = result.replace(placeholder, str(value))
    return result

def get_available_templates():
    """Return list of available template names (without .qss extension)."""
    if not TEMPLATES_DIR.exists():
        return []
    return [p.stem for p in TEMPLATES_DIR.glob("*.qss")]