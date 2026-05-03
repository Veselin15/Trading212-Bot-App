from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPixmap, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
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
    QSpinBox,
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
from .license_checker import LicenseResult, check_license
from .paper_live_toggle import PaperLiveToggle
from .settings_store import AppSettings, SettingsStore
from .t212_client import T212APIError, T212Client, T212Keys
from .ws_client import ExecWsClient, WsConfig, _smoke_health_url

# Background license re-validation interval (ms). Server is source of truth for tier.
LICENSE_RECHECK_INTERVAL_MS = 10 * 60 * 1000

# ── colour tokens — SwiftTrade dark theme (emerald primary) ──────────────────
_BG       = "#0c0c10"   # body — deepest layer
_SURFACE  = "#13131a"   # cards / panels
_SURFACE2 = "#1c1c25"   # elevated cards, groupboxes
_BORDER   = "#2a2a38"   # subtle borders
_BORDER2  = "#3a3a4e"   # interactive borders
_SKY      = "#10b981"   # emerald-500 — primary accent
_SKY_HVR  = "#34d399"   # emerald-400 — hover
_SKY_DIM  = "#064e3b"   # emerald tint bg for tags/indicators
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

/* ── navbar ───────────────────────────────────────────────────────── */
QFrame#Navbar {{
    background-color: {_SURFACE};
    border-bottom: 1px solid {_BORDER};
    min-height: 44px;
    max-height: 52px;
}}

QLabel#AppWordmark {{
    color: {_TEXT};
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: -0.01em;
    background: transparent;
    padding: 0 4px;
}}

QLabel#AppWordmarkAccent {{
    color: {_SKY};
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: -0.01em;
    background: transparent;
    padding: 0;
}}

QLabel#BrandLogoMark, QLabel#BrandLogoText {{
    background: transparent;
}}

QFrame#NavSep {{
    background-color: {_BORDER};
    min-width: 1px;
    max-width: 1px;
    min-height: 20px;
    max-height: 28px;
    border: none;
    margin: 0 4px;
}}

/* ── status indicator inside navbar ─────────────────────────────── */
QFrame#StatusBadge {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 12px;
    padding: 0 2px;
}}

/* ── broker pill ─────────────────────────────────────────────────── */
QLabel#BrokerPill {{
    color: {_MUTED};
    background-color: transparent;
    border: none;
    padding: 0 4px;
    font-size: 8.5pt;
}}

/* ── nav settings button ─────────────────────────────────────────── */
QPushButton#NavSettingsBtn {{
    background-color: transparent;
    color: {_MUTED};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11pt;
    min-width: 28px;
    max-width: 32px;
    min-height: 22px;
    max-height: 28px;
}}
QPushButton#NavSettingsBtn:hover {{
    color: {_TEXT};
    border-color: {_BORDER2};
    background-color: {_SURFACE2};
}}

/* ── top-bar status card — kept for backward compat ─────────────── */
QFrame#StatusCard {{
    background-color: transparent;
    border: none;
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

/* ── menu bar (hidden — replaced by custom navbar) ───────────────── */
QMenuBar {{
    min-height: 0;
    max-height: 0;
    padding: 0;
    margin: 0;
    border: none;
    background: transparent;
}}
QMenuBar::item {{ max-height: 0; min-height: 0; padding: 0; margin: 0; }}
QMenu {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 8px;
    padding: 6px 4px;
    font-size: 9.5pt;
}}
QMenu::item {{ padding: 8px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: {_SKY_DIM}; color: #e0f2fe; }}
QMenu::separator {{
    height: 1px;
    background: {_BORDER};
    margin: 4px 10px;
}}

/* ── settings dialog ─────────────────────────────────────────────── */
QDialog {{
    background-color: {_SURFACE};
    border: 1px solid {_BORDER2};
    border-radius: 10px;
}}
QDialog QLabel#PrefSectionLabel {{
    color: {_SKY};
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    background: transparent;
}}
QSpinBox {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 9pt;
    selection-background-color: {_SKY_DIM};
}}
QSpinBox:focus {{ border-color: {_SKY}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {_SURFACE2};
    border: none;
    width: 18px;
    border-radius: 3px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {_BORDER2};
}}

QDoubleSpinBox {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 9pt;
    selection-background-color: {_SKY_DIM};
}}
QDoubleSpinBox:focus {{ border-color: {_SKY}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {_SURFACE2};
    border: none;
    width: 18px;
    border-radius: 3px;
}}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {_BORDER2};
}}

