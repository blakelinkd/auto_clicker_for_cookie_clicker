import logging
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

log = logging.getLogger(__name__)


def _format_number(value):
    if value is None:
        return "-"
    abs_value = abs(float(value))
    if abs_value >= 1e12:
        return f"{value/1e12:.3f}T"
    if abs_value >= 1e9:
        return f"{value/1e9:.3f}B"
    if abs_value >= 1e6:
        return f"{value/1e6:.3f}M"
    if abs_value >= 1e3:
        return f"{value/1e3:.3f}K"
    return f"{float(value):.2f}"


def _format_percent(value):
    if value is None:
        return "-"
    return f"{100.0 * float(value):.0f}%"


def _latest_non_null_metric(history, key):
    for point in reversed(history or []):
        value = point.get(key)
        if value is not None:
            return value
    return None


def _format_duration(seconds):
    if seconds is None:
        return "-"
    seconds = max(0, int(round(float(seconds))))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _format_reason_label(reason):
    if reason is None:
        return "-"
    text = str(reason).strip()
    if not text:
        return "-"
    return text.replace("_", " ")


def _progress_fraction(current, total):
    if total is None or float(total) <= 0:
        return 0.0
    return max(0.0, min(1.0, float(current) / float(total)))


def _first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text != "-":
            return text
    return "-"


def _lock_panel_size(widget, *, width=None, height=None):
    if width is not None:
        widget.configure(width=int(width))
    if height is not None:
        widget.configure(height=int(height))
    if width is None or height is None:
        return
    try:
        widget.grid_propagate(False)
    except Exception:
        pass
    try:
        widget.pack_propagate(False)
    except Exception:
        pass


