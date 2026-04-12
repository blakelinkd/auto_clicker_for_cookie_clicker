# 🍪 Auto Clicker for Cookie Clicker (Steam)

<div align="center">

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

**Advanced automation bot for the Steam version of Cookie Clicker.**  
Automate clicking, golden cookies, stock market, buildings, garden, spells, and more—while you sleep!

## 🚀 Quick Start

1. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

2. **Copy the mod**  
   ```bash
   xcopy /E cookie_shimmer_bridge_mod "D:\SteamLibrary\steamapps\common\Cookie Clicker\resources\app\mods\local\shimmerBridge\"
   ```
   *(Adjust the path if your Steam library is elsewhere.)*

3. **Restart Cookie Clicker** (full restart required)

4. **Run the bot**  
   ```bash
   python main.py
   ```
   Use **Ctrl+Alt+F12** to start/pause, **Ctrl+Alt+F11** to exit.

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
- **No computer vision** – Uses a lightweight in‑game mod that exports exact DOM coordinates
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

### 2. Install the In‑Game Mod
Copy the mod folder into Cookie Clicker’s local mods directory:

```bash
# From the repository root
xcopy /E cookie_shimmer_bridge_mod "D:\SteamLibrary\steamapps\common\Cookie Clicker\resources\app\mods\local\shimmerBridge\"
```

> **Note:** The bot automatically syncs the mod files on startup—if you update the mod in the repository, the changes will be copied to the game folder the next time you run `main.py`.

**Important:** If your Steam library is on a different drive, edit the path constants in `clicker.py` (lines 135‑140) before running the bot.

### 3. Restart Cookie Clicker
A full restart of the game is required—the mod loads only at process start.

## 🎮 Usage

### Starting the Bot
```bash
python main.py
```

The bot starts **paused**. A HUD window will appear showing status, cookies, CPS, and active buffs.

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

The bot uses hard‑coded paths in `clicker.py`. If your Steam installation is not at `D:\SteamLibrary`, update these constants:

```python
FEED_PATH = Path(r"D:\SteamLibrary\steamapps\common\Cookie Clicker\resources\app\file_outputs\shimmers.txt")
GAME_EXE_PATH = Path(r"D:\SteamLibrary\steamapps\common\Cookie Clicker\Cookie Clicker.exe")
MOD_INSTALL_DIR = Path(r"D:\SteamLibrary\steamapps\common\Cookie Clicker\resources\app\mods\local\shimmerBridge")
```

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
clicker/
├── main.py                      # Entry point
├── clicker.py                   # Legacy runtime (core loops, hotkeys, mod sync)
├── clicker_bot/                 # New orchestration modules
│   ├── app.py                   # Application wiring
│   ├── runtime.py               # Runtime configuration
│   ├── dom_loop.py              # DOM‑coordinate loop orchestrator
│   └── …
├── building_autobuyer.py        # ROI‑based building purchases
├── stock_trader.py              # Stock‑market strategy
├── garden_controller.py         # Garden planting/harvesting
├── spell_autocaster.py          # Spell‑casting logic
├── godzamok_combo.py            # Godzamok combo detection
├── wrinkler_controller.py       # Wrinkler mode management
├── ascension_prep.py            # Ascension preparation
├── cookie_shimmer_bridge_mod/   # In‑game mod (JavaScript)
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

**Disclaimer:** This bot is for educational and personal‑use purposes. Use it at your own risk. The developers are not responsible for any account penalties or unintended consequences from automating Cookie Clicker.