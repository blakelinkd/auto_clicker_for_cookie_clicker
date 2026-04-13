# PyInstaller Specification

## Overview
This document details the PyInstaller configuration for freezing the Cookie Clicker Auto-Clicker bot into a standalone Windows executable.

## Spec File Location
`pyinstaller.spec` (in repository root)

## Analysis Configuration

```python
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('cookie_shimmer_bridge_mod', 'cookie_shimmer_bridge_mod'),
    ],
    hiddenimports=[
        'keyboard',
        'pywin32',
        'pywin32.api',
        'pywin32.api_time',
        'pywin32comext',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
```

## Hidden Imports
The following packages need explicit hidden imports because they are imported dynamically:
- `keyboard` - keyboard hooks
- `pywin32` - Windows API bindings
- `pywin32.api` - COM API
- `pywin32.api_time` - time API
- `pywin32comext` - extended COM
- `PySide6` - Qt bindings (core, gui, widgets)

## Data Files
Include the following as additional files:
- `cookie_shimmer_bridge_mod/` - mod files for game integration

## Exclusions
Exclude test directories and unnecessary packages:
- `tests/`
- `__pycache__/`
- `.git/`

## Output Configuration

### Console Window
- **WindowedConfig** - Hide console window (GUI app)
- **ConsoleIcon** - Use appropriate icon

### One-file Mode
- **onefile=True** - Single executable output
- **name='CookieClickerAutoClicker'** - Output name

## Build Command

```bash
python -m PyInstaller main.spec --clean --noconfirm
```

## Testing

1. Run PyInstaller build
2. Execute `dist/CookieClickerAutoClicker.exe`
3. Verify HUD appears
4. Test hotkey registration
5. Test config save/load
6. Test mod file sync

## Known Issues

### Antivirus False Positives
PyInstaller-packaged executables may trigger antivirus warnings. This is common with keyboard-hook software. Mitigations:
- Code-sign the executable (optional)
- Document in README

### Missing Imports
If modules are missing at runtime:
- Add to `hiddenimports` list
- Use `--collect-all package` for packages with submodules

## Version Information
- Created: 2026-04-13
- Updated: 2026-04-13