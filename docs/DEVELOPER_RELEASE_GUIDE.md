# Developer Guide: Release System

## Overview

This project uses an automated release system that builds Windows installers using PyInstaller and Inno Setup. Releases are triggered by git tags and automatically published to GitHub.

## Prerequisites

### Local Development Machine

Install these tools on your machine:

1. **Python 3.x** with pip
2. **PyInstaller**: `pip install pyinstaller`
3. **Inno Setup**: Download from https://jrsoftware.org/isdl.php

### GitHub (for releases)

No additional setup required - the release workflow runs on GitHub's Windows runners which already have Inno Setup installed.

---

## Building Locally

### Full Build (exe + installer)

```bash
python installer/build_installer.py
```

Output:
- `installer/dist/main/CookieClickerAutoClicker.exe` - Frozen executable
- `installer/dist/installer/CookieClickerAutoClicker_Setup.exe` - Windows installer

### Build Options

| Flag | Description |
|------|-------------|
| `--pyinstaller-only` | Build only the frozen exe (skip installer) |
| `--installer-only` | Build only the installer (requires existing exe in `installer/dist/main/`) |

### Build Without Cleaning

To rebuild without deleting old files (faster):

```bash
# Just run PyInstaller directly (bypasses the clean step)
python -m PyInstaller installer/pyinstaller.spec --noconfirm
```

---

## Creating a Release

### Step 1: Prepare Your Changes

```bash
# Make your code changes
git add .
git commit -m "Description of your changes"
```

### Step 2: Create a Version Tag

Tags must follow `v*` format (e.g., v1.0.0, v1.0.1, v2.0.0-beta):

```bash
git tag v1.0.0
```

### Step 3: Push to Remote

```bash
git push origin v1.0.0
```

### What Happens Automatically

1. GitHub Actions detects the tag push
2. Workflow runs on Windows runner:
   - Installs PyInstaller
   - Builds frozen exe with PyInstaller
   - Creates installer with Inno Setup
   - Creates GitHub Release with attached `.exe`
3. Release appears on GitHub with auto-generated release notes

### Verify Release

1. Go to your repository on GitHub
2. Click "Releases" in the sidebar
3. Your new release should appear with the installer attached

---

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

| Type | Example | When to use |
|------|---------|-------------|
| Major | v2.0.0 | Breaking changes |
| Minor | v1.2.0 | New features |
| Patch | v1.1.1 | Bug fixes |
| Pre-release | v1.0.0-beta | Testing |

---

## Troubleshooting

### "Inno Setup not found" error

Install Inno Setup from https://jrsoftware.org/isdl.php and restart your terminal.

### "PyInstaller not found" error

Run: `pip install pyinstaller`

### Build fails on GitHub but works locally

- Check that `pyinstaller.spec` paths are relative to repo root
- Ensure all dependencies are listed in the workflow file
- Verify Inno Setup path in workflow: `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"`

### Need to test workflow without releasing

Run a local build first:
```bash
python build_installer.py
```

Then manually test the installer before creating a tag.

---

## Files Reference

| File | Purpose |
|------|---------|
| `installer/pyinstaller.spec` | PyInstaller configuration |
| `installer/installer.iss` | Inno Setup script |
| `installer/build_installer.py` | Local build automation |
| `.github/workflows/release.yml` | GitHub Actions release workflow |

---

## Manual Release (Without Git Tag)

If you need to create a release manually:

1. Go to your repository on GitHub
2. Navigate to Actions
3. Select the "Release" workflow
4. Click "Run workflow"
5. This will build and create a draft release (requires workflow dispatch trigger - see note below)

**Note:** The workflow currently only triggers on tag push. To enable manual triggers, add this to `.github/workflows/release.yml`:

```yaml
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:  # Add this for manual trigger
```