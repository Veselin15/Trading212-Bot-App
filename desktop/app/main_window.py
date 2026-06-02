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
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot

from .__version__ import __version__ as _APP_VERSION
from .crypto_store import CryptoStore, SecretPayload
from .sleep_guard import SleepGuard
from . import startup_manager
from .default_executor_url import DEFAULT_EXECUTOR_WS_URL
from .license_checker import LicenseResult, check_license
from .license_key_util import normalize_license_key
from .paper_live_toggle import PaperLiveToggle
from .paths import load_brand_icon, repo_root
from .settings_store import AppSettings, SettingsStore
from .t212_client import (
    T212_API_DEMO_BASE,
    T212_API_LIVE_BASE,
    T212APIError,
    T212Client,
    T212Keys,
)
from .ui.activity_panel import build_activity_tab
from .ui.log_panel import build_log_panel
from .ui.help_dialog import run_help_dialog
from .ui.preferences_dialog import run_preferences_dialog
from .ui.nav_status import NavStatusPill
from .ui.setup_panel import build_setup_tab
from .ui.theme import (
    _DANGER,
    _MUTED,
    _SKY,
    _SUCCESS,
    _TEXT,
    _WARN,
)
from .ui.trades_panel import build_trades_tab
from .ui.widgets import status_text
from .ws_client import ExecWsClient, WsConfig, _smoke_health_url

LICENSE_RECHECK_INTERVAL_MS = 10 * 60 * 1000


