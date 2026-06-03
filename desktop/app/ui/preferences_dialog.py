"""Preferences modal — returns new :class:`AppSettings` or ``None`` if cancelled."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import sys

from ..settings_store import AppSettings
from .. import startup_manager
from .theme import _BORDER, _MUTED, _TEXT


def _apply_to_widgets(s: AppSettings, widgets: dict) -> None:
    widgets["auto_connect_cb"].setChecked(s.auto_connect_on_start)
    widgets["start_min_cb"].setChecked(s.start_minimized)
    widgets["close_to_tray_cb"].setChecked(s.close_to_tray)
    widgets["keep_awake_cb"].setChecked(s.keep_awake)
    if "start_with_windows_cb" in widgets:
        widgets["start_with_windows_cb"].setChecked(s.start_with_windows)
    widgets["notify_signal_cb"].setChecked(s.notify_on_signal)
    widgets["notify_connect_cb"].setChecked(s.notify_on_connect)
    widgets["reconnect_spin"].setValue(s.reconnect_interval_s)
    widgets["max_retry_spin"].setValue(s.max_reconnect_attempts)
    widgets["qty_spin"].setValue(s.order_quantity)
    widgets["stop_spin"].setValue(s.default_stop_loss_pct)
    widgets["max_daily_spin"].setValue(s.max_daily_trades)
    widgets["cooldown_spin"].setValue(s.signal_cooldown_s)
    widgets["confirm_trade_cb"].setChecked(s.confirm_before_trade)
    widgets["skip_non_long_cb"].setChecked(s.skip_non_long_signals)
    widgets["font_spin"].setValue(s.log_font_size)
    widgets["lines_spin"].setValue(s.log_max_lines)
    widgets["auto_scroll_cb"].setChecked(s.log_auto_scroll)
    widgets["timestamps_cb"].setChecked(s.log_show_timestamps)
    level_combo: QComboBox = widgets["level_combo"]
    level_combo.setCurrentIndex({"all": 0, "warn": 1, "error": 2}.get(s.log_level_filter, 0))


def _read_from_widgets(s: AppSettings, widgets: dict, splitter_sizes: list[int]) -> AppSettings:
    level_combo: QComboBox = widgets["level_combo"]
    return AppSettings(
        ws_url=s.ws_url,
        license_key=s.license_key,
        reconnect_interval_s=widgets["reconnect_spin"].value(),
        max_reconnect_attempts=widgets["max_retry_spin"].value(),
        order_quantity=widgets["qty_spin"].value(),
        max_daily_trades=widgets["max_daily_spin"].value(),
        signal_cooldown_s=widgets["cooldown_spin"].value(),
        default_stop_loss_pct=widgets["stop_spin"].value(),
        confirm_before_trade=widgets["confirm_trade_cb"].isChecked(),
        skip_non_long_signals=widgets["skip_non_long_cb"].isChecked(),
        log_font_size=widgets["font_spin"].value(),
        log_max_lines=widgets["lines_spin"].value(),
        log_auto_scroll=widgets["auto_scroll_cb"].isChecked(),
        log_show_timestamps=widgets["timestamps_cb"].isChecked(),
        log_level_filter=level_combo.currentData(),
        notify_on_signal=widgets["notify_signal_cb"].isChecked(),
        notify_on_connect=widgets["notify_connect_cb"].isChecked(),
        auto_connect_on_start=widgets["auto_connect_cb"].isChecked(),
        start_minimized=widgets["start_min_cb"].isChecked(),
        start_with_windows=widgets["start_with_windows_cb"].isChecked() if "start_with_windows_cb" in widgets else s.start_with_windows,
        close_to_tray=widgets["close_to_tray_cb"].isChecked(),
        keep_awake=widgets["keep_awake_cb"].isChecked(),
        seen_welcome=s.seen_welcome,
        terms_accepted=s.terms_accepted,
        splitter_sizes=splitter_sizes,
    )


def run_preferences_dialog(
    parent: QWidget,
    s: AppSettings,
    splitter_sizes: list[int],
) -> AppSettings | None:
    dlg = QDialog(parent)
    dlg.setWindowTitle("Settings")
    dlg.setMinimumWidth(540)
    dlg.setMinimumHeight(440)
    dlg.setModal(True)

    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(16, 14, 16, 14)
    outer.setSpacing(10)

    pref_tabs = QTabWidget()
    pref_tabs.setDocumentMode(False)

    def pref_section(title: str, description: str = "") -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 2)
        lay.setSpacing(2)
        lab = QLabel(title.upper())
        lab.setObjectName("PrefSectionLabel")
        lay.addWidget(lab)
        if description:
            desc = QLabel(description)
            desc.setStyleSheet(f"color: {_MUTED}; font-size: 8.5pt; background: transparent;")
            desc.setWordWrap(True)
            lay.addWidget(desc)
        return w

    def pref_row(label: str, widget: QWidget, tooltip: str = "", hint: str = "") -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(14)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {_TEXT}; font-size: 9.5pt; background: transparent;")
        if tooltip:
            lbl.setToolTip(tooltip)
            widget.setToolTip(tooltip)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(lbl)
        row.addWidget(widget)
        col.addLayout(row)
        if hint:
            h = QLabel(hint)
            h.setStyleSheet(f"color: {_MUTED}; font-size: 8.2pt; background: transparent; padding-left: 2px;")
            h.setWordWrap(True)
            col.addWidget(h)
        return col

    def pref_sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet(f"background:{_BORDER}; max-height:1px; border:none;")
        return f

    def make_tab() -> tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 12)
        lay.setSpacing(14)
        return w, lay

    widgets: dict = {}

    # ── General tab ─────────────────────────────────────────────────
    tab_gen, lay_gen = make_tab()
    lay_gen.addWidget(pref_section("Startup"))
    widgets["auto_connect_cb"] = QCheckBox("")
    lay_gen.addLayout(
        pref_row(
            "Auto-connect when the app opens",
            widgets["auto_connect_cb"],
            tooltip="Automatically connects to the SwiftTrade signal server each time you launch the app.",
            hint="Saves you from clicking Connect manually every time.",
        )
    )
    widgets["start_min_cb"] = QCheckBox("")
    lay_gen.addLayout(
        pref_row(
            "Start the app minimized to the taskbar",
            widgets["start_min_cb"],
            tooltip="The app will open in the background without showing the main window.",
        )
    )

    # Start with Windows — only shown inside a frozen EXE (not dev mode)
    if startup_manager._is_available():
        widgets["start_with_windows_cb"] = QCheckBox("")
        lay_gen.addLayout(
            pref_row(
                "Launch SwiftTrade automatically when Windows starts",
                widgets["start_with_windows_cb"],
                tooltip="Adds SwiftTrade to your Windows startup programs. The app will launch minimized to the tray.",
                hint="Best used together with Auto-connect so the bot is always ready without any manual steps.",
            )
        )

    lay_gen.addWidget(pref_sep())
    lay_gen.addWidget(
        pref_section(
            "Background & power",
            "Control what happens when you close the window and whether the PC can sleep.",
        )
    )
    widgets["close_to_tray_cb"] = QCheckBox("")
    lay_gen.addLayout(
        pref_row(
            "Keep running in the background when the window is closed",
            widgets["close_to_tray_cb"],
            tooltip="Hides SwiftTrade to the system tray instead of quitting when you press the X button.\nRight-click the tray icon to reopen or quit.",
            hint="The bot keeps receiving signals and executing trades even while the window is hidden.",
        )
    )
    widgets["keep_awake_cb"] = QCheckBox("")
    lay_gen.addLayout(
        pref_row(
            "Keep the computer awake while connected",
            widgets["keep_awake_cb"],
            tooltip="Prevents Windows from putting the PC to sleep while the bot is connected.\nThe display can still turn off — only sleep/hibernate is blocked.",
            hint="Important for unattended trading. The PC will sleep normally again when you disconnect.",
        )
    )

    lay_gen.addWidget(pref_sep())
    lay_gen.addWidget(pref_section("Notifications", "Desktop pop-ups when something important happens."))
    widgets["notify_signal_cb"] = QCheckBox("")
    lay_gen.addLayout(
        pref_row(
            "Notify me when a new trading signal arrives",
            widgets["notify_signal_cb"],
            tooltip="Shows a desktop notification each time the bot receives a new buy or sell signal.",
        )
    )
    widgets["notify_connect_cb"] = QCheckBox("")
    lay_gen.addLayout(
        pref_row(
            "Notify me when the connection changes",
            widgets["notify_connect_cb"],
            tooltip="Shows a notification when the bot connects to or disconnects from the server.",
        )
    )
    lay_gen.addStretch(1)
    pref_tabs.addTab(tab_gen, "General")

    # ── Connection tab ───────────────────────────────────────────────
    tab_conn, lay_conn = make_tab()
    lay_conn.addWidget(
        pref_section(
            "Auto-reconnect",
            "If the connection drops, the app will try to reconnect automatically.",
        )
    )
    widgets["reconnect_spin"] = QSpinBox()
    widgets["reconnect_spin"].setRange(1, 120)
    widgets["reconnect_spin"].setSuffix(" seconds")
    widgets["reconnect_spin"].setFixedWidth(120)
    lay_conn.addLayout(
        pref_row(
            "Wait between retry attempts",
            widgets["reconnect_spin"],
            tooltip="How long to wait before trying to reconnect after a connection failure.",
            hint="5–15 seconds is a good balance between responsiveness and server load.",
        )
    )
    widgets["max_retry_spin"] = QSpinBox()
    widgets["max_retry_spin"].setRange(0, 999)
    widgets["max_retry_spin"].setSpecialValueText("Unlimited")
    widgets["max_retry_spin"].setFixedWidth(120)
    lay_conn.addLayout(
        pref_row(
            "Maximum number of retry attempts",
            widgets["max_retry_spin"],
            tooltip="How many times to try reconnecting before giving up. Set to 0 to keep trying forever.",
            hint="0 = keep trying until you manually disconnect.",
        )
    )
    lay_conn.addStretch(1)
    pref_tabs.addTab(tab_conn, "Connection")

    # ── Trading tab ──────────────────────────────────────────────────
    tab_trade, lay_trade = make_tab()
    lay_trade.addWidget(
        pref_section(
            "Order size",
            "Controls how much the bot buys or sells each time a signal arrives.",
        )
    )
    widgets["qty_spin"] = QDoubleSpinBox()
    widgets["qty_spin"].setRange(0.01, 100_000.0)
    widgets["qty_spin"].setDecimals(2)
    widgets["qty_spin"].setSingleStep(0.5)
    widgets["qty_spin"].setSuffix(" units")
    widgets["qty_spin"].setFixedWidth(140)
    lay_trade.addLayout(
        pref_row(
            "Units per trade",
            widgets["qty_spin"],
            tooltip="How many shares/units of a stock to buy or sell per signal. Start small while testing.",
            hint="Start with 1 unit while in demo mode. Increase only when you are confident in the strategy.",
        )
    )
    widgets["stop_spin"] = QDoubleSpinBox()
    widgets["stop_spin"].setRange(0.0, 50.0)
    widgets["stop_spin"].setDecimals(2)
    widgets["stop_spin"].setSingleStep(0.25)
    widgets["stop_spin"].setSuffix(" %")
    widgets["stop_spin"].setSpecialValueText("Off (no stop-loss)")
    widgets["stop_spin"].setFixedWidth(160)
    lay_trade.addLayout(
        pref_row(
            "Stop-loss — auto-sell if position drops by",
            widgets["stop_spin"],
            tooltip="Automatically closes a position if it loses this percentage. Set to 0 to disable.",
            hint="A stop-loss limits how much you can lose on any single trade. 2–5% is common.",
        )
    )
    lay_trade.addWidget(pref_sep())
    lay_trade.addWidget(
        pref_section(
            "Limits & cooldowns",
            "Guardrails to prevent over-trading.",
        )
    )
    widgets["max_daily_spin"] = QSpinBox()
    widgets["max_daily_spin"].setRange(0, 500)
    widgets["max_daily_spin"].setSpecialValueText("No daily limit")
    widgets["max_daily_spin"].setFixedWidth(140)
    lay_trade.addLayout(
        pref_row(
            "Maximum trades per day",
            widgets["max_daily_spin"],
            tooltip="The bot will stop placing trades once this number is reached for the day. 0 = no limit.",
            hint="Useful for keeping trading costs and exposure under control.",
        )
    )
    widgets["cooldown_spin"] = QSpinBox()
    widgets["cooldown_spin"].setRange(0, 3600)
    widgets["cooldown_spin"].setSingleStep(5)
    widgets["cooldown_spin"].setSuffix(" seconds")
    widgets["cooldown_spin"].setSpecialValueText("No cooldown")
    widgets["cooldown_spin"].setFixedWidth(160)
    lay_trade.addLayout(
        pref_row(
            "Minimum gap between trades on the same stock",
            widgets["cooldown_spin"],
            tooltip="Wait at least this many seconds before trading the same stock again. 0 = no cooldown.",
            hint="Prevents the bot from trading the same stock too rapidly.",
        )
    )
    lay_trade.addWidget(pref_sep())
    lay_trade.addWidget(
        pref_section(
            "Safety",
            "Extra controls to keep you in charge.",
        )
    )
    widgets["confirm_trade_cb"] = QCheckBox("")
    lay_trade.addLayout(
        pref_row(
            "Ask me to confirm before each trade",
            widgets["confirm_trade_cb"],
            tooltip="A confirmation dialog will appear before every order is placed. Recommended for new users.",
            hint="Recommended while you are learning how the bot behaves.",
        )
    )
    widgets["skip_non_long_cb"] = QCheckBox("")
    lay_trade.addLayout(
        pref_row(
            "Only act on buy signals (no short-selling)",
            widgets["skip_non_long_cb"],
            tooltip="Ignores any signal that would open a short/sell position. Only buy (long) signals are acted on.",
            hint="Short-selling involves extra risk. Keep this on unless you know what you are doing.",
        )
    )
    lay_trade.addStretch(1)
    pref_tabs.addTab(tab_trade, "Trading")

    # ── Log tab ──────────────────────────────────────────────────────
    tab_log, lay_log = make_tab()
    lay_log.addWidget(
        pref_section(
            "Activity log display",
            "Controls how the log panel on the right side of the app looks.",
        )
    )
    widgets["font_spin"] = QSpinBox()
    widgets["font_spin"].setRange(8, 18)
    widgets["font_spin"].setSuffix(" pt")
    widgets["font_spin"].setFixedWidth(90)
    lay_log.addLayout(pref_row("Text size", widgets["font_spin"], tooltip="Font size for the activity log text."))
    widgets["lines_spin"] = QSpinBox()
    widgets["lines_spin"].setRange(50, 5000)
    widgets["lines_spin"].setSingleStep(50)
    widgets["lines_spin"].setSuffix(" lines")
    widgets["lines_spin"].setFixedWidth(130)
    lay_log.addLayout(
        pref_row(
            "Maximum lines to keep",
            widgets["lines_spin"],
            tooltip="Older log lines are removed once this limit is reached. Higher values use more memory.",
            hint="600 lines is usually plenty for a day's activity.",
        )
    )
    widgets["level_combo"] = QComboBox()
    widgets["level_combo"].addItem("Show everything", "all")
    widgets["level_combo"].addItem("Warnings and errors only", "warn")
    widgets["level_combo"].addItem("Errors only", "error")
    widgets["level_combo"].setFixedWidth(210)
    lay_log.addLayout(
        pref_row(
            "Which messages to show",
            widgets["level_combo"],
            tooltip="Filter the log to only show messages above a certain severity.",
        )
    )
    lay_log.addWidget(pref_sep())
    widgets["auto_scroll_cb"] = QCheckBox("")
    lay_log.addLayout(
        pref_row(
            "Automatically scroll to the latest message",
            widgets["auto_scroll_cb"],
            tooltip="Keeps the log pinned to the bottom so you always see the newest entries.",
        )
    )
    widgets["timestamps_cb"] = QCheckBox("")
    lay_log.addLayout(
        pref_row(
            "Show timestamps next to each log entry",
            widgets["timestamps_cb"],
            tooltip="Prepends the time (HH:MM:SS) to every log message.",
        )
    )
    lay_log.addStretch(1)
    pref_tabs.addTab(tab_log, "Log")

    _apply_to_widgets(s, widgets)

    outer.addWidget(pref_tabs, 1)

    btn_row = QHBoxLayout()
    reset_btn = QPushButton("Reset to defaults")
    reset_btn.setObjectName("GhostBtn")
    reset_btn.setToolTip(
        "Restore all trading, connection, log, and notification settings to their original values. "
        "Your license key, server address, and window layout are not changed."
    )

    def _on_reset() -> None:
        r = QMessageBox.question(
            dlg,
            "Reset settings?",
            "This will restore all settings on this dialog back to their default values.\n\n"
            "Your license key, server address, and window layout will not be affected.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        defaults = s.reset_preferences(keep=s)
        _apply_to_widgets(defaults, widgets)

    reset_btn.clicked.connect(_on_reset)  # type: ignore[arg-type]
    btn_row.addWidget(reset_btn)
    btn_row.addStretch(1)
    outer.addLayout(btn_row)

    btns = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    btns.button(QDialogButtonBox.StandardButton.Save).setText("Save")
    btns.button(QDialogButtonBox.StandardButton.Save).setDefault(True)
    btns.accepted.connect(dlg.accept)  # type: ignore[arg-type]
    btns.rejected.connect(dlg.reject)  # type: ignore[arg-type]
    outer.addWidget(btns)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None

    return _read_from_widgets(s, widgets, splitter_sizes)