QComboBox {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 9pt;
}}
QComboBox:focus {{ border-color: {_SKY}; }}
QComboBox::drop-down {{
    border: none;
    background-color: {_SURFACE2};
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    selection-background-color: {_SKY_DIM};
    selection-color: #e0f2fe;
    padding: 4px;
}}
QDialogButtonBox QPushButton {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 6px 18px;
    font-size: 9pt;
    font-weight: 600;
    min-height: 22px;
}}
QDialogButtonBox QPushButton:default {{
    background-color: {_SKY};
    color: #fff;
    border: none;
}}
QDialogButtonBox QPushButton:hover {{
    background-color: {_SURFACE};
    border-color: {_SKY};
    color: {_SKY_HVR};
}}
QDialogButtonBox QPushButton:default:hover {{ background-color: {_SKY_HVR}; color: #fff; }}

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


def _repo_root() -> Path:
    """Repository root (parent of ``desktop/``)."""
    return Path(__file__).resolve().parents[2]


def _load_brand_pixmaps() -> tuple[QPixmap | None, QPixmap | None]:
    icon_path = _repo_root() / "logo.png"
    text_path = _repo_root() / "logo_text.png"
    icon_pm = QPixmap(str(icon_path)) if icon_path.is_file() else QPixmap()
    text_pm = QPixmap(str(text_path)) if text_path.is_file() else QPixmap()
    return (
        icon_pm if not icon_pm.isNull() else None,
        text_pm if not text_pm.isNull() else None,
    )


# ── main window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SwiftTrade — Desktop Executor")
        _icon_file = _repo_root() / "logo.png"
        if _icon_file.is_file():
            self.setWindowIcon(QIcon(str(_icon_file)))
        self.setMinimumSize(980, 640)
        self.resize(1120, 720)

        self._base_dir = Path.home() / ".t212_executor"
        self._store = CryptoStore(self._base_dir)
        self._settings_store = SettingsStore(self._base_dir)
        self._ws_task: asyncio.Task | None = None
        self._ws_client: ExecWsClient | None = None

        # ── trading / risk settings (populated from settings store) ──
        self._order_quantity: float = 1.0
        self._default_stop_loss_pct: float = 2.0
        self._confirm_before_trade: bool = False
        self._skip_non_long_signals: bool = True
        self._max_daily_trades: int = 0
        self._signal_cooldown_s: int = 0
        self._notify_on_signal: bool = True
        self._notify_on_connect: bool = True
        self._reconnect_interval_s: int = 5
        self._max_reconnect_attempts: int = 0
        self._log_level_filter: str = "all"

        # ── runtime trade tracking ───────────────────────────────────
        self._trades_today: int = 0
        self._trades_today_date = datetime.now().date()
        self._last_signal_times: dict[str, datetime] = {}

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
        self.license_key.setPlaceholderText("Paste your license key from the SwiftTrade portal")
        self.license_key.setToolTip("UUID from the SwiftTrade portal, e.g. 550e8400-e29b-41d4-a716-446655440000")

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

        self.trading_mode = PaperLiveToggle()
        self.trading_mode.setToolTip(
            "Paper: log signals only — no broker orders.\n"
            "Live: place real orders (requires active Pro license; re-checked periodically)."
        )
        self.trading_mode.set_pro_unlocked(False)
        self.trading_mode.live_enable_requested.connect(self._on_live_enable_requested)  # type: ignore[arg-type]
        self.trading_mode.mode_changed.connect(self._on_trading_mode_changed)  # type: ignore[arg-type]

        self._setup_trading_mode_hint = QLabel(
            "Top bar: Paper trading — use the toggle to switch (Live requires Pro)."
        )
        self._setup_trading_mode_hint.setObjectName("HintLabel")
        self._setup_trading_mode_hint.setWordWrap(True)

        # ── license tier state & widgets ─────────────────────────────
        self._license_tier: str = "unvalidated"
        self._license_check_busy: bool = False

        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setObjectName("SecondaryBtn")
        self.validate_btn.setFixedWidth(92)
        self.validate_btn.setToolTip(
            "Check your license tier against the SwiftTrade backend.\n"
            "Pro subscription required to enable live trading."
        )
        self.validate_btn.clicked.connect(self.on_validate_clicked)  # type: ignore[arg-type]

        self.tier_status_label = QLabel(
            "Not validated — click Validate to check your license tier."
        )
        self.tier_status_label.setObjectName("HintLabel")
        self.tier_status_label.setWordWrap(True)

        self.tier_badge_nav = QLabel("● Not validated")
        self.tier_badge_nav.setStyleSheet(
            f"color: {_MUTED}; font-size: 8.5pt; background: transparent; border: none; padding: 0 4px;"
        )

        # ── buttons ──────────────────────────────────────────────────
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("PrimaryBtn")
        self.connect_btn.setFixedWidth(88)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("DangerBtn")
        self.disconnect_btn.setFixedWidth(88)
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

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self.tabs)
        self._splitter.addWidget(self._build_log_panel())
        self._splitter.setStretchFactor(0, 5)
        self._splitter.setStretchFactor(1, 4)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_navbar())

        content_wrap = QWidget()
        cw_layout = QVBoxLayout(content_wrap)
        cw_layout.setContentsMargins(10, 8, 10, 6)
        cw_layout.setSpacing(0)
        cw_layout.addWidget(self._splitter, 1)
        root.addWidget(content_wrap, 1)

        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        self._build_menu_bar()   # hidden — keyboard shortcuts still register
        self._setup_status_bar()

        self._set_status("OFFLINE")
        self._append_event("info", "App started — SwiftTrade Desktop Executor.")
        self._append_event("info", f"Build: {self._git_version()}")
        self._refresh_t212_status()

        settings = self._settings_store.load()
        if settings.ws_url:
            self.ws_url.setText(settings.ws_url)
        if settings.license_key:
            self.license_key.setText(settings.license_key)
        self._apply_log_settings(settings)
        self._apply_trading_settings(settings)
        self.start_minimized = settings.start_minimized
        if settings.splitter_sizes and len(settings.splitter_sizes) == 2:
            self._splitter.setSizes(settings.splitter_sizes)
        else:
            self._splitter.setSizes([580, 440])

        existing = self._store.load()
        if existing:
            self.t212_api_key.setText(existing.t212_api_key)
            self.t212_secret_key.setText(existing.t212_secret_key or "")
            self._refresh_t212_status()

        self.activity_symbol_filter.textChanged.connect(self._on_filter_changed)  # type: ignore[arg-type]

        self._license_recheck_timer = QTimer(self)
        self._license_recheck_timer.setInterval(LICENSE_RECHECK_INTERVAL_MS)
        self._license_recheck_timer.timeout.connect(self._on_license_recheck_tick)  # type: ignore[arg-type]
        self._license_recheck_timer.start()

        if settings.auto_connect_on_start:
            QTimer.singleShot(600, self.on_connect_clicked)

        self._sync_setup_mode_hint()

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

    # ── navbar ────────────────────────────────────────────────────────────────

    def _build_navbar(self) -> QFrame:
        nav = QFrame()
        nav.setObjectName("Navbar")
        nav.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        bar = QHBoxLayout(nav)
        bar.setContentsMargins(14, 0, 10, 0)
        bar.setSpacing(0)

        # ── left: brand (logo mark + wordmark image) ───────────────
        icon_pm, text_pm = _load_brand_pixmaps()
        if icon_pm is not None:
            logo_mark = QLabel()
            logo_mark.setObjectName("BrandLogoMark")
            scaled_i = icon_pm.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation)
            logo_mark.setPixmap(scaled_i)
            logo_mark.setFixedSize(scaled_i.width(), scaled_i.height())
            logo_mark.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            bar.addWidget(logo_mark)
            bar.addSpacing(8)
        if text_pm is not None:
            logo_txt = QLabel()
            logo_txt.setObjectName("BrandLogoText")
            scaled_t = text_pm.scaledToHeight(22, Qt.TransformationMode.SmoothTransformation)
            logo_txt.setPixmap(scaled_t)
            logo_txt.setFixedSize(scaled_t.width(), scaled_t.height())
            logo_txt.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            bar.addWidget(logo_txt)
            bar.addSpacing(16)
        if icon_pm is None and text_pm is None:
            alg = QLabel("Swift")
            alg.setObjectName("AppWordmark")
            alg.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            flow = QLabel("Trade")
            flow.setObjectName("AppWordmarkAccent")
            flow.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            bar.addWidget(alg)
            bar.addWidget(flow)
            bar.addSpacing(16)

        # vertical separator
        sep1 = QFrame()
        sep1.setObjectName("NavSep")
        sep1.setFrameShape(QFrame.Shape.VLine)
        bar.addWidget(sep1)
        bar.addSpacing(12)

        # ── status badge ────────────────────────────────────────────
        status_badge = QFrame()
        status_badge.setObjectName("StatusBadge")
        sb_inner = QHBoxLayout(status_badge)
        sb_inner.setContentsMargins(8, 4, 10, 4)
        sb_inner.setSpacing(6)
        sb_inner.addWidget(self.status_dot)
        sb_inner.addWidget(self.status_label)
        bar.addWidget(status_badge)
        bar.addSpacing(10)

        # broker pill (text-only, next to badge)
        bar.addWidget(self.t212_status)
        bar.addSpacing(4)

        # tier badge
        bar.addWidget(self.tier_badge_nav)

        bar.addStretch(1)

        # ── right cluster ─────────────────────────────────────────
        bar.addWidget(self.trading_mode)
        bar.addSpacing(12)

        sep2 = QFrame()
        sep2.setObjectName("NavSep")
        sep2.setFrameShape(QFrame.Shape.VLine)
        bar.addWidget(sep2)
        bar.addSpacing(8)

        bar.addWidget(self.connect_btn)
        bar.addSpacing(6)
        bar.addWidget(self.disconnect_btn)
        bar.addSpacing(8)

        sep3 = QFrame()
        sep3.setObjectName("NavSep")
        sep3.setFrameShape(QFrame.Shape.VLine)
        bar.addWidget(sep3)
        bar.addSpacing(6)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("NavSettingsBtn")
        settings_btn.setToolTip("Preferences")
        settings_btn.clicked.connect(self._show_settings)  # type: ignore[arg-type]
        bar.addWidget(settings_btn)
        bar.addSpacing(4)

        return nav

    # ── menu bar (hidden, only for keyboard shortcuts) ────────────────────────

    def _build_menu_bar(self) -> None:
        # Completely crush the native menu bar so it contributes zero height.
        # The navbar frame replaces it visually; we keep QActions for shortcuts.
        mb = self.menuBar()
        mb.setFixedHeight(0)
        mb.setVisible(False)
        hmenu = mb.addMenu("&Help")
        for label, slot in [
            ("&Quick start tips", self._show_quick_tips),
            ("&About SwiftTrade", self._show_about),
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

    # ── license tier enforcement ──────────────────────────────────────────────

    def _update_tier_ui(self, tier: str) -> None:
        """Apply UI state for the validated tier: pro / free / unvalidated."""
        self._license_tier = tier
        if tier == "pro":
            self.trading_mode.set_pro_unlocked(True)
            self.trading_mode.setToolTip(
                "Paper: log signals only — no broker orders.\n"
                "Live: place real market orders on Trading212 (tier re-checked periodically on the server)."
            )
            self.tier_badge_nav.setText("● Pro")
            self.tier_badge_nav.setStyleSheet(
                f"color: {_SUCCESS}; font-size: 8.5pt; font-weight: 700; "
                "background: transparent; border: none; padding: 0 4px;"
            )
            self.tier_status_label.setText("Pro license active — live trading is unlocked.")
            self.tier_status_label.setStyleSheet(
                f"color: {_SUCCESS}; font-size: 8.8pt; background: transparent; padding: 0; margin: 0;"
            )
        elif tier == "free":
            self.trading_mode.set_pro_unlocked(False)
            self.trading_mode.setToolTip(
                "Pro subscription required for Live trading. Upgrade on the SwiftTrade website.\n"
                "Paper mode stays available."
            )
            self.tier_badge_nav.setText("● Free")
            self.tier_badge_nav.setStyleSheet(
                f"color: {_WARN}; font-size: 8.5pt; font-weight: 700; "
                "background: transparent; border: none; padding: 0 4px;"
            )
            self.tier_status_label.setText(
                "Free Demo License active — live trading disabled. Upgrade on the SwiftTrade website."
            )
            self.tier_status_label.setStyleSheet(
                f"color: {_WARN}; font-size: 8.8pt; background: transparent; padding: 0; margin: 0;"
            )
        else:
            self.trading_mode.set_pro_unlocked(False)
            self.trading_mode.setToolTip(
                "Validate your license key against the SwiftTrade server to unlock Live trading."
            )
            self.tier_badge_nav.setText("● Not validated")
            self.tier_badge_nav.setStyleSheet(
                f"color: {_MUTED}; font-size: 8.5pt; "
                "background: transparent; border: none; padding: 0 4px;"
            )
            self.tier_status_label.setText(
                "Not validated — click Validate to check your license tier."
            )
            self.tier_status_label.setStyleSheet(
                f"color: {_MUTED}; font-size: 8.8pt; background: transparent; padding: 0; margin: 0;"
            )
        self._sync_setup_mode_hint()

    async def _run_license_validation(self, *, silent: bool) -> LicenseResult | None:
        """
        Query the backend license endpoint (Supabase-backed). Returns None if a check is already in flight.
        """
        if self._license_check_busy:
            return None
        self._license_check_busy = True
        prev_tier = self._license_tier
        try:
            lic = self.license_key.text().strip()
            ws = self.ws_url.text().strip()
            result = await check_license(lic, ws)
            self._update_tier_ui(result.tier)
            if silent:
                if result.tier != prev_tier:
                    self._append_event(
                        "warn",
                        f"Periodic license check: tier changed from {prev_tier!r} to {result.tier!r}. {result.message}",
                    )
                elif not result.valid and prev_tier in ("pro", "free"):
                    self._append_event(
                        "error",
                        f"Periodic license check failed (was {prev_tier!r}) — {result.message}",
                    )
            return result
        finally:
            self._license_check_busy = False

    @asyncSlot()
    async def on_validate_clicked(self) -> None:
        self.validate_btn.setEnabled(False)
        self.validate_btn.setText("Checking…")
        self._set_sb("Validating license key…")

        try:
            result = await self._run_license_validation(silent=False)
            if result is None:
                self._append_event("warn", "A license check is already running — please wait.")
                self._set_sb("")
                return
            if result.tier == "pro":
                self._append_event("ok", result.message)
                self._set_sb("Pro license validated — live trading unlocked.")
            elif result.tier == "free":
                self._append_event("warn", result.message)
                self._set_sb("Free license — live trading disabled.")
            else:
                self._append_event("error", result.message)
                self._set_sb("License validation failed.")
        finally:
            self.validate_btn.setEnabled(True)
            self.validate_btn.setText("Validate")

    @asyncSlot()
    async def _on_license_recheck_tick(self) -> None:
        """Timer-driven re-validation so the UI cannot stay on Pro/Live after a subscription lapses."""
        lic = self.license_key.text().strip()
        if not lic:
            return
        try:
            uuid.UUID(lic)
        except ValueError:
            return
        await self._run_license_validation(silent=True)

    def _sync_setup_mode_hint(self) -> None:
        """Mirror the top-bar Paper/Live state in the Setup tab hint."""
        if self.trading_mode.is_live():
            self._setup_trading_mode_hint.setText(
                "Top bar: Live trading is ON — real orders may be sent when signals arrive."
            )
            self._setup_trading_mode_hint.setStyleSheet(
                f"color: {_DANGER}; font-size: 8.8pt; font-weight: 600; background: transparent; padding: 0; margin: 0;"
            )
        else:
            self._setup_trading_mode_hint.setText(
                "Top bar: Paper trading — signals are logged only; no broker orders."
            )
            self._setup_trading_mode_hint.setStyleSheet(
                f"color: {_MUTED}; font-size: 8.8pt; background: transparent; padding: 0; margin: 0;"
            )

    def _on_live_enable_requested(self) -> None:
        """User clicked Live — confirm before we arm real-money execution."""
        r = QMessageBox.warning(
            self,
            "Enable live trading?",
            "Live mode will send real-money orders to Trading212 every time the bot fires a LONG signal.\n\n"
            "Your Pro license is active. Stay on Paper if you only want to watch signals in the log.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if r == QMessageBox.StandardButton.Ok:
            self.trading_mode.set_live(True)
        # Stay on Paper if cancelled (toggle widget never switched).

    def _on_trading_mode_changed(self, live: bool) -> None:
        if live:
            self._set_sb("Live trading ON — real orders will be placed.")
        else:
            self._set_sb("Paper trading — signals will be logged only.")
        self._sync_setup_mode_hint()

    # ── settings dialog ───────────────────────────────────────────────────────

    def _apply_log_settings(self, s: AppSettings) -> None:
        self._log_show_timestamps = s.log_show_timestamps
        self._log_auto_scroll = s.log_auto_scroll
        self._log_level_filter = s.log_level_filter
        self.event_log.document().setMaximumBlockCount(s.log_max_lines)
        _f = QFont("Cascadia Mono", s.log_font_size)
        if not _f.exactMatch():
            _f = QFont("Consolas", s.log_font_size)
        self.event_log.setFont(_f)

    def _apply_trading_settings(self, s: AppSettings) -> None:
        self._order_quantity = s.order_quantity
        self._default_stop_loss_pct = s.default_stop_loss_pct
        self._confirm_before_trade = s.confirm_before_trade
        self._skip_non_long_signals = s.skip_non_long_signals
        self._max_daily_trades = s.max_daily_trades
        self._signal_cooldown_s = s.signal_cooldown_s
        self._notify_on_signal = s.notify_on_signal
        self._notify_on_connect = s.notify_on_connect
        self._reconnect_interval_s = s.reconnect_interval_s
        self._max_reconnect_attempts = s.max_reconnect_attempts

    def _show_settings(self) -> None:  # noqa: PLR0915  (intentionally long — builds complex dialog)
        s = self._settings_store.load()

        dlg = QDialog(self)
        dlg.setWindowTitle("Preferences")
        dlg.setMinimumWidth(520)
        dlg.setMinimumHeight(420)
        dlg.setModal(True)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)

        pref_tabs = QTabWidget()
        pref_tabs.setDocumentMode(False)

        def _pref_section(title: str) -> QLabel:
            lab = QLabel(title.upper())
            lab.setObjectName("PrefSectionLabel")
            return lab

        def _pref_row(label: str, widget: QWidget, tooltip: str = "") -> QHBoxLayout:
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

        def _pref_sep() -> QFrame:
            f = QFrame()
            f.setFrameShape(QFrame.Shape.HLine)
            f.setStyleSheet(f"background:{_BORDER}; max-height:1px; border:none;")
            return f

        def _make_tab() -> tuple[QWidget, QVBoxLayout]:
            w = QWidget()
            lay = QVBoxLayout(w)
            lay.setContentsMargins(18, 16, 18, 12)
            lay.setSpacing(13)
            return w, lay

        # ── TAB 1: General ───────────────────────────────────────────
        tab_gen, lay_gen = _make_tab()

        lay_gen.addWidget(_pref_section("Startup"))

        auto_connect_cb = QCheckBox("")
        auto_connect_cb.setChecked(s.auto_connect_on_start)
        lay_gen.addLayout(_pref_row(
            "Auto-connect on startup", auto_connect_cb,
            "Automatically connect to the bot server when the app starts.",
        ))

        start_min_cb = QCheckBox("")
        start_min_cb.setChecked(s.start_minimized)
        lay_gen.addLayout(_pref_row(
            "Start minimized", start_min_cb,
            "Open the window minimized to the taskbar on launch.",
        ))

        lay_gen.addWidget(_pref_sep())
        lay_gen.addWidget(_pref_section("Notifications"))

        notify_signal_cb = QCheckBox("")
        notify_signal_cb.setChecked(s.notify_on_signal)
        lay_gen.addLayout(_pref_row(
            "Notify on incoming signal", notify_signal_cb,
            "Show a status-bar message each time a signal arrives.",
        ))

        notify_connect_cb = QCheckBox("")
        notify_connect_cb.setChecked(s.notify_on_connect)
        lay_gen.addLayout(_pref_row(
            "Notify on connect / disconnect", notify_connect_cb,
            "Log a message when the WebSocket connection status changes.",
        ))

        lay_gen.addStretch(1)
        pref_tabs.addTab(tab_gen, "  General  ")

        # ── TAB 2: Connection ────────────────────────────────────────
        tab_conn, lay_conn = _make_tab()

        lay_conn.addWidget(_pref_section("Reconnect behaviour"))

        reconnect_spin = QSpinBox()
        reconnect_spin.setRange(1, 120)
        reconnect_spin.setValue(s.reconnect_interval_s)
        reconnect_spin.setSuffix("  s")
        reconnect_spin.setFixedWidth(95)
        lay_conn.addLayout(_pref_row(
            "Reconnect interval", reconnect_spin,
            "Seconds to wait before retrying after a connection drop.",
        ))

        max_retry_spin = QSpinBox()
        max_retry_spin.setRange(0, 999)
        max_retry_spin.setValue(s.max_reconnect_attempts)
        max_retry_spin.setSpecialValueText("Unlimited")
        max_retry_spin.setFixedWidth(110)
        lay_conn.addLayout(_pref_row(
            "Max reconnect attempts", max_retry_spin,
            "Stop retrying after this many failed attempts. 0 = keep trying forever.",
        ))

        lay_conn.addStretch(1)
        pref_tabs.addTab(tab_conn, "  Connection  ")

        # ── TAB 3: Trading ───────────────────────────────────────────
        tab_trade, lay_trade = _make_tab()

        lay_trade.addWidget(_pref_section("Order sizing"))

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0.01, 100_000.0)
        qty_spin.setDecimals(2)
        qty_spin.setSingleStep(0.5)
        qty_spin.setValue(s.order_quantity)
        qty_spin.setSuffix("  units")
        qty_spin.setFixedWidth(130)
        lay_trade.addLayout(_pref_row(
            "Default order quantity", qty_spin,
            "Number of shares / units per market order when the signal does not specify a size.",
        ))

        stop_spin = QDoubleSpinBox()
        stop_spin.setRange(0.0, 50.0)
        stop_spin.setDecimals(2)
        stop_spin.setSingleStep(0.25)
        stop_spin.setValue(s.default_stop_loss_pct)
        stop_spin.setSuffix("  %")
        stop_spin.setSpecialValueText("Disabled")
        stop_spin.setFixedWidth(120)
        lay_trade.addLayout(_pref_row(
            "Default stop-loss", stop_spin,
            "Fallback stop-loss percentage when the incoming signal does not provide one. 0 = disabled.",
        ))

        lay_trade.addWidget(_pref_sep())
        lay_trade.addWidget(_pref_section("Risk controls"))

        max_daily_spin = QSpinBox()
        max_daily_spin.setRange(0, 500)
        max_daily_spin.setValue(s.max_daily_trades)
        max_daily_spin.setSpecialValueText("Unlimited")
        max_daily_spin.setFixedWidth(120)
        lay_trade.addLayout(_pref_row(
            "Max trades per day", max_daily_spin,
            "Stop placing orders once this many live trades have been placed today. 0 = no limit.",
        ))

        cooldown_spin = QSpinBox()
        cooldown_spin.setRange(0, 3600)
        cooldown_spin.setSingleStep(5)
        cooldown_spin.setValue(s.signal_cooldown_s)
        cooldown_spin.setSuffix("  s")
        cooldown_spin.setSpecialValueText("No cooldown")
        cooldown_spin.setFixedWidth(130)
        lay_trade.addLayout(_pref_row(
            "Signal cooldown (per symbol)", cooldown_spin,
            "Minimum seconds between two executed signals for the same ticker. 0 = no cooldown.",
        ))

        lay_trade.addWidget(_pref_sep())
        lay_trade.addWidget(_pref_section("Behaviour"))

        confirm_trade_cb = QCheckBox("")
        confirm_trade_cb.setChecked(s.confirm_before_trade)
        lay_trade.addLayout(_pref_row(
            "Confirm before placing order", confirm_trade_cb,
            "Show a confirmation dialog before each live market order is submitted.",
        ))

        skip_non_long_cb = QCheckBox("")
        skip_non_long_cb.setChecked(s.skip_non_long_signals)
        lay_trade.addLayout(_pref_row(
            "Skip non-LONG signals", skip_non_long_cb,
            "Ignore SHORT and FLAT signal directions — only execute LONG entries.",
        ))

        lay_trade.addStretch(1)
        pref_tabs.addTab(tab_trade, "  Trading  ")

        # ── TAB 4: Activity Log ──────────────────────────────────────
        tab_log, lay_log = _make_tab()

        lay_log.addWidget(_pref_section("Display"))

        font_spin = QSpinBox()
        font_spin.setRange(8, 18)
        font_spin.setValue(s.log_font_size)
        font_spin.setSuffix("  pt")
        font_spin.setFixedWidth(85)
        font_spin.setToolTip("Monospace font size for the activity log.")
        lay_log.addLayout(_pref_row("Font size", font_spin))

        lines_spin = QSpinBox()
        lines_spin.setRange(50, 5000)
        lines_spin.setSingleStep(50)
        lines_spin.setValue(s.log_max_lines)
        lines_spin.setSuffix("  lines")
        lines_spin.setFixedWidth(120)
        lines_spin.setToolTip("How many lines to keep before older ones are discarded.")
        lay_log.addLayout(_pref_row("Max entries", lines_spin))

        level_combo = QComboBox()
        level_combo.addItem("All messages", "all")
        level_combo.addItem("Warnings & errors only", "warn")
        level_combo.addItem("Errors only", "error")
        level_combo.setCurrentIndex({"all": 0, "warn": 1, "error": 2}.get(s.log_level_filter, 0))
        level_combo.setFixedWidth(190)
        level_combo.setToolTip("Filter which log messages appear in the activity pane.")
        lay_log.addLayout(_pref_row("Log level filter", level_combo))

        lay_log.addWidget(_pref_sep())
        lay_log.addWidget(_pref_section("Behaviour"))

        auto_scroll_cb = QCheckBox("")
        auto_scroll_cb.setChecked(s.log_auto_scroll)
        lay_log.addLayout(_pref_row(
            "Auto-scroll to latest", auto_scroll_cb,
            "Automatically scroll to the newest log entry when new lines arrive.",
        ))

        timestamps_cb = QCheckBox("")
        timestamps_cb.setChecked(s.log_show_timestamps)
        lay_log.addLayout(_pref_row(
            "Show timestamps", timestamps_cb,
            "Prefix each log line with [HH:MM:SS].",
        ))

        lay_log.addStretch(1)
        pref_tabs.addTab(tab_log, "  Activity Log  ")

        outer.addWidget(pref_tabs, 1)

        # ── Dialog buttons ───────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Save).setDefault(True)
        btns.accepted.connect(dlg.accept)   # type: ignore[arg-type]
        btns.rejected.connect(dlg.reject)   # type: ignore[arg-type]
        outer.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_s = AppSettings(
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
            splitter_sizes=self._splitter.sizes(),
        )
        self._settings_store.save(new_s)
        self._apply_log_settings(new_s)
        self._apply_trading_settings(new_s)
        self._append_event("info", "Preferences saved.")

    # ── setup tab ────────────────────────────────────────────────────────────

    def _build_setup_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        # ── Subscription group ───────────────────────────────────────
        grp_sub = QGroupBox("License && server")
        g = QVBoxLayout(grp_sub)
        g.setSpacing(10)

        g.addWidget(_field_label("License key"))
        lic_row = QHBoxLayout()
        lic_row.setSpacing(8)
        lic_row.addWidget(self.license_key, 1)
        lic_row.addWidget(self.validate_btn)
        g.addLayout(lic_row)
        g.addWidget(self.tier_status_label)
        g.addWidget(_hint("Copy your key from the SwiftTrade portal, then click Validate to check your tier."))

        g.addSpacing(6)
        g.addWidget(_field_label("Bot server address"))
        g.addWidget(self.ws_url)
        g.addWidget(
            _hint(
                "Leave as default (ws://127.0.0.1:8010/ws/exec) if the SwiftTrade server runs on this computer."
            )
        )
        layout.addWidget(grp_sub)

        # ── Trading212 keys group ────────────────────────────────────
        grp_keys = QGroupBox("Trading212 API keys")
        k = QVBoxLayout(grp_keys)
        k.setSpacing(10)

        k.addWidget(
            _hint("Only needed to place real trades or check market hours. Keys are encrypted and never leave this PC.")
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
        lv.addWidget(self._setup_trading_mode_hint)
        lv.addWidget(
            _hint(
                "Paper (default): signals are recorded in the log and queue — no orders are sent.\n"
                "Live: LONG signals place real market orders on your Trading212 account.\n"
                "The Paper / Live control is in the top bar; your tier is re-checked periodically against the server."
            )
        )
        layout.addWidget(grp_live)

        # ── Troubleshooting group ────────────────────────────────────
        grp_diag = QGroupBox("Troubleshooting")
        dg = QVBoxLayout(grp_diag)
        dg.setSpacing(8)
        dg.addWidget(
            _hint(
                "If the app cannot reach the SwiftTrade backend, use this to open a health check page in your browser "
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
                "Every signal the SwiftTrade bot sends appears here. With live mode off, "
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
            "About SwiftTrade Desktop",
            f"SwiftTrade — Desktop Executor\n\n"
            "Bridges your SwiftTrade bot server to Trading212. Signals from TradingView "
            "(or any webhook source) flow through the server to this app, which can "
            "optionally place real orders on your behalf.\n\n"
            f"Build: {self._git_version()}",
        )

    def _show_quick_tips(self) -> None:
        QMessageBox.information(
            self,
            "Quick start",
            "1.  Setup tab — paste your license key from the SwiftTrade portal and click Validate.\n\n"
            "2.  Trading212 keys — enter your API key, click 'Test connection', then Save.\n\n"
            "3.  Click Connect (top bar) — status changes to green when linked.\n\n"
            "4.  Paper / Live — use the top-bar toggle (Live needs Pro). Tier is re-checked periodically on the server.\n\n"
            "Tip: right-click any table row to copy it.",
        )

    # ── status helpers ────────────────────────────────────────────────────────

    def _set_status(self, status: str) -> None:
        text, color = _status_text(status)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"font-weight: 600; font-size: 9pt; color: {color}; background: transparent;"
        )
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

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
            self.t212_status.setText("Trading212 ✓")
            self.t212_status.setStyleSheet(
                f"color: {_SUCCESS}; font-size: 8.5pt; background: transparent; border: none; padding: 0 4px;"
            )
        else:
            self.t212_status.setText("Broker not configured")
            self.t212_status.setStyleSheet(
                f"color: {_MUTED}; font-size: 8.5pt; background: transparent; border: none; padding: 0 4px;"
            )

    # ── coloured log append ───────────────────────────────────────────────────

    def _append_event(self, level: str, message: str) -> None:
        level_filter = getattr(self, "_log_level_filter", "all")
        if level_filter == "error" and level not in ("error",):
            return
        if level_filter == "warn" and level not in ("warn", "error"):
            return

        colour_map = {
            "info":    _TEXT,
            "ok":      _SUCCESS,
            "warn":    _WARN,
            "error":   _DANGER,
        }
        colour = colour_map.get(level, _TEXT)

        cursor = self.event_log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        show_ts = getattr(self, "_log_show_timestamps", True)
        if show_ts:
            ts = datetime.now().strftime("%H:%M:%S")
            fmt_ts = QTextCharFormat()
            fmt_ts.setForeground(QColor(_MUTED))
            cursor.setCharFormat(fmt_ts)
            cursor.insertText(f"[{ts}] ")

        fmt_msg = QTextCharFormat()
        fmt_msg.setForeground(QColor(colour))
        cursor.setCharFormat(fmt_msg)
        cursor.insertText(message + "\n")

        self.event_log.setTextCursor(cursor)
        if getattr(self, "_log_auto_scroll", True):
            self.event_log.ensureCursorVisible()

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
                "Paste your license key from the SwiftTrade portal in the Setup tab, then click Connect.",
            )
            return
        try:
            uuid.UUID(lic)
        except ValueError:
            QMessageBox.warning(
                self,
                "License key format",
                "The key should look like:\n\n550e8400-e29b-41d4-a716-446655440000\n\nCopy it again from the SwiftTrade portal.",
            )
            return

        url = self.ws_url.text().strip()
        saved = self._settings_store.load()
        cfg = WsConfig(
            url=url,
            license_key=lic,
            reconnect_interval_s=self._reconnect_interval_s,
            max_reconnect_attempts=self._max_reconnect_attempts,
        )
        self._settings_store.save(AppSettings(
            ws_url=url,
            license_key=lic,
            reconnect_interval_s=saved.reconnect_interval_s,
            max_reconnect_attempts=saved.max_reconnect_attempts,
            order_quantity=saved.order_quantity,
            max_daily_trades=saved.max_daily_trades,
            signal_cooldown_s=saved.signal_cooldown_s,
            default_stop_loss_pct=saved.default_stop_loss_pct,
            confirm_before_trade=saved.confirm_before_trade,
            skip_non_long_signals=saved.skip_non_long_signals,
            log_font_size=saved.log_font_size,
            log_max_lines=saved.log_max_lines,
            log_auto_scroll=saved.log_auto_scroll,
            log_show_timestamps=saved.log_show_timestamps,
            log_level_filter=saved.log_level_filter,
            notify_on_signal=saved.notify_on_signal,
            notify_on_connect=saved.notify_on_connect,
            auto_connect_on_start=saved.auto_connect_on_start,
            start_minimized=saved.start_minimized,
            splitter_sizes=self._splitter.sizes(),
        ))
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

        if self._notify_on_signal:
            self._append_event("info", f"Signal received: {line}")

        if not self.trading_mode.is_live():
            self._append_event("info", "Paper trading — signal logged, no order sent.")
            return

        if self._license_tier != "pro":
            self._append_event(
                "error",
                "Live execution blocked — server reports this license is not Pro. "
                "Validate again or switch to Paper.",
            )
            self.trading_mode.set_live(False)
            return

        direction_upper = str(payload.get("direction") or "LONG").strip().upper()
        sym_str = str(payload.get("symbol") or "").strip()

        # Skip non-LONG signals if configured
        if self._skip_non_long_signals and direction_upper != "LONG":
            self._append_event("warn", f"Skipped (direction={direction_upper}) — only LONG signals are executed.")
            return

        # Daily trade limit check
        today = datetime.now().date()
        if today != self._trades_today_date:
            self._trades_today = 0
            self._trades_today_date = today
        if self._max_daily_trades > 0 and self._trades_today >= self._max_daily_trades:
            self._append_event("warn", f"Daily trade limit reached ({self._max_daily_trades}). Signal skipped.")
            return

        # Signal cooldown per symbol
        if self._signal_cooldown_s > 0 and sym_str:
            last_time = self._last_signal_times.get(sym_str)
            now = datetime.now()
            if last_time is not None:
                elapsed = (now - last_time).total_seconds()
                if elapsed < self._signal_cooldown_s:
                    remaining = int(self._signal_cooldown_s - elapsed)
                    self._append_event("warn", f"Cooldown active for {sym_str} ({remaining}s remaining). Signal skipped.")
                    return
            self._last_signal_times[sym_str] = now

        # Confirm before trade
        if self._confirm_before_trade:
            r = QMessageBox.question(
                self,
                "Confirm trade",
                f"Place a {direction_upper} market order for {sym_str}?\n\n"
                f"Quantity: {self._order_quantity:.2f} units",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                self._append_event("info", "Trade confirmation declined. Signal skipped.")
                return

        try:
            stored = self._store.load()
            if not stored or not stored.t212_api_key:
                self._append_event("error", "T212 keys missing — cannot execute.")
                return

            async with T212Client(
                keys=T212Keys(api_key=stored.t212_api_key, secret_key=stored.t212_secret_key)
            ) as client:
                rp = payload.get("risk_params") or {}
                stop_loss_pct = float(rp.get("stop_loss_pct") or 0.0)
                if stop_loss_pct == 0.0:
                    stop_loss_pct = self._default_stop_loss_pct
                is_debug = bool(payload.get("debug"))
                qty = self._order_quantity

                price = await client.get_price_from_positions(sym_str)
                if price is None:
                    price = 0.0

                resp = await client.place_market_order(sym_str, qty)
                self._append_event("ok", f"Market order placed: {resp}")
                self._trades_today += 1

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
                    price2 = await client.get_price_from_positions(sym_str)
                    if price2 is not None:
                        price = float(price2)
                    if price > 0 and stop_loss_pct > 0:
                        stop_price = price * (1.0 - stop_loss_pct / 100.0)
                        if filled_qty >= qty:
                            stop_resp = await client.place_stop_order(sym_str, qty=-qty, stop_price=stop_price)
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
                    close_resp = await client.close_position(sym_str)
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
    app.setApplicationName("SwiftTrade")
    app.setOrganizationName("SwiftTrade")
    _apply_desktop_styles(app)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    w = MainWindow()
    if getattr(w, "start_minimized", False):
        w.showMinimized()
    else:
        w.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
