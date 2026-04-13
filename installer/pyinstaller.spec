# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

project_root = Path(SPECPATH).parent.resolve()
cookie_mod_src = project_root / 'cookie_shimmer_bridge_mod'
qt_hud_src = project_root / 'qt_hud'

# Get keyboard module path from site-packages
import keyboard
keyboard_path = Path(keyboard.__file__).parent
keyboard_datas = [(str(keyboard_path), 'keyboard')]

# Get pyautogui module path from site-packages
import pyautogui
pyautogui_path = Path(pyautogui.__file__).parent
pyautogui_datas = [(str(pyautogui_path), 'pyautogui')]

# Get all keyboard submodules explicitly
keyboard_submodules = collect_submodules('keyboard')

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(cookie_mod_src), 'cookie_shimmer_bridge_mod'),
        (str(qt_hud_src), 'qt_hud'),
    ] + keyboard_datas + pyautogui_datas,
    hiddenimports=[
        'keyboard',
        'keyboard._keyboard',
        'keyboard._winkeyboard',
        'keyboard._winmouse',
        'keyboard._nixkeyboard',
        'keyboard._nixmouse',
        'keyboard._generic',
        'keyboard._canonical_names',
        'keyboard.mouse',
        'win32api',
        'win32gui',
        'win32con',
        'win32process',
        'win32ts',
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'win32file',
        'win32pipe',
        'win32net',
        'win32netcon',
        'win32security',
        'ntsecuritycon',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ] + keyboard_submodules,
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=True,
    name='CookieClickerAutoClicker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)