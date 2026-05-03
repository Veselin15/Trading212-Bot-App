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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot

from .crypto_store import CryptoStore, SecretPayload
from .license_checker import LicenseResult, check_license
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
from .ui.preferences_dialog import run_preferences_dialog
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
        self.setMinimumSize(980, 640)
        self.resize(1120, 720)

        self._base_dir = base_dir if base_dir is not None else (Path.home() / ".t212_executor")
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

        self.practice_t212_api_key = QLineEdit()
        self.practice_t212_api_key.setPlaceholderText("Practice API key — Trading212 Practice → Settings → API")
        self.practice_t212_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.practice_t212_secret_key = QLineEdit()
        self.practice_t212_secret_key.setPlaceholderText("Practice API secret (optional)")
        self.practice_t212_secret_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.live_t212_api_key = QLineEdit()
        self.live_t212_api_key.setPlaceholderText("Invest / real-money API key — Trading212 Invest → Settings → API")
        self.live_t212_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.live_t212_secret_key = QLineEdit()
        self.live_t212_secret_key.setPlaceholderText("Invest API secret (optional)")
        self.live_t212_secret_key.setEchoMode(QLineEdit.EchoMode.Password)

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

        self.test_t212_practice_btn = QPushButton("Test practice (demo)")
        self.test_t212_practice_btn.setObjectName("SecondaryBtn")
        self.test_t212_practice_btn.setToolTip("GET cash on demo.trading212.com using the Practice fields above.")

        self.test_t212_live_btn = QPushButton("Test live (Invest)")
        self.test_t212_live_btn.setObjectName("SecondaryBtn")
        self.test_t212_live_btn.setToolTip("GET cash on live.trading212.com using the Invest fields (Pro only).")

        self.save_practice_keys_btn = QPushButton("Save practice keys")
        self.save_practice_keys_btn.setObjectName("PrimaryBtn")
        self.save_practice_keys_btn.setToolTip("Encrypt and store the Practice account key pair on this PC.")

        self.save_live_keys_btn = QPushButton("Save live keys")
        self.save_live_keys_btn.setObjectName("SecondaryBtn")
        self.save_live_keys_btn.setToolTip("Encrypt and store the Invest / real-money key pair on this PC.")

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
        self._update_broker_keys_hint()
        self.start_minimized = settings.start_minimized
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

        self._sync_setup_mode_hint()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _git_version(self) -> str:
        try:
            root = repo_root()
            out = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], cwd=str(root), text=True
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
                "Paper: log signals only; Trading212 calls use Practice keys + demo.trading212.com.\n"
                "Live: place real orders using your saved Invest keys + live.trading212.com (tier re-checked on the server)."
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
        self._update_broker_keys_hint()
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
                self._append_event(
                    "info",
                    "Invest keys: save under “Real-money / Invest”, then use the top bar Live mode when you want real orders.",
                )
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
            "Live mode will send real-money orders on live.trading212.com using your saved Invest keys "
            "every time the bot fires a LONG signal.\n\n"
            "Your Pro license is active. Stay on Paper if you only want to watch signals in the log.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if r == QMessageBox.StandardButton.Ok:
            self.trading_mode.set_live(True)
        # Stay on Paper if cancelled (toggle widget never switched).

    def _on_trading_mode_changed(self, live: bool) -> None:
        if live:
            self._set_sb("Live trading ON — Invest API + real orders when signals arrive.")
        else:
            self._set_sb("Paper trading — Practice API; signals logged only.")
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
        if is_pro and self.trading_mode.is_live():
            self._broker_keys_hint.setText(
                "Trading mode is Live (top bar): the app uses your saved Invest keys on live.trading212.com "
                "for orders and market data. Use “Test live” to verify those keys."
            )
            self._broker_keys_hint.setStyleSheet(
                f"color: {_DANGER}; font-size: 8.8pt; font-weight: 600; background: transparent; padding: 0; margin: 0;"
            )
        else:
            self._broker_keys_hint.setText(
                "Trading mode is Paper (top bar): the app uses Practice keys on demo.trading212.com. "
                "Pro users can still press “Test live” to check Invest keys without turning on Live trading."
            )
            self._broker_keys_hint.setStyleSheet(
                f"color: {_MUTED}; font-size: 8.8pt; background: transparent; padding: 0; margin: 0;"
            )

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

    def _show_settings(self) -> None:
        s = self._settings_store.load()
        new_s = run_preferences_dialog(self, s, self._splitter.sizes())
        if new_s is None:
            return
        self._settings_store.save(new_s)
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
            "2.  Trading212 — save Practice and/or Invest keys; use Paper/Live in the top bar for broker mode; Test each side as needed.\n\n"
            "3.  Click Connect (top bar) — status changes to green when linked.\n\n"
            "4.  Paper / Live — use the top-bar toggle (Live needs Pro). Tier is re-checked periodically on the server.\n\n"
            "Tip: right-click any table row to copy it.",
        )

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
        if status == "ONLINE":
            self._set_sb("Connected to bot server — receiving data.")
        elif status == "CONNECTING":
            self._set_sb("Connecting to bot server…")
        else:
            self._set_sb("")

    def _refresh_t212_status(self) -> None:
        stored = self._store.load()
        active = self._stored_active_t212_keys()
        if active and active[0]:
            label = "T212 ✓ live" if self._t212_base_url() == T212_API_LIVE_BASE else "T212 ✓ practice"
            self.t212_status.setText(label)
            self.t212_status.setStyleSheet(
                f"color: {_SUCCESS}; font-size: 8.5pt; background: transparent; border: none; padding: 0 4px;"
            )
        elif stored and (stored.practice_api_key.strip() or stored.live_api_key.strip()):
            self.t212_status.setText("T212 keys saved — use top bar Paper/Live for active broker")
            self.t212_status.setStyleSheet(
                f"color: {_WARN}; font-size: 8.5pt; background: transparent; border: none; padding: 0 4px;"
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
            QMessageBox.warning(self, "No API key", "Enter your Practice Trading212 API key before saving.")
            return
        self._store.save(payload)
        self._append_event("ok", "Practice Trading212 keys saved (encrypted).")
        self._refresh_t212_status()
        self._set_sb("Practice keys saved.")

    def on_save_live_keys_clicked(self) -> None:
        cur = self._store.load()
        payload = SecretPayload(
            practice_api_key=(cur.practice_api_key if cur else ""),
            practice_secret_key=(cur.practice_secret_key if cur else None),
            live_api_key=self.live_t212_api_key.text().strip(),
            live_secret_key=self.live_t212_secret_key.text().strip() or None,
        )
        if not payload.live_api_key:
            QMessageBox.warning(self, "No API key", "Enter your Invest / live Trading212 API key before saving.")
            return
        self._store.save(payload)
        self._append_event("ok", "Live (Invest) Trading212 keys saved (encrypted).")
        self._refresh_t212_status()
        self._set_sb("Live keys saved.")

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
            QMessageBox.warning(self, "API key required", "Enter your Practice API key first.")
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
                "Testing the live (Invest) API requires an active Pro license.",
            )
            return
        api = self.live_t212_api_key.text().strip()
        sec = self.live_t212_secret_key.text().strip() or None
        if not api:
            QMessageBox.warning(self, "API key required", "Enter your Invest / live API key first.")
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
            pair = self._stored_active_t212_keys()
            if not pair or not pair[0]:
                self._append_event("error", "T212 keys missing for the active profile — save keys and try again.")
                return

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
