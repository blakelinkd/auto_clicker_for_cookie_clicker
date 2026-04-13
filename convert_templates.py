#!/usr/bin/env python3
"""
Convert theme.py functions to template files with %placeholders%.
"""
import re
import sys
from pathlib import Path

theme_path = Path(__file__).parent / "qt_hud" / "styles" / "theme.py"
qss_dir = Path(__file__).parent / "qt_hud" / "styles" / "qss"

# Read theme.py source
with open(theme_path, "r", encoding="utf-8") as f:
    source = f.read()

# Find all function definitions with triple-quoted return strings
# Pattern: def func_name(...): ... return f"""..."""
# We'll use a simpler approach: split by 'def ' and parse each function block.
lines = source.splitlines()
functions = {}
current_func = None
func_lines = []
for i, line in enumerate(lines):
    if line.startswith("def "):
        if current_func is not None:
            functions[current_func] = "\n".join(func_lines)
        # Start new function
        match = re.match(r'def (\w+)', line)
        if match:
            current_func = match.group(1)
            func_lines = [line]
        else:
            current_func = None
    elif current_func is not None:
        func_lines.append(line)
# Add last function
if current_func is not None:
    functions[current_func] = "\n".join(func_lines)

print(f"Found {len(functions)} functions")

# Process each function
for name, body in list(functions.items()):
    # Find return f"""...""" (triple quotes)
    match = re.search(r'return f"""([\s\S]*?)"""', body)
    if not match:
        # Try return f"..." (single line)
        match = re.search(r'return f"([^"]*)"', body)
    if not match:
        # Try return """...""" (plain triple quotes)
        match = re.search(r'return """([\s\S]*?)"""', body)
    if not match:
        # Try return "..." (plain single line)
        match = re.search(r'return "([^"]*)"', body)
    if not match:
        # Skip functions without CSS
        print(f"  - {name}: no CSS found")
        continue
    
    css = match.group(1)
    # Remove leading/trailing whitespace
    css = css.strip()
    # Replace f-string placeholders with %placeholders%
    # Pattern: {colors['key']} or {colors["key"]}
    def replace_color(match):
        key = match.group(2)
        return f"%{key}%"
    css = re.sub(r"{colors\[('|\")(\w+)('|\")\]}", replace_color, css)
    # Replace direct constants like {BUTTON_PRIMARY_BG}
    css = re.sub(r"{(\w+)}", r"%\1%", css)
    # Note: there may be leftover {color} from metric_value_style (parameter)
    # We'll keep them as %color% (already replaced)
    
    # Ensure CSS braces are single (they already are in literal)
    # But the literal had double braces because inside f-string. Need to dedouble.
    css = css.replace("{{", "{").replace("}}", "}")
    
    functions[name] = css

# Write each template to qss directory
qss_dir.mkdir(exist_ok=True)

# Delete existing .qss files
for f in qss_dir.glob("*.qss"):
    f.unlink()

for name, css in functions.items():
    if not css:
        continue
    file_path = qss_dir / f"{name}.qss"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(css)
    print(f"  - {name}: wrote {len(css)} chars to {file_path}")

print("Done.")