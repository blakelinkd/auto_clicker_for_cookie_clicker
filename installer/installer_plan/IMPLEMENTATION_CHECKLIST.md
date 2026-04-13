# Implementation Checklist

## Phase 1: PyInstaller Freeze

### 1.1 Create PyInstaller Spec File
- [x] Create `installer_plan/SPEC.md`
- [ ] Create `pyinstaller.spec` in repo root
- [ ] Configure entry point (main.py)
- [ ] Configure hidden imports (keyboard, pywin32, PySide6)
- [ ] Configure data files (cookie_shimmer_bridge_mod/)
- [ ] Configure windowed mode (no console)

### 1.2 Test Frozen Build
- [ ] Run: `python -m PyInstaller main.spec --clean`
- [ ] Verify `dist/main/CookieClickerAutoClicker.exe` exists
- [ ] Execute and verify HUD appears
- [ ] Test hotkey registration
- [ ] Test config save/load

## Phase 2: Inno Setup Script

### 2.1 Create installer.iss
- [x] Create `installer_plan/INNO_SETUP.md`
- [ ] Create `installer.iss` in repo root
- [ ] Configure App name, version, publisher
- [ ] Configure default install directory
- [ ] Configure file sources (PyInstaller output)
- [ ] Configure shortcuts (desktop, start menu)
- [ ] Configure license file
- [ ] Configure post-install launch option

### 2.2 Build Installer
- [ ] Run: `iscc installer.iss`
- [ ] Verify installer exe created
- [ ] Test installation wizard
- [ ] Verify shortcuts created
- [ ] Test uninstaller

## Phase 3: Configuration & Data Handling

### 3.1 Modify Config Loading
- [ ] Read `clicker_bot/config_manager.py`
- [ ] Modify `load_config()` to check `%LOCALAPPDATA%\CookieClickerAutoClicker\` first
- [ ] Modify `save_config()` to use `%LOCALAPPDATA%` path
- [ ] Handle frozen exe detection (sys.frozen)
- [ ] Test config persistence in frozen build

### 3.2 Handle Mod Files in Frozen Build
- [ ] Read `clicker.py` - find sync_mod_files() method
- [ ] Modify to use `sys._MEIPASS` when frozen
- [ ] Test mod file sync in frozen build

### 3.3 Update Dashboard/Theme Paths
- [ ] Check qt_hud/hud_qt.py for hardcoded paths
- [ ] Check qt_hud/styles/theme.py for asset paths
- [ ] Modify if needed for frozen exe

## Phase 4: Build Automation

### 4.1 Create build_installer.py
- [ ] Create `build_installer.py` script
- [ ] Add PyInstaller build step
- [ ] Add Inno Setup compile step
- [ ] Add cleanup step
- [ ] Add output to dist/installer/

### 4.2 GitHub Actions Workflow (Optional)
- [ ] Create `.github/workflows/build.yml`
- [ ] Configure trigger on tag push
- [ ] Add PyInstaller build job
- [ ] Add Inno Setup build job
- [ ] Add artifact upload

## Phase 5: Testing & Validation

### 5.1 Fresh Install Testing
- [ ] Run installer on clean Windows VM
- [ ] Verify shortcuts created
- [ ] Verify uninstaller registered in "Add or Remove Programs"

### 5.2 Bot Functionality Testing
- [ ] Launch from shortcut
- [ ] Verify HUD appears (no console window)
- [ ] Test bot toggle (Ctrl+Alt+F12)
- [ ] Test hotkeys work
- [ ] Test config saves to LOCALAPPDATA

### 5.3 Uninstall Testing
- [ ] Run uninstaller
- [ ] Verify all files removed
- [ ] Verify shortcuts removed
- [ ] Verify user config preserved (if exists in LOCALAPPDATA)

## Phase 6: Documentation

- [ ] Update INSTALLER_LOG.md with build instructions
- [ ] Update README.md with installation instructions
- [ ] Document code signing (optional)
- [ ] Document antivirus false positive handling

## Notes

### Dependencies
- PyInstaller: `pip install pyinstaller`
- Inno Setup: Download from https://jrsoftware.org/isdl.php

### Output Locations
- PyInstaller output: `dist/main/`
- Installer output: `dist/installer/CookieClickerAutoClicker_Setup.exe`

### Testing Priority
1. Frozen exe runs without Python
2. HUD displays correctly
3. All hotkeys work
4. Config saves properly
5. Installer/uninstaller work

## Sign-off
- [ ] Phase 1 complete
- [ ] Phase 2 complete
- [ ] Phase 3 complete
- [ ] Phase 4 complete
- [ ] All tests passing