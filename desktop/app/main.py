from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyleFactory,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop, asyncSlot

from .crypto_store import CryptoStore, SecretPayload
from .settings_store import AppSettings, SettingsStore
from .t212_client import T212APIError, T212Client, T212Keys
from .ws_client import ExecWsClient, WsConfig, _smoke_health_url

# ── colour tokens matching the AlgoFlow website (sky-500 primary) ─────────────
_BG       = "#0c0c10"   # body — deepest layer
_SURFACE  = "#13131a"   # cards / panels
_SURFACE2 = "#1c1c25"   # elevated cards, groupboxes
_BORDER   = "#2a2a38"   # subtle borders
_BORDER2  = "#3a3a4e"   # interactive borders
_SKY      = "#0ea5e9"   # sky-500 — primary accent (website)
_SKY_HVR  = "#38bdf8"   # sky-400 — hover
_SKY_DIM  = "#0c3a52"   # sky tint bg for tags/indicators
_TEXT     = "#f1f1f3"   # primary text
_MUTED    = "#8b8b9e"   # secondary / hint text
_SUCCESS  = "#22c55e"
_WARN     = "#f59e0b"
_DANGER   = "#ef4444"

_DESKTOP_QSS = f"""
/* ── globals ──────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 9.5pt;
    color: {_TEXT};
    background-color: {_BG};
}}

/* ── top-bar status card ─────────────────────────────────────────── */
QFrame#StatusCard {{
    background-color: {_SURFACE};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    min-width: 160px;
}}

/* ── broker pill ─────────────────────────────────────────────────── */
QLabel#BrokerPill {{
    color: {_TEXT};
    background-color: {_SURFACE};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 8.5pt;
}}

/* ── labelled field labels (above each input) ───────────────────── */
QLabel#FieldLabel {{
    color: {_TEXT};
    font-size: 9.5pt;
    font-weight: 600;
    background: transparent;
    padding: 0;
    margin: 0;
}}

/* ── hint text ───────────────────────────────────────────────────── */
QLabel#HintLabel {{
    color: {_MUTED};
    font-size: 8.8pt;
    background: transparent;
    padding: 0;
    margin: 0;
}}

/* ── section headings inside tabs ────────────────────────────────── */
QLabel#SectionTitle {{
    color: {_TEXT};
    font-size: 9pt;
    font-weight: 600;
    background: transparent;
    padding: 0;
    margin: 0;
}}

/* ── groupboxes ───────────────────────────────────────────────────── */
QGroupBox {{
    font-weight: 600;
    font-size: 9.5pt;
    color: {_TEXT};
    margin-top: 18px;
    padding: 20px 16px 14px 16px;
    border: 1px solid {_BORDER};
    border-radius: 10px;
    background-color: {_SURFACE2};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 1px;
    padding: 2px 10px;
    color: {_SKY};
    background-color: {_BG};
    border-radius: 4px;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 0.03em;
}}

/* ── line edits ───────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 8px;
    padding: 9px 12px;
    min-height: 18px;
    selection-background-color: {_SKY_DIM};
    selection-color: #ffffff;
    font-size: 9.5pt;
}}
QLineEdit:focus {{
    border: 1px solid {_SKY};
    background-color: {_SURFACE2};
}}
QLineEdit:disabled {{
    color: {_MUTED};
    border-color: {_BORDER};
}}

/* ── text log ────────────────────────────────────────────────────── */
QTextEdit {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {_SKY_DIM};
    selection-color: #ffffff;
}}

/* ── tabs ─────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {_BORDER};
    border-radius: 0 8px 8px 8px;
    background-color: {_SURFACE};
    top: -1px;
    margin-top: 0;
}}
QTabBar::tab {{
    background-color: {_BG};
    color: {_MUTED};
    border: 1px solid {_BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 4px 14px;
    margin-right: 2px;
    min-width: 4.5em;
    font-size: 8.5pt;
}}
QTabBar::tab:selected {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border-bottom: 2px solid {_SKY};
    font-weight: 600;
    padding-bottom: 2px;
}}
QTabBar::tab:hover:!selected {{
    color: {_TEXT};
    background-color: {_SURFACE2};
}}

/* ── buttons ─────────────────────────────────────────────────────── */
QPushButton#PrimaryBtn {{
    background-color: {_SKY};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 22px;
    max-height: 28px;
    font-weight: 700;
    font-size: 8.5pt;
    letter-spacing: 0.01em;
}}
QPushButton#PrimaryBtn:hover {{ background-color: {_SKY_HVR}; }}
QPushButton#PrimaryBtn:pressed {{ background-color: #0284c7; }}
QPushButton#PrimaryBtn:disabled {{
    background-color: {_BORDER};
    color: {_MUTED};
}}

QPushButton#SecondaryBtn {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 22px;
    max-height: 28px;
    font-weight: 600;
    font-size: 8.5pt;
}}
QPushButton#SecondaryBtn:hover {{
    background-color: #252530;
    border-color: {_SKY};
    color: {_SKY_HVR};
}}
QPushButton#SecondaryBtn:pressed {{ background-color: {_SURFACE}; }}
QPushButton#SecondaryBtn:disabled {{ color: {_MUTED}; border-color: {_BORDER}; }}

QPushButton#GhostBtn {{
    background-color: transparent;
    color: {_MUTED};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    min-height: 20px;
    max-height: 26px;
    font-size: 8.5pt;
}}
QPushButton#GhostBtn:hover {{
    color: {_TEXT};
    border-color: {_BORDER2};
    background-color: {_SURFACE2};
}}

QPushButton#DangerBtn {{
    background-color: {_SURFACE};
    color: #fca5a5;
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 22px;
    max-height: 28px;
    font-weight: 600;
    font-size: 8.5pt;
}}
QPushButton#DangerBtn:hover {{
    background-color: #2d0f0f;
    border-color: {_DANGER};
    color: #fee2e2;
}}
QPushButton#DangerBtn:pressed {{ background-color: #450a0a; }}
QPushButton#DangerBtn:disabled {{ color: {_MUTED}; border-color: {_BORDER}; background-color: {_SURFACE}; }}

/* ── checkbox ────────────────────────────────────────────────────── */
QCheckBox {{
    color: {_TEXT};
    spacing: 6px;
    font-size: 8.5pt;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 4px;
    border: 1px solid {_BORDER2};
    background-color: {_SURFACE};
}}
QCheckBox::indicator:checked {{
    background-color: {_SKY};
    border-color: {_SKY};
}}
QCheckBox::indicator:hover {{
    border-color: {_SKY};
}}

/* ── tables ───────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {_SURFACE};
    alternate-background-color: {_SURFACE2};
    color: {_TEXT};
    gridline-color: {_BORDER};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    font-size: 9pt;
}}
QTableWidget::item:selected {{
    background-color: {_SKY_DIM};
    color: #e0f2fe;
}}
QHeaderView::section {{
    background-color: {_SURFACE2};
    color: {_MUTED};
    padding: 5px 8px;
    border: none;
    border-bottom: 1px solid {_BORDER};
    border-right: 1px solid {_BORDER};
    font-weight: 700;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
QHeaderView::section:last {{
    border-right: none;
}}

/* ── list widget ────────────────────────────────────────────────── */
QListWidget {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 4px;
    font-size: 9pt;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-radius: 5px;
}}
QListWidget::item:selected {{
    background-color: {_SKY_DIM};
    color: #e0f2fe;
}}

/* ── splitter ────────────────────────────────────────────────────── */
QSplitter::handle:horizontal {{
    background-color: {_BORDER};
    width: 3px;
    margin: 6px 2px;
    border-radius: 2px;
}}
QSplitter::handle:horizontal:hover {{
    background-color: {_SKY};
}}

QSplitter::handle:vertical {{
    background-color: {_BORDER};
    height: 4px;
    margin: 2px 6px;
    border-radius: 2px;
}}
QSplitter::handle:vertical:hover {{
    background-color: {_SKY};
}}

/* ── scrollbars ───────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {_SURFACE};
    width: 10px;
    margin: 4px 2px 4px 0;
    border-radius: 5px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER2};
    min-height: 28px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{ background: {_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background: {_SURFACE};
    height: 10px;
    margin: 0 4px 2px 4px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {_BORDER2};
    min-width: 28px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{ background: {_MUTED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── scroll area ─────────────────────────────────────────────────── */
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* ── menu bar ────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {_BG};
    color: {_MUTED};
    padding: 0 4px;
    spacing: 0;
    border-bottom: 1px solid {_BORDER};
    font-size: 8.5pt;
}}
QMenuBar::item {{ padding: 2px 8px; border-radius: 4px; margin: 1px 0; }}
QMenuBar::item:selected {{ background-color: {_SURFACE2}; color: {_TEXT}; }}
QMenu {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 8px;
    padding: 4px;
    font-size: 9.5pt;
}}
QMenu::item {{ padding: 8px 16px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: {_SKY_DIM}; color: #e0f2fe; }}

/* ── status bar at the bottom ─────────────────────────────────────── */
QStatusBar {{
    background-color: {_BG};
    color: {_MUTED};
    border-top: 1px solid {_BORDER};
    font-size: 8pt;
    padding: 0 4px;
    min-height: 18px;
    max-height: 22px;
}}
"""


