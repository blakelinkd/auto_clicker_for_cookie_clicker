#!/usr/bin/env python3
"""
Extract CSS templates from theme.py functions and write to qss/ directory.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from styles.theme import COLORS

theme_path = Path(__file__).parent / "styles" / "theme.py"
with open(theme_path, "r", encoding="utf-8") as f:
    source = f.read()

# Find function definitions and their bodies
function_pattern = r'def (\w+)\s*\([^)]*\):\s*"""[^"]*"""\s*return f"""([\s\S]*?)"""'
# This pattern is naive but works for our specific formatting

# Better: find all functions and their return statements
lines = source.splitlines()
functions = {}
current_func = None
current_body = []
in_function = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("def ") and "(" in stripped and "):" in stripped:
        if current_func is not None:
            functions[current_func] = "\n".join(current_body)
        # Start new function
        func_name = stripped[4:stripped.index("(")].strip()
        current_func = func_name
        current_body = []
        in_function = True
    elif in_function:
        if stripped.startswith("def "):
            # Another function without blank line? shouldn't happen
            continue
        current_body.append(line)
        # If we encounter a blank line after return? Not reliable
        # We'll stop when we hit a line that is not indented (i.e., at column 0)
        # but functions are nested under class? No, they're top-level.
        # Actually we can stop when we see a line with same indentation as def (0)
        # but all function bodies are indented. We'll rely on empty line detection later.
    else:
        pass

# Add last function
if current_func is not None:
    functions[current_func] = "\n".join(current_body)

print(f"Found {len(functions)} functions")

# Now extract return f"""...""" from each body
for name, body in list(functions.items()):
    # Look for return f""" pattern (triple quotes)
    match = re.search(r'return f"""([\s\S]*?)"""', body)
    if not match:
        # Maybe return f"..." single line
        match = re.search(r'return f"([^"]*)"', body)
    if not match:
        # Maybe return """...""" without f (plain string)
        match = re.search(r'return """([\s\S]*?)"""', body)
    if not match:
        match = re.search(r'return "([^"]*)"', body)
    if match:
        css = match.group(1)
        # Remove leading/trailing whitespace
        css = css.strip()
        # Replace f-string placeholders
        # Pattern: {colors['key']} or {colors["key"]}
        def replace_color(match):
            key = match.group(2)
            return f"{{{key}}}"
        css = re.sub(r"{colors\[('|\")(\w+)('|\")\]}", replace_color, css)
        # Replace direct constants
        css = re.sub(r"{(\w+)}", r"{\1}", css)
        functions[name] = css
    else:
        # No CSS found, maybe function returns something else
        print(f"  - {name}: no CSS found")
        del functions[name]

# Write each template to qss directory
qss_dir = Path(__file__).parent / "styles" / "qss"
qss_dir.mkdir(exist_ok=True)

for name, css in functions.items():
    if not css:
        continue
    # Ensure CSS braces are correct (they should be single braces)
    # But CSS itself contains braces for selectors. We need to keep them.
    # The CSS string already has double braces for selectors? Let's check.
    # In source, CSS selectors are written as QGroupBox {{ ... }} with double braces
    # because they are inside an f-string. The raw string has single braces.
    # However our regex extracted the content inside the f-string literal, which
    # has double braces escaped. We need to convert double braces to single.
    # Replace '{{' with '{' and '}}' with '}'
    css = css.replace("{{", "{").replace("}}", "}")
    # Write to file
    file_path = qss_dir / f"{name}.qss"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(css)
    print(f"  - {name}: wrote {len(css)} chars to {file_path}")

print("Done.")