class MainWindow(QMainWindow):
    def __init__(self, *, base_dir: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("SwiftTrade — Desktop Executor")
        _icon_file = repo_root() / "logo.png"
        if _icon_file.is_file():
            self.setWindowIcon(QIcon(str(_icon_file)))
        self.setMinimumSize(1040, 700)
        self.resize(1180, 760)

        self._base_dir = base_dir if base_dir is not None else (Path.home() / ".t212_executor")
        self._store = CryptoStore(self._base_dir)
        self._settings_store = SettingsStore(self._base_dir)
        self._ws_task: asyncio.Task | None = None
        self._ws_client: ExecWsClient | None = None

        # ── background / power ───────────────────────────────────────
        self._sleep_guard = SleepGuard()
        self._close_to_tray: bool = True
        self._keep_awake: bool = True
        self._tray: QSystemTrayIcon | None = None
        self._quit_for_real: bool = False   # set True only by "Quit" tray action

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
        self._t212_test_busy: bool = False

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

        # ── consolidated nav status (replaces separate broker/license pills) ──
        self.nav_status = NavStatusPill()

        # kept for tests / internal checks — not shown in navbar
        self.t212_status = QLabel("")
        self.t212_status.hide()
        self.tier_badge_nav = QLabel("")
        self.tier_badge_nav.hide()

        # ── inputs ───────────────────────────────────────────────────
        self.license_key = QLineEdit()
        self.license_key.setPlaceholderText("Pro license key (optional)")
        self.license_key.setToolTip("Leave empty for free demo trading.")

        self.ws_url = QLineEdit(DEFAULT_EXECUTOR_WS_URL)
        self.ws_url.setPlaceholderText("wss://…")
        self.ws_url.setToolTip("Leave default unless support says otherwise.")

        self.practice_t212_api_key = QLineEdit()
        self.practice_t212_api_key.setPlaceholderText("Paste your Trading212 demo API key here")
        self.practice_t212_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.practice_t212_secret_key = QLineEdit()
        self.practice_t212_secret_key.setPlaceholderText("Secret (optional)")
        self.practice_t212_secret_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.live_t212_api_key = QLineEdit()
        self.live_t212_api_key.setPlaceholderText("Paste your Trading212 real-money API key here")
        self.live_t212_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.live_t212_secret_key = QLineEdit()
        self.live_t212_secret_key.setPlaceholderText("Secret (optional)")
        self.live_t212_secret_key.setEchoMode(QLineEdit.EchoMode.Password)

        # ── checkboxes ───────────────────────────────────────────────
        self.show_t212_secrets = QCheckBox("Show API keys in plain text")
        self.show_t212_secrets.setToolTip("Temporarily displays your API keys as readable text. Turn this off if others can see your screen.")
        self.show_t212_secrets.toggled.connect(self._on_show_t212_secrets_toggled)  # type: ignore[arg-type]

        self.trading_mode = PaperLiveToggle()
        self.trading_mode.setToolTip(
            "Demo mode: place orders on your Trading212 practice account.\n"
            "Real trades: place orders on your real-money account (Pro subscription required)."
        )
        self.trading_mode.set_pro_unlocked(False)
        self.trading_mode.live_enable_requested.connect(self._on_live_enable_requested)  # type: ignore[arg-type]
        self.trading_mode.mode_changed.connect(self._on_trading_mode_changed)  # type: ignore[arg-type]

        self._setup_trading_mode_hint = QLabel("Use Demo mode in the top bar until you're ready for real trades.")
        self._setup_trading_mode_hint.setObjectName("HintLabel")
        self._setup_trading_mode_hint.setWordWrap(True)

        # ── license tier state & widgets ─────────────────────────────
        self._license_tier: str = "free"
        self._license_check_busy: bool = False

        self.validate_btn = QPushButton("Check license")
        self.validate_btn.setObjectName("PrimaryBtn")
        self.validate_btn.setMinimumWidth(130)
        self.validate_btn.setToolTip(
            "Check your license tier against the SwiftTrade backend.\n"
            "Pro subscription required to enable real trades."
        )
        self.validate_btn.clicked.connect(self.on_validate_clicked)  # type: ignore[arg-type]

        self.tier_status_label = QLabel("Paste your license key from swifttrade.app to start your free 14-day trial.")
        self.tier_status_label.setObjectName("TierStatusLabel")
        self.tier_status_label.setWordWrap(True)

        self._server_connected = False

        # ── buttons ──────────────────────────────────────────────────
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("PrimaryBtn")
        self.connect_btn.setMinimumWidth(96)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("DangerBtn")
        self.disconnect_btn.setFixedWidth(88)
        self.disconnect_btn.setEnabled(False)

        self.test_t212_practice_btn = QPushButton("Test connection")
        self.test_t212_practice_btn.setObjectName("SecondaryBtn")
        self.test_t212_practice_btn.setToolTip("Verify your demo API keys with Trading212.")

        self.test_t212_live_btn = QPushButton("Test real account")
        self.test_t212_live_btn.setObjectName("SecondaryBtn")
        self.test_t212_live_btn.setToolTip("Verify your real-money API keys (Pro license required).")

        self.save_practice_keys_btn = QPushButton("Save demo keys")
        self.save_practice_keys_btn.setObjectName("PrimaryBtn")
        self.save_practice_keys_btn.setToolTip("Encrypt and store your demo account keys on this PC.")

        self.save_live_keys_btn = QPushButton("Save real-money keys")
        self.save_live_keys_btn.setObjectName("SecondaryBtn")
        self.save_live_keys_btn.setToolTip("Encrypt and store your real-money key pair on this PC.")

        self._broker_keys_hint = QLabel()
        self._broker_keys_hint.setObjectName("HintLabel")
        self._broker_keys_hint.setWordWrap(True)

        self.connect_btn.clicked.connect(self.on_connect_clicked)   # type: ignore[arg-type]
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)  # type: ignore[arg-type]
        self.save_practice_keys_btn.clicked.connect(self.on_save_practice_keys_clicked)  # type: ignore[arg-type]
        self.save_live_keys_btn.clicked.connect(self.on_save_live_keys_clicked)  # type: ignore[arg-type]
        self.test_t212_practice_btn.clicked.connect(self.on_test_t212_practice_clicked)  # type: ignore[arg-type]
        self.test_t212_live_btn.clicked.connect(self.on_test_t212_live_clicked)  # type: ignore[arg-type]
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
        self.tabs.addTab(self._build_setup_tab(), "  Get started  ")
        self.tabs.setTabToolTip(0, "Set up your license, Trading212 keys, and connect to the bot")
        self.tabs.addTab(self._build_activity_tab(), "  Live feed  ")
        self.tabs.setTabToolTip(1, "Real-time view of open markets, bot activity, and incoming signals")
        self.tabs.addTab(self._build_trades_tab(), "  Signals  ")
        self.tabs.setTabToolTip(2, "Full list of every AI trading signal received since you connected")
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
        cw_layout.setContentsMargins(12, 10, 12, 8)
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
        self._append_event("info", f"Version: {self._app_version()}")
        self._refresh_t212_status()

        settings = self._settings_store.load()
        if settings.ws_url:
            self.ws_url.setText(settings.ws_url)
        if settings.license_key:
            normalized = normalize_license_key(settings.license_key)
            if normalized:
                self.license_key.setText(normalized)
            elif settings.license_key.strip():
                self.license_key.clear()
        self._apply_log_settings(settings)
        self._apply_trading_settings(settings)
        self._close_to_tray = settings.close_to_tray
        self._keep_awake = settings.keep_awake
        self._update_broker_keys_hint()
        self.start_minimized = settings.start_minimized
        self._build_tray_icon()
        if settings.splitter_sizes and len(settings.splitter_sizes) == 2:
            self._splitter.setSizes(settings.splitter_sizes)
        else:
            self._splitter.setSizes([580, 440])

        existing = self._store.load()
        if existing:
            self.practice_t212_api_key.setText(existing.practice_api_key)
            self.practice_t212_secret_key.setText(existing.practice_secret_key or "")
            self.live_t212_api_key.setText(existing.live_api_key)
            self.live_t212_secret_key.setText(existing.live_secret_key or "")
            self._refresh_t212_status()

        self.activity_symbol_filter.textChanged.connect(self._on_filter_changed)  # type: ignore[arg-type]

        self._license_recheck_timer = QTimer(self)
        self._license_recheck_timer.setInterval(LICENSE_RECHECK_INTERVAL_MS)
        self._license_recheck_timer.timeout.connect(self._on_license_recheck_tick)  # type: ignore[arg-type]
        self._license_recheck_timer.start()

        if settings.auto_connect_on_start:
            QTimer.singleShot(600, self.on_connect_clicked)

        self.license_key.textChanged.connect(lambda _: self._refresh_setup_checklist())  # type: ignore[arg-type]
        self._update_tier_ui("free")
        self._sync_setup_mode_hint()
        self._refresh_setup_checklist()

        if not settings.seen_welcome:
            QTimer.singleShot(400, self._show_welcome_and_dismiss)

    # ── background / tray / sleep ─────────────────────────────────────────────

    def _build_tray_icon(self) -> None:
        """Create the system-tray icon and its context menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon = self.windowIcon()
        if icon.isNull():
            # Fallback: use a coloured dot rendered into a 32×32 pixmap
            from PySide6.QtGui import QPainter, QBrush
            from PySide6.QtCore import QRect
            pm = QPixmap(32, 32)
            pm.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor("#14b8a6")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRect(2, 2, 28, 28))
            painter.end()
            icon = QIcon(pm)

        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("SwiftTrade — Not connected")

        menu = QMenu()

        show_act = QAction("Open SwiftTrade", self)
        show_act.triggered.connect(self._tray_show_window)  # type: ignore[arg-type]
        menu.addAction(show_act)

        menu.addSeparator()

        self._tray_connect_act = QAction("Connect", self)
        self._tray_connect_act.triggered.connect(self.on_connect_clicked)  # type: ignore[arg-type]
        menu.addAction(self._tray_connect_act)

        self._tray_disconnect_act = QAction("Disconnect", self)
        self._tray_disconnect_act.triggered.connect(self.on_disconnect_clicked)  # type: ignore[arg-type]
        self._tray_disconnect_act.setEnabled(False)
        menu.addAction(self._tray_disconnect_act)

        menu.addSeparator()

        quit_act = QAction("Quit SwiftTrade", self)
        quit_act.triggered.connect(self._tray_quit)  # type: ignore[arg-type]
        menu.addAction(quit_act)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)  # type: ignore[arg-type]
        self._tray.show()

    def _tray_show_window(self) -> None:
        """Bring the main window back from the tray."""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _tray_quit(self) -> None:
        """Exit from the tray context menu — actually quits the process."""
        self._quit_for_real = True
        self.close()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Left-click / double-click on the tray icon toggles the window."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if self.isVisible():
                self.hide()
            else:
                self._tray_show_window()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Intercept the window-close so we can hide to tray instead of quitting."""
        if not self._quit_for_real and self._close_to_tray and self._tray is not None:
            event.ignore()
            self.hide()
            self._tray.showMessage(
                "SwiftTrade is still running",
                "The bot stays connected in the background.\n"
                "Right-click the tray icon to open or quit.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
        else:
            # Real quit — release the sleep guard cleanly
            self._sleep_guard.release()
            event.accept()

    def _update_sleep_guard(self) -> None:
        """Acquire or release the sleep-prevention hold based on current state."""
        should_hold = self._keep_awake and self._server_connected
        if should_hold:
            acquired = self._sleep_guard.acquire()
            if acquired:
                self._append_event("info", "Sleep prevention active — PC will stay awake while connected.")
        else:
            if self._sleep_guard.active:
                self._sleep_guard.release()
                self._append_event("info", "Sleep prevention released.")

    def _update_tray_status(self) -> None:
        """Sync tray tooltip and connect/disconnect actions with current state."""
        if self._tray is None:
            return
        if self._server_connected:
            mode = "Real money" if self.trading_mode.is_live() else "Demo"
            self._tray.setToolTip(f"SwiftTrade — Connected ({mode} mode)")
            self._tray_connect_act.setEnabled(False)
            self._tray_disconnect_act.setEnabled(True)
        else:
            self._tray.setToolTip("SwiftTrade — Not connected")
            self._tray_connect_act.setEnabled(True)
            self._tray_disconnect_act.setEnabled(False)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _app_version(self) -> str:
        """App version string; appends git short-hash in dev when git is available."""
        base = _APP_VERSION
        if getattr(sys, "frozen", False):
            return base
        try:
            root = repo_root()
            sha = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], cwd=str(root), text=True
            ).strip()
            return f"{base}+{sha}"
        except Exception:
            return base

    # ── navbar ────────────────────────────────────────────────────────────────

    def _build_navbar(self) -> QFrame:
        nav = QFrame()
        nav.setObjectName("Navbar")
        nav.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        bar = QHBoxLayout(nav)
        bar.setContentsMargins(14, 0, 10, 0)
        bar.setSpacing(0)

        # ── left: mark (logo.png) + typographic wordmark — logo_text.png is full lockup, too tall for bar
        icon_pm = load_brand_icon()
        if icon_pm is not None:
            logo_mark = QLabel()
            logo_mark.setObjectName("BrandLogoMark")
            scaled_i = icon_pm.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation)
            logo_mark.setPixmap(scaled_i)
            logo_mark.setFixedSize(scaled_i.width(), scaled_i.height())
            logo_mark.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            bar.addWidget(logo_mark)
            bar.addSpacing(8)
        word = QLabel()
        word.setObjectName("AppWordmark")
        word.setTextFormat(Qt.TextFormat.RichText)
        word.setText(
            f'<span style="color:{_TEXT};font-size:11pt;font-weight:700;letter-spacing:-0.01em">Swift</span>'
            f'<span style="color:{_SKY};font-size:11pt;font-weight:700;letter-spacing:-0.01em">Trade</span>'
        )
        word.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        bar.addWidget(word)
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
        bar.addWidget(self.nav_status)
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
        settings_btn.setToolTip("Settings — order size, stop-loss, notifications and more")
        settings_btn.clicked.connect(self._show_settings)  # type: ignore[arg-type]
        bar.addWidget(settings_btn)
        bar.addSpacing(4)

        help_btn = QPushButton("Help")
        help_btn.setObjectName("NavHelpBtn")
        help_btn.setToolTip("Open the help guide — explains signals, demo vs real-money mode, and troubleshooting")
        help_btn.clicked.connect(self._show_help)  # type: ignore[arg-type]
        bar.addWidget(help_btn)

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
            ("&Help guide", self._show_help),
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
        """Apply UI state for the validated tier: pro / trial / expired / free / invalid."""
        self._license_tier = tier
        if tier == "pro":
            self.trading_mode.set_pro_unlocked(True)
            self.trading_mode.setToolTip(
                "Demo mode: place orders on your Trading212 practice account.\n"
                "Real trades: place orders using your saved real-money keys (tier re-checked on the server)."
            )
            self.tier_status_label.setText("Pro license active — real-money trading is unlocked.")
            self.tier_status_label.setProperty("tierKind", "pro")
        elif tier == "trial":
            self.trading_mode.set_pro_unlocked(False)
            self.trading_mode.setToolTip(
                "Free trial: paper trade on your Trading212 practice account.\n"
                "Upgrade to Pro to unlock real-money trades."
            )
            self.tier_status_label.setText(
                "Free trial active — paper trading only. Upgrade to Pro for real-money trading."
            )
            self.tier_status_label.setProperty("tierKind", "trial")
        elif tier == "expired":
            self.trading_mode.set_pro_unlocked(False)
            self.trading_mode.setToolTip(
                "Your free trial has ended. Upgrade at swifttrade.app to resume trading."
            )
            self.tier_status_label.setText(
                "Free trial expired — trading is paused. Upgrade at swifttrade.app to resume."
            )
            self.tier_status_label.setProperty("tierKind", "expired")
        elif tier == "free":
            # Legacy value — no standalone free tier anymore; prompt for a license.
            self.trading_mode.set_pro_unlocked(False)
            self.trading_mode.setToolTip(
                "Paste your license key from swifttrade.app to start your free 14-day trial."
            )
            self.tier_status_label.setText(
                "Paste your license key from swifttrade.app — sign up for a free 14-day trial to get one."
            )
            self.tier_status_label.setProperty("tierKind", "free")
        else:
            self.trading_mode.set_pro_unlocked(False)
            self.trading_mode.setToolTip(
                "License key not recognized. Copy it again from your dashboard at swifttrade.app."
            )
            self.tier_status_label.setText(
                "License key not recognized — double-check it, or copy it again from swifttrade.app."
            )
            self.tier_status_label.setProperty("tierKind", "pending")
        # Show/hide real-money section based on tier
        if hasattr(self, "_live_key_lock_msg"):
            is_pro = (tier == "pro")
            self._live_key_lock_msg.setVisible(not is_pro)
            self._live_key_fields.setVisible(is_pro)
            self._live_key_box.setProperty("locked", "" if is_pro else "true")
            self._live_key_box.style().unpolish(self._live_key_box)
            self._live_key_box.style().polish(self._live_key_box)
        self.tier_status_label.style().unpolish(self.tier_status_label)
        self.tier_status_label.style().polish(self.tier_status_label)
        self._update_broker_keys_hint()
        self._sync_setup_mode_hint()
        self._refresh_nav_status()
        self._refresh_setup_checklist()

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
                elif not result.valid and prev_tier in ("pro", "trial", "free"):
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
                self._append_event(
                    "info",
                    "Real-money keys: save under Step 2, then use Real trades in the top bar when ready.",
                )
                self._set_sb("Pro license validated — real trades unlocked.")
            elif result.tier == "trial":
                self._append_event("ok", result.message)
                self._set_sb("Free trial active — paper trading only.")
            elif result.tier == "expired":
                self._append_event("warn", result.message)
                self._set_sb("Free trial expired — upgrade at swifttrade.app to resume.")
            elif result.tier == "free":
                self._append_event("warn", result.message)
                self._set_sb("No active plan — start a free trial at swifttrade.app.")
            else:
                self._append_event("error", result.message)
                self._set_sb("License validation failed.")
        finally:
            self.validate_btn.setEnabled(True)
            self.validate_btn.setText("Check license")

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
            self._setup_trading_mode_hint.setText("Real trades ON — orders use your live account.")
            self._setup_trading_mode_hint.setStyleSheet(
                f"color: {_DANGER}; font-size: 8.8pt; font-weight: 600; background: transparent; padding: 0; margin: 0;"
            )
        else:
            self._setup_trading_mode_hint.setText("Use Demo mode in the top bar until you're ready for real trades.")
            self._setup_trading_mode_hint.setStyleSheet(
                f"color: {_MUTED}; font-size: 8.8pt; background: transparent; padding: 0; margin: 0;"
            )

    def _on_live_enable_requested(self) -> None:
        """User clicked Live — confirm before we arm real-money execution."""
        r = QMessageBox.warning(
            self,
            "Switch to Real money mode?",
            "You are about to enable Real money mode.\n\n"
            "In this mode, the bot will place actual buy orders on your Trading212 "
            "real-money account using your saved real-money API key — every time a signal arrives.\n\n"
            "⚠  Make sure you understand the risks before continuing. "
            "Start with Demo mode if you are unsure — no real money is used there.\n\n"
            "Your Pro license is active and your real-money keys are saved. "
            "Press OK only if you are ready to trade with real funds.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if r == QMessageBox.StandardButton.Ok:
            self.trading_mode.set_live(True)
        # Stay on Paper if cancelled (toggle widget never switched).

    def _on_trading_mode_changed(self, live: bool) -> None:
        if live:
            self._set_sb("Real trades ON — orders sent to your live account when signals arrive.")
        else:
            self._set_sb("Demo mode — orders sent to your practice account when signals arrive.")
        self._update_broker_keys_hint()
        self._refresh_t212_status()
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

    def _update_broker_keys_hint(self) -> None:
        """Explain how top-bar Paper/Live maps to T212; enable test buttons when idle."""
        is_pro = self._license_tier == "pro"
        busy = self._t212_test_busy
        self.test_t212_practice_btn.setEnabled(not busy)
        self.test_t212_live_btn.setEnabled(is_pro and not busy)
        self.save_live_keys_btn.setEnabled(is_pro)
        if is_pro and self.trading_mode.is_live():
            self._broker_keys_hint.setText("Real trades ON — using live account keys.")
            self._broker_keys_hint.setStyleSheet(
                f"color: {_DANGER}; font-size: 8.8pt; font-weight: 600; background: transparent; padding: 0; margin: 0;"
            )
            self._broker_keys_hint.show()
        else:
            self._broker_keys_hint.clear()
            self._broker_keys_hint.hide()

    def _t212_base_url(self) -> str:
        """Live Trading212 host only when Pro and top bar is Live; otherwise demo."""
        if self._license_tier == "pro" and self.trading_mode.is_live():
            return T212_API_LIVE_BASE
        return T212_API_DEMO_BASE

    def _stored_active_t212_keys(self) -> tuple[str, str | None] | None:
        """Keys from disk for the currently active profile + tier (used for orders / market state)."""
        stored = self._store.load()
        if not stored:
            return None
        if self._t212_base_url() == T212_API_LIVE_BASE:
            if not stored.live_api_key.strip():
                return None
            return stored.live_api_key.strip(), stored.live_secret_key
        if not stored.practice_api_key.strip():
            return None
        return stored.practice_api_key.strip(), stored.practice_secret_key

    def _apply_background_settings(self, s: AppSettings) -> None:
        """Apply background/power settings from a freshly-saved AppSettings."""
        self._close_to_tray = s.close_to_tray
        self._keep_awake = s.keep_awake
        self._update_sleep_guard()

        # Start-with-Windows registry toggle
        if startup_manager.is_enabled() != s.start_with_windows:
            if s.start_with_windows:
                startup_manager.enable()
            else:
                startup_manager.disable()

    def _show_settings(self) -> None:
        s = self._settings_store.load()
        new_s = run_preferences_dialog(self, s, self._splitter.sizes())
        if new_s is None:
            return
        self._settings_store.save(new_s)
        self._apply_log_settings(new_s)
        self._apply_trading_settings(new_s)
        self._apply_background_settings(new_s)
        self._apply_log_settings(new_s)
        self._apply_trading_settings(new_s)
        self._update_broker_keys_hint()
        self._append_event("info", "Preferences saved.")

    # ── setup tab ────────────────────────────────────────────────────────────

    def _build_setup_tab(self) -> QWidget:
        return build_setup_tab(self)

    def _build_activity_tab(self) -> QWidget:
        return build_activity_tab(self)

    def _build_trades_tab(self) -> QWidget:
        return build_trades_tab(self)

    def _build_log_panel(self) -> QWidget:
        return build_log_panel(self)

    # ── menu callbacks ────────────────────────────────────────────────────────

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About SwiftTrade Desktop",
            f"SwiftTrade — Desktop Executor\n\n"
            "Connects to the SwiftTrade signal server and optionally executes trades "
            "on Trading212 on your behalf.\n\n"
            f"Version: {self._app_version()}",
        )

    def _show_welcome_and_dismiss(self) -> None:
        self._show_welcome()
        saved = self._settings_store.load()
        self._persist_settings(saved, seen_welcome=True)

    def _persist_settings(self, saved: AppSettings, **overrides) -> None:
        fields = {
            "ws_url": saved.ws_url,
            "license_key": saved.license_key,
            "reconnect_interval_s": saved.reconnect_interval_s,
            "max_reconnect_attempts": saved.max_reconnect_attempts,
            "order_quantity": saved.order_quantity,
            "max_daily_trades": saved.max_daily_trades,
            "signal_cooldown_s": saved.signal_cooldown_s,
            "default_stop_loss_pct": saved.default_stop_loss_pct,
            "confirm_before_trade": saved.confirm_before_trade,
            "skip_non_long_signals": saved.skip_non_long_signals,
            "log_font_size": saved.log_font_size,
            "log_max_lines": saved.log_max_lines,
            "log_auto_scroll": saved.log_auto_scroll,
            "log_show_timestamps": saved.log_show_timestamps,
            "log_level_filter": saved.log_level_filter,
            "notify_on_signal": saved.notify_on_signal,
            "notify_on_connect": saved.notify_on_connect,
            "auto_connect_on_start": saved.auto_connect_on_start,
            "start_minimized": saved.start_minimized,
            "start_with_windows": saved.start_with_windows,
            "close_to_tray": saved.close_to_tray,
            "keep_awake": saved.keep_awake,
            "seen_welcome": saved.seen_welcome,
            "splitter_sizes": saved.splitter_sizes,
        }
        fields.update(overrides)
        self._settings_store.save(AppSettings(**fields))

    def _show_help(self) -> None:
        run_help_dialog(self)

    def _show_quick_tips(self) -> None:
        """Setup tab Help button — same full guide as navbar."""
        self._show_help()

    def _show_welcome(self) -> None:
        QMessageBox.information(
            self,
            "Welcome to SwiftTrade",
            "3 steps on Get started:\n\n"
            "1. License (optional — skip if you don't have Pro)\n"
            "2. Trading212 demo key\n"
            "3. Connect\n\n"
            "Stay on Demo mode at first.",
        )

    def _has_saved_broker_keys(self) -> bool:
        stored = self._store.load()
        if not stored:
            return False
        return bool(stored.practice_api_key.strip() or stored.live_api_key.strip())

    def _refresh_setup_checklist(self) -> None:
        checklist = getattr(self, "setup_checklist", None)
        if checklist is None:
            return
        license_validated = self._license_tier in ("pro", "trial")
        has_broker_keys = self._has_saved_broker_keys()
        connected = self._server_connected
        checklist.update_state(
            license_validated=license_validated,
            has_broker_keys=has_broker_keys,
            connected=connected,
            license_field_nonempty=bool(self.license_key.text().strip()),
        )

        step1 = getattr(self, "_setup_step1", None)
        step2 = getattr(self, "_setup_step2", None)
        step3 = getattr(self, "_setup_step3", None)
        if step1 is None:
            return

        if connected:
            step1.set_state("done", expand=False)
            step2.set_state("done", expand=False)
            step3.set_state("done", expand=False)
        elif not has_broker_keys:
            if self.license_key.text().strip() and self._license_tier not in ("pro",):
                step1.set_state("active")
            else:
                step1.set_state("done", expand=False)
            step2.set_state("active")
            step3.set_state("locked", expand=False)
        else:
            step1.set_state("done", expand=False)
            step2.set_state("done", expand=False)
            step3.set_state("active")

        setup_connect = getattr(self, "setup_connect_btn", None)
        setup_disconnect = getattr(self, "setup_disconnect_btn", None)
        if setup_connect is not None:
            if connected:
                setup_connect.hide()
                if setup_disconnect is not None:
                    setup_disconnect.show()
            elif self.connect_btn.isEnabled():
                setup_connect.setText("  Connect  ")
                setup_connect.setEnabled(True)
                setup_connect.show()
                if setup_disconnect is not None:
                    setup_disconnect.hide()
            else:
                setup_connect.setText("  Connecting…  ")
                setup_connect.setEnabled(False)
                setup_connect.show()
                if setup_disconnect is not None:
                    setup_disconnect.hide()

        self._refresh_nav_status()

        QTimer.singleShot(80, self._scroll_to_active_setup_step)

    def _scroll_to_active_setup_step(self) -> None:
        scroll = getattr(self, "_setup_scroll", None)
        if scroll is None:
            return
        for step in (
            getattr(self, "_setup_step1", None),
            getattr(self, "_setup_step2", None),
            getattr(self, "_setup_step3", None),
        ):
            if step is not None and step.property("stepState") == "active":
                scroll.ensureWidgetVisible(step, 24, 24)
                break

    # ── status helpers ────────────────────────────────────────────────────────

    def _set_status(self, status: str) -> None:
        text, color = status_text(status)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"font-weight: 600; font-size: 9pt; color: {color}; background: transparent;"
        )
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

    def _on_ws_status(self, status: str) -> None:
        self._set_status(status)
        self._server_connected = status == "ONLINE"
        self._refresh_nav_status()
        self._refresh_setup_checklist()
        self._update_sleep_guard()
        self._update_tray_status()
        if status == "ONLINE":
            self._set_sb("Connected to bot server — receiving data.")
        elif status == "CONNECTING":
            self._set_sb("Connecting to bot server…")
        else:
            self._set_sb("")

    def _refresh_nav_status(self) -> None:
        """One plain-English status pill instead of scattered broker/license labels."""
        if not hasattr(self, "nav_status"):
            return
        status = getattr(self, "status_label", None)
        status_text_val = status.text() if status else ""

        if status_text_val == "Connecting…":
            self.nav_status.set_kind("connecting")
            return
        if self._server_connected:
            if self.trading_mode.is_live():
                self.nav_status.set_kind("online_live")
            else:
                self.nav_status.set_kind("online_demo")
            return

        license_ok = self._license_tier in ("pro", "trial")
        has_keys = self._has_saved_broker_keys()

        if license_ok and has_keys:
            self.nav_status.set_kind("ready")
        elif license_ok:
            self.nav_status.set_kind("custom", "Add Trading212 keys")
        elif bool(self.license_key.text().strip()):
            self.nav_status.set_kind("custom", "Check your license")
        else:
            self.nav_status.set_kind("setup")

    def _refresh_t212_status(self) -> None:
        self._refresh_nav_status()

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
        self.practice_t212_api_key.setEchoMode(mode)
        self.practice_t212_secret_key.setEchoMode(mode)
        self.live_t212_api_key.setEchoMode(mode)
        self.live_t212_secret_key.setEchoMode(mode)

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
        lic_raw = self.license_key.text().strip()
        lic = normalize_license_key(lic_raw)
        if lic_raw and lic is None:
            self._append_event(
                "warn",
                "Invalid license key ignored — connecting in paper mode (demo account only).",
            )
            self.license_key.clear()

        url = self.ws_url.text().strip()
        saved = self._settings_store.load()
        cfg = WsConfig(
            url=url,
            license_key=lic,
            reconnect_interval_s=self._reconnect_interval_s,
            max_reconnect_attempts=self._max_reconnect_attempts,
        )
        self._persist_settings(
            saved,
            ws_url=url,
            license_key=lic or "",
            splitter_sizes=self._splitter.sizes(),
        )
        self._ws_client = ExecWsClient(
            cfg=cfg,
            on_status=self._on_ws_status,
            on_event=lambda msg: self._append_event("info", msg),
            on_signal=self._handle_signal,
            on_bot_snapshot=self._handle_bot_snapshot,
            on_tier=self._on_ws_tier,
        )
        self._ws_task = asyncio.create_task(self._ws_client.run_forever())

        def _ws_task_done(task: asyncio.Task) -> None:
            """Re-arm the Connect button whenever the WS task exits for any reason."""
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self._refresh_setup_checklist()
            if task.cancelled():
                return
            exc = task.exception()
            if exc is not None:
                self._append_event(
                    "error",
                    f"Connection loop crashed ({type(exc).__name__}: {exc}). "
                    "Click Connect to retry.",
                )
                self._on_ws_status("OFFLINE")

        self._ws_task.add_done_callback(_ws_task_done)

        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        if hasattr(self, "setup_connect_btn"):
            self.setup_connect_btn.setEnabled(False)
        self._refresh_setup_checklist()
        if lic:
            self._set_sb("Connecting…")
        else:
            self._set_sb("Connecting in paper mode (no license)…")
            self._append_event("info", "Paper mode — no license key; demo trading only.")

    def _on_ws_tier(self, tier: str) -> None:
        if tier in ("pro", "trial", "expired", "free"):
            self._update_tier_ui(tier)

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
        self._server_connected = False
        self._refresh_setup_checklist()
        self._set_status("OFFLINE")
        self._update_sleep_guard()
        self._update_tray_status()
        self._append_event("info", "Disconnected. You can reconnect at any time.")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self._refresh_setup_checklist()
        self._set_sb("")

    # ── save keys (practice / live are independent) ───────────────────────────

    def on_save_practice_keys_clicked(self) -> None:
        cur = self._store.load()
        payload = SecretPayload(
            practice_api_key=self.practice_t212_api_key.text().strip(),
            practice_secret_key=self.practice_t212_secret_key.text().strip() or None,
            live_api_key=(cur.live_api_key if cur else ""),
            live_secret_key=(cur.live_secret_key if cur else None),
        )
        if not payload.practice_api_key:
            QMessageBox.warning(self, "No API key", "Enter your demo Trading212 API key before saving.")
            return
        self._store.save(payload)
        self._append_event("ok", "Demo Trading212 keys saved (encrypted).")
        self._refresh_t212_status()
        self._refresh_setup_checklist()
        self._set_sb("Demo keys saved.")
        # Silently verify the saved key is actually a demo key, not a live key
        asyncio.create_task(
            self._validate_practice_key_type(
                api=payload.practice_api_key,
                sec=payload.practice_secret_key,
            )
        )

    async def _validate_practice_key_type(self, *, api: str, sec: str | None) -> None:
        """
        Background check: if the demo-slot key is rejected by demo.trading212.com
        with a 401 but accepted by live.trading212.com, it is a real-money key.
        Clears the saved key and warns the user so they can get the correct one.
        """
        if self._license_tier == "pro":
            return  # Pro users can organise keys however they like
        try:
            async with T212Client(
                keys=T212Keys(api_key=api, secret_key=sec),
                base_url=T212_API_DEMO_BASE,
            ) as c:
                await c.get_free_funds()
            return  # Accepted by the demo host — correct key type
        except T212APIError as exc:
            if "401" not in str(exc):
                return  # Some other error (network, 429…) — not a key-type problem
        except Exception:
            return  # Network unreachable, etc. — don't block the user

        # Demo returned 401; probe the live host with the same credentials
        is_live_key = False
        try:
            async with T212Client(
                keys=T212Keys(api_key=api, secret_key=sec),
                base_url=T212_API_LIVE_BASE,
            ) as lc:
                await lc.get_free_funds()
                is_live_key = True
        except Exception:
            pass

        if not is_live_key:
            return  # Just an invalid/expired key — normal error path will handle it

        # Confirmed: a real-money Invest key was saved in the demo slot — clear it
        cur = self._store.load()
        if cur:
            self._store.save(SecretPayload(
                practice_api_key="",
                practice_secret_key=None,
                live_api_key=cur.live_api_key,
                live_secret_key=cur.live_secret_key,
            ))
        self.practice_t212_api_key.clear()
        self.practice_t212_secret_key.clear()
        self._refresh_t212_status()
        self._refresh_setup_checklist()

        self._append_event(
            "error",
            "Real-money key detected in demo slot \u2014 key cleared. "
            "Please generate a Practice account key: Trading212 \u2192 Settings \u2192 API.",
        )
        QMessageBox.critical(
            self,
            "Wrong API key type detected",
            "The key you saved belongs to a real-money Trading212 Invest account.\n\n"
            "Without a Pro license you can only trade on the Practice (demo) account.\n\n"
            "To get the correct key:\n"
            "  \u2022 Open the Trading212 app \u2192 Settings \u2192 API\n"
            "  \u2022 Make sure you are on the Practice account\n"
            "  \u2022 Generate a new API key and copy it\n"
            "  \u2022 Come back here and paste it in the Demo API key field\n\n"
            "Your entry has been cleared for safety.",
        )

    def on_save_live_keys_clicked(self) -> None:
        if self._license_tier != "pro":
            QMessageBox.warning(
                self,
                "Pro license required",
                "Saving real-money API keys requires an active Pro subscription.\n\n"
                "Upgrade to Pro at swifttrade.io, then return here to add your live Trading212 keys.",
            )
            return
        cur = self._store.load()
        payload = SecretPayload(
            practice_api_key=(cur.practice_api_key if cur else ""),
            practice_secret_key=(cur.practice_secret_key if cur else None),
            live_api_key=self.live_t212_api_key.text().strip(),
            live_secret_key=self.live_t212_secret_key.text().strip() or None,
        )
        if not payload.live_api_key:
            QMessageBox.warning(self, "No API key", "Enter your real-money Trading212 API key before saving.")
            return
        self._store.save(payload)
        self._append_event("ok", "Real-money Trading212 keys saved (encrypted).")
        self._refresh_t212_status()
        self._refresh_setup_checklist()
        self._set_sb("Real-money keys saved.")

    # ── test connection (practice / live — independent of top-bar mode) ─────────

    async def _run_t212_connection_test(
        self,
        *,
        base_url: str,
        api: str,
        sec: str | None,
        host_kind: str,
        probe_invest_key_on_demo_401: bool,
    ) -> None:
        self._set_sb("Testing Trading212 connection…")
        try:
            try:
                async with T212Client(keys=T212Keys(api_key=api, secret_key=sec), base_url=base_url) as client:
                    funds = await client.get_free_funds()
            except T212APIError as exc:
                err_str = str(exc)
                if (
                    probe_invest_key_on_demo_401
                    and "401" in err_str
                    and self._license_tier != "pro"
                    and base_url == T212_API_DEMO_BASE
                ):
                    is_live_key = False
                    try:
                        async with T212Client(
                            keys=T212Keys(api_key=api, secret_key=sec),
                            base_url=T212_API_LIVE_BASE,
                        ) as live_probe:
                            await live_probe.get_free_funds()
                            is_live_key = True
                    except Exception:
                        pass
                    if is_live_key:
                        QMessageBox.critical(
                            self,
                            "Real-money API key detected",
                            "These API keys belong to a real-money Trading212 Invest account.\n\n"
                            "Without a Pro license you can only connect to the Practice account.\n\n"
                            "To fix this:\n"
                            "  \u2022 Go to Trading212 \u2192 Settings \u2192 API and generate a key for your Practice account, OR\n"
                            "  \u2022 Upgrade to Pro to unlock the real-money API.",
                        )
                        self._append_event(
                            "error",
                            "T212 test blocked \u2014 real-money (Invest) key detected. "
                            "Non-Pro users must use Practice account keys.",
                        )
                        self._set_sb("")
                        return
                raise
            QMessageBox.information(
                self,
                "Connection OK",
                f"Trading212 accepted your API keys on the {host_kind}.\n\n"
                f"Available funds: {funds:.2f}",
            )
            self._append_event("ok", f"T212 test OK ({host_kind}) — funds ≈ {funds:.2f}")
            self._set_sb("Trading212 connection verified.")
        except T212APIError as exc:
            QMessageBox.critical(self, "Trading212 error", str(exc))
            self._append_event("error", f"T212 test failed: {exc}")
            self._set_sb("")
        except Exception as exc:
            QMessageBox.critical(self, "Connection failed", str(exc))
            self._append_event("error", f"T212 test failed: {exc}")
            self._set_sb("")

    @asyncSlot()
    async def on_test_t212_practice_clicked(self) -> None:
        api = self.practice_t212_api_key.text().strip()
        sec = self.practice_t212_secret_key.text().strip() or None
        if not api:
            QMessageBox.warning(self, "API key required", "Enter your demo API key first.")
            return
        self._t212_test_busy = True
        self._update_broker_keys_hint()
        try:
            await self._run_t212_connection_test(
                base_url=T212_API_DEMO_BASE,
                api=api,
                sec=sec,
                host_kind="practice (demo API)",
                probe_invest_key_on_demo_401=True,
            )
        finally:
            self._t212_test_busy = False
            self._update_broker_keys_hint()

    @asyncSlot()
    async def on_test_t212_live_clicked(self) -> None:
        if self._license_tier != "pro":
            QMessageBox.information(
                self,
                "Pro required",
                "Testing the real-money API requires an active Pro license.",
            )
            return
        api = self.live_t212_api_key.text().strip()
        sec = self.live_t212_secret_key.text().strip() or None
        if not api:
            QMessageBox.warning(self, "API key required", "Enter your real-money API key first.")
            return
        self._t212_test_busy = True
        self._update_broker_keys_hint()
        try:
            await self._run_t212_connection_test(
                base_url=T212_API_LIVE_BASE,
                api=api,
                sec=sec,
                host_kind="real-money (live API)",
                probe_invest_key_on_demo_401=False,
            )
        finally:
            self._t212_test_busy = False
            self._update_broker_keys_hint()

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

        if self.trading_mode.is_live() and self._license_tier != "pro":
            self._append_event(
                "error",
                "Live execution blocked — Pro subscription required. Switching to demo account.",
            )
            self.trading_mode.set_live(False)

        pair = self._stored_active_t212_keys()
        if not pair or not pair[0]:
            if self.trading_mode.is_live() and self._license_tier == "pro":
                self._append_event("error", "T212 keys missing for the active profile — save keys and try again.")
            else:
                self._append_event(
                    "warn",
                    "Paper trading — signal logged. Save your Trading212 practice API keys to auto-trade on the demo account.",
                )
            return

        if self.trading_mode.is_live() and self._license_tier == "pro":
            profile = "live"
        else:
            profile = "demo"

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
            account_label = "live" if profile == "live" else "demo"
            r = QMessageBox.question(
                self,
                "Confirm trade",
                f"Place a {direction_upper} market order for {sym_str} on your {account_label} account?\n\n"
                f"Quantity: {self._order_quantity:.2f} units",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                self._append_event("info", "Trade confirmation declined. Signal skipped.")
                return

        try:
            async with T212Client(
                keys=T212Keys(api_key=pair[0], secret_key=pair[1]),
                base_url=self._t212_base_url(),
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
                label = "Live" if profile == "live" else "Demo"
                self._append_event("ok", f"{label} market order placed: {resp}")
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
        pair = self._stored_active_t212_keys()
        if not pair or not pair[0]:
            return
        parsed: list[tuple[str, str]] = []
        try:
            async with T212Client(
                keys=T212Keys(api_key=pair[0], secret_key=pair[1]),
                base_url=self._t212_base_url(),
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
