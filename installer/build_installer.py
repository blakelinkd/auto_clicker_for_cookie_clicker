#!/usr/bin/env python3
"""
Build script for Cookie Clicker Auto-Clicker installer.

This script automates:
1. PyInstaller build to freeze the Python app
2. Inno Setup compilation to create the Windows installer

Usage:
    python build_installer.py              # Build everything
    python build_installer.py --pyinstaller-only  # Build only the frozen exe
    python build_installer.py --installer-only    # Build only the installer (requires frozen exe)

Requirements:
    pip install pyinstaller
    Download and install Inno Setup from https://jrsoftware.org/isdl.php
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "installer" / "pyinstaller.spec"
INNO_SETUP_SCRIPT = PROJECT_ROOT / "installer" / "installer.iss"

INNO_INSTALL_URL = "https://jrsoftware.org/isdl.php"


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


def check_dependencies():
    """Check if required build dependencies are installed."""
    errors = []
    
    # Check PyInstaller
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("PyInstaller is not installed. Run: pip install pyinstaller")
    
    # Check Inno Setup
    iscc_path = check_inno_setup()
    if not iscc_path:
        errors.append(
            f"Inno Setup is not installed.\n"
            f"  Download: {INNO_INSTALL_URL}\n"
            f"  After installation, restart your terminal and run this script again."
        )
    
    if errors:
        print("ERROR: Missing required dependencies:")
        for err in errors:
            print(f"  - {err}")
        return None
    
    return iscc_path


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


def run_inno_setup(iscc_path):
    """Run Inno Setup compiler to create the installer."""
    print("\n=== Running Inno Setup ===")
    
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
    
    pyinstaller_exe = PROJECT_ROOT / "dist" / "main" / "CookieClickerAutoClicker.exe"
    if pyinstaller_exe.exists():
        print(f"[OK] Frozen exe: {pyinstaller_exe}")
        return True
    else:
        print(f"[FAIL] Frozen exe not found: {pyinstaller_exe}")
    
    installer_exe = INSTALLER_OUTPUT_DIR / "CookieClickerAutoClicker_Setup.exe"
    if installer_exe.exists():
        size_mb = installer_exe.stat().st_size / (1024 * 1024)
        print(f"✓ Installer: {installer_exe} ({size_mb:.1f} MB)")
    else:
        print(f"✗ Installer not found: {installer_exe}")


def main():
    """Main build pipeline."""
    parser = argparse.ArgumentParser(description="Build Cookie Clicker Auto-Clicker installer")
    parser.add_argument(
        "--pyinstaller-only",
        action="store_true",
        help="Build only the frozen exe (skip Inno Setup)",
    )
    parser.add_argument(
        "--installer-only",
        action="store_true",
        help="Build only the installer (requires existing frozen exe)",
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Cookie Clicker Auto-Clicker Installer Build")
    print("=" * 60)
    
    if not sys.platform.startswith("win"):
        print("ERROR: This build script only works on Windows.")
        sys.exit(1)
    
    # Check dependencies first
    iscc_path = check_dependencies()
    if iscc_path is None:
        sys.exit(1)
    
    if args.installer_only:
        # Skip PyInstaller, only run Inno Setup
        if not (DIST_DIR / "main" / "CookieClickerAutoClicker.exe").exists():
            print("ERROR: Frozen exe not found. Run full build first.")
            sys.exit(1)
        INSTALLER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if not run_inno_setup(iscc_path):
            print("\nBuild FAILED at Inno Setup stage.")
            sys.exit(1)
    else:
        # Full build or PyInstaller-only
        if not args.pyinstaller_only:
            clean_build_dirs()
        
        if not run_pyinstaller():
            print("\nBuild FAILED at PyInstaller stage.")
            sys.exit(1)
        
        if not args.pyinstaller_only:
            run_inno_setup(iscc_path)
    
    verify_build()
    
    print("\n" + "=" * 60)
    print("Build Complete!")
    print("=" * 60)
    print(f"\nFrozen exe: {DIST_DIR / 'main' / 'CookieClickerAutoClicker.exe'}")
    print(f"Installer: {INSTALLER_OUTPUT_DIR / 'CookieClickerAutoClicker_Setup.exe'}")


if __name__ == "__main__":
    main()