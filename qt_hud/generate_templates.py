#!/usr/bin/env python3
"""
Generate templates.qss from theme.py functions.
"""
import re
import ast
import sys
from pathlib import Path

theme_path = Path(__file__).parent / "styles" / "theme.py"
output_path = theme_path.parent / "templates.qss"

# Read theme.py source
with open(theme_path, "r", encoding="utf-8") as f:
    source = f.read()

# Parse AST to find function definitions
tree = ast.parse(source)

# Collect function names and their source lines
functions = {}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        start_line = node.lineno - 1  # 0-indexed
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        # Get function source lines
        lines = source.splitlines()[start_line:end_line]
        functions[node.name] = "\n".join(lines)

print(f"Found {len(functions)} functions")

# Extract CSS from functions that return f-strings
template_sections = {}
for name, src in functions.items():
    # Look for return statement with triple-quoted f-string
    # Simple regex: return f""".*?""" with s flag (dot matches newline)
    pattern = r'return f"""([\s\S]*?)"""'
    match = re.search(pattern, src)
    if match:
        css = match.group(1)
        # Replace f-string placeholders with template placeholders
        # pattern: {colors['key']} or {colors["key"]}
        def replace_color(match):
            key = match.group(1) or match.group(2)
            return f"{{{{{key}}}}}"
        css = re.sub(r"{colors\[('|\")(\w+)('|\")\]}", replace_color, css)
        # Also replace direct color constants like {BUTTON_PRIMARY_BG}
        css = re.sub(r"{(\w+)}", r"{{\1}}", css)
        template_sections[name] = css.strip()
        print(f"  - {name}: {len(css)} chars")

# Write templates.qss
with open(output_path, "w", encoding="utf-8") as f:
    f.write("/* Qt HUD CSS Templates */\n")
    f.write("/* This file is auto-generated. Edit theme.py and regenerate. */\n\n")
    for name, css in template_sections.items():
        f.write(f"/* {name} */\n")
        f.write(css)
        f.write("\n\n")

print(f"Written to {output_path}")