# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

project_root = Path(SPECPATH)
cookie_mod_src = project_root / 'cookie_shimmer_bridge_mod'
qt_hud_src = project_root / 'qt_hud'

# Collect all keyboard module files and data
keyboard_datas, keyboard_binaries, keyboard_hiddenimports = collect_all('keyboard')

# Collect pyautogui and its dependencies
pyautogui_datas, pyautogui_binaries, pyautogui_hiddenimports = collect_all('pyautogui')

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=keyboard_binaries + pyautogui_binaries,
    datas=[
        (str(cookie_mod_src), 'cookie_shimmer_bridge_mod'),
        (str(qt_hud_src), 'qt_hud'),
    ] + keyboard_datas + pyautogui_datas,
    hiddenimports=[
        'keyboard',
        'keyboard._keyboard',
        'win32api',
        'win32gui',
        'win32con',
        'win32process',
        'win32ts',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ] + keyboard_hiddenimports + pyautogui_hiddenimports,
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
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)