class BotDashboard:
    def __init__(
        self,
        *,
        get_dashboard_state,
        toggle_active,
        toggle_main_autoclick,
        toggle_shimmer_autoclick,
        toggle_stock_buying,
        toggle_lucky_reserve,
        toggle_building_buying,
        toggle_upgrade_buying,
        toggle_ascension_prep,
        set_upgrade_horizon_seconds,
        set_building_horizon_seconds,
        set_building_cap,
        set_building_cap_ignored,
        cycle_wrinkler_mode,
        exit_program,
        dump_shimmer_data=None,
        initial_geometry=None,
        refresh_interval_ms=500,
    ):
        self.get_dashboard_state = get_dashboard_state
        self.toggle_active = toggle_active
        self.toggle_main_autoclick = toggle_main_autoclick
        self.toggle_shimmer_autoclick = toggle_shimmer_autoclick
        self.toggle_stock_buying = toggle_stock_buying
        self.toggle_lucky_reserve = toggle_lucky_reserve
        self.toggle_building_buying = toggle_building_buying
        self.toggle_upgrade_buying = toggle_upgrade_buying
        self.toggle_ascension_prep = toggle_ascension_prep
        self.set_upgrade_horizon_seconds = set_upgrade_horizon_seconds
        self.set_building_horizon_seconds = set_building_horizon_seconds
        self.set_building_cap = set_building_cap
        self.set_building_cap_ignored = set_building_cap_ignored
        self.cycle_wrinkler_mode = cycle_wrinkler_mode
        self.exit_program = exit_program
        self.dump_shimmer_data = dump_shimmer_data
        self.initial_geometry = initial_geometry
        self.refresh_interval_ms = int(refresh_interval_ms)
        self.building_cap_rows = {}
        self._ignore_horizon_change = False
        self.toggle_buttons = {}
        self.action_buttons = {}

        self.root = tk.Tk()
        self.root.title("Cookie Clicker Bot Dashboard")
        self.root.geometry(self.initial_geometry or "1320x840")
        self.root.minsize(1100, 720)
        self.root.configure(bg="#11161c")
        self.root.protocol("WM_DELETE_WINDOW", self.exit_program)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background="#11161c", foreground="#e7edf4", fieldbackground="#1b2530")
        style.configure("Card.TLabelframe", background="#16202a", foreground="#f7fbff", borderwidth=1)
        style.configure("Card.TLabelframe.Label", background="#16202a", foreground="#f7fbff")
        style.configure("Data.TLabel", background="#16202a", foreground="#e7edf4", font=("Segoe UI", 10))
        style.configure("Value.TLabel", background="#16202a", foreground="#ffffff", font=("Segoe UI Semibold", 12))
        style.configure("Hero.TLabel", background="#0f1720", foreground="#ffffff", font=("Segoe UI Semibold", 16))
        style.configure("Muted.TLabel", background="#16202a", foreground="#9cb0c3", font=("Segoe UI", 9))
        style.configure("Accent.Horizontal.TProgressbar", background="#3ecf8e", troughcolor="#223142", bordercolor="#223142")
        style.configure("Info.Horizontal.TProgressbar", background="#55b6ff", troughcolor="#223142", bordercolor="#223142")
        style.configure("Warn.Horizontal.TProgressbar", background="#ffb14a", troughcolor="#223142", bordercolor="#223142")
        style.configure("Action.TButton", font=("Segoe UI", 10))

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1, minsize=640)

        self._build_header()
        self._build_tabs()

    def _create_scrollable_tab(self, notebook):
        outer = ttk.Frame(notebook, style="Card.TLabelframe")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        canvas = tk.Canvas(
            outer,
            bg="#11161c",
            highlightthickness=0,
            relief=tk.FLAT,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas, style="Card.TLabelframe")

        canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _sync_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_width(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-event.delta / 120), "units")
            elif getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")

        def _bind_mousewheel(_event=None):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(_event=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        body.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_width)
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        body.bind("<Enter>", _bind_mousewheel)
        body.bind("<Leave>", _unbind_mousewheel)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        return outer, body

    def _build_header(self):
        frame = ttk.LabelFrame(self.root, text="Overview", style="Card.TLabelframe", padding=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 8))
        frame.grid_columnconfigure(0, weight=3)
        frame.grid_columnconfigure(1, weight=2)

        left = ttk.Frame(frame, style="Card.TLabelframe")
        left.grid(row=0, column=0, sticky="nsew")
        right = ttk.Frame(frame, style="Card.TLabelframe")
        right.grid(row=0, column=1, sticky="ne", padx=(12, 0))
        left.grid_columnconfigure(0, weight=1, minsize=720)

        self.hero_label = ttk.Label(left, text="Initializing...", style="Hero.TLabel")
        self.hero_label.grid(row=0, column=0, sticky="w")
        self.meta_label = ttk.Label(left, text="-", style="Data.TLabel", wraplength=720)
        self.meta_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.last_actions_label = ttk.Label(left, text="-", style="Muted.TLabel", wraplength=720)
        self.last_actions_label.grid(row=2, column=0, sticky="w", pady=(6, 0))

        self.toggle_buttons["active"] = self._create_toggle_button(right, 0, "Bot", self.toggle_active)
        self.toggle_buttons["stock"] = self._create_toggle_button(right, 1, "Stock Buy", self.toggle_stock_buying)
        self.toggle_buttons["lucky_reserve"] = self._create_toggle_button(right, 2, "Lucky Reserve", self.toggle_lucky_reserve)
        self.toggle_buttons["building"] = self._create_toggle_button(right, 3, "Building Buy", self.toggle_building_buying)
        self.toggle_buttons["upgrade"] = self._create_toggle_button(right, 4, "Upgrade Buy", self.toggle_upgrade_buying)
        self.toggle_buttons["ascension"] = self._create_toggle_button(right, 5, "Ascension Prep", self.toggle_ascension_prep)
        ttk.Button(right, text="Wrinkler Mode", command=self.cycle_wrinkler_mode, style="Action.TButton").grid(row=0, column=6, padx=4, pady=4)
        ttk.Button(right, text="Exit", command=self.exit_program, style="Action.TButton").grid(row=0, column=7, padx=4, pady=4)
        self.action_buttons["main_autoclick"] = self._create_toggle_button(
            right, 0, "Autoclick", self.toggle_main_autoclick, row=1
        )
        self.action_buttons["shimmer_autoclick"] = self._create_toggle_button(
            right, 1, "GC/Wrath Click", self.toggle_shimmer_autoclick, row=1
        )

    def _create_toggle_button(self, parent, column, label, command, row=0):
        button = tk.Button(
            parent,
            text=label,
            command=command,
            bg="#7f1d1d",
            fg="#f8fafc",
            activebackground="#991b1b",
            activeforeground="#f8fafc",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=6,
            font=("Segoe UI", 10, "bold"),
            highlightthickness=0,
        )
        button.grid(row=row, column=column, padx=4, pady=4)
        return button

    def _set_toggle_button_state(self, key, label, enabled):
        button = self.toggle_buttons.get(key)
        if button is None:
            return
        if enabled:
            background = "#166534"
            active_background = "#15803d"
            status = "ON"
        else:
            background = "#991b1b"
            active_background = "#b91c1c"
            status = "OFF"
        button.configure(
            text=f"{label}: {status}",
            bg=background,
            activebackground=active_background,
        )

    def _set_action_button_state(self, key, label, enabled):
        button = self.action_buttons.get(key)
        if button is None:
            return
        if enabled:
            background = "#1d4ed8"
            active_background = "#2563eb"
            status = "ON"
        else:
            background = "#4b5563"
            active_background = "#6b7280"
            status = "OFF"
        button.configure(
            text=f"{label}: {status}",
            bg=background,
            activebackground=active_background,
        )

    def _build_tabs(self):
        notebook = ttk.Notebook(self.root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.notebook = notebook

        gameplay_tab, gameplay = self._create_scrollable_tab(notebook)
        forecasts_tab, forecasts = self._create_scrollable_tab(notebook)
        feed_tab, feed = self._create_scrollable_tab(notebook)
        diagnostics_tab, diagnostics = self._create_scrollable_tab(notebook)
        gameplay.grid_columnconfigure(0, weight=3)
        gameplay.grid_columnconfigure(1, weight=2)
        gameplay.grid_rowconfigure(0, weight=1, minsize=320)
        gameplay.grid_rowconfigure(1, weight=1, minsize=320)
        forecasts.grid_columnconfigure(0, weight=1)
        forecasts.grid_rowconfigure(0, weight=0, minsize=220)
        forecasts.grid_rowconfigure(1, weight=0, minsize=210)
        feed.grid_columnconfigure(0, weight=1)
        feed.grid_rowconfigure(0, weight=1)
        diagnostics.grid_columnconfigure(0, weight=1)
        diagnostics.grid_rowconfigure(0, weight=1)

        notebook.add(gameplay_tab, text="Gameplay")
        notebook.add(forecasts_tab, text="Forecasts")
        notebook.add(feed_tab, text="Feed")
        notebook.add(diagnostics_tab, text="Diagnostics")

        self._build_purchase_panel(gameplay)
        self._build_status_panel(gameplay)
        self._build_trader_panel(gameplay)
        self._build_lump_panel(forecasts, row=0, column=0, pady=0)
        self._build_golden_cookie_panel(forecasts, row=1, column=0, pady=(8, 0))
        self._build_feed_panel(feed)
        self._build_diagnostics_panel(diagnostics)

    def _build_purchase_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Purchase Progress", style="Card.TLabelframe", padding=12)
        frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 8), pady=0)
        _lock_panel_size(frame, width=720)
        frame.grid_columnconfigure(0, weight=1)

        self.purchase_title = ttk.Label(frame, text="Next building", style="Value.TLabel")
        self.purchase_title.grid(row=0, column=0, sticky="w")
        self.purchase_detail = ttk.Label(frame, text="-", style="Data.TLabel", wraplength=560)
        self.purchase_detail.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self._build_horizon_controls(
            frame,
            row=2,
            prefix="building",
            title="Building Horizon",
            description="Ideal: 30-90m. Shorter buys faster CPS, longer chases better ROI.",
            apply_command=self._apply_building_horizon,
        )

        self.purchase_cash_bar = ttk.Progressbar(frame, maximum=100, style="Info.Horizontal.TProgressbar")
        self.purchase_cash_bar.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        self.purchase_cash_label = ttk.Label(frame, text="-", style="Muted.TLabel")
        self.purchase_cash_label.grid(row=6, column=0, sticky="w", pady=(4, 0))

        self.purchase_bank_bar = ttk.Progressbar(frame, maximum=100, style="Accent.Horizontal.TProgressbar")
        self.purchase_bank_bar.grid(row=7, column=0, sticky="ew", pady=(12, 0))
        self.purchase_bank_label = ttk.Label(frame, text="-", style="Muted.TLabel")
        self.purchase_bank_label.grid(row=8, column=0, sticky="w", pady=(4, 0))

        ttk.Separator(frame).grid(row=9, column=0, sticky="ew", pady=14)

        self.upgrade_title = ttk.Label(frame, text="Next upgrade", style="Value.TLabel")
        self.upgrade_title.grid(row=10, column=0, sticky="w")
        self.upgrade_detail = ttk.Label(frame, text="-", style="Data.TLabel", wraplength=560)
        self.upgrade_detail.grid(row=11, column=0, sticky="w", pady=(4, 0))

        self._build_horizon_controls(
            frame,
            row=12,
            prefix="upgrade",
            title="Upgrade Horizon",
            description="Ideal: 1-3h. Longer horizons surface fewer but stronger medium-term upgrades.",
            apply_command=self._apply_upgrade_horizon,
        )

        self.upgrade_cash_bar = ttk.Progressbar(frame, maximum=100, style="Warn.Horizontal.TProgressbar")
        self.upgrade_cash_bar.grid(row=15, column=0, sticky="ew", pady=(12, 0))
        self.upgrade_cash_label = ttk.Label(frame, text="-", style="Muted.TLabel")
        self.upgrade_cash_label.grid(row=16, column=0, sticky="w", pady=(4, 0))

        self.upgrade_bank_bar = ttk.Progressbar(frame, maximum=100, style="Accent.Horizontal.TProgressbar")
        self.upgrade_bank_bar.grid(row=17, column=0, sticky="ew", pady=(12, 0))
        self.upgrade_bank_label = ttk.Label(frame, text="-", style="Muted.TLabel")
        self.upgrade_bank_label.grid(row=18, column=0, sticky="w", pady=(4, 0))

        ttk.Label(frame, text="Lucky reserve", style="Muted.TLabel").grid(row=19, column=0, sticky="w", pady=(12, 0))
        self.lucky_reserve_bar = ttk.Progressbar(frame, maximum=100, style="Warn.Horizontal.TProgressbar")
        self.lucky_reserve_bar.grid(row=20, column=0, sticky="ew", pady=(8, 0))
        self.lucky_reserve_label = ttk.Label(frame, text="-", style="Muted.TLabel")
        self.lucky_reserve_label.grid(row=21, column=0, sticky="w", pady=(4, 0))

    def _build_status_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Live Status", style="Card.TLabelframe", padding=12)
        frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        self.summary_vars = {}
        rows = [
            ("cookies", "Cookies"),
            ("spell", "Spell"),
            ("stock", "Stocks"),
            ("buildings", "Buildings"),
            ("garden", "Garden"),
            ("combo", "Combo"),
            ("perf", "Loop perf"),
            ("buffs", "Buffs"),
        ]
        for index, (key, label) in enumerate(rows):
            ttk.Label(frame, text=label, style="Muted.TLabel").grid(row=index, column=0, sticky="nw", pady=4)
            var = tk.StringVar(value="-")
            self.summary_vars[key] = var
            ttk.Label(
                frame,
                textvariable=var,
                style="Data.TLabel",
                wraplength=360,
                width=42,
                justify="left",
            ).grid(row=index, column=1, sticky="nw", pady=4)
            frame.grid_rowconfigure(index, minsize=30)

        ttk.Separator(frame).grid(row=len(rows), column=0, columnspan=2, sticky="ew", pady=12)

        ttk.Label(frame, text="Mana", style="Muted.TLabel").grid(row=len(rows) + 1, column=0, sticky="w")
        self.mana_bar = ttk.Progressbar(frame, maximum=100, style="Info.Horizontal.TProgressbar")
        self.mana_bar.grid(row=len(rows) + 1, column=1, sticky="ew")

        ttk.Label(frame, text="Wrinkler fill", style="Muted.TLabel").grid(row=len(rows) + 2, column=0, sticky="w", pady=(8, 0))
        self.wrinkler_fill_bar = ttk.Progressbar(frame, maximum=100, style="Warn.Horizontal.TProgressbar")
        self.wrinkler_fill_bar.grid(row=len(rows) + 2, column=1, sticky="ew", pady=(8, 0))

        ttk.Label(frame, text="Stock exposure", style="Muted.TLabel").grid(row=len(rows) + 3, column=0, sticky="w", pady=(8, 0))
        self.stock_exposure_bar = ttk.Progressbar(frame, maximum=100, style="Accent.Horizontal.TProgressbar")
        self.stock_exposure_bar.grid(row=len(rows) + 3, column=1, sticky="ew", pady=(8, 0))
        self.stock_exposure_label = ttk.Label(frame, text="-", style="Muted.TLabel")
        self.stock_exposure_label.grid(row=len(rows) + 4, column=1, sticky="w", pady=(4, 0))

        ttk.Label(frame, text="Ascension", style="Muted.TLabel").grid(row=len(rows) + 5, column=0, sticky="w", pady=(8, 0))
        self.ascension_bar = ttk.Progressbar(frame, maximum=100, style="Info.Horizontal.TProgressbar")
        self.ascension_bar.grid(row=len(rows) + 5, column=1, sticky="ew", pady=(8, 0))

        ttk.Separator(frame).grid(row=len(rows) + 6, column=0, columnspan=2, sticky="ew", pady=12)
        ttk.Label(frame, text="Timing & Targets", style="Value.TLabel").grid(row=len(rows) + 7, column=0, columnspan=2, sticky="w")

        self.timing_vars = {}
        timing_rows = [
            ("purchase_cash_eta", "Purchase cash ETA"),
            ("purchase_bank_eta", "Purchase with bank"),
            ("upgrade_cash_eta", "Upgrade cash ETA"),
            ("upgrade_bank_eta", "Upgrade with bank"),
            ("wrinkler_goal_eta", "Wrinkler goal"),
            ("wrinkler_target", "Wrinkler target"),
            ("garden_timers", "Garden timers"),
            ("combo_timing", "Combo timing"),
        ]
        for offset, (key, label) in enumerate(timing_rows, start=len(rows) + 8):
            ttk.Label(frame, text=label, style="Muted.TLabel").grid(row=offset, column=0, sticky="nw", pady=4)
            var = tk.StringVar(value="-")
            self.timing_vars[key] = var
            ttk.Label(
                frame,
                textvariable=var,
                style="Data.TLabel",
                wraplength=360,
                width=42,
                justify="left",
            ).grid(row=offset, column=1, sticky="nw", pady=4)
            frame.grid_rowconfigure(offset, minsize=30)

    def _build_horizon_controls(self, parent, *, row, prefix, title, description, apply_command):
        box = ttk.Frame(parent, style="Card.TLabelframe")
        box.grid(row=row, column=0, sticky="ew", pady=(10, 0))
        box.grid_columnconfigure(6, weight=1)

        ttk.Label(box, text=title, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(box, text=description, style="Muted.TLabel").grid(row=1, column=0, columnspan=7, sticky="w", pady=(2, 6))

        hours_var = tk.StringVar(value="0")
        minutes_var = tk.StringVar(value="30")
        setattr(self, f"{prefix}_hours_var", hours_var)
        setattr(self, f"{prefix}_minutes_var", minutes_var)

        ttk.Label(box, text="Hours", style="Muted.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(box, from_=0, to=12, width=4, textvariable=hours_var, wrap=False).grid(row=2, column=1, sticky="w", padx=(4, 12))
        ttk.Label(box, text="Minutes", style="Muted.TLabel").grid(row=2, column=2, sticky="w")
        ttk.Spinbox(box, from_=0, to=59, width=4, textvariable=minutes_var, wrap=False).grid(row=2, column=3, sticky="w", padx=(4, 12))
        ttk.Button(box, text="Apply", command=apply_command, style="Action.TButton").grid(row=2, column=4, sticky="w")

        preset_frame = ttk.Frame(box, style="Card.TLabelframe")
        preset_frame.grid(row=3, column=0, columnspan=7, sticky="w", pady=(6, 0))
        for index, minutes in enumerate((3, 15, 30, 60, 120, 180)):
            ttk.Button(
                preset_frame,
                text=self._label_for_minutes(minutes),
                command=lambda value=minutes, target=prefix, callback=apply_command: self._apply_horizon_preset(target, value, callback),
                style="Action.TButton",
            ).grid(row=0, column=index, padx=(0, 6))

        status = ttk.Label(box, text="-", style="Muted.TLabel")
        status.grid(row=4, column=0, columnspan=7, sticky="w", pady=(6, 0))
        setattr(self, f"{prefix}_horizon_status", status)

    def _label_for_minutes(self, minutes):
        if minutes % 60 == 0:
            return f"{minutes // 60}h"
        return f"{minutes}m"

    def _apply_horizon_preset(self, prefix, total_minutes, callback):
        self._set_horizon_inputs(prefix, total_minutes * 60.0)
        callback()

    def _set_horizon_inputs(self, prefix, horizon_seconds):
        total_minutes = max(1, int(round(float(horizon_seconds) / 60.0)))
        hours, minutes = divmod(total_minutes, 60)
        self._ignore_horizon_change = True
        try:
            getattr(self, f"{prefix}_hours_var").set(str(hours))
            getattr(self, f"{prefix}_minutes_var").set(str(minutes))
        finally:
            self._ignore_horizon_change = False

    def _read_horizon_seconds(self, prefix):
        hours_text = getattr(self, f"{prefix}_hours_var").get().strip() or "0"
        minutes_text = getattr(self, f"{prefix}_minutes_var").get().strip() or "0"
        hours = max(0, int(hours_text))
        minutes = max(0, int(minutes_text))
        total_minutes = (hours * 60) + minutes
        if total_minutes <= 0:
            raise ValueError("set at least 1 minute")
        return float(total_minutes * 60)

    def _apply_upgrade_horizon(self):
        if self._ignore_horizon_change:
            return
        self._apply_horizon_change("upgrade", self.set_upgrade_horizon_seconds)

    def _apply_building_horizon(self):
        if self._ignore_horizon_change:
            return
        self._apply_horizon_change("building", self.set_building_horizon_seconds)

    def _apply_horizon_change(self, prefix, setter):
        status = getattr(self, f"{prefix}_horizon_status")
        try:
            horizon_seconds = self._read_horizon_seconds(prefix)
        except Exception as exc:
            status.configure(text=f"Invalid horizon: {exc}")
            return
        ok, result = setter(horizon_seconds)
        if ok:
            self._set_horizon_inputs(prefix, result)
            status.configure(text=f"Applied {_format_duration(result)} horizon.")
        else:
            status.configure(text=f"Update failed: {result}")

    def _sync_horizon_inputs(self, *, upgrade_horizon_seconds, building_horizon_seconds):
        if upgrade_horizon_seconds is not None:
            self._set_horizon_inputs("upgrade", upgrade_horizon_seconds)
        if building_horizon_seconds is not None:
            self._set_horizon_inputs("building", building_horizon_seconds)

    def _build_lump_panel(self, parent, *, row=0, column=0, pady=0):
        frame = ttk.LabelFrame(parent, text="Sugar Lumps", style="Card.TLabelframe", padding=12)
        frame.grid(row=row, column=column, sticky="nsew", padx=(8, 0) if column else 0, pady=pady)
        _lock_panel_size(frame, width=500)
        frame.grid_columnconfigure(0, weight=1)

        self.lump_meta_label = ttk.Label(frame, text="-", style="Data.TLabel", wraplength=1120)
        self.lump_meta_label.grid(row=0, column=0, sticky="w")
        self.lump_modifier_label = ttk.Label(frame, text="-", style="Muted.TLabel", wraplength=1120)
        self.lump_modifier_label.grid(row=1, column=0, sticky="w", pady=(4, 8))
        self.lump_chart = tk.Canvas(
            frame,
            height=108,
            bg="#0f1720",
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.lump_chart.grid(row=2, column=0, sticky="ew")

    def _build_golden_cookie_panel(self, parent, *, row=0, column=0, pady=0):
        frame = ttk.LabelFrame(parent, text="Golden Cookie Forecast", style="Card.TLabelframe", padding=12)
        frame.grid(row=row, column=column, sticky="nsew", padx=(8, 0) if column else 0, pady=pady)
        _lock_panel_size(frame, width=500)
        frame.grid_columnconfigure(0, weight=1)

        self.golden_cookie_meta_label = ttk.Label(frame, text="-", style="Data.TLabel", wraplength=1120)
        self.golden_cookie_meta_label.grid(row=0, column=0, sticky="w")
        self.golden_cookie_detail_label = ttk.Label(frame, text="-", style="Muted.TLabel", wraplength=1120)
        self.golden_cookie_detail_label.grid(row=1, column=0, sticky="w", pady=(4, 8))
        self.golden_cookie_chart = tk.Canvas(
            frame,
            height=108,
            bg="#0f1720",
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.golden_cookie_chart.grid(row=2, column=0, sticky="ew")

    def _build_diagnostics_panel(self, parent):
        container = ttk.Frame(parent, style="Card.TLabelframe")
        container.grid(row=0, column=0, sticky="nsew", padx=0, pady=(8, 0))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=0)
        self._build_shimmer_rng_panel(container)
        self._build_building_caps_panel(container)

    def _build_shimmer_rng_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Shimmer RNG Data", style="Card.TLabelframe", padding=12)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_rowconfigure(2, weight=0)
        frame.grid_rowconfigure(3, weight=0)

        self.shimmer_progress = ttk.Progressbar(frame, length=200, mode="determinate")
        self.shimmer_progress.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self.shimmer_rng_status = ttk.Label(frame, text="0 / 100 samples", style="Muted.TLabel")
        self.shimmer_rng_status.grid(row=1, column=0, sticky="w", pady=(0, 4))

        self.shimmer_stats_detail = ttk.Label(frame, text="+0 -0 =0 | Seeds: 0", style="Muted.TLabel")
        self.shimmer_stats_detail.grid(row=2, column=0, sticky="w", pady=(0, 8))

        self.shimmer_dump_btn = ttk.Button(
            frame,
            text="Dump Data",
            command=self._dump_shimmer_data_clicked,
        )
        self.shimmer_dump_btn.grid(row=3, column=0, sticky="w", pady=(0, 8))

    def _update_shimmer_rng_panel(self, shimmer_stats):
        total = shimmer_stats.get("total", 0)
        positive = shimmer_stats.get("positive", 0)
        negative = shimmer_stats.get("negative", 0)
        neutral = shimmer_stats.get("neutral", 0)
        seeds_captured = shimmer_stats.get("seeds_captured", 0)
        tracking_active = bool(shimmer_stats.get("tracking_active"))
        reset_reason = str(shimmer_stats.get("reset_reason") or "session_start").replace("_", " ")
        predictor_mode = shimmer_stats.get("predictor_mode") or "unknown"
        blocked_total = int(shimmer_stats.get("blocked_total") or 0)

        MIN_SAMPLES = 100
        MIN_SEEDS = 20

        total_progress = min(1.0, float(total) / float(MIN_SAMPLES))
        seeds_progress = min(1.0, float(seeds_captured) / float(MIN_SEEDS))
        progress = max(total_progress, seeds_progress)

        self.shimmer_progress["value"] = int(progress * 100)

        ready = total >= MIN_SAMPLES and seeds_captured >= MIN_SEEDS
        self.shimmer_data_ready = ready

        if not tracking_active:
            status_text = "Paused - predictor session reset"
            status_color = "#f87171"
        elif ready:
            status_text = f"READY {total}/{MIN_SAMPLES} samples"
            status_color = "#12c905"
        else:
            status_text = f"Collecting {total}/{MIN_SAMPLES} samples"
            status_color = "#fbb73c"

        self.shimmer_rng_status.configure(
            text=status_text,
            foreground=status_color,
        )
        self.shimmer_stats_detail.configure(
            text=(
                f"+{positive} -{negative} ={neutral} | Seeds: {seeds_captured}/{MIN_SEEDS} | "
                f"Mode: {predictor_mode} | Blocked: {blocked_total} | Reset: {reset_reason}"
            ),
        )
        self.shimmer_dump_btn.configure(state="normal" if total > 0 else "disabled")

    def _dump_shimmer_data_clicked(self):
        if self.dump_shimmer_data:
            self.dump_shimmer_data()

    def _build_trader_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Trader Performance", style="Card.TLabelframe", padding=12)
        frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(8, 0))
        _lock_panel_size(frame, width=500)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_rowconfigure(2, weight=1)

        self.trader_chart_meta = ttk.Label(frame, text="-", style="Muted.TLabel")
        self.trader_chart_meta.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.trader_chart = tk.Canvas(
            frame,
            height=220,
            bg="#0f1720",
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.trader_chart.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

    def _build_building_caps_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Building Caps", style="Card.TLabelframe", padding=12)
        frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        self.building_caps_meta = ttk.Label(
            frame,
            text="Shows owned, cap, remaining, ignore toggle, and manual cap entry.",
            style="Muted.TLabel",
        )
        self.building_caps_meta.grid(row=0, column=0, sticky="w", pady=(0, 8))

        canvas = tk.Canvas(frame, height=220, bg="#0f1720", highlightthickness=0, relief=tk.FLAT)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.building_caps_body = ttk.Frame(frame, style="Card.TLabelframe")
        self.building_caps_body.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.building_caps_body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.building_caps_canvas = canvas

    def _build_feed_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Live Feed", style="Card.TLabelframe", padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.feed_text = scrolledtext.ScrolledText(
            frame,
            height=18,
            wrap=tk.WORD,
            bg="#0f1720",
            fg="#dbe6f2",
            insertbackground="#dbe6f2",
            relief=tk.FLAT,
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.feed_text.grid(row=0, column=0, sticky="nsew")
        self.feed_text.configure(state="disabled")
        self.feed_text.tag_configure("time", foreground="#7d93a8")
        self.feed_text.tag_configure("bold", font=("Consolas", 10, "bold"))
        self.feed_text.tag_configure("category_shimmer", foreground="#d9b36c")
        self.feed_text.tag_configure("category_spell", foreground="#8fb8ff")
        self.feed_text.tag_configure("category_purchase", foreground="#92c98a")
        self.feed_text.tag_configure("category_garden", foreground="#8ccfba")
        self.feed_text.tag_configure("category_wrinkler", foreground="#c6a0ff")
        self.feed_text.tag_configure("category_lump", foreground="#ffb88c")
        self.feed_text.tag_configure("category_trade", foreground="#8fd3d1")
        self.feed_text.tag_configure("category_ui", foreground="#d3a6c6")
        self.feed_text.tag_configure("category_system", foreground="#a8b3c7")
        self.feed_text.tag_configure("category_event", foreground="#c8d4df")

    def run(self):
        self._schedule_refresh()
        self.root.mainloop()

    def _schedule_refresh(self):
        try:
            self._refresh()
        except Exception:
            log.exception("Dashboard refresh failed")
        self.root.after(self.refresh_interval_ms, self._schedule_refresh)

    def _refresh(self):
        payload = self.get_dashboard_state()
        state = payload["state"]
        trade_stats = payload["trade_stats"]
        building_stats = payload["building_stats"]
        ascension_prep_stats = payload.get("ascension_prep_stats") or {}
        garden_stats = payload["garden_stats"]
        combo_stats = payload["combo_stats"]
        spell_stats = payload["spell_stats"]

        uptime = max(0, int(time.monotonic() - float(state.get("started_at") or time.monotonic())))
        uptime_text = time.strftime("%H:%M:%S", time.gmtime(uptime))
        active_text = "RUNNING" if state.get("active") else "PAUSED"
        self.hero_label.configure(text=f"{active_text}  |  Uptime {uptime_text}")
        self._set_toggle_button_state("active", "Bot", bool(state.get("active")))
        self._set_toggle_button_state("stock", "Stock Buy", bool(state.get("stock_trading_enabled")))
        self._set_toggle_button_state("lucky_reserve", "Lucky Reserve", bool(state.get("lucky_reserve_enabled")))
        self._set_toggle_button_state("building", "Building Buy", bool(state.get("building_autobuy_enabled")))
        self._set_toggle_button_state("upgrade", "Upgrade Buy", bool(state.get("upgrade_autobuy_enabled")))
        self._set_toggle_button_state("ascension", "Ascension Prep", bool(state.get("ascension_prep_enabled")))
        self._set_action_button_state("main_autoclick", "Autoclick", bool(state.get("main_cookie_clicking_enabled")))
        self._set_action_button_state(
            "shimmer_autoclick", "GC/Wrath Click", bool(state.get("shimmer_autoclick_enabled"))
        )
        self.meta_label.configure(
            text=(
                f"Feed age {state.get('last_feed_age', '-')}  |  "
                f"Stocks {'ON' if state.get('stock_trading_enabled') else 'OFF'}  |  "
                f"Autoclick {'ON' if state.get('main_cookie_clicking_enabled') else 'OFF'}  |  "
                f"GC/Wrath {'ON' if state.get('shimmer_autoclick_enabled') else 'OFF'}  |  "
                f"Lucky Reserve {'ON' if state.get('lucky_reserve_enabled') else 'OFF'}  |  "
                f"Buildings {'ON' if state.get('building_autobuy_enabled') else 'OFF'}  |  "
                f"Upgrades {'ON' if state.get('upgrade_autobuy_enabled') else 'OFF'}  |  "
                f"Ascension Prep {'ON' if state.get('ascension_prep_enabled') else 'OFF'}  |  "
                f"Garden {'ON' if state.get('garden_automation_enabled') else 'OFF'}  |  "
                f"Wrinklers {state.get('wrinkler_mode', '-')}"
            )
        )
        self.last_actions_label.configure(
            text=(
                f"Spell: {_first_non_empty(state.get('last_spell_cast'), state.get('last_spell_diag', {}).get('reason'))}   "
                f"Trade: {_first_non_empty(state.get('last_trade_action'), trade_stats.get('last_trade'), state.get('last_bank_diag', {}).get('reason'))}   "
                f"Building: {_first_non_empty(state.get('last_building_action'), state.get('last_building_diag', {}).get('candidate'), state.get('last_building_diag', {}).get('reason'))}   "
                f"Garden: {_first_non_empty(state.get('last_garden_action'), garden_stats.get('last_garden'), state.get('last_garden_diag', {}).get('reason'))}   "
                f"Wrinkler: {_first_non_empty(state.get('last_wrinkler_action'), state.get('last_wrinkler_diag', {}).get('reason'))}   "
                f"Lump: {_first_non_empty(state.get('last_lump_action'), state.get('last_lump_diag', {}).get('stage'))}"
            )
        )

        last_bank_diag = state.get("last_bank_diag") or {}
        last_building_diag = state.get("last_building_diag") or {}
        last_upgrade_diag = state.get("last_upgrade_diag") or {}
        last_wrinkler_diag = state.get("last_wrinkler_diag") or {}
        last_spell_diag = state.get("last_spell_diag") or {}
        last_garden_diag = state.get("last_garden_diag") or {}
        last_combo_diag = state.get("last_combo_diag") or {}
        last_ascension_prep_diag = state.get("last_ascension_prep_diag") or {}
        last_ascension = state.get("last_ascension") or {}
        last_lump_diag = state.get("last_lump_diag") or {}
        last_golden_diag = state.get("last_golden_diag") or {}
        cookies = float(last_bank_diag.get("cookies") or last_building_diag.get("cookies") or 0.0)
        wrinkler_bank = float(last_wrinkler_diag.get("estimated_reward_attached") or 0.0)
        cookies_ps = float(last_building_diag.get("cookies_ps") or last_bank_diag.get("cookies_ps_raw_highest") or 0.0)
        buffs = state.get("last_buffs") or ()

        self._update_purchase_panel(
            building_diag=last_building_diag,
            upgrade_diag=last_upgrade_diag,
            ascension_prep_enabled=bool(state.get("ascension_prep_enabled")),
            ascension_prep_diag=last_ascension_prep_diag,
            cookies=cookies,
            wrinkler_bank=wrinkler_bank,
            cookies_ps=cookies_ps,
            wrinkler_diag=last_wrinkler_diag,
        )

        self._sync_horizon_inputs(
            upgrade_horizon_seconds=state.get("upgrade_horizon_seconds") or last_upgrade_diag.get("horizon_seconds"),
            building_horizon_seconds=state.get("building_horizon_seconds") or last_building_diag.get("payback_horizon_seconds"),
        )

        spell_magic = float(last_spell_diag.get("magic") or 0.0)
        spell_max_magic = float(last_spell_diag.get("max_magic") or 0.0)
        self._update_shimmer_rng_panel(state.get("shimmer_stats") or {})
        wrinkler_attached = float(last_wrinkler_diag.get("attached") or 0.0)
        wrinkler_max = float(last_wrinkler_diag.get("max") or 0.0)
        stock_exposure_ratio = float(last_bank_diag.get("portfolio_exposure_ratio") or 0.0)
        lucky_reserve = float(
            last_upgrade_diag.get("lucky_cookie_reserve")
            or last_building_diag.get("lucky_cookie_reserve")
            or last_bank_diag.get("lucky_cookie_reserve")
            or 0.0
        )
        hard_lucky_reserve = float(
            last_upgrade_diag.get("hard_lucky_cookie_reserve")
            or last_building_diag.get("hard_lucky_cookie_reserve")
            or last_bank_diag.get("hard_lucky_cookie_reserve")
            or lucky_reserve
            or 0.0
        )
        live_lucky_reserve = float(
            last_upgrade_diag.get("live_lucky_cookie_reserve")
            or last_building_diag.get("live_lucky_cookie_reserve")
            or last_bank_diag.get("live_lucky_cookie_reserve")
            or hard_lucky_reserve
            or 0.0
        )
        global_reserve = float(
            last_upgrade_diag.get("global_cookie_reserve")
            or last_building_diag.get("global_cookie_reserve")
            or last_bank_diag.get("global_cookie_reserve")
            or 0.0
        )
        garden_reserve = float(
            last_upgrade_diag.get("garden_cookie_reserve")
            or last_building_diag.get("garden_cookie_reserve")
            or 0.0
        )

        self.summary_vars["cookies"].set(
            f"Cash {_format_number(cookies)} | CPS {_format_number(last_building_diag.get('cookies_ps'))}"
        )
        ascend_gain = last_ascension.get("ascendGain")
        current_prestige = last_ascension.get("currentPrestige")
        next_prestige = last_ascension.get("nextPrestige")
        self.summary_vars["spell"].set(
            f"{_format_reason_label(last_spell_diag.get('reason', '-'))} | {spell_stats.get('last_spell') or '-'} | mana {spell_magic:.1f}/{spell_max_magic:.1f}"
        )
        self.summary_vars["stock"].set(
            f"{_format_reason_label(last_bank_diag.get('reason', '-'))} | held {trade_stats.get('held_goods', 0)} goods / {trade_stats.get('held_shares', 0)} shares | net {_format_number(trade_stats.get('net_pnl'))} | realized {_format_number(trade_stats.get('realized_pnl'))}"
        )
        self.summary_vars["buildings"].set(
            f"{_format_reason_label(last_building_diag.get('reason', '-'))} | next {last_building_diag.get('candidate') or '-'} | "
            f"prep {last_ascension_prep_diag.get('building') or '-'} {last_ascension_prep_diag.get('kind') or '-'} | "
            f"last {building_stats.get('last_building') or ascension_prep_stats.get('last_action') or '-'}"
        )
        self.summary_vars["garden"].set(
            f"{_format_reason_label(last_garden_diag.get('reason', '-'))} | last {garden_stats.get('last_garden') or '-'}"
        )
        self.summary_vars["combo"].set(
            f"{_format_reason_label(last_combo_diag.get('reason', '-'))} | last {combo_stats.get('last_combo') or '-'}"
        )
        self.summary_vars["perf"].set(
            f"dom {self._perf_pair(state.get('dom_loop_avg_ms'), state.get('dom_loop_max_ms'))} | "
            f"extract {self._perf_pair(state.get('dom_extract_avg_ms'), state.get('dom_extract_max_ms'))} | "
            f"action {self._perf_pair(state.get('dom_action_avg_ms'), state.get('dom_action_max_ms'))}"
        )
        self.summary_vars["buffs"].set(", ".join(buffs[:4]) if buffs else "-")
        self._draw_lump_chart(last_lump_diag)
        self._draw_golden_cookie_chart(last_golden_diag)

        self.mana_bar["value"] = _progress_fraction(spell_magic, spell_max_magic) * 100.0
        self.wrinkler_fill_bar["value"] = _progress_fraction(wrinkler_attached, wrinkler_max) * 100.0
        self.stock_exposure_bar["value"] = max(0.0, min(100.0, stock_exposure_ratio * 100.0))
        self.stock_exposure_label.configure(
            text=(
                f"{_format_percent(stock_exposure_ratio)} | "
                f"exposure {_format_number(last_bank_diag.get('portfolio_exposure'))} / "
                f"cap {_format_number(last_bank_diag.get('portfolio_cap'))}"
            )
        )
        self.lucky_reserve_bar["value"] = _progress_fraction(cookies, hard_lucky_reserve) * 100.0
        self.lucky_reserve_label.configure(
            text=(
                "No Lucky reserve target"
                if hard_lucky_reserve <= 0
                else (
                    f"{_format_percent(_progress_fraction(cookies, hard_lucky_reserve))} hard | "
                    f"cash {_format_number(cookies)} / hard {_format_number(hard_lucky_reserve)}"
                    + (
                        ""
                        if live_lucky_reserve <= hard_lucky_reserve
                        else f" | live buff target {_format_number(live_lucky_reserve)}"
                    )
                    + " | "
                    + (
                        "burst spend enabled"
                        if bool((last_building_diag.get("building_buff_burst_window") or {}).get("active"))
                        else f"global hold {_format_number(global_reserve)}"
                    )
                    + (
                        ""
                        if garden_reserve <= 0
                        else f" (garden {_format_number(garden_reserve)})"
                    )
                )
            )
        )
        self.ascension_bar["value"] = max(
            0.0,
            min(100.0, float(last_ascension.get("legacyMeterPercent") or 0.0) * 100.0),
        )

        purchase_price = last_building_diag.get("next_candidate_price")
        upgrade_price = last_upgrade_diag.get("candidate_price")
        purchase_shortfall = None if not isinstance(purchase_price, (int, float)) else max(0.0, float(purchase_price) - cookies)
        upgrade_shortfall = None if not isinstance(upgrade_price, (int, float)) else max(0.0, float(upgrade_price) - cookies)
        purchase_eta = None if purchase_shortfall is None or cookies_ps <= 0 else purchase_shortfall / cookies_ps
        upgrade_eta = None if upgrade_shortfall is None or cookies_ps <= 0 else upgrade_shortfall / cookies_ps
        purchase_bank_ready = bool(
            isinstance(purchase_price, (int, float)) and (cookies + wrinkler_bank) >= float(purchase_price)
        )
        upgrade_bank_ready = bool(
            isinstance(upgrade_price, (int, float)) and (cookies + wrinkler_bank) >= float(upgrade_price)
        )

        self.timing_vars["purchase_cash_eta"].set(
            "-"
            if purchase_shortfall is None
            else f"{_format_duration(purchase_eta)} | shortfall {_format_number(purchase_shortfall)}"
        )
        self.timing_vars["purchase_bank_eta"].set(
            "-"
            if purchase_shortfall is None
            else (
                "ready now with wrinkler bank"
                if purchase_bank_ready
                else f"need {_format_number(max(0.0, float(purchase_price) - (cookies + wrinkler_bank)))} more after bank"
            )
        )
        self.timing_vars["upgrade_cash_eta"].set(
            "-"
            if upgrade_shortfall is None
            else f"{_format_duration(upgrade_eta)} | shortfall {_format_number(upgrade_shortfall)}"
        )
        self.timing_vars["upgrade_bank_eta"].set(
            "-"
            if upgrade_shortfall is None
            else (
                "ready now with wrinkler bank"
                if upgrade_bank_ready
                else f"need {_format_number(max(0.0, float(upgrade_price) - (cookies + wrinkler_bank)))} more after bank"
            )
        )
        self.timing_vars["wrinkler_goal_eta"].set(
            f"{'ready' if last_wrinkler_diag.get('pop_goal_affordable_with_bank') else 'waiting'} | "
            f"bank {_format_number(wrinkler_bank)} / goal gap {_format_number(last_wrinkler_diag.get('pop_goal_shortfall'))}"
        )
        self.timing_vars["wrinkler_target"].set(
            f"{last_wrinkler_diag.get('pop_goal_kind') or '-'} {last_wrinkler_diag.get('pop_goal_name') or '-'} | "
            f"candidate reward {_format_number(last_wrinkler_diag.get('candidate_reward'))}"
        )
        self.timing_vars["garden_timers"].set(
            f"next tick {last_garden_diag.get('next_tick', '-')} | next soil {last_garden_diag.get('next_soil', '-')}"
        )
        self.timing_vars["combo_timing"].set(
            f"combo {_format_reason_label(last_combo_diag.get('reason', '-'))} | last run {_format_duration(state.get('last_combo_run_duration'))}"
        )

        self._draw_lump_chart(last_lump_diag)
        self._draw_trader_chart(trade_stats)
        self._refresh_building_caps(
            building_entries=last_building_diag.get("buildings") or [],
            building_stats=building_stats,
        )

        feed = payload.get("feed") or []
        self._update_feed(feed)

    def _update_feed(self, feed):
        self.feed_text.configure(state="normal")
        self.feed_text.delete("1.0", tk.END)

        if not feed:
            self.feed_text.insert("1.0", "(no feed entries)")
            self.feed_text.see(tk.END)
            self.feed_text.configure(state="disabled")
            return
        
        for entry in reversed(feed):
            timestamp = entry.get("timestamp", "")
            message = entry.get("message", "")
            category = entry.get("category", "event")
            
            tag_time = "time"
            tag_category = f"category_{category}"
            
            self.feed_text.insert("1.0", "\n")
            self.feed_text.insert("1.0", message, tag_category)
            self.feed_text.insert("1.0", f"{timestamp} ", tag_time)

        self.feed_text.see(tk.END)
        self.feed_text.configure(state="disabled")

    def _update_purchase_panel(
        self,
        *,
        building_diag,
        upgrade_diag,
        ascension_prep_enabled,
        ascension_prep_diag,
        cookies,
        wrinkler_bank,
        cookies_ps,
        wrinkler_diag,
    ):
        prep_kind = ascension_prep_diag.get("kind")
        prep_building = ascension_prep_diag.get("building")
        prep_quantity = int(ascension_prep_diag.get("quantity") or 0)
        use_prep_target = bool(ascension_prep_enabled and prep_building and prep_kind in {"buy", "sell", "wait"})
        effective_total = cookies + wrinkler_bank

        if use_prep_target:
            prep_total_value = ascension_prep_diag.get("total_value")
            prep_unit_value = ascension_prep_diag.get("unit_value")
            prep_threshold = ascension_prep_diag.get("threshold")
            prep_phase = ascension_prep_diag.get("phase")
            if prep_kind == "buy":
                goal_price = prep_total_value
                goal_name = f"{prep_building} x{prep_quantity}"
                self.purchase_title.configure(text=f"Ascension prep: buy {goal_name}")
                self.purchase_detail.configure(
                    text=(
                        f"Cost {_format_number(goal_price)} | unit {_format_number(prep_unit_value)} | "
                        f"phase {prep_phase or '-'} to {prep_threshold or '-'} | "
                        f"ETA {_format_duration(None if cookies_ps <= 0 else max(0.0, float(goal_price or 0.0) - cookies) / cookies_ps)}"
                    )
                )
                self.purchase_cash_bar["value"] = _progress_fraction(cookies, goal_price) * 100.0
                self.purchase_cash_label.configure(
                    text=f"Cash only: {_format_number(cookies)} / {_format_number(goal_price)} ({_format_percent(_progress_fraction(cookies, goal_price))})"
                )
                self.purchase_bank_bar["value"] = _progress_fraction(effective_total, goal_price) * 100.0
                self.purchase_bank_label.configure(
                    text=(
                        f"Cash + wrinkler bank: {_format_number(effective_total)} / {_format_number(goal_price)} "
                        f"({_format_percent(_progress_fraction(effective_total, goal_price))})"
                    )
                )
            elif prep_kind == "wait":
                goal_price = prep_total_value
                goal_name = f"{prep_building} x{max(1, prep_quantity)}"
                self.purchase_title.configure(text=f"Ascension prep: waiting for {goal_name}")
                self.purchase_detail.configure(
                    text=(
                        f"Need {_format_number(goal_price)} | unit {_format_number(prep_unit_value)} | "
                        f"phase {prep_phase or '-'} to {prep_threshold or '-'} | "
                        f"ETA {_format_duration(None if cookies_ps <= 0 else max(0.0, float(goal_price or 0.0) - cookies) / cookies_ps)}"
                    )
                )
                self.purchase_cash_bar["value"] = _progress_fraction(cookies, goal_price) * 100.0
                self.purchase_cash_label.configure(
                    text=f"Cash only: {_format_number(cookies)} / {_format_number(goal_price)} ({_format_percent(_progress_fraction(cookies, goal_price))})"
                )
                self.purchase_bank_bar["value"] = _progress_fraction(effective_total, goal_price) * 100.0
                self.purchase_bank_label.configure(
                    text=(
                        f"Cash + wrinkler bank: {_format_number(effective_total)} / {_format_number(goal_price)} "
                        f"({_format_percent(_progress_fraction(effective_total, goal_price))})"
                    )
                )
            else:
                self.purchase_title.configure(text=f"Ascension prep: sell {prep_building} x{prep_quantity}")
                self.purchase_detail.configure(
                    text=(
                        f"Expected sale {_format_number(prep_total_value)} | unit {_format_number(prep_unit_value)} | "
                        f"phase {prep_phase or '-'} to {prep_threshold or '-'} | "
                        f"{_format_reason_label(ascension_prep_diag.get('reason'))}"
                    )
                )
                self.purchase_cash_bar["value"] = 100.0
                self.purchase_bank_bar["value"] = 100.0
                self.purchase_cash_label.configure(text="Ready to liquidate surplus for ascension prep")
                self.purchase_bank_label.configure(text="Sale step does not depend on cash on hand")
        else:
            active_name = building_diag.get("candidate")
            active_price = building_diag.get("candidate_price")
            active_payback = building_diag.get("candidate_payback_seconds")
            horizon_name = building_diag.get("next_candidate")
            horizon_price = building_diag.get("next_candidate_price")
            horizon_payback = building_diag.get("next_candidate_payback_seconds")
            showing_active = isinstance(active_price, (int, float)) and float(active_price) > 0
            goal_name = active_name if showing_active else (horizon_name or "-")
            goal_price = active_price if showing_active else horizon_price
            goal_payback = active_payback if showing_active else horizon_payback

            if isinstance(goal_price, (int, float)) and float(goal_price) > 0:
                title_prefix = "Next building" if showing_active else "Building horizon target"
                self.purchase_title.configure(text=f"{title_prefix}: {goal_name}")
                self.purchase_detail.configure(
                    text=(
                        f"Price {_format_number(goal_price)} | payback "
                        f"{'-' if goal_payback is None else f'{float(goal_payback):.1f}s'} | "
                        f"horizon {_format_duration(building_diag.get('payback_horizon_seconds'))} | "
                        f"cash shortfall {_format_number(max(0.0, float(goal_price) - cookies))} | "
                        f"ETA {_format_duration(None if cookies_ps <= 0 else max(0.0, float(goal_price) - cookies) / cookies_ps)}"
                        + (
                            ""
                            if showing_active
                            else f" | executable now: {building_diag.get('candidate') or '-'}"
                        )
                    )
                )
                self.purchase_cash_bar["value"] = _progress_fraction(cookies, goal_price) * 100.0
                self.purchase_cash_label.configure(
                    text=(
                        f"Cash only: {_format_number(cookies)} / {_format_number(goal_price)} "
                        f"({_format_percent(_progress_fraction(cookies, goal_price))})"
                    )
                )
                self.purchase_bank_bar["value"] = _progress_fraction(effective_total, goal_price) * 100.0
                self.purchase_bank_label.configure(
                    text=(
                        (
                            f"Spendable now {_format_number(building_diag.get('spendable'))} | "
                            f"reserve {_format_number(building_diag.get('reserve'))}"
                            if not showing_active
                            else (
                                f"Cash + wrinkler bank: {_format_number(effective_total)} / {_format_number(goal_price)} "
                                f"({_format_percent(_progress_fraction(effective_total, goal_price))}) | "
                                f"{'wrinkler-ready' if wrinkler_diag.get('pop_goal_affordable_with_bank') else 'not wrinkler-ready'}"
                            )
                        )
                    )
                )
            else:
                self.purchase_title.configure(text="Next building")
                self.purchase_detail.configure(
                    text=(
                        f"{_format_reason_label(building_diag.get('reason', 'no_buy_in_horizon'))} | "
                        f"horizon {_format_duration(building_diag.get('payback_horizon_seconds'))} | "
                        f"spendable {_format_number(building_diag.get('spendable'))}"
                    )
                )
                self.purchase_cash_bar["value"] = 0
                self.purchase_bank_bar["value"] = 0
                self.purchase_cash_label.configure(text="-")
                self.purchase_bank_label.configure(text="-")

        upgrade_name = upgrade_diag.get("candidate") or "-"
        upgrade_price = upgrade_diag.get("candidate_price")
        upgrade_payback = upgrade_diag.get("candidate_payback_seconds")
        if isinstance(upgrade_price, (int, float)) and float(upgrade_price) > 0:
            self.upgrade_title.configure(text=f"Next upgrade: {upgrade_name}")
            self.upgrade_detail.configure(
                text=(
                    f"Price {_format_number(upgrade_price)} | payback "
                    f"{'-' if upgrade_payback is None else f'{float(upgrade_payback):.1f}s'} | "
                    f"horizon {_format_duration(upgrade_diag.get('horizon_seconds'))} | "
                    f"ETA {_format_duration(None if cookies_ps <= 0 else max(0.0, float(upgrade_price) - cookies) / cookies_ps)}"
                )
            )
            self.upgrade_cash_bar["value"] = _progress_fraction(cookies, upgrade_price) * 100.0
            self.upgrade_cash_label.configure(
                text=f"Upgrade cash progress: {_format_number(cookies)} / {_format_number(upgrade_price)} ({_format_percent(_progress_fraction(cookies, upgrade_price))})"
            )
            self.upgrade_bank_bar["value"] = _progress_fraction(effective_total, upgrade_price) * 100.0
            self.upgrade_bank_label.configure(
                text=(
                    f"Upgrade if wrinklers popped: {_format_number(effective_total)} / {_format_number(upgrade_price)} "
                    f"({_format_percent(_progress_fraction(effective_total, upgrade_price))})"
                )
            )
        else:
            self.upgrade_title.configure(text="Next upgrade")
            self.upgrade_detail.configure(
                text=(
                    f"{_format_reason_label(upgrade_diag.get('reason', 'no_upgrade_signal'))} | "
                    f"horizon {_format_duration(upgrade_diag.get('horizon_seconds'))} | "
                    f"in store {int(upgrade_diag.get('upgrades_total') or 0)} | "
                    f"affordable {int(upgrade_diag.get('affordable') or 0)}"
                )
            )
            self.upgrade_cash_bar["value"] = 0
            self.upgrade_bank_bar["value"] = 0
            self.upgrade_cash_label.configure(text="-")
            self.upgrade_bank_label.configure(text="-")

    def _perf_pair(self, avg_ms, max_ms):
        if avg_ms is None or max_ms is None:
            return "-"
        return f"{float(avg_ms):.1f}/{float(max_ms):.1f}ms"

    def _refresh_building_caps(self, *, building_entries, building_stats):
        defaults = building_stats.get("default_building_caps") or {}
        ignored = set(building_stats.get("ignored_building_caps") or ())
        ordered_entries = sorted(
            (entry for entry in building_entries if isinstance(entry, dict) and entry.get("name")),
            key=lambda item: int(item.get("id", 999)),
        )
        self.building_caps_meta.configure(
            text=(
                f"{len(ordered_entries)} buildings | ignored {len(ignored)} | "
                "blank cap entry resets to default"
            )
        )
        seen = set()
        for entry in ordered_entries:
            name = entry["name"]
            seen.add(name)
            row = self.building_cap_rows.get(name)
            if row is None:
                row = self._create_building_cap_row(name)
                self.building_cap_rows[name] = row

            amount = int(entry.get("amount") or 0)
            cap = entry.get("cap")
            default_cap = entry.get("default_cap")
            remaining = entry.get("remaining_to_cap")
            manual_cap = entry.get("manual_cap")
            cap_ignored = bool(entry.get("cap_ignored")) or name in ignored
            row["summary"].set(
                f"owned {amount} | cap {'ignored' if cap_ignored else (cap if cap is not None else '-')} | "
                f"remaining {'-' if remaining is None else remaining} | default {defaults.get(name, default_cap)}"
            )
            row["ignore_var"].set(cap_ignored)
            focus_widget = self.root.focus_get()
            if focus_widget is not row["entry"]:
                row["cap_var"].set("" if manual_cap is None else str(manual_cap))
            row["frame"].grid()

        for name, row in self.building_cap_rows.items():
            if name not in seen:
                row["frame"].grid_remove()

        self.building_caps_canvas.update_idletasks()
        self.building_caps_canvas.configure(scrollregion=self.building_caps_canvas.bbox("all"))

    def _create_building_cap_row(self, building_name):
        index = len(self.building_cap_rows)
        frame = ttk.Frame(self.building_caps_body, style="Card.TLabelframe")
        frame.grid(row=index, column=0, sticky="ew", pady=2)
        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text=building_name, style="Value.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        summary = tk.StringVar(value="-")
        ttk.Label(frame, textvariable=summary, style="Data.TLabel", wraplength=360).grid(row=0, column=1, sticky="w")

        ignore_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Ignore",
            variable=ignore_var,
            command=lambda name=building_name, var=ignore_var: self.set_building_cap_ignored(name, bool(var.get())),
        ).grid(row=0, column=2, sticky="e", padx=(8, 4))

        cap_var = tk.StringVar(value="")
        entry = ttk.Entry(frame, textvariable=cap_var, width=8)
        entry.grid(row=0, column=3, sticky="e", padx=4)
        entry.bind("<Return>", lambda _event, name=building_name: self._submit_building_cap(name))

        ttk.Button(frame, text="Apply", command=lambda name=building_name: self._submit_building_cap(name), style="Action.TButton").grid(
            row=0, column=4, sticky="e", padx=4
        )
        ttk.Button(frame, text="Reset", command=lambda name=building_name: self._reset_building_cap(name), style="Action.TButton").grid(
            row=0, column=5, sticky="e", padx=(4, 0)
        )

        return {
            "frame": frame,
            "summary": summary,
            "ignore_var": ignore_var,
            "cap_var": cap_var,
            "entry": entry,
        }

    def _submit_building_cap(self, building_name):
        row = self.building_cap_rows.get(building_name)
        if row is None:
            return
        raw_value = row["cap_var"].get().strip()
        try:
            cap = None if raw_value == "" else int(raw_value)
        except ValueError:
            row["cap_var"].set("")
            return
        self.set_building_cap(building_name, cap)

    def _reset_building_cap(self, building_name):
        row = self.building_cap_rows.get(building_name)
        if row is not None:
            row["cap_var"].set("")
        self.set_building_cap(building_name, None)

    def _draw_lump_chart(self, lump_diag):
        width = max(480, int(self.lump_chart.winfo_width() or 0))
        height = max(108, int(self.lump_chart.winfo_height() or 0))
        self.lump_chart.configure(width=width, height=height)
        self.lump_chart.delete("all")

        if not lump_diag or not lump_diag.get("unlocked"):
            self.lump_meta_label.configure(text="Sugar lumps are not unlocked yet.")
            self.lump_modifier_label.configure(text="-")
            self.lump_chart.create_text(
                width / 2,
                height / 2,
                text="Waiting for sugar lump unlock...",
                fill="#8aa0b4",
                font=("Segoe UI", 11),
            )
            return

        lumps = lump_diag.get("lumps")
        stage = lump_diag.get("stage") or "-"
        type_name = lump_diag.get("current_type_name") or "normal"
        time_to_ripe = lump_diag.get("time_to_ripe_seconds")
        time_to_overripe = lump_diag.get("time_to_overripe_seconds")
        modifiers = ", ".join(lump_diag.get("modifiers") or ()) or "No active ripening modifiers"
        self.lump_meta_label.configure(
            text=(
                f"Current {_format_number(lumps)} lumps | "
                f"next {stage} {type_name} lump | "
                f"ripe in {_format_duration(time_to_ripe)} | "
                f"overripe in {_format_duration(time_to_overripe)}"
            )
        )
        self.lump_modifier_label.configure(text=modifiers)

        age_ms = float(lump_diag.get("age_ms") or 0.0)
        mature_ms = float(lump_diag.get("mature_age_ms") or 0.0)
        ripe_ms = float(lump_diag.get("ripe_age_ms") or 0.0)
        overripe_ms = float(lump_diag.get("overripe_age_ms") or 0.0)
        total_ms = max(overripe_ms, ripe_ms, mature_ms, 1.0)

        padding_left = 44
        padding_right = 28
        baseline_y = 58
        plot_width = max(1, width - padding_left - padding_right)

        def x_for(value_ms):
            return padding_left + max(0.0, min(1.0, float(value_ms) / total_ms)) * plot_width

        start_x = padding_left
        mature_x = x_for(mature_ms)
        ripe_x = x_for(ripe_ms)
        overripe_x = x_for(overripe_ms)
        marker_x = x_for(min(age_ms, total_ms))

        self.lump_chart.create_line(start_x, baseline_y, overripe_x, baseline_y, fill="#304253", width=10)
        if mature_x > start_x:
            self.lump_chart.create_line(start_x, baseline_y, mature_x, baseline_y, fill="#55b6ff", width=10)
        if ripe_x > mature_x:
            self.lump_chart.create_line(mature_x, baseline_y, ripe_x, baseline_y, fill="#ffb14a", width=10)
        if overripe_x > ripe_x:
            self.lump_chart.create_line(ripe_x, baseline_y, overripe_x, baseline_y, fill="#3ecf8e", width=10)

        for x, label in (
            (start_x, "Now"),
            (mature_x, "Mature"),
            (ripe_x, "Ripe"),
            (overripe_x, "Overripe"),
        ):
            self.lump_chart.create_line(x, baseline_y - 18, x, baseline_y + 18, fill="#7d93a8", width=1)
            self.lump_chart.create_text(x, baseline_y + 28, text=label, fill="#9cb0c3", font=("Segoe UI", 9))

        self.lump_chart.create_oval(
            marker_x - 6,
            baseline_y - 6,
            marker_x + 6,
            baseline_y + 6,
            fill="#f7fbff",
            outline="",
        )
        self.lump_chart.create_text(
            marker_x,
            baseline_y - 24,
            text=stage.upper(),
            fill="#f7fbff",
            font=("Segoe UI Semibold", 9),
        )

    def _draw_golden_cookie_chart(self, golden_diag):
        width = max(480, int(self.golden_cookie_chart.winfo_width() or 0))
        height = max(108, int(self.golden_cookie_chart.winfo_height() or 0))
        self.golden_cookie_chart.configure(width=width, height=height)
        self.golden_cookie_chart.delete("all")

        if not golden_diag or not golden_diag.get("available"):
            self.golden_cookie_meta_label.configure(text="Golden cookie timer data is unavailable.")
            self.golden_cookie_detail_label.configure(text="-")
            self.golden_cookie_chart.create_text(
                width / 2,
                height / 2,
                text="Waiting for golden cookie timer...",
                fill="#8aa0b4",
                font=("Segoe UI", 11),
            )
            return

        curve = list(golden_diag.get("spawn_curve") or ())
        on_screen = int(golden_diag.get("on_screen") or 0)
        progress = float(golden_diag.get("progress") or 0.0)
        pressure = float(golden_diag.get("spawn_pressure") or 0.0)
        min_seconds = golden_diag.get("min_seconds")
        max_seconds = golden_diag.get("max_seconds")
        elapsed_seconds = golden_diag.get("elapsed_seconds")
        chance_10 = golden_diag.get("chance_within_10s")
        chance_30 = golden_diag.get("chance_within_30s")
        chance_60 = golden_diag.get("chance_within_60s")
        median_eta = golden_diag.get("median_remaining_seconds")
        expected_eta = golden_diag.get("expected_remaining_seconds")

        self.golden_cookie_meta_label.configure(
            text=(
                f"on-screen {on_screen} | "
                f"window {_format_duration(min_seconds)} to {_format_duration(max_seconds)} | "
                f"elapsed {_format_duration(elapsed_seconds)} | "
                f"pressure {_format_percent(pressure)}"
            )
        )
        self.golden_cookie_detail_label.configure(
            text=(
                f"spawn chance: 10s {_format_percent(chance_10)} | "
                f"30s {_format_percent(chance_30)} | "
                f"60s {_format_percent(chance_60)} | "
                f"median ETA {_format_duration(median_eta)} | "
                f"expected ETA {_format_duration(expected_eta)}"
            )
        )

        if len(curve) < 2:
            self.golden_cookie_chart.create_text(
                width / 2,
                height / 2,
                text="Collecting spawn forecast...",
                fill="#8aa0b4",
                font=("Segoe UI", 11),
            )
            return

        padding_left = 44
        padding_right = 28
        padding_top = 14
        padding_bottom = 26
        plot_width = max(1, width - padding_left - padding_right)
        plot_height = max(1, height - padding_top - padding_bottom)
        baseline_y = padding_top + plot_height

        self.golden_cookie_chart.create_line(
            padding_left,
            baseline_y,
            padding_left + plot_width,
            baseline_y,
            fill="#304253",
            width=1,
        )
        self.golden_cookie_chart.create_line(
            padding_left,
            padding_top,
            padding_left,
            baseline_y,
            fill="#304253",
            width=1,
        )

        horizon_seconds = max(float(curve[-1].get("second") or 1.0), 1.0)

        def x_for(second):
            return padding_left + (max(0.0, min(horizon_seconds, float(second))) / horizon_seconds) * plot_width

        def y_for(probability):
            return baseline_y - max(0.0, min(1.0, float(probability))) * plot_height

        for second in (10, 30, 60):
            if second > horizon_seconds:
                continue
            x = x_for(second)
            self.golden_cookie_chart.create_line(x, padding_top, x, baseline_y, fill="#243240", width=1)
            self.golden_cookie_chart.create_text(x, baseline_y + 12, text=f"{second}s", fill="#9cb0c3", font=("Segoe UI", 9))

        for probability, label in ((0.25, "25%"), (0.5, "50%"), (0.75, "75%"), (1.0, "100%")):
            y = y_for(probability)
            self.golden_cookie_chart.create_line(padding_left, y, padding_left + plot_width, y, fill="#1d2a36", width=1)
            self.golden_cookie_chart.create_text(22, y, text=label, fill="#9cb0c3", font=("Segoe UI", 8))

        points = []
        for item in curve:
            second = item.get("second")
            probability = item.get("cumulative")
            if not isinstance(second, (int, float)) or not isinstance(probability, (int, float)):
                continue
            points.extend((x_for(second), y_for(probability)))
        if len(points) >= 4:
            self.golden_cookie_chart.create_line(points, fill="#ffd166", width=2, smooth=True)

        marker_x = x_for(progress * horizon_seconds)
        marker_y = y_for(curve[0].get("cumulative") if curve else 0.0)
        self.golden_cookie_chart.create_rectangle(
            padding_left,
            baseline_y - 6,
            padding_left + (progress * plot_width),
            baseline_y,
            fill="#3b6d8b",
            outline="",
        )
        self.golden_cookie_chart.create_text(
            padding_left + 46,
            padding_top + 10,
            text=f"window progress {_format_percent(progress)}",
            fill="#dbe6f2",
            font=("Segoe UI Semibold", 9),
        )

    def _draw_trader_chart(self, trade_stats):
        history = trade_stats.get("performance_history") or []
        width = max(320, int(self.trader_chart.winfo_width() or 0))
        height = max(180, int(self.trader_chart.winfo_height() or 0))
        self.trader_chart.configure(width=width, height=height)
        self.trader_chart.delete("all")

        if len(history) < 2:
            self.trader_chart_meta.configure(text="Waiting for enough trade history to draw performance.")
            self.trader_chart.create_text(
                width / 2,
                height / 2,
                text="Collecting trader samples...",
                fill="#8aa0b4",
                font=("Segoe UI", 11),
            )
            return

        padding_left = 52
        padding_right = 52
        padding_top = 16
        padding_bottom = 28
        plot_width = max(1, width - padding_left - padding_right)
        plot_height = max(1, height - padding_top - padding_bottom)

        timestamps = [int(point.get("timestamp") or 0) for point in history]
        pnl_values = [float(point.get("net_pnl") or 0.0) for point in history]
        spend_values = [float(point.get("cost_basis") or 0.0) for point in history]
        roi_values = [point.get("roi") for point in history if point.get("roi") is not None]
        session_roi_values = [point.get("session_roi") for point in history if point.get("session_roi") is not None]

        pnl_min = min(min(pnl_values), 0.0)
        pnl_max = max(max(pnl_values), 0.0)
        if pnl_max <= pnl_min:
            pnl_max = pnl_min + 1.0
        spend_max = max(max(spend_values), 1.0)

        first_ts = timestamps[0]
        last_ts = timestamps[-1]
        span_ts = max(1, last_ts - first_ts)

        def x_for(ts):
            return padding_left + ((ts - first_ts) / span_ts) * plot_width

        def y_for_pnl(value):
            return padding_top + (1.0 - ((value - pnl_min) / (pnl_max - pnl_min))) * plot_height

        def y_for_spend(value):
            return padding_top + (1.0 - (value / spend_max)) * plot_height

        zero_y = y_for_pnl(0.0)
        self.trader_chart.create_rectangle(
            padding_left,
            padding_top,
            width - padding_right,
            height - padding_bottom,
            outline="#223142",
        )
        self.trader_chart.create_line(
            padding_left,
            zero_y,
            width - padding_right,
            zero_y,
            fill="#394c60",
            dash=(4, 4),
        )

        spend_points = []
        pnl_points = []
        for point in history:
            x = x_for(int(point.get("timestamp") or 0))
            spend_points.extend((x, y_for_spend(float(point.get("cost_basis") or 0.0))))
            pnl_points.extend((x, y_for_pnl(float(point.get("net_pnl") or 0.0))))

        if len(spend_points) >= 4:
            spend_polygon = [padding_left, height - padding_bottom, *spend_points, width - padding_right, height - padding_bottom]
            self.trader_chart.create_polygon(spend_polygon, fill="#183551", outline="")
            self.trader_chart.create_line(spend_points, fill="#6bb8ff", width=2)
        if len(pnl_points) >= 4:
            self.trader_chart.create_line(pnl_points, fill="#3ecf8e", width=2)

        self.trader_chart.create_text(
            padding_left - 6,
            padding_top,
            text=_format_number(pnl_max),
            fill="#7fdca9",
            font=("Segoe UI", 9),
            anchor="e",
        )
        self.trader_chart.create_text(
            padding_left - 6,
            height - padding_bottom,
            text=_format_number(pnl_min),
            fill="#7fdca9",
            font=("Segoe UI", 9),
            anchor="e",
        )
        self.trader_chart.create_text(
            width - padding_right + 6,
            padding_top,
            text=_format_number(spend_max),
            fill="#8dc8ff",
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.trader_chart.create_text(
            padding_left,
            height - 10,
            text="P&L",
            fill="#3ecf8e",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self.trader_chart.create_text(
            padding_left + 48,
            height - 10,
            text="Spend",
            fill="#6bb8ff",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )

        latest = history[-1]
        latest_roi = latest.get("roi")
        displayed_roi = latest_roi if latest_roi is not None else _latest_non_null_metric(history, "roi")
        roi_text = "-" if displayed_roi is None else _format_percent(displayed_roi)
        latest_session_roi = latest.get("session_roi")
        displayed_session_roi = (
            latest_session_roi
            if latest_session_roi is not None
            else _latest_non_null_metric(history, "session_roi")
        )
        session_roi_text = "-" if displayed_session_roi is None else _format_percent(displayed_session_roi)
        roi_range_text = "-"
        if roi_values:
            roi_range_text = f"{_format_percent(min(roi_values))} to {_format_percent(max(roi_values))}"
        session_roi_range_text = "-"
        if session_roi_values:
            session_roi_range_text = (
                f"{_format_percent(min(session_roi_values))} to {_format_percent(max(session_roi_values))}"
            )
        roi_label = "ROI"
        if latest_roi is None and displayed_roi is not None:
            roi_label = "Last ROI"
        self.trader_chart_meta.configure(
            text=(
                f"net {_format_number(latest.get('net_pnl'))} | realized {_format_number(trade_stats.get('realized_pnl'))} | "
                f"unrealized {_format_number(trade_stats.get('unrealized_pnl'))} | spend {_format_number(latest.get('cost_basis'))} | "
                f"{roi_label} {roi_text} | range {roi_range_text} | "
                f"Session ROI {session_roi_text} | session range {session_roi_range_text}"
            )
        )
