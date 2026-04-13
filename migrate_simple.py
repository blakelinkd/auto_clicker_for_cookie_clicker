#!/usr/bin/env python3
"""
Migrate simple theme functions to use template loader.
"""
import re
import sys
from pathlib import Path

theme_path = Path(__file__).parent / "qt_hud" / "styles" / "theme.py"

with open(theme_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find function definitions with simple signature
i = 0
new_lines = []
while i < len(lines):
    line = lines[i]
    # Look for def with colors=COLORS parameter
    match = re.match(r'def (\w+)\((colors=COLORS|colors=COLORS, .*)\):', line.strip())
    if match:
        func_name = match.group(1)
        # Check if function already uses render_template (skip)
        # Look ahead a few lines for render_template
        skip = False
        for j in range(i, min(i+10, len(lines))):
            if 'render_template' in lines[j]:
                skip = True
                break
        if skip:
            new_lines.append(line)
            i += 1
            continue
        
        # Find the function block until the next def or end of file
        start = i
        # Find the line with triple quotes after return
        # We'll assume the function ends at the line with triple quotes alone
        # Actually we'll replace the whole function body until the line before next def
        # Simpler: replace from start to line containing return f"""...""" (single line)
        # We'll just replace the whole function with a simple render_template call.
        # We need to preserve docstring.
        # Let's capture the docstring lines (if any)
        docstring_lines = []
        j = i + 1
        while j < len(lines) and lines[j].strip().startswith('"""'):
            # multi-line docstring
            docstring_lines.append(lines[j])
            j += 1
            while j < len(lines) and not lines[j].strip().endswith('"""'):
                docstring_lines.append(lines[j])
                j += 1
            if j < len(lines) and lines[j].strip().endswith('"""'):
                docstring_lines.append(lines[j])
                j += 1
                break
        # Now find the return line
        while j < len(lines) and not lines[j].strip().startswith('return'):
            j += 1
        if j >= len(lines):
            # function not found, skip
            new_lines.append(line)
            i += 1
            continue
        return_line = j
        # Find end of function (next blank line or next def)
        end = return_line + 1
        while end < len(lines) and not lines[end].strip().startswith('def '):
            end += 1
        # Replace lines[start:end] with new function
        # Build new function lines
        new_func = []
        new_func.append(line)
        new_func.extend(docstring_lines)
        new_func.append(f'    return render_template("{func_name}", **colors)\n')
        # Skip the old body
        i = end
        new_lines.extend(new_func)
        print(f"Migrated {func_name}")
    else:
        new_lines.append(line)
        i += 1

# Write back
with open(theme_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Migration complete.")