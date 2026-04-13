#!/usr/bin/env python3
"""
Build script for Cookie Clicker Auto-Clicker installer.

This script automates:
1. PyInstaller build to freeze the Python app
2. Inno Setup compilation to create the Windows installer

Usage:
    python build_installer.py

Requirements:
    pip install pyinstaller
    Download and install Inno Setup from https://jrsoftware.org/isdl.php
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
INSTALLER_OUTPUT_DIR = DIST_DIR / "installer"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "pyinstaller.spec"
INNO_SETUP_SCRIPT = PROJECT_ROOT / "installer.iss"


def clean_build_dirs():
    """Remove old build artifacts."""
    print("Cleaning old build directories...")
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
    INSTALLER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_pyinstaller():
    """Run PyInstaller to freeze the Python application."""
    print("\n=== Running PyInstaller ===")
    
    if not SPEC_FILE.exists():
        print(f"ERROR: Spec file not found: {SPEC_FILE}")
        return False
    
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        print("PyInstaller build completed successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("ERROR: PyInstaller build failed!")
        print(e.stdout)
        print(e.stderr)
        return False


def check_inno_setup():
    """Check if Inno Setup compiler is available."""
    inno_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    
    for path in inno_paths:
        if path.exists():
            return path
    
    inno_path = shutil.which("iscc")
    if inno_path:
        return Path(inno_path)
    
    return None


def run_inno_setup():
    """Run Inno Setup compiler to create the installer."""
    print("\n=== Running Inno Setup ===")
    
    iscc_path = check_inno_setup()
    if not iscc_path:
        print("WARNING: Inno Setup not found. Skipping installer creation.")
        print("To build the installer, install Inno Setup from https://jrsoftware.org/isdl.php")
        return False
    
    if not INNO_SETUP_SCRIPT.exists():
        print(f"ERROR: Inno Setup script not found: {INNO_SETUP_SCRIPT}")
        return False
    
    pyinstaller_output = DIST_DIR / "main"
    if not pyinstaller_output.exists():
        print(f"ERROR: PyInstaller output not found: {pyinstaller_output}")
        print("Run PyInstaller first!")
        return False
    
    cmd = [str(iscc_path), str(INNO_SETUP_SCRIPT)]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        print("Inno Setup compilation completed successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("ERROR: Inno Setup compilation failed!")
        print(e.stdout)
        print(e.stderr)
        return False


def verify_build():
    """Verify the build outputs exist."""
    print("\n=== Verifying Build ===")
    
    pyinstaller_exe = DIST_DIR / "main" / "CookieClickerAutoClicker.exe"
    if pyinstaller_exe.exists():
        print(f"✓ Frozen exe: {pyinstaller_exe}")
    else:
        print(f"✗ Frozen exe not found: {pyinstaller_exe}")
    
    installer_exe = INSTALLER_OUTPUT_DIR / "CookieClickerAutoClicker_Setup.exe"
    if installer_exe.exists():
        size_mb = installer_exe.stat().st_size / (1024 * 1024)
        print(f"✓ Installer: {installer_exe} ({size_mb:.1f} MB)")
    else:
        print(f"✗ Installer not found: {installer_exe}")


def main():
    """Main build pipeline."""
    print("=" * 60)
    print("Cookie Clicker Auto-Clicker Installer Build")
    print("=" * 60)
    
    if not sys.platform.startswith("win"):
        print("ERROR: This build script only works on Windows.")
        sys.exit(1)
    
    clean_build_dirs()
    
    if not run_pyinstaller():
        print("\nBuild FAILED at PyInstaller stage.")
        sys.exit(1)
    
    run_inno_setup()
    
    verify_build()
    
    print("\n" + "=" * 60)
    print("Build Complete!")
    print("=" * 60)
    print(f"\nFrozen exe: {DIST_DIR / 'main' / 'CookieClickerAutoClicker.exe'}")
    print(f"Installer: {INSTALLER_OUTPUT_DIR / 'CookieClickerAutoClicker_Setup.exe'}")


if __name__ == "__main__":
    main()