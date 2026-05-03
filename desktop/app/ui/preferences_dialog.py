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
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..settings_store import AppSettings
from .theme import _BORDER


def run_preferences_dialog(
    parent: QWidget,
    s: AppSettings,
    splitter_sizes: list[int],
) -> AppSettings | None:
    dlg = QDialog(parent)
    dlg.setWindowTitle("Preferences")
    dlg.setMinimumWidth(520)
    dlg.setMinimumHeight(420)
    dlg.setModal(True)

    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(16, 14, 16, 14)
    outer.setSpacing(10)

    pref_tabs = QTabWidget()
    pref_tabs.setDocumentMode(False)

    def pref_section(title: str) -> QLabel:
        lab = QLabel(title.upper())
        lab.setObjectName("PrefSectionLabel")
        return lab

    def pref_row(label: str, widget: QWidget, tooltip: str = "") -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        lbl = QLabel(label)
        if tooltip:
            lbl.setToolTip(tooltip)
            widget.setToolTip(tooltip)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(lbl)
        row.addWidget(widget)
        return row

    def pref_sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet(f"background:{_BORDER}; max-height:1px; border:none;")
        return f

    def make_tab() -> tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 16, 18, 12)
        lay.setSpacing(13)
        return w, lay

    tab_gen, lay_gen = make_tab()
    lay_gen.addWidget(pref_section("Startup"))
    auto_connect_cb = QCheckBox("")
    auto_connect_cb.setChecked(s.auto_connect_on_start)
    lay_gen.addLayout(
        pref_row(
            "Auto-connect on startup",
            auto_connect_cb,
            "Automatically connect to the bot server when the app starts.",
        )
    )
    start_min_cb = QCheckBox("")
    start_min_cb.setChecked(s.start_minimized)
    lay_gen.addLayout(
        pref_row(
            "Start minimized",
            start_min_cb,
            "Open the window minimized to the taskbar on launch.",
        )
    )
    lay_gen.addWidget(pref_sep())
    lay_gen.addWidget(pref_section("Notifications"))
    notify_signal_cb = QCheckBox("")
    notify_signal_cb.setChecked(s.notify_on_signal)
    lay_gen.addLayout(
        pref_row(
            "Notify on incoming signal",
            notify_signal_cb,
            "Show a status-bar message each time a signal arrives.",
        )
    )
    notify_connect_cb = QCheckBox("")
    notify_connect_cb.setChecked(s.notify_on_connect)
    lay_gen.addLayout(
        pref_row(
            "Notify on connect / disconnect",
            notify_connect_cb,
            "Log a message when the WebSocket connection status changes.",
        )
    )
    lay_gen.addStretch(1)
    pref_tabs.addTab(tab_gen, "  General  ")

    tab_conn, lay_conn = make_tab()
    lay_conn.addWidget(pref_section("Reconnect behaviour"))
    reconnect_spin = QSpinBox()
    reconnect_spin.setRange(1, 120)
    reconnect_spin.setValue(s.reconnect_interval_s)
    reconnect_spin.setSuffix("  s")
    reconnect_spin.setFixedWidth(95)
    lay_conn.addLayout(
        pref_row(
            "Reconnect interval",
            reconnect_spin,
            "Seconds to wait before retrying after a connection drop.",
        )
    )
    max_retry_spin = QSpinBox()
    max_retry_spin.setRange(0, 999)
    max_retry_spin.setValue(s.max_reconnect_attempts)
    max_retry_spin.setSpecialValueText("Unlimited")
    max_retry_spin.setFixedWidth(110)
    lay_conn.addLayout(
        pref_row(
            "Max reconnect attempts",
            max_retry_spin,
            "Stop retrying after this many failed attempts. 0 = keep trying forever.",
        )
    )
    lay_conn.addStretch(1)
    pref_tabs.addTab(tab_conn, "  Connection  ")

    tab_trade, lay_trade = make_tab()
    lay_trade.addWidget(pref_section("Order sizing"))
    qty_spin = QDoubleSpinBox()
    qty_spin.setRange(0.01, 100_000.0)
    qty_spin.setDecimals(2)
    qty_spin.setSingleStep(0.5)
    qty_spin.setValue(s.order_quantity)
    qty_spin.setSuffix("  units")
    qty_spin.setFixedWidth(130)
    lay_trade.addLayout(
        pref_row(
            "Default order quantity",
            qty_spin,
            "Number of shares / units per market order when the signal does not specify a size.",
        )
    )
    stop_spin = QDoubleSpinBox()
    stop_spin.setRange(0.0, 50.0)
    stop_spin.setDecimals(2)
    stop_spin.setSingleStep(0.25)
    stop_spin.setValue(s.default_stop_loss_pct)
    stop_spin.setSuffix("  %")
    stop_spin.setSpecialValueText("Disabled")
    stop_spin.setFixedWidth(120)
    lay_trade.addLayout(
        pref_row(
            "Default stop-loss",
            stop_spin,
            "Fallback stop-loss percentage when the incoming signal does not provide one. 0 = disabled.",
        )
    )
    lay_trade.addWidget(pref_sep())
    lay_trade.addWidget(pref_section("Risk controls"))
    max_daily_spin = QSpinBox()
    max_daily_spin.setRange(0, 500)
    max_daily_spin.setValue(s.max_daily_trades)
    max_daily_spin.setSpecialValueText("Unlimited")
    max_daily_spin.setFixedWidth(120)
    lay_trade.addLayout(
        pref_row(
            "Max trades per day",
            max_daily_spin,
            "Stop placing orders once this many live trades have been placed today. 0 = no limit.",
        )
    )
    cooldown_spin = QSpinBox()
    cooldown_spin.setRange(0, 3600)
    cooldown_spin.setSingleStep(5)
    cooldown_spin.setValue(s.signal_cooldown_s)
    cooldown_spin.setSuffix("  s")
    cooldown_spin.setSpecialValueText("No cooldown")
    cooldown_spin.setFixedWidth(130)
    lay_trade.addLayout(
        pref_row(
            "Signal cooldown (per symbol)",
            cooldown_spin,
            "Minimum seconds between two executed signals for the same ticker. 0 = no cooldown.",
        )
    )
    lay_trade.addWidget(pref_sep())
    lay_trade.addWidget(pref_section("Behaviour"))
    confirm_trade_cb = QCheckBox("")
    confirm_trade_cb.setChecked(s.confirm_before_trade)
    lay_trade.addLayout(
        pref_row(
            "Confirm before placing order",
            confirm_trade_cb,
            "Show a confirmation dialog before each live market order is submitted.",
        )
    )
    skip_non_long_cb = QCheckBox("")
    skip_non_long_cb.setChecked(s.skip_non_long_signals)
    lay_trade.addLayout(
        pref_row(
            "Skip non-LONG signals",
            skip_non_long_cb,
            "Ignore SHORT and FLAT signal directions — only execute LONG entries.",
        )
    )
    lay_trade.addStretch(1)
    pref_tabs.addTab(tab_trade, "  Trading  ")

    tab_log, lay_log = make_tab()
    lay_log.addWidget(pref_section("Display"))
    font_spin = QSpinBox()
    font_spin.setRange(8, 18)
    font_spin.setValue(s.log_font_size)
    font_spin.setSuffix("  pt")
    font_spin.setFixedWidth(85)
    font_spin.setToolTip("Monospace font size for the activity log.")
    lay_log.addLayout(pref_row("Font size", font_spin))
    lines_spin = QSpinBox()
    lines_spin.setRange(50, 5000)
    lines_spin.setSingleStep(50)
    lines_spin.setValue(s.log_max_lines)
    lines_spin.setSuffix("  lines")
    lines_spin.setFixedWidth(120)
    lines_spin.setToolTip("How many lines to keep before older ones are discarded.")
    lay_log.addLayout(pref_row("Max entries", lines_spin))
    level_combo = QComboBox()
    level_combo.addItem("All messages", "all")
    level_combo.addItem("Warnings & errors only", "warn")
    level_combo.addItem("Errors only", "error")
    level_combo.setCurrentIndex({"all": 0, "warn": 1, "error": 2}.get(s.log_level_filter, 0))
    level_combo.setFixedWidth(190)
    level_combo.setToolTip("Filter which log messages appear in the activity pane.")
    lay_log.addLayout(pref_row("Log level filter", level_combo))
    lay_log.addWidget(pref_sep())
    lay_log.addWidget(pref_section("Behaviour"))
    auto_scroll_cb = QCheckBox("")
    auto_scroll_cb.setChecked(s.log_auto_scroll)
    lay_log.addLayout(
        pref_row(
            "Auto-scroll to latest",
            auto_scroll_cb,
            "Automatically scroll to the newest log entry when new lines arrive.",
        )
    )
    timestamps_cb = QCheckBox("")
    timestamps_cb.setChecked(s.log_show_timestamps)
    lay_log.addLayout(
        pref_row(
            "Show timestamps",
            timestamps_cb,
            "Prefix each log line with [HH:MM:SS].",
        )
    )
    lay_log.addStretch(1)
    pref_tabs.addTab(tab_log, "  Activity Log  ")

    outer.addWidget(pref_tabs, 1)
    btns = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    btns.button(QDialogButtonBox.StandardButton.Save).setDefault(True)
    btns.accepted.connect(dlg.accept)  # type: ignore[arg-type]
    btns.rejected.connect(dlg.reject)  # type: ignore[arg-type]
    outer.addWidget(btns)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None

    return AppSettings(
        ws_url=s.ws_url,
        license_key=s.license_key,
        reconnect_interval_s=reconnect_spin.value(),
        max_reconnect_attempts=max_retry_spin.value(),
        order_quantity=qty_spin.value(),
        max_daily_trades=max_daily_spin.value(),
        signal_cooldown_s=cooldown_spin.value(),
        default_stop_loss_pct=stop_spin.value(),
        confirm_before_trade=confirm_trade_cb.isChecked(),
        skip_non_long_signals=skip_non_long_cb.isChecked(),
        log_font_size=font_spin.value(),
        log_max_lines=lines_spin.value(),
        log_auto_scroll=auto_scroll_cb.isChecked(),
        log_show_timestamps=timestamps_cb.isChecked(),
        log_level_filter=level_combo.currentData(),
        notify_on_signal=notify_signal_cb.isChecked(),
        notify_on_connect=notify_connect_cb.isChecked(),
        auto_connect_on_start=auto_connect_cb.isChecked(),
        start_minimized=start_min_cb.isChecked(),
        splitter_sizes=splitter_sizes,
    )
