import logging
import time
from datetime import datetime
from typing import Optional, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import Qt, QTimer, QSize, QPoint, QRect
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QFrame,
    QTabWidget,
    QTabBar,
    QScrollArea,
    QProgressBar,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QStyledItemDelegate,
    QStyle,
    QStylePainter,
    QStyleOptionTab,
    QSlider,
)
from PySide6.QtGui import QFont, QColor, QPalette, QBrush, QLinearGradient, QPainter, QPen, QFontMetrics

log = logging.getLogger(__name__)

from .styles import theme


def _auto_detect_game_path() -> Optional[str]:
    """Attempt to auto-detect Cookie Clicker installation path.
    
    Searches common Steam locations for Cookie Clicker.exe.
    
    Returns:
        Path string if found, None otherwise.
    """
    import os
    
    possible_paths = []
    
    steam_common_paths = [
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Steam", "steamapps", "common"),
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Steam", "steamapps", "common"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "..", "Local", "Steam", "steamapps", "common"),
        "D:\\Steam\\steamapps\\common",
        "E:\\Steam\\steamapps\\common",
    ]
    
    for base_path in steam_common_paths:
        if os.path.isdir(base_path):
            possible_paths.append(base_path)
            try:
                for entry in os.listdir(base_path):
                    if "cookie" in entry.lower() and os.path.isdir(os.path.join(base_path, entry)):
                        possible_paths.append(os.path.join(base_path, entry))
            except OSError:
                pass
    
    steam_library_paths = set()
    steam_dir = os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Steam")
    if os.path.isdir(steam_dir):
        steam_cfg = os.path.join(steam_dir, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(steam_cfg):
            try:
                with open(steam_cfg, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if '"path"' in line.lower():
                            parts = line.split('"')
                            if len(parts) >= 4:
                                lib_path = parts[3].replace("\\\\", "\\")
                                lib_common = os.path.join(lib_path, "steamapps", "common")
                                if os.path.isdir(lib_common):
                                    steam_library_paths.add(lib_common)
            except OSError:
                pass
    
    possible_paths.extend(steam_library_paths)
    
    exe_name = "Cookie Clicker.exe"
    for search_path in possible_paths:
        if not os.path.isdir(search_path):
            continue
        try:
            for entry in os.listdir(search_path):
                full_path = os.path.join(search_path, entry)
                if os.path.isfile(os.path.join(full_path, exe_name)):
                    return full_path
        except OSError:
            pass
    
    return None


def _validate_game_path(path_str: str) -> tuple[bool, str]:
    """Validate that the given path contains Cookie Clicker.exe.
    
    Returns:
        Tuple of (is_valid, message)
    """
    from pathlib import Path
    
    if not path_str:
        return False, "Path is empty"
    
    game_dir = Path(path_str)
    
    if not game_dir.exists():
        return False, "Directory does not exist"
    
    if not game_dir.is_dir():
        return False, "Path is not a directory"
    
    exe_path = game_dir / "Cookie Clicker.exe"
    if not exe_path.is_file():
        return False, f"Cookie Clicker.exe not found in {path_str}"
    
    return True, "Valid"

# STYLING ARCHITECTURE NOTE:
# All styling MUST use the centralized theme system in `qt_hud/styles/theme.py`.
# DO NOT write inline CSS or hardcode colors in this file.
# See: `QT_HUD_STYLE_GUIDE.md` for comprehensive guidelines.
# All UI components should use: widget.setStyleSheet(theme.function_name())


class HorizontalTabBar(QTabBar):
    """Custom tab bar that draws text horizontally for vertical tab positions."""
    
    def tabSizeHint(self, index):
        """Calculate appropriate size for horizontal text in vertical tab position."""
        # Get the text that will be displayed
        text = self.tabText(index)
        if not text:
            text = "MM"  # Fallback width estimate
        
        # Estimate text width for horizontal text
        font = self.font()
        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(text) + 20  # padding
        
        # For West/East tabs: height becomes the horizontal extent (fixed),
        # width becomes the vertical extent (based on text)
        if self.shape() in (QTabBar.RoundedWest, QTabBar.RoundedEast,
                           QTabBar.TriangularWest, QTabBar.TriangularEast):
            # Fixed height for tab button, width based on text
            return QSize(text_width, 35)  # height=35, width=text_width
        return super().tabSizeHint(index)
    
    def paintEvent(self, event):
        """Draw tabs with horizontal text (no rotation)."""
        painter = QStylePainter(self)
        option = QStyleOptionTab()
        
        for i in range(self.count()):
            self.initStyleOption(option, i)
            # Save original shape
            original_shape = option.shape
            # Force horizontal shape for drawing to prevent style rotation
            if self.shape() in (QTabBar.RoundedWest, QTabBar.RoundedEast,
                               QTabBar.TriangularWest, QTabBar.TriangularEast):
                option.shape = QTabBar.RoundedNorth
            
            # Draw tab shape using style painter (with horizontal shape)
            painter.drawControl(QStyle.CE_TabBarTabShape, option)
            
            # Restore shape for text positioning if needed
            option.shape = original_shape
            
            # Draw text horizontally without rotation
            rect = self.tabRect(i)
            painter.drawText(rect, Qt.AlignCenter, self.tabText(i))


class LumpChartWidget(QWidget):
    """Custom widget for displaying sugar lump timeline visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.lump_diag = {}
        self.setStyleSheet("background-color: #1e2630;")

    def set_data(self, lump_diag):
        """Set the lump diagnostic data and update display."""
        self.lump_diag = lump_diag or {}
        self.update()

    def paintEvent(self, event):
        """Paint the lump timeline chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        if not self.lump_diag or not self.lump_diag.get("unlocked"):
            painter.setPen(QPen(QColor("#8aa0b4")))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(width // 2, height // 2, "Waiting for sugar lump unlock...")
            return

        age_ms = self._safe_float(self.lump_diag.get("age_ms"))
        mature_ms = self._safe_float(self.lump_diag.get("mature_age_ms"))
        ripe_ms = self._safe_float(self.lump_diag.get("ripe_age_ms"))
        overripe_ms = self._safe_float(self.lump_diag.get("overripe_age_ms"))
        total_ms = max(overripe_ms, ripe_ms, mature_ms, 1.0)

        padding_left = 44
        padding_right = 28
        baseline_y = 50
        plot_width = max(1, width - padding_left - padding_right)

        def x_for(value_ms):
            return padding_left + max(0.0, min(1.0, float(value_ms) / total_ms)) * plot_width

        start_x = padding_left
        mature_x = x_for(mature_ms)
        ripe_x = x_for(ripe_ms)
        overripe_x = x_for(overripe_ms)
        marker_x = x_for(min(age_ms, total_ms))

        # Draw timeline bar segments
        bar_width = 10
        # Inactive (gray)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#304253")))
        painter.drawRect(QRect(start_x, baseline_y - bar_width//2, overripe_x - start_x, bar_width))
        # Mature (blue)
        if mature_x > start_x:
            painter.setBrush(QBrush(QColor("#55b6ff")))
            painter.drawRect(QRect(start_x, baseline_y - bar_width//2, mature_x - start_x, bar_width))
        # Ripe (orange)
        if ripe_x > mature_x:
            painter.setBrush(QBrush(QColor("#ffb14a")))
            painter.drawRect(QRect(mature_x, baseline_y - bar_width//2, ripe_x - mature_x, bar_width))
        # Overripe (green)
        if overripe_x > ripe_x:
            painter.setBrush(QBrush(QColor("#3ecf8e")))
            painter.drawRect(QRect(ripe_x, baseline_y - bar_width//2, overripe_x - ripe_x, bar_width))

        # Draw tick marks
        painter.setPen(QPen(QColor("#7d93a8")))
        for x, label in ((start_x, "Now"), (mature_x, "Mature"), (ripe_x, "Ripe"), (overripe_x, "Overripe")):
            painter.drawLine(x, baseline_y - 18, x, baseline_y + 18)
            painter.setFont(QFont("Segoe UI", 9))
            fm = QFontMetrics(painter.font())
            painter.drawText(x - fm.horizontalAdvance(label) // 2, baseline_y + 28, label)

        # Draw current position marker
        stage = self.lump_diag.get("stage", "-")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#f7fbff")))
        painter.drawEllipse(QRect(int(marker_x) - 6, baseline_y - 6, 12, 12))
        # Stage label above marker
        painter.setPen(QPen(QColor("#f7fbff")))
        painter.setFont(QFont("Segoe UI Semibold", 9))
        painter.drawText(int(marker_x) - 10, baseline_y - 24, stage.upper())

    def _safe_float(self, value):
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class GoldenCookieChartWidget(QWidget):
    """Custom widget for displaying golden cookie spawn visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.golden_diag = {}
        self.setStyleSheet("background-color: #1e2630;")

    def set_data(self, golden_diag):
        """Set the golden cookie diagnostic data and update display."""
        self.golden_diag = golden_diag or {}
        self.update()

    def paintEvent(self, event):
        """Paint the golden cookie spawn chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        if not self.golden_diag or not self.golden_diag.get("available"):
            painter.setPen(QPen(QColor("#8aa0b4")))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(width // 2, height // 2, "Waiting for golden cookie data...")
            return

        curve = list(self.golden_diag.get("spawn_curve") or [])
        on_screen = int(self.golden_diag.get("on_screen") or 0)
        progress = float(self.golden_diag.get("progress") or 0.0)
        spawned = self.golden_diag.get("spawned", [])

        padding = 40
        chart_width = width - 2 * padding
        chart_height = height - 2 * padding

        # Draw progress bar background
        bar_y = height // 2 - 15
        bar_height = 30
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#304253")))
        painter.drawRect(padding, bar_y, chart_width, bar_height)

        # Draw spawn curve if available
        if curve and len(curve) > 1:
            pen = QPen(QColor("#ffb347"))
            pen.setWidth(2)
            painter.setPen(pen)
            points = []
            for i, val in enumerate(curve):
                x = padding + (i / (len(curve) - 1)) * chart_width
                try:
                    y_val = float(val) if not isinstance(val, dict) else 0.0
                except (TypeError, ValueError):
                    y_val = 0.0
                y = (bar_y + bar_height) - (y_val * bar_height)
                points.append(QPoint(int(x), int(y)))
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        # Draw current progress indicator
        progress_x = padding + progress * chart_width
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#fffacd")))
        painter.drawEllipse(QRect(int(progress_x) - 8, bar_y + bar_height // 2 - 8, 16, 16))

        # Draw labels
        painter.setPen(QPen(QColor("#9cb0c3")))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(padding, height - 10, "0%")
        painter.drawText(width - padding - 20, height - 10, "100%")

        # On-screen count
        onscreen_text = f"On screen: {on_screen}"
        painter.drawText(padding + 10, 25, onscreen_text)

    def _safe_float(self, value):
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class QtDashboard(QMainWindow):
    """PySide6-based dashboard for the Cookie Clicker bot, styled after hud_mockup.html."""

    def __init__(
        self,
        *,
        get_dashboard_state,
        toggle_active,
        toggle_main_autoclick,
        toggle_shimmer_autoclick,
        toggle_wrath_cookie_clicking,
        toggle_stock_buying,
        toggle_lucky_reserve,
        toggle_building_buying,
        toggle_upgrade_buying,
        toggle_ascension_prep,
        toggle_garden_automation,
        set_upgrade_horizon_seconds,
        set_building_horizon_seconds,
        set_building_cap,
        set_building_cap_ignored,
        cycle_wrinkler_mode,
        cycle_garden_mode,
        exit_program,
        dump_shimmer_data=None,
        get_config=None,
        save_config=None,
        initial_geometry=None,
        refresh_interval_ms=500,
        send_overlay_message=None,
        delete_overlay_message=None,
        send_biden_timer=None,
    ):
        super().__init__()
        self.get_dashboard_state = get_dashboard_state
        self.toggle_active = toggle_active
        self.toggle_main_autoclick = toggle_main_autoclick
        self.toggle_shimmer_autoclick = toggle_shimmer_autoclick
        self.toggle_wrath_cookie_clicking = toggle_wrath_cookie_clicking or (lambda: None)
        self.toggle_stock_buying = toggle_stock_buying
        self.toggle_lucky_reserve = toggle_lucky_reserve
        self.toggle_building_buying = toggle_building_buying
        self.toggle_upgrade_buying = toggle_upgrade_buying
        self.toggle_ascension_prep = toggle_ascension_prep
        self.toggle_garden_automation = toggle_garden_automation
        self.set_upgrade_horizon_seconds = set_upgrade_horizon_seconds
        self.set_building_horizon_seconds = set_building_horizon_seconds
        self.set_building_cap = set_building_cap
        self.set_building_cap_ignored = set_building_cap_ignored
        self.cycle_wrinkler_mode = cycle_wrinkler_mode
        self.cycle_garden_mode = cycle_garden_mode
        self.exit_program = exit_program
        self.dump_shimmer_data = dump_shimmer_data
        self.get_config = get_config
        self.save_config = save_config
        self.send_overlay_message = send_overlay_message or (lambda *args, **kwargs: None)
        self.delete_overlay_message = delete_overlay_message or (lambda *args, **kwargs: None)
        self.send_biden_timer = send_biden_timer or (lambda *args, **kwargs: None)
        self.refresh_interval_ms = int(refresh_interval_ms)
        self._overlay_tz = self._resolve_overlay_timezone()
        self._overlay_card_counter = 0
        self._overlay_message_cards = {}

        # Color palette from theme
        self.COLORS = theme.COLORS

        # Toggle buttons dictionary - initialized once here, not in _create_toggle_group
        self.toggle_buttons = {}
        self.action_buttons = {}

        # Compatibility aliases for hud_gui.py naming convention
        # These are initialized as empty dicts - actual widgets are created in the tab methods
        self.summary_vars = {}
        self.timing_vars = {}
        self.building_cap_rows = {}
        
        # Horizon sync state
        self._syncing_horizons = False

        self.setWindowTitle("Cookie Clicker Bot (Qt)")
        if initial_geometry:
            if "+" in initial_geometry:
                geom, pos = initial_geometry.split("+", 1)
                w, h = map(int, geom.split("x"))
                x, y = map(int, pos.split("+"))
                self.setGeometry(x, y, w, h)
            else:
                w, h = map(int, initial_geometry.split("x"))
                self.resize(w, h)
        else:
            self.resize(1200, 800)

        # Apply dark theme
        self._apply_dark_theme()

        # Main container
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. HEADER
        header = self._create_header()
        main_layout.addWidget(header)

        # 2. TOGGLE CONTROLS SECTION
        toggle_section = self._create_toggle_section()
        main_layout.addWidget(toggle_section)

        # 3. MAIN CONTENT AREA (tabs + content)
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Left: Tab Navigation (vertical)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabBar(HorizontalTabBar())
        self.tab_widget.setTabPosition(QTabWidget.West)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setStyleSheet(theme.tab_widget_style())

        # Create tabs (matching hud_mockup.html structure)
        self.status_logs_tab = self._create_status_logs_tab()
        self.settings_config_tab = self._create_settings_config_tab()
        self.building_stats_tab = self._create_building_stats_tab()
        self.garden_automation_tab = self._create_garden_automation_tab()
        # Additional tabs from hud_gui.py
        self.gameplay_tab = self._create_gameplay_tab()
        self.forecasts_tab = self._create_forecasts_tab()
        self.feed_tab = self._create_feed_tab()
        self.diagnostics_tab = self._create_diagnostics_tab()
        self.overlay_tab = self._create_overlay_tab()

        self.tab_widget.addTab(self.status_logs_tab, "Status & Logs")
        self.tab_widget.addTab(self.settings_config_tab, "⚙️ Settings / Config")
        self.tab_widget.addTab(self.building_stats_tab, "🧱 Building Stats")
        self.tab_widget.addTab(self.garden_automation_tab, "🌱 Garden Automation")
        self.tab_widget.addTab(self.gameplay_tab, "Gameplay")
        self.tab_widget.addTab(self.forecasts_tab, "Forecasts")
        self.tab_widget.addTab(self.feed_tab, "Feed")
        self.tab_widget.addTab(self.diagnostics_tab, "Diagnostics")
        self.tab_widget.addTab(self.overlay_tab, "Overlay")

        content_layout.addWidget(self.tab_widget, 1)  # Takes remaining space

        main_layout.addWidget(content_area, 1)  # Allow content area to expand

        # 4. FOOTER
        footer = self._create_footer()
        main_layout.addWidget(footer)

        # Map compatibility aliases after all tabs are created
        self._create_compatibility_aliases()
        self._restore_overlay_messages_from_config()

        # Set up refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh)
        self.timer.start(self.refresh_interval_ms)

        # Initial refresh
        QTimer.singleShot(100, self._refresh)

    def _apply_dark_theme(self):
        """Apply dark color palette to the window."""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            theme.apply_dark_palette(app)

    def _create_compatibility_aliases(self):
        """Create compatibility aliases for hud_gui.py naming convention."""
        # Purchase panel aliases (hud_gui.py naming)
        self.purchase_title = None  # alias for building_detail
        self.purchase_detail = self.building_detail
        self.purchase_cash_bar = self.building_cash_bar
        self.purchase_cash_label = self.building_cash_label
        self.purchase_bank_bar = self.building_bank_bar
        self.purchase_bank_label = self.building_bank_label

        # Upgrade panel aliases
        self.upgrade_title = None  # alias for upgrade_detail
        self.upgrade_detail = self.upgrade_detail
        self.upgrade_cash_bar = self.upgrade_cash_bar
        self.upgrade_cash_label = self.upgrade_cash_label
        self.upgrade_bank_bar = self.upgrade_bank_bar
        self.upgrade_bank_label = self.upgrade_bank_label

        # Lucky reserve aliases
        self.lucky_reserve_label = QLabel("-")  # placeholder

        # Chart aliases - now use widgets instead of labels
        self.lump_chart = self.lump_chart_widget
        self.golden_cookie_chart = self.gc_chart_widget
        self.trader_chart = self.trader_chart_label

        # Shimmer RNG aliases - find the dump button in diagnostics tab
        self.shimmer_dump_btn = None
        dump_btns = self.diagnostics_tab.findChildren(QPushButton)
        for btn in dump_btns:
            if "Dump" in btn.text():
                self.shimmer_dump_btn = btn
                break

        # Summary and timing vars map to labels
        self.summary_vars = self.summary_labels
        self.timing_vars = self.timing_labels

    def run(self):
        """Start the Qt event loop - called by the bot runtime."""
        self.show()
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.exec()

    def closeEvent(self, event):
        """Handle window close - stop the timer and accept the close."""
        self.timer.stop()
        event.accept()
        # Call the exit callback
        self.exit_program()

    def _safe_toggle_active(self):
        """Validate game path before allowing bot to start (like hud_gui.py)."""
        try:
            payload = self.get_dashboard_state()
            currently_active = payload.get("state", {}).get("active", False) if payload else False
        except Exception:
            currently_active = False

        if currently_active:
            self.toggle_active()
            return

        if self.get_config is None:
            self.toggle_active()
            return

        try:
            config = self.get_config()
        except Exception:
            self.toggle_active()
            return

        game_dir_str = config.get("game_install_dir")
        is_valid, _ = _validate_game_path(game_dir_str or "")
        if not game_dir_str or not is_valid:
            self._show_game_path_setup_dialog()
            return

        self.toggle_active()

    def _show_game_path_setup_dialog(self):
        """Show a dialog for setting up the game path when it's missing/invalid."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Game Path Setup")
        dialog.setMinimumWidth(500)
        dialog_layout = QVBoxLayout(dialog)
        
        info_label = QLabel(
            "The Cookie Clicker installation path is not set or invalid.\n\n"
            "Please set the path to the folder containing 'Cookie Clicker.exe'."
        )
        info_label.setWordWrap(True)
        dialog_layout.addWidget(info_label)
        
        path_label = QLabel("Game Directory:")
        dialog_layout.addWidget(path_label)
        
        path_layout = QHBoxLayout()
        path_entry = QLineEdit()
        path_entry.setPlaceholderText("e.g., C:\\Steam\\steamapps\\common\\Cookie Clicker")
        path_layout.addWidget(path_entry, 1)
        
        auto_detect_btn = QPushButton("Auto Detect")
        auto_detect_btn.setStyleSheet(theme.button_style("secondary"))
        auto_detect_btn.clicked.connect(lambda: self._auto_detect_and_fill(path_entry, status_label))
        path_layout.addWidget(auto_detect_btn)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setStyleSheet(theme.button_style("secondary"))
        browse_btn.clicked.connect(lambda: self._browse_and_fill(path_entry, status_label))
        path_layout.addWidget(browse_btn)
        
        dialog_layout.addLayout(path_layout)
        
        status_label = QLabel("")
        dialog_layout.addWidget(status_label)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save & Start Bot")
        save_btn.setStyleSheet(theme.button_style("primary"))
        save_btn.clicked.connect(lambda: self._save_path_and_start(path_entry, dialog, status_label))
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(theme.button_style("secondary"))
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        dialog_layout.addLayout(button_layout)
        
        dialog.exec()

    def _auto_detect_and_fill(self, path_entry: QLineEdit, status_label: QLabel):
        """Auto-detect path and fill the entry field."""
        detected_path = _auto_detect_game_path()
        if detected_path:
            path_entry.setText(detected_path)
            self._validate_and_update_status(detected_path, status_label)
        else:
            status_label.setText("⚠️ Could not auto-detect. Please browse manually.")
            status_label.setStyleSheet(theme.secondary_label_style())

    def _browse_and_fill(self, path_entry: QLineEdit, status_label: QLabel):
        """Browse for path and fill the entry field."""
        from PySide6.QtWidgets import QFileDialog
        current_dir = path_entry.text() or ""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Cookie Clicker Installation Directory",
            current_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if dir_path:
            path_entry.setText(dir_path)
            self._validate_and_update_status(dir_path, status_label)

    def _validate_and_update_status(self, path_str: str, status_label: QLabel):
        """Validate path and update status label."""
        is_valid, message = _validate_game_path(path_str)
        if is_valid:
            status_label.setText(f"✅ {message}")
        else:
            status_label.setText(f"⚠️ {message}")

    def _save_path_and_start(self, path_entry: QLineEdit, dialog, status_label: QLabel):
        """Save the path and start the bot."""
        path = path_entry.text().strip()
        if not path:
            status_label.setText("⚠️ Please enter a path")
            return
        
        is_valid, message = _validate_game_path(path)
        if not is_valid:
            status_label.setText(f"⚠️ Invalid: {message}")
            return
        
        if self.save_config and self.get_config:
            try:
                config = self.get_config() or {}
                config["game_install_dir"] = path
                self.save_config(config)
            except Exception as e:
                status_label.setText(f"⚠️ Error saving: {e}")
                return
        
        dialog.accept()
        self.toggle_active()

    def _show_warning(self, title, message):
        """Show a warning dialog - uses QMessageBox for Qt."""
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(title)
        msg.setInformativeText(message)
        msg.exec()

    def _switch_to_settings_tab(self):
        """Switch to the Settings tab."""
        if hasattr(self, 'tab_widget'):
            for i in range(self.tab_widget.count()):
                if "Settings" in self.tab_widget.tabText(i):
                    self.tab_widget.setCurrentIndex(i)
                    return

    def _create_header(self):
        """Create header with hero label and meta status."""
        header = QWidget()
        header.setStyleSheet(theme.header_style())
        layout = QHBoxLayout(header)
        layout.setContentsMargins(25, 15, 25, 15)

        # Left side: Status info
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.hero_label = QLabel("INITIALIZING...")
        self.hero_label.setStyleSheet(theme.hero_label_style())
        left_layout.addWidget(self.hero_label)

        self.meta_label = QLabel("Loading dashboard state...")
        self.meta_label.setStyleSheet(theme.meta_label_style())
        left_layout.addWidget(self.meta_label)

        self.last_actions_label = QLabel("Last actions: -")
        self.last_actions_label.setStyleSheet(theme.secondary_label_style())
        left_layout.addWidget(self.last_actions_label)

        layout.addWidget(left_widget, 1)

        # Right side: Quick actions
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        if self.dump_shimmer_data:
            dump_btn = QPushButton("Dump Shimmer Data")
            dump_btn.setStyleSheet(theme.button_style("secondary"))
            dump_btn.clicked.connect(self.dump_shimmer_data)
            right_layout.addWidget(dump_btn)

        layout.addWidget(right_widget)

        return header

    def _create_toggle_section(self):
        """Create toggle controls section with grouped buttons."""
        section = QWidget()
        section.setStyleSheet(theme.toggle_section_style())
        layout = QHBoxLayout(section)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(20)

        # Core Automation group
        core_group = self._create_toggle_group("Core Automation", [
            ("active", "Bot Active", self._safe_toggle_active),
            ("main_autoclick", "Main Autoclick", self.toggle_main_autoclick),
            ("shimmer_autoclick", "GC Click", self.toggle_shimmer_autoclick),
            ("wrath_cookie", "Wrath Cookies", self.toggle_wrath_cookie_clicking),
        ])
        layout.addWidget(core_group)

        # Optimization & Strategy group
        opt_group = self._create_toggle_group("Optimization & Strategy", [
            ("stock", "Stock Buying", self.toggle_stock_buying),
            ("lucky_reserve", "Lucky Reserve", self.toggle_lucky_reserve),
            ("building", "Building Purchase", self.toggle_building_buying),
        ])
        layout.addWidget(opt_group)

        # Advanced Features group (includes Wrinkler Mode button)
        adv_group = QWidget()
        adv_group.setStyleSheet(theme.toggle_group_style())
        adv_layout = QVBoxLayout(adv_group)
        adv_layout.setContentsMargins(0, 0, 0, 0)
        adv_layout.setSpacing(10)
        
        label = QLabel("Advanced Features")
        label.setStyleSheet(theme.toggle_group_label_style())
        adv_layout.addWidget(label)
        
        # Upgrade Buying toggle
        upgrade_btn = QPushButton("Upgrade Buying")
        upgrade_btn.setCheckable(True)
        upgrade_btn.setStyleSheet(theme.button_style("toggle"))
        upgrade_btn.clicked.connect(self.toggle_upgrade_buying)
        adv_layout.addWidget(upgrade_btn)
        self.toggle_buttons["upgrade"] = upgrade_btn
        
        # Ascension Prep toggle
        ascension_btn = QPushButton("Ascension Prep")
        ascension_btn.setCheckable(True)
        ascension_btn.setStyleSheet(theme.button_style("toggle"))
        ascension_btn.clicked.connect(self.toggle_ascension_prep)
        adv_layout.addWidget(ascension_btn)
        self.toggle_buttons["ascension"] = ascension_btn
        
        # Garden Automation toggle (off by default)
        garden_btn = QPushButton("Garden Automation")
        garden_btn.setCheckable(True)
        garden_btn.setStyleSheet(theme.button_style("toggle"))
        garden_btn.clicked.connect(self.toggle_garden_automation)
        adv_layout.addWidget(garden_btn)
        self.toggle_buttons["garden"] = garden_btn
        
        # Cycle Wrinkler Mode button (special, not a toggle)
        self.wrinkler_btn = QPushButton("Cycle Wrinkler Mode")
        self.wrinkler_btn.setStyleSheet(theme.button_style("toggle"))
        self.wrinkler_btn.clicked.connect(self.cycle_wrinkler_mode)
        adv_layout.addWidget(self.wrinkler_btn)
        
        adv_layout.addStretch()
        layout.addWidget(adv_group)

        return section

    def _create_toggle_group(self, title, buttons):
        """Create a group of toggle buttons."""
        group = QWidget()
        group.setStyleSheet(theme.toggle_group_style())
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(title)
        label.setStyleSheet(theme.toggle_group_label_style())
        layout.addWidget(label)

        for key, text, callback in buttons:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(theme.button_style("toggle"))
            btn.clicked.connect(callback)
            layout.addWidget(btn)
            self.toggle_buttons[key] = btn

        layout.addStretch()
        return group



    def _create_gameplay_tab(self):
        """Create Gameplay tab with purchase progress and live status."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left column: Purchase Progress
        left_panel = QGroupBox("Purchase Progress")
        left_panel.setStyleSheet(theme.panel_style())
        left_layout = QVBoxLayout(left_panel)

        # Building section
        left_layout.addWidget(QLabel("<b>Next Building</b>"))
        self.building_detail = QLabel("-")
        self.building_detail.setStyleSheet(theme.text_light_color_style())
        left_layout.addWidget(self.building_detail)

        self.building_cash_bar = QProgressBar()
        self.building_cash_bar.setStyleSheet(theme.progressbar_style("info"))
        left_layout.addWidget(self.building_cash_bar)
        self.building_cash_label = QLabel("-")
        self.building_cash_label.setStyleSheet(theme.secondary_label_style())
        left_layout.addWidget(self.building_cash_label)

        self.building_bank_bar = QProgressBar()
        self.building_bank_bar.setStyleSheet(theme.progressbar_style("accent"))
        left_layout.addWidget(self.building_bank_bar)
        self.building_bank_label = QLabel("-")
        self.building_bank_label.setStyleSheet(theme.secondary_label_style())
        left_layout.addWidget(self.building_bank_label)

        left_layout.addSpacing(20)

        # Upgrade section
        left_layout.addWidget(QLabel("<b>Next Upgrade</b>"))
        self.upgrade_detail = QLabel("-")
        self.upgrade_detail.setStyleSheet(theme.text_light_color_style())
        left_layout.addWidget(self.upgrade_detail)

        self.upgrade_cash_bar = QProgressBar()
        self.upgrade_cash_bar.setStyleSheet(theme.progressbar_style("warn"))
        left_layout.addWidget(self.upgrade_cash_bar)
        self.upgrade_cash_label = QLabel("-")
        self.upgrade_cash_label.setStyleSheet(theme.secondary_label_style())
        left_layout.addWidget(self.upgrade_cash_label)

        self.upgrade_bank_bar = QProgressBar()
        self.upgrade_bank_bar.setStyleSheet(theme.progressbar_style("accent"))
        left_layout.addWidget(self.upgrade_bank_bar)
        self.upgrade_bank_label = QLabel("-")
        self.upgrade_bank_label.setStyleSheet(theme.secondary_label_style())
        left_layout.addWidget(self.upgrade_bank_label)

        left_layout.addSpacing(20)

        # Lucky reserve
        left_layout.addWidget(QLabel("<b>Lucky Reserve</b>"))
        self.lucky_reserve_bar = QProgressBar()
        self.lucky_reserve_bar.setStyleSheet(theme.progressbar_style("warn"))
        left_layout.addWidget(self.lucky_reserve_bar)
        self.lucky_reserve_label = QLabel("-")
        self.lucky_reserve_label.setStyleSheet(theme.secondary_label_style())
        left_layout.addWidget(self.lucky_reserve_label)

        left_layout.addStretch()

        # Middle column: Live Status
        middle_panel = QGroupBox("Live Status")
        middle_panel.setStyleSheet(theme.panel_style())
        middle_layout = QVBoxLayout(middle_panel)

        # Summary metrics grid
        metrics_grid = QGridLayout()
        self.summary_labels = {}
        summaries = [
            ("cookies", "Cookies"),
            ("spell", "Spell"),
            ("stock", "Stocks"),
            ("buildings", "Buildings"),
            ("garden", "Garden"),
            ("combo", "Combo"),
            ("buffs", "Buffs"),
        ]
        for i, (key, title) in enumerate(summaries):
            metrics_grid.addWidget(QLabel(f"<small>{title}</small>"), i, 0)
            label = QLabel("-")
            label.setStyleSheet(theme.summary_label_style())
            metrics_grid.addWidget(label, i, 1)
            self.summary_labels[key] = label
        middle_layout.addLayout(metrics_grid)

        middle_layout.addSpacing(15)

        # Progress bars
        middle_layout.addWidget(QLabel("<small>Mana</small>"))
        self.mana_bar = QProgressBar()
        self.mana_bar.setStyleSheet(theme.progressbar_style("info"))
        middle_layout.addWidget(self.mana_bar)

        middle_layout.addWidget(QLabel("<small>Wrinkler Fill</small>"))
        self.wrinkler_fill_bar = QProgressBar()
        self.wrinkler_fill_bar.setStyleSheet(theme.progressbar_style("warn"))
        middle_layout.addWidget(self.wrinkler_fill_bar)

        middle_layout.addWidget(QLabel("<small>Stock Exposure</small>"))
        self.stock_exposure_bar = QProgressBar()
        self.stock_exposure_bar.setStyleSheet(theme.progressbar_style("accent"))
        middle_layout.addWidget(self.stock_exposure_bar)
        self.stock_exposure_label = QLabel("-")
        self.stock_exposure_label.setStyleSheet(theme.secondary_label_style())
        middle_layout.addWidget(self.stock_exposure_label)

        middle_layout.addWidget(QLabel("<small>Ascension</small>"))
        self.ascension_bar = QProgressBar()
        self.ascension_bar.setStyleSheet(theme.progressbar_style("info"))
        middle_layout.addWidget(self.ascension_bar)

        middle_layout.addSpacing(20)

        # Timing ETAs
        timing_label = QLabel("<b>Timing & Targets</b>")
        timing_label.setStyleSheet(theme.accent_green_color_style())
        middle_layout.addWidget(timing_label)

        self.timing_labels = {}
        timing_items = [
            ("purchase_cash_eta", "Purchase cash ETA"),
            ("purchase_bank_eta", "Purchase with bank"),
            ("upgrade_cash_eta", "Upgrade cash ETA"),
            ("upgrade_bank_eta", "Upgrade with bank"),
            ("garden_timers", "Garden timers"),
            ("combo_timing", "Combo timing"),
            ("wrinkler_goal_eta", "Wrinkler goal ETA"),
            ("wrinkler_target", "Wrinkler target"),
        ]
        for key, text in timing_items:
            middle_layout.addWidget(QLabel(f"<small>{text}</small>"))
            label = QLabel("-")
            label.setStyleSheet(theme.summary_label_style())
            middle_layout.addWidget(label)
            self.timing_labels[key] = label

        middle_layout.addStretch()

        # Right column: Trader Performance (placeholder)
        right_panel = QGroupBox("Trader Performance")
        right_panel.setStyleSheet(theme.panel_style())
        right_layout = QVBoxLayout(right_panel)
        self.trader_chart_label = QLabel("Portfolio chart placeholder")
        self.trader_chart_label.setStyleSheet(theme.chart_label_style(min_height=200))
        right_layout.addWidget(self.trader_chart_label)
        right_layout.addStretch()

        # Add panels to layout
        layout.addWidget(left_panel, 2)
        layout.addWidget(middle_panel, 2)
        layout.addWidget(right_panel, 1)

        return tab

    def _create_forecasts_tab(self):
        """Create Forecasts tab with sugar lump and golden cookie charts."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Sugar Lumps panel
        lump_panel = QGroupBox("Sugar Lumps")
        lump_panel.setStyleSheet(theme.panel_style())
        lump_layout = QVBoxLayout(lump_panel)

        self.lump_meta_label = QLabel("Sugar lumps are not unlocked yet.")
        self.lump_meta_label.setStyleSheet(theme.text_light_color_style())
        lump_layout.addWidget(self.lump_meta_label)

        self.lump_modifier_label = QLabel("-")
        self.lump_modifier_label.setStyleSheet(theme.secondary_label_style())
        lump_layout.addWidget(self.lump_modifier_label)

        self.lump_chart_widget = LumpChartWidget()
        self.lump_chart_widget.setStyleSheet("border: 1px solid #3a4552;")
        lump_layout.addWidget(self.lump_chart_widget)

        layout.addWidget(lump_panel)

        # Golden Cookie Forecast panel
        gc_panel = QGroupBox("Golden Cookie Forecast")
        gc_panel.setStyleSheet(theme.panel_style())
        gc_layout = QVBoxLayout(gc_panel)

        self.gc_meta_label = QLabel("Golden cookie timer data is unavailable.")
        self.gc_meta_label.setStyleSheet(theme.text_light_color_style())
        gc_layout.addWidget(self.gc_meta_label)

        self.gc_detail_label = QLabel("-")
        self.gc_detail_label.setStyleSheet(theme.secondary_label_style())
        gc_layout.addWidget(self.gc_detail_label)

        self.gc_chart_widget = GoldenCookieChartWidget()
        self.gc_chart_widget.setStyleSheet("border: 1px solid #3a4552;")
        gc_layout.addWidget(self.gc_chart_widget)

        layout.addWidget(gc_panel)
        layout.addStretch()

        return tab

    def _create_overlay_tab(self):
        """Create Overlay tab for sending manual OBS overlay messages."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel("OBS Overlay Messages")
        header.setStyleSheet(theme.large_label_style())
        layout.addWidget(header)

        form_panel = QGroupBox("Send Message")
        form_panel.setStyleSheet(theme.panel_style())
        form_layout = QGridLayout(form_panel)
        form_layout.setColumnStretch(1, 1)

        self.overlay_message_input = QLineEdit()
        self.overlay_message_input.setPlaceholderText("Type a message for the OBS overlay...")
        self.overlay_message_input.setMaxLength(500)
        self.overlay_message_input.setStyleSheet(theme.line_edit_style())
        self.overlay_message_input.returnPressed.connect(self._submit_overlay_message)

        self.overlay_ttl_input = QLineEdit()
        self.overlay_ttl_input.setPlaceholderText("default 4s")
        self.overlay_ttl_input.setStyleSheet(theme.line_edit_style())

        self.overlay_repeat_input = QLineEdit()
        self.overlay_repeat_input.setPlaceholderText("optional")
        self.overlay_repeat_input.setStyleSheet(theme.line_edit_style())

        self.overlay_submit_btn = QPushButton("Submit")
        self.overlay_submit_btn.setStyleSheet(theme.button_style("primary"))
        self.overlay_submit_btn.clicked.connect(self._submit_overlay_message)

        form_layout.addWidget(QLabel("Message"), 0, 0)
        form_layout.addWidget(self.overlay_message_input, 0, 1, 1, 3)
        form_layout.addWidget(QLabel("TTL minutes"), 1, 0)
        form_layout.addWidget(self.overlay_ttl_input, 1, 1)
        form_layout.addWidget(QLabel("Repeat minutes"), 1, 2)
        form_layout.addWidget(self.overlay_repeat_input, 1, 3)
        form_layout.addWidget(self.overlay_submit_btn, 2, 3)

        self.overlay_status_label = QLabel("Blank TTL uses the 4 second default. Blank repeat sends once.")
        self.overlay_status_label.setStyleSheet(theme.secondary_label_style())
        form_layout.addWidget(self.overlay_status_label, 2, 0, 1, 3)

        layout.addWidget(form_panel)

        cards_panel = QGroupBox("Saved Messages")
        cards_panel.setStyleSheet(theme.panel_style())
        cards_layout = QVBoxLayout(cards_panel)
        self.overlay_cards_scroll = QScrollArea()
        self.overlay_cards_scroll.setWidgetResizable(True)
        self.overlay_cards_scroll.setStyleSheet(theme.scroll_area_style())
        self.overlay_cards_container = QWidget()
        self.overlay_cards_layout = QVBoxLayout(self.overlay_cards_container)
        self.overlay_cards_layout.setContentsMargins(6, 6, 6, 6)
        self.overlay_cards_layout.setSpacing(10)
        self.overlay_cards_layout.addStretch()
        self.overlay_cards_scroll.setWidget(self.overlay_cards_container)
        cards_layout.addWidget(self.overlay_cards_scroll)
        layout.addWidget(cards_panel, 1)

        return tab

    def _resolve_overlay_timezone(self):
        try:
            return ZoneInfo("America/Chicago")
        except ZoneInfoNotFoundError:
            return datetime.now().astimezone().tzinfo

    def _submit_overlay_message(self):
        message = self.overlay_message_input.text().strip()
        if not message:
            self._set_overlay_status("Enter a message before submitting.", error=True)
            return
        try:
            ttl_minutes = self._parse_optional_positive_minutes(self.overlay_ttl_input.text(), "TTL")
            repeat_minutes = self._parse_optional_positive_minutes(self.overlay_repeat_input.text(), "Repeat interval")
        except ValueError as exc:
            self._set_overlay_status(str(exc), error=True)
            return

        submitted_at = time.time()
        event_id = self._next_overlay_event_id(submitted_at)
        self.send_overlay_message(
            message,
            ttl_minutes=ttl_minutes,
            repeat_interval_minutes=repeat_minutes,
            submitted_at=submitted_at,
            event_id=event_id,
        )
        self._add_overlay_message_card(
            event_id=event_id,
            message=message,
            ttl_minutes=ttl_minutes,
            repeat_minutes=repeat_minutes,
            created_at=submitted_at,
        )
        self._save_overlay_messages_to_config()
        self.overlay_message_input.clear()
        self._set_overlay_status("Message sent to OBS overlay.", error=False)

    def _parse_optional_positive_minutes(self, raw_value, label):
        value = str(raw_value or "").strip()
        if not value:
            return None
        try:
            minutes = float(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be a number of minutes.") from exc
        if minutes <= 0:
            raise ValueError(f"{label} must be greater than zero.")
        return minutes

    def _set_overlay_status(self, text, *, error):
        style = theme.accent_red_color_style() if error else theme.accent_green_small_label_style()
        self.overlay_status_label.setStyleSheet(style)
        self.overlay_status_label.setText(text)

    def _next_overlay_event_id(self, timestamp):
        self._overlay_card_counter += 1
        return f"hud:{int(timestamp * 1000)}:{self._overlay_card_counter}"

    def _add_overlay_message_card(self, *, event_id, message, ttl_minutes, repeat_minutes, created_at):
        if event_id in self._overlay_message_cards:
            card = self._overlay_message_cards[event_id]
            card["message"] = message
            card["ttl_input"].setText(self._format_optional_minutes(ttl_minutes))
            card["repeat_input"].setText(self._format_optional_minutes(repeat_minutes))
            return

        card_widget = QFrame()
        card_widget.setStyleSheet(
            f"QFrame {{ background-color: {self.COLORS['panel_bg']}; "
            f"border: 1px solid {self.COLORS['border_color']}; border-radius: 8px; padding: 8px; }}"
        )
        card_layout = QHBoxLayout(card_widget)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(10)

        timestamp = datetime.fromtimestamp(float(created_at), tz=self._overlay_tz).strftime("%I:%M:%S %p").lstrip("0")
        message_label = QLabel(f"{timestamp}\n{message}")
        message_label.setWordWrap(True)
        message_label.setStyleSheet(theme.text_light_color_style())
        card_layout.addWidget(message_label, 1)

        ttl_input = QLineEdit()
        ttl_input.setPlaceholderText("4s")
        ttl_input.setText(self._format_optional_minutes(ttl_minutes))
        ttl_input.setMaximumWidth(90)
        ttl_input.setStyleSheet(theme.line_edit_style())

        repeat_input = QLineEdit()
        repeat_input.setPlaceholderText("once")
        repeat_input.setText(self._format_optional_minutes(repeat_minutes))
        repeat_input.setMaximumWidth(90)
        repeat_input.setStyleSheet(theme.line_edit_style())

        card_layout.addWidget(QLabel("TTL"))
        card_layout.addWidget(ttl_input)
        card_layout.addWidget(QLabel("Repeat"))
        card_layout.addWidget(repeat_input)

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet(theme.button_style("secondary"))
        card_layout.addWidget(delete_btn)

        self.overlay_cards_layout.insertWidget(max(0, self.overlay_cards_layout.count() - 1), card_widget)
        self._overlay_message_cards[event_id] = {
            "event_id": event_id,
            "message": message,
            "created_at": float(created_at),
            "widget": card_widget,
            "ttl_input": ttl_input,
            "repeat_input": repeat_input,
        }
        ttl_input.editingFinished.connect(lambda event_id=event_id: self._overlay_card_settings_changed(event_id))
        repeat_input.editingFinished.connect(lambda event_id=event_id: self._overlay_card_settings_changed(event_id))
        delete_btn.clicked.connect(lambda _checked=False, event_id=event_id: self._delete_overlay_message_card(event_id))

    def _overlay_card_settings_changed(self, event_id):
        card = self._overlay_message_cards.get(event_id)
        if card is None:
            return
        try:
            ttl_minutes = self._parse_optional_positive_minutes(card["ttl_input"].text(), "TTL")
            repeat_minutes = self._parse_optional_positive_minutes(card["repeat_input"].text(), "Repeat interval")
        except ValueError as exc:
            self._set_overlay_status(str(exc), error=True)
            return
        self.send_overlay_message(
            card["message"],
            ttl_minutes=ttl_minutes,
            repeat_interval_minutes=repeat_minutes,
            submitted_at=time.time(),
            event_id=event_id,
        )
        self._save_overlay_messages_to_config()
        self._set_overlay_status("Overlay message settings updated.", error=False)

    def _delete_overlay_message_card(self, event_id):
        card = self._overlay_message_cards.pop(event_id, None)
        if card is None:
            return
        card["widget"].setParent(None)
        card["widget"].deleteLater()
        self.delete_overlay_message(event_id)
        self._save_overlay_messages_to_config()
        self._set_overlay_status("Overlay message deleted.", error=False)

    def _format_optional_minutes(self, value):
        return "" if value is None else f"{float(value):g}"

    def _overlay_messages_for_config(self):
        messages = []
        for event_id, card in self._overlay_message_cards.items():
            try:
                ttl_minutes = self._parse_optional_positive_minutes(card["ttl_input"].text(), "TTL")
                repeat_minutes = self._parse_optional_positive_minutes(card["repeat_input"].text(), "Repeat interval")
            except ValueError:
                continue
            messages.append({
                "event_id": event_id,
                "text": card["message"],
                "ttl_minutes": ttl_minutes,
                "repeat_interval_minutes": repeat_minutes,
                "created_at": card["created_at"],
            })
        return messages

    def _save_overlay_messages_to_config(self):
        if self.get_config is None or self.save_config is None:
            return
        try:
            config = dict(self.get_config() or {})
            config["overlay_messages"] = self._overlay_messages_for_config()
            self.save_config(config)
        except Exception as exc:
            log.debug("Failed to save overlay messages: %s", exc)

    def _restore_overlay_messages_from_config(self):
        if self.get_config is None:
            return
        try:
            config = self.get_config() or {}
        except Exception as exc:
            log.debug("Failed to load overlay messages: %s", exc)
            return
        messages = config.get("overlay_messages") if isinstance(config, dict) else []
        if not isinstance(messages, (list, tuple)):
            return
        for message in messages:
            if not isinstance(message, dict):
                continue
            text = str(message.get("text") or "").strip()
            if not text:
                continue
            created_at = self._safe_float(message.get("created_at"), time.time())
            event_id = str(message.get("event_id") or self._next_overlay_event_id(created_at))
            ttl_minutes = self._safe_optional_float(message.get("ttl_minutes"))
            repeat_minutes = self._safe_optional_float(message.get("repeat_interval_minutes"))
            self._add_overlay_message_card(
                event_id=event_id,
                message=text[:500],
                ttl_minutes=ttl_minutes,
                repeat_minutes=repeat_minutes,
                created_at=created_at,
            )
            self.send_overlay_message(
                text[:500],
                ttl_minutes=ttl_minutes,
                repeat_interval_minutes=repeat_minutes,
                submitted_at=time.time(),
                event_id=event_id,
            )

    def _safe_optional_float(self, value):
        if value is None or value == "":
            return None
        return self._safe_float(value, None)

    def _create_feed_tab(self):
        """Create Feed tab with color-coded event log."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        panel = QGroupBox("Live Feed")
        panel.setStyleSheet(theme.panel_style())
        panel_layout = QVBoxLayout(panel)

        self.feed_text = QTextEdit()
        self.feed_text.setReadOnly(True)
        self.feed_text.setStyleSheet(theme.text_edit_style())
        panel_layout.addWidget(self.feed_text)

        layout.addWidget(panel)
        return tab

    def _create_diagnostics_tab(self):
        """Create Diagnostics tab with shimmer RNG and building caps."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Shimmer RNG panel
        shimmer_panel = QGroupBox("Shimmer RNG Data")
        shimmer_panel.setStyleSheet(theme.panel_style())
        shimmer_layout = QVBoxLayout(shimmer_panel)

        self.shimmer_progress = QProgressBar()
        self.shimmer_progress.setStyleSheet(theme.progressbar_style("info"))
        shimmer_layout.addWidget(self.shimmer_progress)

        self.shimmer_rng_status = QLabel("0 / 100 samples")
        self.shimmer_rng_status.setStyleSheet(theme.secondary_label_style())
        shimmer_layout.addWidget(self.shimmer_rng_status)

        self.shimmer_stats_detail = QLabel("+0 -0 =0 | Seeds: 0")
        self.shimmer_stats_detail.setStyleSheet(theme.secondary_label_style())
        shimmer_layout.addWidget(self.shimmer_stats_detail)

        if self.dump_shimmer_data:
            dump_btn = QPushButton("Dump Shimmer Data")
            dump_btn.setStyleSheet(theme.button_style("secondary"))
            dump_btn.clicked.connect(self.dump_shimmer_data)
            shimmer_layout.addWidget(dump_btn)

        layout.addWidget(shimmer_panel)

        layout.addStretch()

        return tab

    def _create_settings_tab(self):
        """Create Settings tab with game path and horizon controls."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        panel = QGroupBox("Configuration Settings")
        panel.setStyleSheet(theme.panel_style())
        panel_layout = QVBoxLayout(panel)

        # Game path setup
        panel_layout.addWidget(QLabel("<b>Game Path</b>"))
        path_layout = QHBoxLayout()
        self.game_path_entry = QLineEdit()
        self.game_path_entry.setPlaceholderText("e.g., C:\\Games\\Cookie Clicker")
        self.game_path_entry.setStyleSheet(theme.line_edit_style())
        path_layout.addWidget(self.game_path_entry, 1)

        self.auto_detect_btn = QPushButton("Auto Detect")
        self.auto_detect_btn.setStyleSheet(theme.button_style("secondary"))
        self.auto_detect_btn.clicked.connect(self._auto_detect_game_path_action)
        path_layout.addWidget(self.auto_detect_btn)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setStyleSheet(theme.button_style("secondary"))
        self.browse_btn.clicked.connect(self._browse_game_directory)
        path_layout.addWidget(self.browse_btn)

        panel_layout.addLayout(path_layout)

        # Path validation status
        self.game_path_status_label = QLabel("")
        self.game_path_status_label.setStyleSheet(theme.secondary_label_style())
        panel_layout.addWidget(self.game_path_status_label)

        # Auto-launch and hotkeys checkboxes
        panel_layout.addSpacing(15)
        self.auto_launch_var = QCheckBox("Auto-launch game on startup")
        self.auto_launch_var.setStyleSheet(theme.checkbox_style())
        panel_layout.addWidget(self.auto_launch_var)
        
        self.register_hotkeys_var = QCheckBox("Register global hotkeys (Ctrl+Alt+Fxx)")
        self.register_hotkeys_var.setStyleSheet(theme.checkbox_style())
        panel_layout.addWidget(self.register_hotkeys_var)

        # Horizon controls (advanced)
        panel_layout.addSpacing(20)
        panel_layout.addWidget(QLabel("<b>Horizon Timers (Advanced)</b>"))

        # Upgrade horizon slider
        upgrade_layout = QVBoxLayout()
        upgrade_header = QHBoxLayout()
        upgrade_header.addWidget(QLabel("Upgrade Horizon:"))
        self.upgrade_horizon_value_label = QLabel("6m")
        self.upgrade_horizon_value_label.setStyleSheet(theme.accent_green_color_style())
        upgrade_header.addWidget(self.upgrade_horizon_value_label)
        upgrade_header.addStretch()
        upgrade_header.addWidget(QLabel("Ideal: 1-3h"))
        upgrade_layout.addLayout(upgrade_header)
        
        self.upgrade_horizon_slider = QSlider(Qt.Horizontal)
        self.upgrade_horizon_slider.setRange(1, 180)  # 1 to 180 minutes (3 hours)
        self.upgrade_horizon_slider.setValue(6)  # Default 6 minutes
        self.upgrade_horizon_slider.setTickPosition(QSlider.TicksBelow)
        self.upgrade_horizon_slider.setTickInterval(15)  # Tick every 15 minutes
        self.upgrade_horizon_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {self.COLORS['border_color']};
                height: 8px;
                background: {self.COLORS['panel_bg']};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {self.COLORS['info_blue']};
                border: 1px solid {self.COLORS['border_color']};
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.COLORS['info_blue']};
                border-radius: 4px;
            }}
        """)
        self.upgrade_horizon_slider.valueChanged.connect(self._on_upgrade_horizon_slider_changed)
        upgrade_layout.addWidget(self.upgrade_horizon_slider)
        
        self.upgrade_horizon_status = QLabel("")
        self.upgrade_horizon_status.setStyleSheet(theme.secondary_label_style())
        upgrade_layout.addWidget(self.upgrade_horizon_status)
        
        panel_layout.addLayout(upgrade_layout)

        # Building horizon slider
        building_layout = QVBoxLayout()
        building_header = QHBoxLayout()
        building_header.addWidget(QLabel("Building Horizon:"))
        self.building_horizon_value_label = QLabel("2m")
        self.building_horizon_value_label.setStyleSheet(theme.accent_green_color_style())
        building_header.addWidget(self.building_horizon_value_label)
        building_header.addStretch()
        building_header.addWidget(QLabel("Ideal: 30-90m"))
        building_layout.addLayout(building_header)
        
        self.building_horizon_slider = QSlider(Qt.Horizontal)
        self.building_horizon_slider.setRange(1, 180)  # 1 to 180 minutes (3 hours)
        self.building_horizon_slider.setValue(2)  # Default 2 minutes
        self.building_horizon_slider.setTickPosition(QSlider.TicksBelow)
        self.building_horizon_slider.setTickInterval(15)  # Tick every 15 minutes
        self.building_horizon_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {self.COLORS['border_color']};
                height: 8px;
                background: {self.COLORS['panel_bg']};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {self.COLORS['info_blue']};
                border: 1px solid {self.COLORS['border_color']};
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.COLORS['info_blue']};
                border-radius: 4px;
            }}
        """)
        self.building_horizon_slider.valueChanged.connect(self._on_building_horizon_slider_changed)
        building_layout.addWidget(self.building_horizon_slider)
        
        self.building_horizon_status = QLabel("")
        self.building_horizon_status.setStyleSheet(theme.secondary_label_style())
        building_layout.addWidget(self.building_horizon_status)
        
        panel_layout.addLayout(building_layout)

        # Horizon preset buttons
        panel_layout.addSpacing(10)
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick presets:"))
        for minutes in (3, 15, 30, 60, 120, 180):
            btn = QPushButton(f"{minutes}m")
            btn.setStyleSheet(theme.button_style("secondary"))
            btn.setMinimumWidth(50)
            btn.clicked.connect(lambda checked=False, m=minutes: self._apply_horizon_preset(m))
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        panel_layout.addLayout(preset_layout)

        # Save button
        panel_layout.addSpacing(30)
        save_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setStyleSheet(theme.button_style("primary"))
        if self.save_config:
            save_btn.clicked.connect(self._save_config)
        save_layout.addWidget(save_btn)
        self.config_status_label = QLabel("Status: Idle")
        self.config_status_label.setStyleSheet(theme.secondary_label_style())
        save_layout.addWidget(self.config_status_label)
        save_layout.addStretch()
        panel_layout.addLayout(save_layout)

        panel_layout.addStretch()
        layout.addWidget(panel)
        return tab

    def _create_footer(self):
        """Create footer with exit button."""
        footer = QWidget()
        footer.setStyleSheet(theme.footer_style())
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(25, 15, 25, 15)

        exit_btn = QPushButton("❌ Exit Program")
        exit_btn.setStyleSheet(theme.button_style("primary"))
        exit_btn.clicked.connect(self.exit_program)
        layout.addWidget(exit_btn)

        layout.addStretch()
        return footer

    def _create_status_logs_tab(self):
        """Create Status & Logs tab matching hud_mockup.html."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Metrics Grid (4 boxes)
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(15)
        
        # Metric boxes data: (row, col, title, value_id, default_value, color)
        metrics_data = [
            (0, 0, "Total Cookies Clicked", "click_count_label", "1,450,000", theme.COLORS["text_light"]),
            (0, 1, "Shimmer Cookie Count", "shimmer_stats_label", "52", theme.COLORS["shimmer_yellow"]),
            (1, 0, "Last Bot Action", "last_action_label", "Trade Executed", theme.COLORS["text_light"]),
            (1, 1, "Feed Parse Age", "feed_parse_age_label", "12s ago", "#aaa"),
        ]
        
        self.metric_labels = {}
        for row, col, title, value_id, default_value, color in metrics_data:
            metric_box = QWidget()
            metric_box.setStyleSheet(theme.metric_box_style())
            box_layout = QVBoxLayout(metric_box)
            box_layout.setAlignment(Qt.AlignCenter)
            
            value_label = QLabel(default_value)
            value_label.setStyleSheet(theme.metric_value_style(color))
            box_layout.addWidget(value_label)
            
            title_label = QLabel(title)
            title_label.setStyleSheet(theme.metric_title_style())
            box_layout.addWidget(title_label)
            
            metrics_grid.addWidget(metric_box, row, col)
            self.metric_labels[value_id] = value_label

        layout.addLayout(metrics_grid)

        # Logs Panel
        log_panel = QGroupBox("Recent Bot Events Log")
        log_panel.setStyleSheet(theme.panel_style())
        log_layout = QVBoxLayout(log_panel)
        
        self.events_log = QTextEdit()
        self.events_log.setReadOnly(True)
        self.events_log.setPlaceholderText("Bot activity and system logs will appear here...")
        self.events_log.setStyleSheet(theme.text_edit_style(min_height=300))
        log_layout.addWidget(self.events_log)

        layout.addWidget(log_panel, 1)  # Expand log area

        return tab

    def _create_settings_config_tab(self):
        """Create Settings / Config tab (reuses existing settings tab)."""
        return self._create_settings_tab()

    def _create_building_stats_tab(self):
        """Create Building Stats tab matching hud_mockup.html."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Building Purchase Statistics panel
        stats_panel = QGroupBox("Building Purchase Statistics")
        stats_panel.setStyleSheet(theme.panel_style())
        stats_layout = QVBoxLayout(stats_panel)

        # Building table (placeholder)
        self.building_stats_table = QTableWidget(2, 3)  # 2 rows, 3 columns
        self.building_stats_table.setHorizontalHeaderLabels(["Building", "Current Cap", "Target Cap"])
        self.building_stats_table.setStyleSheet(theme.table_widget_style())
        self.building_stats_table.horizontalHeader().setStretchLastSection(True)
        self.building_stats_table.verticalHeader().setVisible(False)
        self.building_stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Sample data
        sample_data = [
            ["Mine", "10,000", "50,000"],
            ["Farm", "5,000", "20,000"],
        ]
        for row, (building, current, target) in enumerate(sample_data):
            self.building_stats_table.setItem(row, 0, QTableWidgetItem(building))
            self.building_stats_table.setItem(row, 1, QTableWidgetItem(current))
            self.building_stats_table.setItem(row, 2, QTableWidgetItem(target))
        
        self.building_stats_table.resizeColumnsToContents()
        stats_layout.addWidget(self.building_stats_table)

        stats_layout.addWidget(self._create_building_caps_panel(), 1)

        # Stats summary
        self.stats_summary = QLabel("Purchases Completed: 4,567 | Total Gold Spent: 89 Million")
        self.stats_summary.setStyleSheet(theme.medium_label_style(margin_top=10))
        stats_layout.addWidget(self.stats_summary)

        stats_layout.addStretch()
        layout.addWidget(stats_panel)

        return tab

    def _create_building_caps_panel(self):
        caps_panel = QGroupBox("Building Caps")
        caps_panel.setStyleSheet(theme.panel_style())
        caps_layout = QVBoxLayout(caps_panel)

        self.building_caps_meta = QLabel("0 buildings | ignored 0 | blank cap entry resets to default")
        self.building_caps_meta.setStyleSheet(theme.secondary_label_style())
        caps_layout.addWidget(self.building_caps_meta)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(theme.scroll_area_style())
        self.building_caps_widget = QWidget()
        self.building_caps_layout = QVBoxLayout(self.building_caps_widget)
        self.building_caps_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.building_caps_widget)
        caps_layout.addWidget(scroll)

        return caps_panel

    def _create_garden_automation_tab(self):
        """Create Garden Automation tab matching hud_mockup.html."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Garden Automation Status panel
        garden_panel = QGroupBox("Garden Automation Status")
        garden_panel.setStyleSheet(theme.panel_style())
        garden_layout = QVBoxLayout(garden_panel)

        # Plant Growth Progress
        garden_layout.addWidget(QLabel("Plant Growth Progress:"))
        self.garden_progress_bar = QProgressBar()
        self.garden_progress_bar.setStyleSheet(theme.progressbar_style("info"))
        self.garden_progress_bar.setValue(65)
        garden_layout.addWidget(self.garden_progress_bar)

        # Key Garden Stats grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(15)
        
        # Soil type
        soil_box = QWidget()
        soil_box.setStyleSheet(theme.metric_box_style())
        soil_layout = QVBoxLayout(soil_box)
        soil_layout.setAlignment(Qt.AlignCenter)
        self.garden_soil_value = QLabel("Oak")
        self.garden_soil_value.setStyleSheet(theme.large_label_style())
        soil_layout.addWidget(self.garden_soil_value)
        soil_label = QLabel("Current Soil Type")
        soil_label.setStyleSheet(theme.secondary_label_style())
        soil_layout.addWidget(soil_label)
        stats_grid.addWidget(soil_box, 0, 0)
        
        # Planting cycle
        cycle_box = QWidget()
        cycle_box.setStyleSheet(theme.metric_box_style())
        cycle_layout = QVBoxLayout(cycle_box)
        cycle_layout.setAlignment(Qt.AlignCenter)
        self.garden_cycle_value = QLabel("3 days")
        self.garden_cycle_value.setStyleSheet(theme.large_label_style())
        cycle_layout.addWidget(self.garden_cycle_value)
        cycle_label = QLabel("Planting Cycle Remaining")
        cycle_label.setStyleSheet(theme.secondary_label_style())
        cycle_layout.addWidget(cycle_label)
        stats_grid.addWidget(cycle_box, 0, 1)
        
        garden_layout.addLayout(stats_grid)

        # Status label
        self.garden_status_label = QLabel("Status: Automation Active - Ready for Harvest.")
        self.garden_status_label.setStyleSheet(theme.accent_green_medium_label_style(margin_top=15))
        garden_layout.addWidget(self.garden_status_label)
        
        # Mode display and cycle button
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.garden_mode_label = QLabel("Auto")
        self.garden_mode_label.setStyleSheet(theme.accent_green_color_style())
        mode_layout.addWidget(self.garden_mode_label)
        mode_layout.addStretch()
        
        self.cycle_garden_mode_btn = QPushButton("Cycle Garden Mode")
        self.cycle_garden_mode_btn.setStyleSheet(theme.button_style("secondary"))
        self.cycle_garden_mode_btn.clicked.connect(self.cycle_garden_mode)
        mode_layout.addWidget(self.cycle_garden_mode_btn)
        
        garden_layout.addLayout(mode_layout)

        garden_layout.addStretch()
        layout.addWidget(garden_panel)

        return tab





    def _refresh(self):
        """Update UI with current dashboard state."""
        try:
            payload = self.get_dashboard_state()
        except Exception as e:
            log.exception("Failed to get dashboard state")
            self.hero_label.setText("ERROR")
            self.hero_label.setStyleSheet(theme.accent_red_hero_label_style())
            return

        # Guard against None payload from mock callbacks
        if payload is None:
            self.hero_label.setText("WAITING FOR DATA...")
            return

        state = payload["state"]
        trade_stats = payload["trade_stats"]
        building_stats = payload["building_stats"]
        ascension_prep_stats = payload.get("ascension_prep_stats") or {}
        garden_stats = payload["garden_stats"]
        combo_stats = payload["combo_stats"]
        spell_stats = payload["spell_stats"]
        last_building_diag = state.get("last_building_diag") or payload.get("last_building_diag") or {}
        last_upgrade_diag = state.get("last_upgrade_diag") or {}
        last_spell_diag = state.get("last_spell_diag") or {}
        last_garden_diag = state.get("last_garden_diag") or {}
        last_combo_diag = state.get("last_combo_diag") or {}
        last_wrinkler_diag = state.get("last_wrinkler_diag") or {}
        last_bank_diag = state.get("last_bank_diag") or {}
        last_lump_diag = state.get("last_lump_diag") or {}
        last_golden_diag = state.get("last_golden_diag") or {}
        last_santa_diag = state.get("last_santa_diag") or {}

        # Update header
        started_at = state.get("started_at")
        uptime = max(0, int(time.monotonic() - float(started_at if started_at is not None else time.monotonic())))
        uptime_text = time.strftime("%H:%M:%S", time.gmtime(uptime))
        active_text = "RUNNING" if state.get("active") else "PAUSED"
        self.hero_label.setText(f"{active_text} | Uptime: {uptime_text}")
        if state.get('active'):
            self.hero_label.setStyleSheet(theme.hero_label_style())
        else:
            self.hero_label.setStyleSheet(theme.accent_red_hero_label_style())

        # Update meta label
        meta_parts = []
        meta_parts.append(f"🍪 Cookies: {self._format_number(state.get('main_clicks', 0))} clicks")
        meta_parts.append(f"✨ Shimmers: {state.get('shimmer_clicks', 0)}")
        meta_parts.append(f"📈 DPS: {self._format_number(last_building_diag.get('cookies_ps', 0))}")
        self.meta_label.setText(" | ".join(meta_parts))

        # Update last actions
        last_actions = []
        for key, label in [
            ("last_spell_cast", "Spell"),
            ("last_trade_action", "Trade"),
            ("last_building_action", "Building"),
            ("last_garden_action", "Garden"),
            ("last_wrinkler_action", "Wrinkler"),
            ("last_lump_action", "Lump"),
        ]:
            value = state.get(key)
            if value:
                last_actions.append(f"{label}: {value}")
        last_actions.append(
            "Santa: "
            f"{last_santa_diag.get('reason', '-')}"
            f" | open={'Y' if last_santa_diag.get('open') else 'N'}"
            f" evolve={'Y' if last_santa_diag.get('evolve_target') else 'N'}"
            f" | level={last_santa_diag.get('level', '-')}/{last_santa_diag.get('max_level', '-')}"
            f" | target={last_santa_diag.get('target_level', '-')}"
            f" | current={last_santa_diag.get('current_name') or '-'}"
            f" | next={last_santa_diag.get('next_name') or '-'}"
        )
        self.last_actions_label.setText("Last actions: " + (" | ".join(last_actions) if last_actions else "-"))

        # Update toggle button states
        for key, btn in self.toggle_buttons.items():
            state_key = {
                "active": "active",
                "stock": "stock_trading_enabled",
                "lucky_reserve": "lucky_reserve_enabled",
                "building": "building_autobuy_enabled",
                "upgrade": "upgrade_autobuy_enabled",
                "ascension": "ascension_prep_enabled",
                "garden": "garden_automation_enabled",
                "main_autoclick": "main_cookie_clicking_enabled",
                "shimmer_autoclick": "shimmer_autoclick_enabled",
                "wrath_cookie": "wrath_cookie_clicking_enabled",
            }.get(key)
            if state_key:
                btn.setChecked(bool(state.get(state_key)))

        # Update wrinkler button text
        self.wrinkler_btn.setText(f"Wrinkler Mode: {state.get('wrinkler_mode', '-')}")

        # Update status & logs tab
        self._update_status_logs_tab(state, payload.get("feed", []))
        
        # Update building stats tab
        self._update_building_stats_tab(building_stats, last_building_diag.get("buildings", []))
        
        # Update garden automation tab
        self._update_garden_automation_tab(garden_stats, last_garden_diag)
        
        # Update settings tab
        self._update_settings_tab()
        
        # Sync horizon slider values from current state
        upgrade_horizon_seconds = state.get("upgrade_horizon_seconds") or last_upgrade_diag.get("horizon_seconds")
        building_horizon_seconds = state.get("building_horizon_seconds") or last_building_diag.get("payback_horizon_seconds")
        self._sync_horizon_inputs(
            upgrade_horizon_seconds=upgrade_horizon_seconds,
            building_horizon_seconds=building_horizon_seconds,
        )

        # Update gameplay tab (purchase progress, live status, trader)
        self._update_gameplay_tab(
            state,
            last_building_diag,
            last_upgrade_diag,
            last_spell_diag,
            last_wrinkler_diag,
            last_bank_diag,
            trade_stats,
            garden_stats,
            combo_stats,
            building_stats,
            ascension_prep_stats,
        )
        
        # Update forecasts tab (lumps, golden cookies)
        self._update_forecasts_tab(last_lump_diag, last_golden_diag)
        self.send_biden_timer(last_golden_diag)
        
        # Update feed tab
        self._update_feed_tab(payload.get("feed", []))
        
        # Update diagnostics tab (shimmer RNG, building caps)
        shimmer_stats = payload.get("shimmer_stats") or {}
        building_entries = last_building_diag.get("buildings") or building_stats.get("buildings") or []
        self._update_diagnostics_tab(shimmer_stats, building_entries, building_stats)
        self._update_building_caps(building_entries, building_stats)

    def _update_gameplay_tab(self, state, building_diag, upgrade_diag, spell_diag,
                            wrinkler_diag, bank_diag, trade_stats, garden_stats,
                            combo_stats, building_stats, ascension_prep_stats):
        """Update gameplay tab widgets."""
        # Purchase progress - use _safe_float to handle string values
        cookies = self._safe_float(bank_diag.get("cookies") or building_diag.get("cookies"))
        cookies_ps = self._safe_float(building_diag.get("cookies_ps") or bank_diag.get("cookies_ps_raw_highest"))
        wrinkler_bank = self._safe_float(wrinkler_diag.get("estimated_reward_attached"))

        # Building progress
        building_price = building_diag.get("next_candidate_price")
        building_name = building_diag.get("candidate") or "-"
        self.building_detail.setText(f"{building_name} ({self._format_number(building_price)})" if building_price else "-")

        if building_price and cookies_ps > 0:
            progress = min(100.0, (cookies / self._safe_float(building_price)) * 100.0)
            self.building_cash_bar.setValue(int(progress))
            eta = (self._safe_float(building_price) - cookies) / cookies_ps if cookies < self._safe_float(building_price) else 0
            self.building_cash_label.setText(
                f"{progress:.1f}% • ETA: {self._format_duration(eta)}" if eta > 0 else "Ready!"
            )
        else:
            self.building_cash_bar.setValue(0)
            self.building_cash_label.setText("-")

        # Building with bank
        if building_price and cookies_ps > 0:
            total = cookies + wrinkler_bank
            progress = min(100.0, (total / self._safe_float(building_price)) * 100.0)
            self.building_bank_bar.setValue(int(progress))
            self.building_bank_label.setText(
                f"{progress:.1f}% • Bank: {self._format_number(wrinkler_bank)}"
            )
        else:
            self.building_bank_bar.setValue(0)
            self.building_bank_label.setText("-")

        # Upgrade progress
        upgrade_price = upgrade_diag.get("candidate_price")
        upgrade_name = upgrade_diag.get("candidate") or "-"
        self.upgrade_detail.setText(f"{upgrade_name} ({self._format_number(upgrade_price)})" if upgrade_price else "-")

        if upgrade_price and cookies_ps > 0:
            progress = min(100.0, (cookies / self._safe_float(upgrade_price)) * 100.0)
            self.upgrade_cash_bar.setValue(int(progress))
            eta = (self._safe_float(upgrade_price) - cookies) / cookies_ps if cookies < self._safe_float(upgrade_price) else 0
            self.upgrade_cash_label.setText(
                f"{progress:.1f}% • ETA: {self._format_duration(eta)}" if eta > 0 else "Ready!"
            )
        else:
            self.upgrade_cash_bar.setValue(0)
            self.upgrade_cash_label.setText("-")

        # Upgrade with bank
        if upgrade_price and cookies_ps > 0:
            total = cookies + wrinkler_bank
            progress = min(100.0, (total / self._safe_float(upgrade_price)) * 100.0)
            self.upgrade_bank_bar.setValue(int(progress))
            self.upgrade_bank_label.setText(
                f"{progress:.1f}% • Bank: {self._format_number(wrinkler_bank)}"
            )
        else:
            self.upgrade_bank_bar.setValue(0)
            self.upgrade_bank_label.setText("-")

        # Lucky reserve
        hard_lucky = self._safe_float(
            upgrade_diag.get("hard_lucky_cookie_reserve") or
            building_diag.get("hard_lucky_cookie_reserve") or
            bank_diag.get("hard_lucky_cookie_reserve")
        )
        if hard_lucky > 0:
            progress = min(100.0, (cookies / hard_lucky) * 100.0)
            self.lucky_reserve_bar.setValue(int(progress))
            self.lucky_reserve_label.setText(
                f"{progress:.1f}% • {self._format_number(cookies)} / {self._format_number(hard_lucky)}"
            )
        else:
            self.lucky_reserve_bar.setValue(0)
            self.lucky_reserve_label.setText("No lucky reserve target")

        # Live Status summaries
        self.summary_labels["cookies"].setText(
            f"{self._format_number(cookies)} | {self._format_number(cookies_ps)}/s"
        )
        self.summary_labels["spell"].setText(
            f"{spell_diag.get('reason', '-')} | {state.get('last_spell_cast', '-')}"
        )
        self.summary_labels["stock"].setText(
            f"{bank_diag.get('reason', '-')} | P&L: {self._format_number(trade_stats.get('net_pnl'))}"
        )
        self.summary_labels["buildings"].setText(
            f"{building_diag.get('reason', '-')} | {building_stats.get('last_building', '-')}"
        )
        self.summary_labels["garden"].setText(
            f"{garden_stats.get('last_garden', '-')} | {garden_stats.get('status', '-')}"
        )
        self.summary_labels["combo"].setText(
            f"{combo_stats.get('last_combo', '-')} | Gain: {self._format_number(combo_stats.get('last_gain'))}"
        )
        self.summary_labels["buffs"].setText(
            ", ".join(state.get("last_buffs", [])[:3]) or "-"
        )

        # Progress bars
        spell_magic = self._safe_float(spell_diag.get("magic"))
        spell_max = self._safe_float(spell_diag.get("max_magic"))
        self.mana_bar.setValue(int((spell_magic / spell_max * 100) if spell_max > 0 else 0))

        wrinkler_attached = self._safe_float(wrinkler_diag.get("attached"))
        wrinkler_max = self._safe_float(wrinkler_diag.get("max"))
        self.wrinkler_fill_bar.setValue(int((wrinkler_attached / wrinkler_max * 100) if wrinkler_max > 0 else 0))

        exposure = self._safe_float(bank_diag.get("portfolio_exposure_ratio"))
        self.stock_exposure_bar.setValue(int(exposure * 100))
        self.stock_exposure_label.setText(
            f"{exposure*100:.1f}% | {self._format_number(bank_diag.get('portfolio_exposure'))}"
        )

        ascension = self._safe_float(state.get("last_ascension", {}).get("legacyMeterPercent"))
        self.ascension_bar.setValue(int(ascension * 100))

        # Timing ETAs
        if building_price and cookies_ps > 0:
            eta = max(0, (self._safe_float(building_price) - cookies) / cookies_ps)
            self.timing_labels["purchase_cash_eta"].setText(
                f"{self._format_duration(eta)} | Shortfall: {self._format_number(max(0, self._safe_float(building_price) - cookies))}"
            )
            bank_ready = (cookies + wrinkler_bank) >= self._safe_float(building_price)
            self.timing_labels["purchase_bank_eta"].setText(
                "Ready with bank" if bank_ready else f"Need {self._format_number(max(0, self._safe_float(building_price) - (cookies + wrinkler_bank)))} more"
            )
        else:
            self.timing_labels["purchase_cash_eta"].setText("-")
            self.timing_labels["purchase_bank_eta"].setText("-")

        if upgrade_price and cookies_ps > 0:
            eta = max(0, (self._safe_float(upgrade_price) - cookies) / cookies_ps)
            self.timing_labels["upgrade_cash_eta"].setText(
                f"{self._format_duration(eta)} | Shortfall: {self._format_number(max(0, self._safe_float(upgrade_price) - cookies))}"
            )
            bank_ready = (cookies + wrinkler_bank) >= self._safe_float(upgrade_price)
            self.timing_labels["upgrade_bank_eta"].setText(
                "Ready with bank" if bank_ready else f"Need {self._format_number(max(0, self._safe_float(upgrade_price) - (cookies + wrinkler_bank)))} more"
            )
        else:
            self.timing_labels["upgrade_cash_eta"].setText("-")
            self.timing_labels["upgrade_bank_eta"].setText("-")

        self.timing_labels["garden_timers"].setText(
            f"Next tick: {garden_stats.get('next_tick', '-')} | Soil: {garden_stats.get('soil', '-')}"
        )
        self.timing_labels["combo_timing"].setText(
            f"{combo_stats.get('status', '-')} | Last run: {self._format_duration(combo_stats.get('last_duration'))}"
        )

        # Wrinkler timing - use wrinkler_diag
        wrinkler_diag = state.get("last_wrinkler_diag") or {}
        goal_eta = wrinkler_diag.get("goal_eta_seconds")
        if goal_eta:
            self.timing_labels["wrinkler_goal_eta"].setText(self._format_duration(goal_eta))
        else:
            self.timing_labels["wrinkler_goal_eta"].setText("-")

        target = wrinkler_diag.get("target")
        if target:
            self.timing_labels["wrinkler_target"].setText(str(target))
        else:
            self.timing_labels["wrinkler_target"].setText("-")

        # Trader portfolio data
        portfolio_val = trade_stats.get('portfolio_exposure')
        held_goods = trade_stats.get('held_goods', 0)
        held_shares = trade_stats.get('held_shares', 0)
        realized_pnl = trade_stats.get('realized_pnl', 0)
        unrealized_pnl = trade_stats.get('unrealized_pnl')
        session_roi = trade_stats.get('session_roi')
        
        pnl_line = ""
        if unrealized_pnl is not None:
            pnl_emoji = "📈" if unrealized_pnl >= 0 else "📉"
            pnl_line = f"{pnl_emoji} Unrealized: {self._format_number(unrealized_pnl)}"
            if session_roi is not None:
                roi_pct = float(session_roi) * 100
                pnl_line += f" ({roi_pct:+.1f}%)"
            pnl_line += "\n"
        
        self.trader_chart_label.setText(
            f"📊 Portfolio: {self._format_number(portfolio_val)}\n"
            f"📦 Holdings: {held_goods} goods, {held_shares} shares\n"
            f"{pnl_line}"
            f"💰 Realized P&L: {self._format_number(realized_pnl)}"
        )

    def _update_forecasts_tab(self, lump_diag, golden_diag):
        """Update forecasts tab widgets."""
        # Sugar lumps
        if lump_diag and lump_diag.get("unlocked"):
            lumps = lump_diag.get("lumps", 0)
            stage = lump_diag.get("stage", "-")
            type_name = lump_diag.get("current_type_name", "normal")
            time_to_ripe = lump_diag.get("time_to_ripe_seconds")
            time_to_overripe = lump_diag.get("time_to_overripe_seconds")
            modifiers = ", ".join(lump_diag.get("modifiers") or []) or "No active modifiers"
            self.lump_meta_label.setText(
                f"{lumps} lumps • Next: {stage} {type_name} lump • "
                f"Ripe in {self._format_duration(time_to_ripe)} • "
                f"Overripe in {self._format_duration(time_to_overripe)}"
            )
            self.lump_modifier_label.setText(modifiers)
            self.lump_chart_widget.set_data(lump_diag)
        else:
            self.lump_meta_label.setText("Sugar lumps are not unlocked yet.")
            self.lump_modifier_label.setText("-")
            self.lump_chart_widget.set_data({})

        # Golden cookies
        if golden_diag and golden_diag.get("available"):
            next_spawn = golden_diag.get("next_spawn_seconds")
            force_spawn = golden_diag.get("force_spawn_seconds")
            wrath = golden_diag.get("wrath_cookie", False)
            on_screen = golden_diag.get("on_screen", 0)
            spawn_windows = golden_diag.get("spawn_windows", [])
            self.gc_meta_label.setText(
                f"Next spawn: {self._format_duration(next_spawn)}"
                f"{' (Wrath)' if wrath else ''}"
            )
            self.gc_detail_label.setText(
                f"Force spawn: {self._format_duration(force_spawn)}" if force_spawn else "No force spawn pending"
            )
            # Update chart with full diagnostic data
            golden_diag["_meta"] = f"On screen: {on_screen} | Windows: {len(spawn_windows)}"
            self.gc_chart_widget.set_data(golden_diag)
        else:
            self.gc_meta_label.setText("Golden cookie timer data is unavailable.")
            self.gc_detail_label.setText("-")
            self.gc_chart_widget.set_data({})

    def _update_feed_tab(self, feed):
        """Update feed tab with color-coded events."""
        self.feed_text.clear()
        if not feed:
            self.feed_text.setPlainText("(no feed entries)")
            return

        for entry in reversed(feed):
            timestamp = self._safe_float(entry.get("timestamp"))
            message = entry.get("message", "")
            category = entry.get("category", "event")
            self.feed_text.append(f"{timestamp:.1f}s: {message}")

    def _update_diagnostics_tab(self, shimmer_stats, building_entries, building_stats):
        """Update diagnostics tab widgets."""
        # Shimmer RNG
        total = shimmer_stats.get("total", 0)
        positive = shimmer_stats.get("positive", 0)
        negative = shimmer_stats.get("negative", 0)
        neutral = shimmer_stats.get("neutral", 0)
        seeds = shimmer_stats.get("seeds_captured", 0)
        ready = total >= 100 and seeds >= 20

        self.shimmer_progress.setValue(min(100, int((total / 100.0) * 100)))
        if ready:
            self.shimmer_rng_status.setText(f"READY {total}/100 samples")
            self.shimmer_rng_status.setStyleSheet(theme.accent_green_small_label_style())
        else:
            self.shimmer_rng_status.setText(f"Collecting {total}/100 samples")
            self.shimmer_rng_status.setStyleSheet(theme.shimmer_yellow_small_label_style())

        self.shimmer_stats_detail.setText(
            f"+{positive} -{negative} ={neutral} | Seeds: {seeds}/20"
        )

    def _create_building_cap_row(self, name):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(5, 5, 5, 5)

        name_label = QLabel(name)
        summary_label = QLabel("Owned: - | Cap: - | Remaining: -")
        row_layout.addWidget(name_label)
        row_layout.addWidget(summary_label, 1)

        ignore_check = QCheckBox("Ignore")
        if self.set_building_cap_ignored:
            ignore_check.stateChanged.connect(
                lambda state, n=name: self.set_building_cap_ignored(n, bool(state))
            )
        row_layout.addWidget(ignore_check)

        cap_input = QLineEdit()
        cap_input.setPlaceholderText("Manual cap")
        cap_input.setMaximumWidth(80)
        cap_input.returnPressed.connect(lambda n=name, inp=cap_input: self._apply_building_cap(n, inp))
        row_layout.addWidget(cap_input)

        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet(theme.button_style("secondary"))
        if self.set_building_cap:
            apply_btn.clicked.connect(
                lambda checked=False, n=name, inp=cap_input: self._apply_building_cap(n, inp)
            )
        row_layout.addWidget(apply_btn)

        return {
            "widget": row,
            "name": name_label,
            "summary": summary_label,
            "ignore": ignore_check,
            "cap_input": cap_input,
            "apply": apply_btn,
        }

    def _update_building_caps(self, building_entries, building_stats):
        ignored = set(building_stats.get("ignored_building_caps") or [])
        self.building_caps_meta.setText(
            f"{len(building_entries)} buildings | ignored {len(ignored)}"
        )

        seen_names = set()
        for entry in building_entries:
            if not isinstance(entry, dict) or not entry.get("name"):
                continue
            name = entry["name"]
            seen_names.add(name)
            amount = entry.get("amount", 0)
            cap = entry.get("cap", "-")
            remaining = entry.get("remaining_to_cap", "-")
            manual_cap = entry.get("manual_cap")
            cap_ignored = entry.get("cap_ignored") or name in ignored

            row = self.building_cap_rows.get(name)
            if row is None:
                row = self._create_building_cap_row(name)
                self.building_cap_rows[name] = row
                self.building_caps_layout.addWidget(row["widget"])

            row["widget"].setVisible(True)
            row["summary"].setText(f"Owned: {amount} | Cap: {cap} | Remaining: {remaining}")
            row["ignore"].blockSignals(True)
            row["ignore"].setChecked(bool(cap_ignored))
            row["ignore"].blockSignals(False)

            if not row["cap_input"].hasFocus() and not row["cap_input"].isModified():
                row["cap_input"].setText(str(manual_cap) if manual_cap is not None else "")
                row["cap_input"].setModified(False)

        for name, row in self.building_cap_rows.items():
            if name not in seen_names:
                row["widget"].setVisible(False)

    def _update_status_logs_tab(self, state, feed):
        """Update status & logs tab with current state."""
        # Update metric labels
        if hasattr(self, 'metric_labels'):
            # Total Cookies Clicked - use main_clicks from state
            clicks = state.get("main_clicks", 0)
            self.metric_labels.get("click_count_label").setText(self._format_number(clicks))
            
            # Shimmer Cookie Count
            shimmers = state.get("shimmer_clicks", 0)
            self.metric_labels.get("shimmer_stats_label").setText(str(shimmers))
            
            # Last Bot Action - find the most recent action
            last_action = "Idle"
            for key, label in [
                ("last_spell_cast", "Spell"),
                ("last_trade_action", "Trade"),
                ("last_building_action", "Building"),
                ("last_garden_action", "Garden"),
                ("last_wrinkler_action", "Wrinkler"),
                ("last_lump_action", "Lump"),
            ]:
                value = state.get(key)
                if value:
                    last_action = f"{label}: {value}"
                    break
            self.metric_labels.get("last_action_label").setText(last_action)
            
            # Feed Parse Age - use last_feed_age
            feed_age = state.get("last_feed_age", "0s")
            self.metric_labels.get("feed_parse_age_label").setText(feed_age)
        
        # Update events log
        if hasattr(self, 'events_log'):
            self.events_log.clear()
            if feed:
                for entry in reversed(feed[-20:]):  # Show last 20 entries
                    timestamp = self._safe_float(entry.get("timestamp"))
                    message = entry.get("message", "")
                    self.events_log.append(f"{timestamp:.1f}s: {message}")
            else:
                self.events_log.setPlainText("(no feed entries)")

    def _update_building_stats_tab(self, building_stats, building_entries):
        """Update building stats tab."""
        # Update table with building entries
        if hasattr(self, 'building_stats_table') and building_entries:
            self.building_stats_table.setRowCount(len(building_entries))
            for row, entry in enumerate(building_entries):
                name = entry.get("name", "-")
                amount = entry.get("amount", 0)
                cap = entry.get("cap", "-")
                
                self.building_stats_table.setItem(row, 0, QTableWidgetItem(name))
                self.building_stats_table.setItem(row, 1, QTableWidgetItem(self._format_number(amount)))
                self.building_stats_table.setItem(row, 2, QTableWidgetItem(str(cap) if cap != "-" else "-"))
            
            self.building_stats_table.resizeColumnsToContents()
        
        # Update stats summary
        if hasattr(self, 'stats_summary'):
            total_purchases = building_stats.get("total_purchases", 0)
            total_gold = building_stats.get("total_gold_spent", 0)
            self.stats_summary.setText(
                f"Purchases Completed: {self._format_number(total_purchases)} | Total Gold Spent: {self._format_number(total_gold)}"
            )
        
        # Update cap ignore toggle state if exists
        if hasattr(self, 'cap_ignore_toggle'):
            ignored = building_stats.get("ignored_building_caps") or []
            # This is a simple representation; in reality would need more logic
            pass

    def _update_garden_automation_tab(self, garden_stats, garden_diag):
        """Update garden automation tab."""
        # Update progress bar
        if hasattr(self, 'garden_progress_bar'):
            progress = garden_stats.get("progress", 0)
            if isinstance(progress, (int, float)):
                self.garden_progress_bar.setValue(int(progress))
            else:
                self.garden_progress_bar.setValue(65)  # default mock
        
        # Update soil type
        if hasattr(self, 'garden_soil_value'):
            soil = garden_diag.get("soil") or garden_stats.get("soil") or "Unknown"
            self.garden_soil_value.setText(str(soil))
        
        # Update planting cycle (from garden_diag)
        if hasattr(self, 'garden_cycle_value'):
            cycle = garden_diag.get("next_tick") or garden_stats.get("next_tick") or "-"
            if cycle != "-":
                self.garden_cycle_value.setText(cycle)
            else:
                self.garden_cycle_value.setText("Ready")
        
        # Update status label
        if hasattr(self, 'garden_status_label'):
            status = garden_stats.get("status") or "Active"
            last_garden = garden_stats.get("last_garden") or "None"
            self.garden_status_label.setText(f"Status: {status} - Last: {last_garden}")
        
        # Update mode label
        if hasattr(self, 'garden_mode_label'):
            mode = garden_stats.get("mode") or "auto"
            self.garden_mode_label.setText(mode.capitalize())
            # Color code based on mode
            if mode == "off":
                self.garden_mode_label.setStyleSheet(theme.accent_red_color_style())
            elif mode == "shimmerlilly":
                self.garden_mode_label.setStyleSheet(theme.shimmer_yellow_color_style())
            else:
                self.garden_mode_label.setStyleSheet(theme.accent_green_color_style())

    def _update_settings_tab(self):
        """Update settings tab widgets."""
        if self.get_config:
            try:
                config = self.get_config()
                path = config.get("game_install_dir", "")
                self.game_path_entry.setText(path)
                if path:
                    self._validate_and_update_path_status(path)
            except Exception:
                pass

    def _save_config(self):
        """Save configuration."""
        if not self.save_config:
            return
        path = self.game_path_entry.text().strip()
        if path:
            is_valid, message = _validate_game_path(path)
            if not is_valid:
                self._show_warning(
                    "Invalid Game Path",
                    f"The path appears to be invalid: {message}\n\nPlease correct the path before saving."
                )
                return
        
        try:
            config = {}
            if self.get_config:
                config = self.get_config() or {}
            config["game_install_dir"] = path
            self.save_config(config)
            self.config_status_label.setText("✅ Configuration saved!")
        except Exception as e:
            self.config_status_label.setText(f"❌ Error: {e}")

    def _browse_game_directory(self):
        """Open file dialog to browse for game directory."""
        from PySide6.QtWidgets import QFileDialog
        current_dir = self.game_path_entry.text() or ""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Cookie Clicker Installation Directory",
            current_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if dir_path:
            self.game_path_entry.setText(dir_path)
            self._validate_and_update_path_status(dir_path)

    def _auto_detect_game_path_action(self):
        """Attempt to auto-detect game path and update the entry field."""
        detected_path = _auto_detect_game_path()
        if detected_path:
            self.game_path_entry.setText(detected_path)
            self._validate_and_update_path_status(detected_path)
            self.config_status_label.setText(f"✅ Auto-detected: {detected_path}")
        else:
            self._show_warning(
                "Game Not Found",
                "Could not auto-detect Cookie Clicker installation.\n\n"
                "Please browse manually to the folder containing 'Cookie Clicker.exe'."
            )

    def _validate_and_update_path_status(self, path_str: str):
        """Validate the path and update the status label."""
        is_valid, message = _validate_game_path(path_str)
        if is_valid:
            self.game_path_status_label.setText(f"✅ {message}")
        else:
            self.game_path_status_label.setText(f"⚠️ {message}")

    def _apply_building_cap(self, building_name, input_widget):
        """Apply building cap from input field."""
        if not self.set_building_cap:
            return
        text = input_widget.text().strip()
        try:
            cap = None if text == "" else int(text)
            self.set_building_cap(building_name, cap)
            input_widget.setModified(False)
            input_widget.clearFocus()
        except ValueError:
            pass

    def _on_upgrade_horizon_slider_changed(self, minutes):
        """Handle upgrade horizon slider value change."""
        # Update value label
        self.upgrade_horizon_value_label.setText(f"{minutes}m")
        
        # Skip if we're syncing from external state
        if hasattr(self, '_syncing_horizons') and self._syncing_horizons:
            return
        
        # Convert to seconds and call setter
        seconds = minutes * 60
        if self.set_upgrade_horizon_seconds:
            ok, result = self.set_upgrade_horizon_seconds(seconds)
            if ok:
                self.upgrade_horizon_status.setText(f"✅ Upgrade horizon set to {minutes}m")
                # Update slider to exact value (in case setter adjusted it)
                if isinstance(result, (int, float)):
                    actual_minutes = max(1, int(round(float(result) / 60.0)))
                    if actual_minutes != minutes:
                        self.upgrade_horizon_slider.setValue(actual_minutes)
            else:
                self.upgrade_horizon_status.setText(f"❌ Failed: {result}")
    
    def _on_building_horizon_slider_changed(self, minutes):
        """Handle building horizon slider value change."""
        # Update value label
        self.building_horizon_value_label.setText(f"{minutes}m")
        
        # Skip if we're syncing from external state
        if hasattr(self, '_syncing_horizons') and self._syncing_horizons:
            return
        
        # Convert to seconds and call setter
        seconds = minutes * 60
        if self.set_building_horizon_seconds:
            ok, result = self.set_building_horizon_seconds(seconds)
            if ok:
                self.building_horizon_status.setText(f"✅ Building horizon set to {minutes}m")
                # Update slider to exact value (in case setter adjusted it)
                if isinstance(result, (int, float)):
                    actual_minutes = max(1, int(round(float(result) / 60.0)))
                    if actual_minutes != minutes:
                        self.building_horizon_slider.setValue(actual_minutes)
            else:
                self.building_horizon_status.setText(f"❌ Failed: {result}")

    def _sync_horizon_inputs(self, *, upgrade_horizon_seconds=None, building_horizon_seconds=None):
        """Sync horizon slider values from current state."""
        # Prevent recursive updates
        if hasattr(self, '_syncing_horizons') and self._syncing_horizons:
            return
        self._syncing_horizons = True
        
        try:
            if upgrade_horizon_seconds is not None:
                minutes = max(1, min(180, int(round(float(upgrade_horizon_seconds) / 60.0))))
                if self.upgrade_horizon_slider.value() != minutes:
                    self.upgrade_horizon_slider.setValue(minutes)
                    self.upgrade_horizon_value_label.setText(f"{minutes}m")
            
            if building_horizon_seconds is not None:
                minutes = max(1, min(180, int(round(float(building_horizon_seconds) / 60.0))))
                if self.building_horizon_slider.value() != minutes:
                    self.building_horizon_slider.setValue(minutes)
                    self.building_horizon_value_label.setText(f"{minutes}m")
        finally:
            self._syncing_horizons = False

    def _apply_horizon_preset(self, minutes):
        """Apply horizon preset (in minutes) to building horizon slider."""
        # Clip to slider range
        minutes = max(1, min(180, minutes))
        self.building_horizon_slider.setValue(minutes)
        # Also update upgrade horizon if it's a common preset?
        # For now, just update building horizon.
        # Call the slider change handler to apply the change
        self._on_building_horizon_slider_changed(minutes)

    def _format_number(self, value):
        """Format large numbers with suffixes (K, M, B, T)."""
        if value is None:
            return "-"
        try:
            num = float(value)
        except (ValueError, TypeError):
            return str(value)

        abs_num = abs(num)
        if abs_num >= 1e12:
            return f"{num/1e12:.3f}T"
        if abs_num >= 1e9:
            return f"{num/1e9:.3f}B"
        if abs_num >= 1e6:
            return f"{num/1e6:.3f}M"
        if abs_num >= 1e3:
            return f"{num/1e3:.3f}K"
        return f"{num:.2f}"

    def _safe_float(self, value, default=0.0):
        """Safely convert value to float, returning default on failure."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _format_duration(self, seconds):
        """Format duration in seconds to human-readable string."""
        if seconds is None:
            return "-"
        try:
            seconds = max(0, int(round(float(seconds))))
        except (ValueError, TypeError):
            return "-"
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    def closeEvent(self, event):
        """Handle window close."""
        self.timer.stop()
        super().closeEvent(event)
