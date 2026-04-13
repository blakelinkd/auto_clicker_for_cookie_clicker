# GitHub Release Automation

## Overview
Automated GitHub Actions workflow that builds and publishes installer releases when the developer creates a git tag.

## How to Create a Release

```bash
# Make your code changes...
git add .
git commit -m "Describe your changes"

# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

## What Happens
1. GitHub receives the tag push
2. Actions workflow triggers automatically
3. Build runs on Windows runner (~5-10 minutes)
4. When complete, release appears on GitHub with:
   - Release notes (auto-generated from commits)
   - Installer .exe attached as download

## Files
- `.github/workflows/release.yml` - The GitHub Actions workflow

## Requirements
- Inno Setup must be installed on the runner (pre-installed on windows-latest)
- PyInstaller installed in the workflow

## Version Format
Use `v1.0.0`, `v1.0.1`, etc. (v prefix required)