def _apply_desktop_styles(app: QApplication) -> None:
    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:
        app.setStyle(fusion)
    app.setStyleSheet(_DESKTOP_QSS)


# ── small widget factories ────────────────────────────────────────────────────
def _field_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("FieldLabel")
    return lab


def _hint(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("HintLabel")
    lab.setWordWrap(True)
    return lab


def _section_title(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("SectionTitle")
    f = lab.font()
    f.setBold(True)
    lab.setFont(f)
    return lab


def _divider() -> QFrame:
    d = QFrame()
    d.setFrameShape(QFrame.Shape.HLine)
    d.setStyleSheet(f"color: {_BORDER}; background: {_BORDER}; max-height: 1px; border: none;")
    return d


def _status_text(status: str) -> tuple[str, str]:
    if status == "ONLINE":
        return ("Connected", _SUCCESS)
    if status == "CONNECTING":
        return ("Connecting…", _WARN)
    return ("Not connected", _DANGER)


# ── main window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AlgoFlow — Desktop Executor")
        self.setMinimumSize(980, 640)
        self.resize(1120, 720)

        self._base_dir = Path.home() / ".t212_executor"
        self._store = CryptoStore(self._base_dir)
        self._settings_store = SettingsStore(self._base_dir)
        self._ws_task: asyncio.Task | None = None
        self._ws_client: ExecWsClient | None = None

        # ── status dot + label ───────────────────────────────────────
        self.status_dot = QLabel("●")
        self.status_dot.setAlignment(Qt.AlignCenter)
        self.status_dot.setFixedWidth(16)

        self.status_label = QLabel("Not connected")
        self.status_label.setMinimumWidth(100)
        self.status_label.setStyleSheet(f"font-weight: 600; font-size: 9pt; color: {_DANGER};")

        # ── broker indicator ─────────────────────────────────────────
        self.t212_status = QLabel("Broker: not configured")
        self.t212_status.setObjectName("BrokerPill")

        # ── inputs ───────────────────────────────────────────────────
        self.license_key = QLineEdit()
        self.license_key.setPlaceholderText("Paste your license key from the AlgoFlow portal")
        self.license_key.setToolTip("UUID from the web portal, e.g. 550e8400-e29b-41d4-a716-446655440000")

        self.ws_url = QLineEdit("ws://127.0.0.1:8010/ws/exec")
        self.ws_url.setToolTip(
            "Backend WebSocket address. Leave as default if the bot server runs on this PC."
        )

        self.t212_api_key = QLineEdit()
        self.t212_api_key.setPlaceholderText("API key — Trading212 → Settings → API")
        self.t212_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.t212_secret_key = QLineEdit()
        self.t212_secret_key.setPlaceholderText("API secret (optional — only if shown by T212)")
        self.t212_secret_key.setEchoMode(QLineEdit.EchoMode.Password)

        # ── checkboxes ───────────────────────────────────────────────
        self.show_t212_secrets = QCheckBox("Reveal keys on screen")
        self.show_t212_secrets.setToolTip("Show/hide API credentials. Turn off if others can see your screen.")
        self.show_t212_secrets.toggled.connect(self._on_show_t212_secrets_toggled)  # type: ignore[arg-type]

        self.exec_mode = QCheckBox("Place real trades  (Live mode)")
        self.exec_mode.setChecked(False)
        self.exec_mode.setToolTip(
            "Off: signals are logged only — no orders sent.\n"
            "On: LONG signals place real market orders on Trading212."
        )
        self.exec_mode.toggled.connect(self._on_live_mode_toggled)  # type: ignore[arg-type]

        # ── buttons ──────────────────────────────────────────────────
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("PrimaryBtn")
        self.connect_btn.setFixedWidth(96)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("DangerBtn")
        self.disconnect_btn.setFixedWidth(96)
        self.disconnect_btn.setEnabled(False)

        self.test_t212_btn = QPushButton("Test connection")
        self.test_t212_btn.setObjectName("SecondaryBtn")
        self.test_t212_btn.setToolTip("Verifies keys with Trading212. Nothing saved until you click Save.")

        self.save_btn = QPushButton("Save keys (encrypted)")
        self.save_btn.setObjectName("PrimaryBtn")
        self.save_btn.setToolTip("Keys are encrypted and stored on this computer only.")

        self.connect_btn.clicked.connect(self.on_connect_clicked)   # type: ignore[arg-type]
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)  # type: ignore[arg-type]
        self.save_btn.clicked.connect(self.on_save_clicked)          # type: ignore[arg-type]
        self.test_t212_btn.clicked.connect(self.on_test_t212_clicked)  # type: ignore[arg-type]

        # ── event log ────────────────────────────────────────────────
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.document().setMaximumBlockCount(600)
        _mono = QFont("Cascadia Mono", 10)
        if not _mono.exactMatch():
            _mono = QFont("Consolas", 10)
        self.event_log.setFont(_mono)

        # ── activity data ─────────────────────────────────────────────
        self._last_bot_snapshot: dict[str, dict] = {}
        self._signal_rows: list[tuple[str, str, str, str, str]] = []
        self._market_rows: list[tuple[str, str]] = []
        self._signal_count = 0

        self.activity_symbol_filter = QLineEdit()
        self.activity_symbol_filter.setPlaceholderText("Filter by ticker (e.g. AAPL, ASML)…")
        self.activity_symbol_filter.setClearButtonEnabled(True)  # type: ignore[attr-defined]

        self.market_table = QTableWidget(0, 2)
        self.market_table.setHorizontalHeaderLabels(["Symbol", "Market state"])
        self._wire_table(self.market_table)

        self.bot_table = QTableWidget(0, 7)
        self.bot_table.setHorizontalHeaderLabels(
            ["Symbol", "Ready", "Regime", "Trigger", "Side", "Blocked", "Reason"]
        )
        self._wire_table(self.bot_table)

        self.signals_table = QTableWidget(0, 5)
        self.signals_table.setHorizontalHeaderLabels(["Time", "ID", "Direction", "Symbol", "Summary"])
        self._wire_table(self.signals_table)

        self.exec_queue = QListWidget()
        self.exec_queue.addItem("No signals received yet.")

        # ── tabs ─────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_setup_tab(), "  Setup  ")
        self.tabs.setTabToolTip(0, "License key, server address, and Trading212 API keys")
        self.tabs.addTab(self._build_activity_tab(), "  Markets && Bot  ")
        self.tabs.setTabToolTip(1, "Live market hours, bot state, and recent signals")
        self.tabs.addTab(self._build_trades_tab(), "  Trades  ")
        self.tabs.setTabToolTip(2, "Signal queue and execution status")
        self.tabs.setDocumentMode(True)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._build_log_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([580, 440])

        root = QVBoxLayout()
        root.setContentsMargins(10, 4, 10, 6)
        root.setSpacing(4)
        root.addLayout(self._build_top_bar())
        root.addWidget(_divider())
        root.addWidget(splitter, 1)

        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        self._build_menu_bar()
        self._setup_status_bar()

        self._set_status("OFFLINE")
        self._append_event("info", "App started — AlgoFlow Desktop Executor.")
        self._append_event("info", f"Build: {self._git_version()}")
        self._refresh_t212_status()

        settings = self._settings_store.load()
        if settings.ws_url:
            self.ws_url.setText(settings.ws_url)
        if settings.license_key:
            self.license_key.setText(settings.license_key)

        existing = self._store.load()
        if existing:
            self.t212_api_key.setText(existing.t212_api_key)
            self.t212_secret_key.setText(existing.t212_secret_key or "")
            self._refresh_t212_status()

        self.activity_symbol_filter.textChanged.connect(self._on_filter_changed)  # type: ignore[arg-type]

    # ── helpers ──────────────────────────────────────────────────────────────

    def _git_version(self) -> str:
        try:
            repo_root = Path(__file__).resolve().parents[2]
            out = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], cwd=str(repo_root), text=True
            )
            return out.strip()
        except Exception:
            return "unknown"

    # ── top bar ──────────────────────────────────────────────────────────────

    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.setContentsMargins(0, 0, 0, 0)

        # Status card
        status_card = QFrame()
        status_card.setObjectName("StatusCard")
        sc = QHBoxLayout(status_card)
        sc.setContentsMargins(8, 3, 10, 3)
        sc.setSpacing(6)
        sc.addWidget(self.status_dot)
        sc.addWidget(self.status_label)
        bar.addWidget(status_card)

        # Broker pill
        bar.addWidget(self.t212_status)

        bar.addStretch(1)

        # Live mode on the right, closer to the action buttons
        bar.addWidget(self.exec_mode)
        bar.addSpacing(8)
        bar.addWidget(self.connect_btn)
        bar.addWidget(self.disconnect_btn)
        return bar

    # ── menu bar ─────────────────────────────────────────────────────────────

    def _build_menu_bar(self) -> None:
        bar = self.menuBar()
        hmenu = bar.addMenu("&Help")
        for label, slot in [
            ("&Quick start tips", self._show_quick_tips),
            ("&About AlgoFlow", self._show_about),
        ]:
            a = QAction(label, self)
            a.triggered.connect(slot)  # type: ignore[arg-type]
            hmenu.addAction(a)

    def _setup_status_bar(self) -> None:
        sb = self.statusBar()
        self._sb_label = QLabel("")
        sb.addWidget(self._sb_label)
        sb.setSizeGripEnabled(False)

    def _set_sb(self, text: str) -> None:
        self._sb_label.setText(f"  {text}")

    # ── setup tab ────────────────────────────────────────────────────────────

    def _build_setup_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        # ── Subscription group ───────────────────────────────────────
        grp_sub = QGroupBox("Subscription && server")
        g = QVBoxLayout(grp_sub)
        g.setSpacing(10)

        g.addWidget(_field_label("License key"))
        g.addWidget(self.license_key)
        g.addWidget(_hint("Copy and paste the full key from your AlgoFlow account on the website."))

        g.addSpacing(6)
        g.addWidget(_field_label("Bot server address"))
        g.addWidget(self.ws_url)
        g.addWidget(
            _hint(
                "Leave as default (ws://127.0.0.1:8010/ws/exec) if the server runs on this computer."
            )
        )
        layout.addWidget(grp_sub)

        # ── Trading212 keys group ────────────────────────────────────
        grp_keys = QGroupBox("Trading212 API keys")
        k = QVBoxLayout(grp_keys)
        k.setSpacing(10)

        k.addWidget(
            _hint("Only needed to place real trades or check market hours. Keys never leave this PC.")
        )
        k.addWidget(_field_label("API key"))
        k.addWidget(self.t212_api_key)
        k.addWidget(_field_label("API secret  (optional)"))
        k.addWidget(self.t212_secret_key)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addWidget(self.show_t212_secrets)
        btns.addStretch(1)
        btns.addWidget(self.test_t212_btn)
        k.addLayout(btns)
        k.addWidget(self.save_btn)
        layout.addWidget(grp_keys)

        # ── Live mode group ──────────────────────────────────────────
        grp_live = QGroupBox("Trade execution")
        lv = QVBoxLayout(grp_live)
        lv.setSpacing(10)
        lv.addWidget(self.exec_mode)
        lv.addWidget(
            _hint(
                "Off (default): signals are recorded in the log and queue — no orders are sent.\n"
                "On: LONG signals place real market orders on your Trading212 account."
            )
        )
        layout.addWidget(grp_live)

        # ── Troubleshooting group ────────────────────────────────────
        grp_diag = QGroupBox("Troubleshooting")
        dg = QVBoxLayout(grp_diag)
        dg.setSpacing(8)
        dg.addWidget(
            _hint(
                "If the app cannot reach the backend, use this to open a health check page in your browser "
                "(no secrets are shown)."
            )
        )
        self.diagnostics_btn = QPushButton("Open backend health check")
        self.diagnostics_btn.setObjectName("GhostBtn")
        self.diagnostics_btn.clicked.connect(self._open_backend_diagnostics)  # type: ignore[arg-type]
        dg.addWidget(self.diagnostics_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(grp_diag)

        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer = QWidget()
        QVBoxLayout(outer).addWidget(scroll)
        outer.layout().setContentsMargins(0, 0, 0, 0)  # type: ignore[union-attr]
        return outer

    # ── activity tab ─────────────────────────────────────────────────────────

    def _build_activity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(10)

        filt_row = QHBoxLayout()
        filt_row.setSpacing(8)
        filt_row.addWidget(QLabel("Filter:"))
        filt_row.addWidget(self.activity_symbol_filter, 1)
        layout.addLayout(filt_row)

        layout.addWidget(_divider())

        # Vertical splitter so users can resize how much space each table gets.
        v_split = QSplitter(Qt.Orientation.Vertical)

        p_market = QWidget()
        lm = QVBoxLayout(p_market)
        lm.setContentsMargins(0, 0, 0, 0)
        lm.setSpacing(6)
        lm.addWidget(_section_title("Market hours  (from Trading212)"))
        lm.addWidget(self.market_table, 1)
        v_split.addWidget(p_market)

        p_bot = QWidget()
        lb = QVBoxLayout(p_bot)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.setSpacing(4)
        lb.addWidget(_section_title("Bot state  (per symbol, latest snapshot)"))
        lb.addWidget(
            _hint(
                "When the exchange is closed and the server has no cached price bars yet, "
                "you will see ready=False and reason like market_closed_no_cache — that is expected. "
                "After a session with data, cached bars allow richer fields even off-hours.",
            ),
        )
        lb.addWidget(self.bot_table, 1)
        v_split.addWidget(p_bot)

        p_sig = QWidget()
        ls = QVBoxLayout(p_sig)
        ls.setContentsMargins(0, 0, 0, 0)
        ls.setSpacing(6)
        ls.addWidget(_section_title("Recent signals  (newest first)"))
        ls.addWidget(self.signals_table, 1)
        v_split.addWidget(p_sig)

        v_split.setStretchFactor(0, 1)
        v_split.setStretchFactor(1, 2)
        v_split.setStretchFactor(2, 2)
        v_split.setSizes([140, 220, 200])
        layout.addWidget(v_split, 1)
        return w

    # ── trades tab ───────────────────────────────────────────────────────────

    def _build_trades_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(10)
        layout.addWidget(
            _hint(
                "Every signal the bot sends appears here. With live mode off, "
                "nothing is traded — check the activity log on the right for detail."
            )
        )
        layout.addWidget(_section_title("Signal queue"))
        layout.addWidget(self.exec_queue, 1)
        return w

    # ── log panel ────────────────────────────────────────────────────────────

    def _build_log_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(6)
        head.addWidget(_section_title("Activity log"))
        head.addStretch(1)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("GhostBtn")
        clear_btn.setFixedWidth(70)
        clear_btn.setToolTip("Clears this log view only — the server is not affected.")
        clear_btn.clicked.connect(self.event_log.clear)  # type: ignore[arg-type]
        head.addWidget(clear_btn)

        layout.addLayout(head)
        layout.addWidget(self.event_log, 1)
        return w

    # ── menu callbacks ────────────────────────────────────────────────────────

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About AlgoFlow Desktop",
            f"AlgoFlow — Desktop Executor\n\n"
            "Bridges your AlgoFlow bot server to Trading212. Signals from TradingView "
            "(or any webhook source) flow through the server to this app, which can "
            "optionally place real orders on your behalf.\n\n"
            f"Build: {self._git_version()}",
        )

    def _show_quick_tips(self) -> None:
        QMessageBox.information(
            self,
            "Quick start",
            "1.  Setup tab — paste your license key, leave the server address as default.\n\n"
            "2.  Trading212 keys — enter your API key, click 'Test connection', then Save.\n\n"
            "3.  Click Connect (top bar) — status changes to green when linked.\n\n"
            "4.  Live mode — leave Off while you learn; turn On only for real orders.\n\n"
            "Tip: right-click any table row to copy it.",
        )

    # ── status helpers ────────────────────────────────────────────────────────

    def _set_status(self, status: str) -> None:
        text, color = _status_text(status)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-weight: 600; font-size: 9pt; color: {color};")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 15px;")

    def _on_ws_status(self, status: str) -> None:
        self._set_status(status)
        if status == "ONLINE":
            self._set_sb("Connected to bot server — receiving data.")
        elif status == "CONNECTING":
            self._set_sb("Connecting to bot server…")
        else:
            self._set_sb("")

    def _refresh_t212_status(self) -> None:
        stored = self._store.load()
        if stored and stored.t212_api_key:
            self.t212_status.setText("Broker: API keys saved ✓")
        else:
            self.t212_status.setText("Broker: not configured")

    # ── coloured log append ───────────────────────────────────────────────────

    def _append_event(self, level: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        colour_map = {
            "info":    _TEXT,
            "ok":      _SUCCESS,
            "warn":    _WARN,
            "error":   _DANGER,
        }
        colour = colour_map.get(level, _TEXT)

        cursor = self.event_log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Timestamp in muted colour
        fmt_ts = QTextCharFormat()
        fmt_ts.setForeground(QColor(_MUTED))
        cursor.setCharFormat(fmt_ts)
        cursor.insertText(f"[{ts}] ")

        # Message in level colour
        fmt_msg = QTextCharFormat()
        fmt_msg.setForeground(QColor(colour))
        cursor.setCharFormat(fmt_msg)
        cursor.insertText(message + "\n")

        self.event_log.setTextCursor(cursor)
        self.event_log.ensureCursorVisible()

    # ── live mode toggle ──────────────────────────────────────────────────────

    def _on_live_mode_toggled(self, checked: bool) -> None:
        if not checked:
            self._set_sb("Live mode off — signals will be logged only.")
            return
        r = QMessageBox.warning(
            self,
            "Enable live trading?",
            "Live mode will send real-money orders to Trading212 every time the bot fires a LONG signal.\n\n"
            "Leave it off if you just want to watch signals in the log.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if r != QMessageBox.StandardButton.Ok:
            self.exec_mode.blockSignals(True)
            self.exec_mode.setChecked(False)
            self.exec_mode.blockSignals(False)
        else:
            self._set_sb("⚠  Live mode ON — real orders will be placed.")

    def _on_show_t212_secrets_toggled(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.t212_api_key.setEchoMode(mode)
        self.t212_secret_key.setEchoMode(mode)

    # ── backend diagnostics ───────────────────────────────────────────────────

    def _open_backend_diagnostics(self) -> None:
        url = QUrl(_smoke_health_url(self.ws_url.text()))
        if not QDesktopServices.openUrl(url):
            self._append_event("warn", f"Could not open browser: {url.toString()}")

    # ── connect / disconnect ──────────────────────────────────────────────────

    @asyncSlot()
    async def on_connect_clicked(self) -> None:
        if self._ws_task and not self._ws_task.done():
            return
        lic = self.license_key.text().strip()
        if not lic:
            QMessageBox.information(
                self,
                "License key required",
                "Paste your license key in the Setup tab, then click Connect.",
            )
            return
        try:
            uuid.UUID(lic)
        except ValueError:
            QMessageBox.warning(
                self,
                "License key format",
                "The key should look like:\n\n550e8400-e29b-41d4-a716-446655440000\n\nCopy it again from the portal.",
            )
            return

        url = self.ws_url.text().strip()
        cfg = WsConfig(url=url, license_key=lic)
        self._settings_store.save(AppSettings(ws_url=url, license_key=lic))
        self._ws_client = ExecWsClient(
            cfg=cfg,
            on_status=self._on_ws_status,
            on_event=lambda msg: self._append_event("info", msg),
            on_signal=self._handle_signal,
            on_bot_snapshot=self._handle_bot_snapshot,
        )
        self._ws_task = asyncio.create_task(self._ws_client.run_forever())
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self._set_sb("Connecting…")

    @asyncSlot()
    async def on_disconnect_clicked(self) -> None:
        if self._ws_client:
            self._ws_client.stop()
        if self._ws_task:
            try:
                await asyncio.wait_for(self._ws_task, timeout=2.0)
            except Exception:
                pass
        self._ws_task = None
        self._ws_client = None
        self._set_status("OFFLINE")
        self._append_event("info", "Disconnected. You can reconnect at any time.")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self._set_sb("")

    # ── save keys ────────────────────────────────────────────────────────────

    def on_save_clicked(self) -> None:
        payload = SecretPayload(
            t212_api_key=self.t212_api_key.text().strip(),
            t212_secret_key=(self.t212_secret_key.text().strip() or None),
        )
        if not payload.t212_api_key:
            QMessageBox.warning(self, "No API key", "Enter your Trading212 API key before saving.")
            return
        self._store.save(payload)
        self._append_event("ok", "Trading212 API keys saved (encrypted).")
        self._refresh_t212_status()
        self._set_sb("API keys saved.")

    # ── test connection ───────────────────────────────────────────────────────

    @asyncSlot()
    async def on_test_t212_clicked(self) -> None:
        api = self.t212_api_key.text().strip()
        sec = self.t212_secret_key.text().strip() or None
        if not api:
            QMessageBox.warning(self, "API key required", "Enter your Trading212 API key first.")
            return
        self.test_t212_btn.setEnabled(False)
        self._set_sb("Testing Trading212 connection…")
        try:
            async with T212Client(keys=T212Keys(api_key=api, secret_key=sec)) as client:
                funds = await client.get_free_funds()
                pending = len(await client.get_pending_orders())
            QMessageBox.information(
                self,
                "Connection OK",
                f"Trading212 accepted your API keys.\n\n"
                f"Available funds: {funds:.2f}\n"
                f"Pending orders: {pending}\n\n"
                "(Numbers reflect your practice account if you use one.)",
            )
            self._append_event("ok", f"T212 test OK — funds ≈ {funds:.2f}, pending orders: {pending}")
            self._set_sb("Trading212 connection verified.")
        except T212APIError as exc:
            QMessageBox.critical(self, "Trading212 error", str(exc))
            self._append_event("error", f"T212 test failed: {exc}")
            self._set_sb("")
        except Exception as exc:
            QMessageBox.critical(self, "Connection failed", str(exc))
            self._append_event("error", f"T212 test failed: {exc}")
            self._set_sb("")
        finally:
            self.test_t212_btn.setEnabled(True)

    # ── table helpers ─────────────────────────────────────────────────────────

    def _wire_table(self, table: QTableWidget) -> None:
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._table_context_menu)  # type: ignore[arg-type]
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        table.setWordWrap(False)

        hdr = table.horizontalHeader()
        hdr.setMinimumSectionSize(56)
        hdr.setHighlightSections(False)
        n = table.columnCount()
        for i in range(max(0, n - 1)):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        if n >= 1:
            # Last column grows with the table; drag the separator before it to widen others.
            hdr.setSectionResizeMode(n - 1, QHeaderView.ResizeMode.Stretch)

    def _table_context_menu(self, pos: QPoint) -> None:
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        idx = table.indexAt(pos)
        if not idx.isValid():
            return
        row = idx.row()
        parts = []
        for c in range(table.columnCount()):
            it = table.item(row, c)
            parts.append(it.text() if it else "")
        line = "\t".join(parts)
        menu = QMenu(self)
        act = QAction("Copy row", self)
        act.triggered.connect(lambda _=False, t=line: QApplication.clipboard().setText(t))
        menu.addAction(act)
        menu.exec(table.viewport().mapToGlobal(pos))

    # ── filter ────────────────────────────────────────────────────────────────

    def _matches_filter(self, symbol: str) -> bool:
        flt = self.activity_symbol_filter.text().strip()
        return not flt or flt.upper() in str(symbol).upper()

    def _on_filter_changed(self, _: str) -> None:
        self._refresh_bot_table()
        self._refresh_signals_table()
        self._refresh_market_table()

    # ── table refresh ─────────────────────────────────────────────────────────

    def _refresh_bot_table(self) -> None:
        rows: list[tuple[str, ...]] = []
        for sym in sorted(self._last_bot_snapshot):
            if not self._matches_filter(sym):
                continue
            snap = self._last_bot_snapshot.get(sym) or {}
            if not isinstance(snap, dict):
                continue
            rows.append((
                sym,
                str(snap.get("ready")),
                str(snap.get("regime")),
                str(snap.get("trigger")),
                str(snap.get("signal_side")),
                str(snap.get("entry_blocked")),
                str(snap.get("reason")),
            ))
        self.bot_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                text = str(val)
                it = QTableWidgetItem(text)
                if len(text) > 48:
                    it.setToolTip(text)
                self.bot_table.setItem(r, c, it)

    def _refresh_signals_table(self) -> None:
        rows = [t for t in self._signal_rows if self._matches_filter(t[3])]
        self.signals_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                text = str(val)
                it = QTableWidgetItem(text)
                if len(text) > 48 or c == 4:  # Summary often long
                    it.setToolTip(text)
                self.signals_table.setItem(r, c, it)

    def _refresh_market_table(self) -> None:
        rows = [t for t in self._market_rows if self._matches_filter(t[0])]
        self.market_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                text = str(val)
                it = QTableWidgetItem(text)
                if len(text) > 40:
                    it.setToolTip(text)
                self.market_table.setItem(r, c, it)

    # ── signal handler ────────────────────────────────────────────────────────

    async def _handle_signal(self, payload: dict) -> None:
        sid = payload.get("id")
        direction = payload.get("direction")
        symbol = payload.get("symbol")
        line = f"{sid} | {direction} | {symbol}"
        ts = datetime.now().strftime("%H:%M:%S")

        self._signal_rows.insert(0, (ts, str(sid), str(direction), str(symbol), line))
        if len(self._signal_rows) > 200:
            self._signal_rows.pop()
        self._refresh_signals_table()

        self._signal_count += 1
        self.exec_queue.insertItem(0, QListWidgetItem(f"[{ts}]  {line}"))
        if self.exec_queue.count() > 200:
            self.exec_queue.takeItem(self.exec_queue.count() - 1)

        self._append_event("info", f"Signal received: {line}")

        if not self.exec_mode.isChecked():
            self._append_event("info", "Practice mode — signal logged, no order sent.")
            return

        try:
            stored = self._store.load()
            if not stored or not stored.t212_api_key:
                self._append_event("error", "T212 keys missing — cannot execute.")
                return

            async with T212Client(
                keys=T212Keys(api_key=stored.t212_api_key, secret_key=stored.t212_secret_key)
            ) as client:
                symbol = str(payload.get("symbol") or "").strip()
                direction = str(payload.get("direction") or "LONG").strip().upper()
                rp = payload.get("risk_params") or {}
                stop_loss_pct = float(rp.get("stop_loss_pct") or 0.0)
                is_debug = bool(payload.get("debug"))

                if direction != "LONG":
                    self._append_event("warn", f"Skipped (direction={direction}) — SHORT not implemented.")
                    return

                price = await client.get_price_from_positions(symbol)
                if price is None:
                    price = 0.0

                qty = 1.0
                resp = await client.place_market_order(symbol, qty)
                self._append_event("ok", f"Market order placed: {resp}")

                order_id = resp.get("id") if isinstance(resp, dict) else None
                filled = False
                filled_qty = 0.0
                for _ in range(45):
                    await asyncio.sleep(1.0)
                    if order_id is not None:
                        order = await client.get_order_by_id(int(order_id))
                        if isinstance(order, dict):
                            fq = order.get("filledQuantity")
                            st = str(order.get("status") or "").upper()
                            try:
                                filled_qty = float(fq) if fq is not None else 0.0
                            except Exception:
                                filled_qty = 0.0
                            self._append_event("info", f"Order poll: status={st} filled={filled_qty}")
                            if st in {"CANCELLED", "REJECTED"}:
                                break
                            if st in {"FILLED", "EXECUTED"} or filled_qty >= qty:
                                filled = True
                                break

                if not filled:
                    self._append_event("warn", "Order not filled (premarket/illiquid). Stop skipped.")
                else:
                    price2 = await client.get_price_from_positions(symbol)
                    if price2 is not None:
                        price = float(price2)
                    if price > 0 and stop_loss_pct > 0:
                        stop_price = price * (1.0 - stop_loss_pct / 100.0)
                        if filled_qty >= qty:
                            stop_resp = await client.place_stop_order(symbol, qty=-qty, stop_price=stop_price)
                            self._append_event("ok", f"Protective STOP placed: {stop_resp}")
                        else:
                            self._append_event("warn", "Protective STOP skipped (filledQty still 0).")
                    else:
                        self._append_event("warn", "Protective STOP skipped (no price or stop_loss_pct).")

                if is_debug:
                    if not filled and order_id:
                        try:
                            cancel_resp = await client.cancel_order(str(order_id))
                            self._append_event("info", f"Debug: cancelled unfilled order: {cancel_resp}")
                        except Exception as exc:
                            self._append_event("error", f"Debug: cancel failed: {exc}")
                        return
                    self._append_event("info", "Debug: closing position…")
                    close_resp = await client.close_position(symbol)
                    self._append_event("info", f"Debug: close submitted: {close_resp}")

        except Exception as exc:
            self._append_event("error", f"EXECUTION ERROR: {exc}")

    # ── bot snapshot ──────────────────────────────────────────────────────────

    def _handle_bot_snapshot(self, payload: dict) -> None:
        snap: dict[str, dict] = {}
        for symbol, raw in payload.items():
            if isinstance(raw, dict):
                snap[str(symbol)] = raw
        self._last_bot_snapshot = snap
        self._refresh_bot_table()
        asyncio.create_task(self._refresh_market_state(list(payload.keys())))

    async def _refresh_market_state(self, symbols: list[str]) -> None:
        stored = self._store.load()
        if not stored or not stored.t212_api_key:
            return
        parsed: list[tuple[str, str]] = []
        try:
            async with T212Client(
                keys=T212Keys(api_key=stored.t212_api_key, secret_key=stored.t212_secret_key)
            ) as client:
                for sym in sorted(set(symbols)):
                    try:
                        state = await client.get_market_state(sym)
                    except Exception:
                        state = "unknown"
                    parsed.append((sym, state))
        except Exception:
            return
        self._market_rows = parsed
        self._refresh_market_table()


# ── entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("AlgoFlow")
    app.setOrganizationName("AlgoFlow")
    _apply_desktop_styles(app)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    w = MainWindow()
    w.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
