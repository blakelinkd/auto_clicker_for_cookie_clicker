# Installer Specification & Build Log

**Goal:** Create a single-file Windows installer that delivers the bot as a regular desktop application—no separate Python installation, no manual dependency management, just download, run the installer, and launch the bot.

## 1. Target Platform & Assumptions

*   **OS:** Windows 10/11 (64-bit)
*   **Target user:** Non-technical gamers who play the **Steam version of Cookie Clicker**.
*   **Installation model:** `C:\Program Files\Cookie Clicker Auto-Clicker` (or user-chosen location) with a proper uninstaller.
*   **User experience:**
    *   Download a single `.exe` (e.g., `CookieClickerAutoClicker_Setup.exe`).
    *   Run the installer, accept license, choose install location, opt-in for desktop/start-menu shortcuts.
    *   After installation, launch the bot from the shortcut; it starts with its HUD, ready to attach to the running Cookie Clicker window.

## 2. High-Level Architecture

| Component | Responsibility | Implementation choice |
|-----------|----------------|----------------------|
| **App bundle** | Contains the Python interpreter, all dependencies, and the bot’s source code. | **PyInstaller** (freezes Python into a standalone `.exe` or directory). |
| **Windows installer** | Provides the familiar installation wizard, file placement, shortcuts, uninstaller. | **Inno Setup** (free, scriptable, produces a single-file installer). |
| **Configuration persistence** | Store user settings (game install dir, auto-launch, hotkeys) across runs. | Keep current JSON-based `cookie_bot_config.json` in `%LOCALAPPDATA%\CookieClickerAutoClicker`. |
| **Mod-file synchronization** | Ensure the bot can copy the local `cookie_shimmer_bridge_mod/` files to the game’s mod folder. | The frozen executable will still have access to its own bundled mod files; the installer will place them alongside the `.exe`. |

## 3. Required Installer Features

*   **Single-file installer** (`.exe`).
*   **Install-location selection** (default: `%PROGRAMFILES%\Cookie Clicker Auto-Clicker`).
*   **Shortcut options:** Desktop icon, Start-menu folder (both optional).
*   **Uninstaller** (via Windows “Add or Remove Programs”).
*   **License agreement** (include a simple MIT-style license).
*   **Post-install “Launch bot” checkbox.**

## 4. Development & Build Steps

**Phase 1 – Freeze the bot with PyInstaller**
1.  Create a `pyinstaller.spec` file that:
    *   Bundles all Python modules (`clicker_bot/`, top-level feature modules).
    *   Includes the `cookie_shimmer_bridge_mod/` directory as data files.
    *   Sets the entry point to `main.py`.
    *   Hides the console window (GUI app).
    *   Collects hidden imports (`keyboard`, `pywin32`, `PySide6`, etc.).
2.  Test the frozen `.exe` locally to verify it launches the HUD and can attach to the game.

**Phase 2 – Create the Inno Setup script**
1.  Write `installer.iss` that:
    *   Defines the application name, version, publisher, and copyright.
    *   Points to the PyInstaller output directory as the source.
    *   Creates the installation directory and copies all files.
    *   Creates shortcuts (desktop, start menu) pointing to the frozen `.exe`.
    *   Adds an uninstaller entry.
    *   Optionally sets a registry key for the installation path (e.g., `HKLM\Software\CookieClickerAutoClicker`).
2.  Build the installer with Inno Setup’s compiler; verify it runs and installs cleanly.

**Phase 3 – Configuration & data-directory handling**
1.  Modify the bot’s config-loading logic to first check `%LOCALAPPDATA%\CookieClickerAutoClicker\cookie_bot_config.json`. If missing, fall back to a location next to the executable (for portable-like behavior).
2.  Ensure the frozen executable can locate the bundled `cookie_shimmer_bridge_mod/` files (PyInstaller’s `sys._MEIPASS`).

**Phase 4 – Automation & packaging**
1.  Write a `build_installer.py` script that:
    *   Runs PyInstaller with the spec.
    *   Compiles the Inno Setup script.
    *   Outputs the final installer `.exe` in a `dist/` folder.
2.  Add a GitHub Actions workflow that builds the installer on each tag push.

## 5. Known Challenges & Mitigations

| Challenge | Mitigation |
|-----------|------------|
| **PyInstaller missing hidden imports** (keyboard hooks, pywin32 COM). | Use `--collect-all` for problematic packages; add explicit `hiddenimports` in the spec. |
| **Antivirus false positives** (common with PyInstaller-packaged keyboard hooks). | Sign the installer with a code-signing certificate (optional but recommended). Provide clear “false-positive” guidance in README. |
| **Game-path detection** (Steam Cookie Clicker install location). | The installer can optionally read the Steam registry key `HKCU\Software\Valve\Steam\Apps\1454400\InstalledPath` and pre-populate the config. |
| **Administrator privileges** (required for installing to `Program Files`). | Inno Setup will request elevation; the bot itself does not need admin rights to run. |
| **Global hotkeys (keyboard) may be blocked by other software.** | Document that users may need to run the bot as administrator if hotkeys are not working (but try without first). |

## 6. Testing Checklist

*   [ ] Fresh Windows VM: run installer, verify shortcuts created.
*   [ ] Launch bot, verify HUD appears, no console window.
*   [ ] Bot can attach to a running Cookie Clicker (Steam) window.
*   [ ] Toggle bot on/off via HUD and hotkeys.
*   [ ] Settings tab can save config to `%LOCALAPPDATA%`.
*   [ ] Uninstaller removes all files and shortcuts, leaves user config intact.
*   [ ] Installer upgrade (over existing version) works cleanly.

## 7. Future Enhancements (Post-MVP)

*   **Auto-update** mechanism (e.g., using `winsparkle` or a custom update checker).
*   **Portable version** (zip archive with pre-frozen `.exe` that writes config next to itself).
*   **Silent install** options for advanced users.
*   **Code-signing** the installer and executable.

---

## Build Log

*2026-04-12* – Spec created.
