# 🍪 Auto Clicker for Cookie Clicker (Steam Edition)

<div align="center">

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

<div align="center">

## 🎥 **Watch the App in Action Live!**

<div style="margin: 2.5rem 0 1.5rem; display: flex; align-items: center; justify-content: center; gap: 1rem;">
  <a href="https://www.twitch.tv/biotachyonic">
    <img src="https://img.shields.io/badge/Twitch-9146FF?style=for-the-badge&logo=twitch&logoColor=white" alt="Twitch">
  </a>
  <strong>Live on <a href="https://www.twitch.tv/biotachyonic">Twitch.tv/biotachyonic</a></strong> – See real-time automation, strategies, and development!
</div>

</div>



**Advanced automation bot for the Steam version of Cookie Clicker.**  
Automate clicking, golden cookies, stock market, buildings, garden, spells, and more—while you sleep!

## 📥 Download

### Latest Release
Download the Windows installer from the [Releases](https://github.com/blakelinkd/auto_clicker_for_cookie_clicker/releases) page.

### Installation
1. Download `CookieClickerAutoClicker_Setup.exe` from the releases page
2. Run the installer
3. Launch "Cookie Clicker Auto-Clicker" from your Start Menu or Desktop shortcut

## 🚀 Quick Start (Development)

1. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the bot**  
   ```bash
   python main.py
   ```
   A dashboard window will appear.

3. **Configure the game path**  
   - Go to the **Settings** tab
   - Click **Browse...** and select your Cookie Clicker installation directory (usually in `Steam\steamapps\common\Cookie Clicker`)
   - Optionally adjust other settings (auto‑launch, hotkeys)
   - Click **Save Configuration**

4. **Copy the mod**  
   The bot will automatically sync the mod files when you first start it.  
   *(If you prefer manual copy:)*
   ```bash
   xcopy /E cookie_shimmer_bridge_mod "D:\SteamLibrary\steamapps\common\Cookie Clicker\resources\app\mods\local\shimmerBridge\"
   ```
   *(Adjust the path if your Steam library is elsewhere.)*

5. **Restart Cookie Clicker** (full restart required for the mod)

6. **Start the bot**  
   Click the **Bot** button on the dashboard or press **Ctrl+Alt+F12** to begin automation.

## ✨ Features

### 🎮 **Gameplay Automation**
- **Auto‑clicking** – Continuously clicks the big cookie at optimal speed
- **Golden & Wrath Cookies** – Instantly clicks all shimmers for maximum bonuses
- **Stock Market Trading** – Smart buy‑low, sell‑high strategy with hidden‑state awareness
- **Building Autobuy** – ROI‑based purchase decisions with reserve‑aware spending
- **Spell Autocasting** – Casts *Force the Hand of Fate* and other spells when ready
- **Garden Management** – Plants, harvests, and mutates seeds according to a predefined recipe plan
- **Wrinkler Control** – Toggle between hold, seasonal‑farm, and shiny‑hunt modes
- **Ascension Preparation** – Automatically prepares for ascension by reaching target cookies
- **Upgrade Autobuy** – Purchases affordable upgrades that improve CPS
- **Godzamok Combo** – Detects and executes optimal Godzamok sell‑click combos

### 🛠 **Technical Highlights**
- **Achievement‑safe** – This bot simulates mouse clicks only. It does not modify save files or trigger any achievement‑disabling mechanisms. Auto‑clickers are a widely accepted part of the Cookie Clicker 
- **Real‑time decision making** – Prioritizes golden cookies, spells, stocks, then buildings
- **Hotkey‑controlled** – Toggle features on/off with keyboard shortcuts
- **Live HUD** – Graphical dashboard showing bot status, cookies, CPS, and active buffs
- **Windows‑native** – Built with `pyautogui` and `win32gui` for precise input injection
- **Extensible architecture** – Modular design with separate controllers for each game system

## 🚀 How It Works

1. **In‑Game Mod** – A small JavaScript mod runs inside the Steam Cookie Clicker Electron app and writes a live JSON snapshot of UI coordinates to a file.
2. **Coordinate Polling** – The Python bot reads this file every 80 ms, converting client‑relative coordinates to screen positions.
3. **Priority‑Based Loop** – The bot executes actions in a strict priority order:
   - Click golden/wrath cookies
   - Cast ready spells (Force the Hand of Fate)
   - Execute stock‑market trades
   - Buy the best ROI building
   - Click the big cookie
4. **Input Injection** – `pyautogui` moves the mouse and clicks at the exact screen coordinates.

## 📦 Detailed Installation

> **Note:** If you already followed the Quick Start steps, you can skip this section.

### Prerequisites
- **Windows 10/11** (the bot uses Windows‑specific APIs)
- **Steam Cookie Clicker** installed (default path: `D:\SteamLibrary\steamapps\common\Cookie Clicker`)
- **Python 3.8 or newer** (add Python to your PATH)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

*Requirements:* `keyboard`, `pyautogui`, `pywin32`

### 2. Configure the Bot
Run the bot to open the dashboard:
```bash
python main.py
```

In the dashboard:
1. Go to the **Settings** tab
2. Click **Browse...** and select your Cookie Clicker installation directory (usually in `Steam\steamapps\common\Cookie Clicker`)
3. Optionally adjust other settings:
   - **Auto‑launch game on startup**: When enabled, the bot will launch Cookie Clicker automatically
   - **Register global hotkeys**: Enable/disable the Ctrl+Alt+Fxx hotkeys
4. Click **Save Configuration**

The bot will now know where your game is installed.

### 3. Install the In‑Game Mod
The bot automatically syncs the mod files when you first start it.  
*(If you prefer manual copy or want to verify the mod is installed:)*

```bash
# From the repository root (adjust the path if your Steam library is elsewhere)
xcopy /E cookie_shimmer_bridge_mod "D:\SteamLibrary\steamapps\common\Cookie Clicker\resources\app\mods\local\shimmerBridge\"
```

> **Note:** The bot automatically syncs the mod files on startup—if you update the mod in the repository, the changes will be copied to the game folder the next time you run `main.py`.

### 4. Restart Cookie Clicker
A full restart of the game is required—the mod loads only at process start.

## 🎮 Usage

### Starting the Bot
```bash
python main.py
```

A dashboard window will appear with several tabs. If this is your first run:

1. Go to the **Settings** tab and configure your Cookie Clicker installation directory
2. Save the configuration
3. Ensure Cookie Clicker is running (or enable "Auto‑launch game on startup")
4. Click the **Bot** button or press **Ctrl+Alt+F12** to begin automation

The bot starts **paused**. The HUD shows real‑time status, cookies, CPS, and active buffs.

### Hotkeys
| Hotkey | Action |
|--------|--------|
| **Ctrl+Alt+F12** | Toggle bot (start/pause) |
| **Ctrl+Alt+F8**  | Cycle wrinkler mode (hold / seasonal farm / shiny hunt) |
| **Ctrl+Alt+F9**  | Toggle stock‑market trading |
| **Ctrl+Alt+F10** | Toggle building autobuy |
| **Ctrl+Alt+F7**  | Toggle upgrade autobuy |
| **Ctrl+Alt+F6**  | Toggle ascension‑preparation mode |
| **Ctrl+Alt+F11** | Exit bot |

### HUD Controls
- **Bot** button – start/pause the automation loop
- **Stock** toggle – enable/disable stock trading
- **Build** toggle – enable/disable building autobuy
- **Upgrade** toggle – enable/disable upgrade autobuy
- **Ascend** toggle – enable/disable ascension prep
- **Wrinkler** cycle – switch wrinkler mode

## ⚙️ Configuration

The bot now includes a **Settings tab** in the dashboard where you can configure:

- **Game install directory** – Click **Browse…** to select your Cookie Clicker installation folder (usually inside Steam's `common` folder)
- **Auto‑launch game on startup** – When enabled, the bot will automatically launch Cookie Clicker on startup
- **Register global hotkeys** – Enable/disable the Ctrl+Alt+Fxx hotkeys

### Settings File
Configuration is saved to `cookie_bot_config.json` in the repository root (automatically added to `.gitignore`).

### Manual Configuration (Advanced)
If you prefer to edit the configuration file directly, it uses the following JSON format:

```json
{
  "register_hotkeys": true,
  "auto_launch_game": false,
  "game_install_dir": "C:/Path/To/Cookie Clicker"
}
```

The bot validates the game path when you try to start automation and will show a warning if the path is missing or invalid.

## 🧪 Testing

Run the full test suite with:

```bash
python -m pytest -q
```

Run a specific test module (e.g., stock trader):

```bash
python -m pytest -q tests/test_stock_trader.py
```

## 🏗 Project Structure

```
auto_clicker_for_cookie_clicker/
├── main.py                      # Entry point
├── clicker.py                   # Legacy runtime (core loops, hotkeys, mod sync)
├── clicker_bot/                 # New orchestration modules
│   ├── app.py                   # Application wiring
│   ├── runtime.py               # Runtime configuration
│   ├── dom_loop.py              # DOM‑coordinate loop orchestrator
│   ├── config.py                # AppConfig dataclass
│   ├── config_manager.py        # JSON load/save for settings
│   └── …
├── building_autobuyer.py        # ROI‑based building purchases
├── stock_trader.py              # Stock‑market strategy
├── garden_controller.py         # Garden planting/harvesting
├── spell_autocaster.py          # Spell‑casting logic
├── godzamok_combo.py            # Godzamok combo detection
├── wrinkler_controller.py       # Wrinkler mode management
├── ascension_prep.py            # Ascension preparation
├── cookie_shimmer_bridge_mod/   # In‑game mod (JavaScript)
├── cookie_bot_config.json       # User settings (auto‑generated)
└── tests/                       # Unit tests (`test_*.py`)
```

## 🤝 Contributing

Contributions are welcome! Please follow the existing code style (PEP 8, 4‑space indentation, `snake_case` for functions, `PascalCase` for classes) and add tests for any new behavior.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite (`python -m pytest -q`)
5. Submit a pull request with a clear description of the changes

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

**Note on achievements:** This bot uses only mouse and keyboard input. It does not alter save files or trigger any achievement‑disabling mechanisms. Auto‑clickers are a standard part of the Cookie Clicker community, and your achievements will remain intact.

**Disclaimer:** This bot is for educational and personal‑use purposes. Use it at your own risk. The developers are not responsible for any account penalties or unintended consequences from automating Cookie Clicker.
