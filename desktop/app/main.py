from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
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
from qasync import QEventLoop, asyncSlot

from .crypto_store import CryptoStore, SecretPayload
from .settings_store import AppSettings, SettingsStore
from .t212_client import T212APIError, T212Client, T212Keys
from .ws_client import ExecWsClient, WsConfig, _smoke_health_url


def _status_text(status: str) -> tuple[str, str]:
    if status == "ONLINE":
        return ("Online", "green")
    if status == "CONNECTING":
        return ("Connecting...", "goldenrod")
    return ("Offline", "red")


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Trading212 Executor")
        self.setMinimumSize(900, 560)

        self._base_dir = Path.home() / ".t212_executor"
        self._store = CryptoStore(self._base_dir)
        self._settings_store = SettingsStore(self._base_dir)
        self._ws_task: asyncio.Task | None = None
        self._ws_client: ExecWsClient | None = None

        self.status_dot = QLabel("●")
        self.status_dot.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("Offline")
        self.status_label.setMinimumWidth(120)
        self.t212_status = QLabel("Trading212: Not configured")
        self.t212_status.setMinimumWidth(220)
        self.exec_mode = QCheckBox("LIVE execution")
        self.exec_mode.setChecked(False)
        self.exec_mode.setToolTip(
            "Unchecked: signals are logged only (safe). Checked: LONG signals place real orders on your Trading212 account."
        )

        self.license_key = QLineEdit()
        self.license_key.setPlaceholderText("License key (UUID)")
        self.license_key.setToolTip("Portal subscription license (UUID format).")

        self.ws_url = QLineEdit("ws://127.0.0.1:8010/ws/exec")
        self.ws_url.setMinimumWidth(300)
        self.ws_url.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ws_url.setToolTip("Backend WebSocket URL. Use 127.0.0.1 if the server binds to IPv4 only.")

        self.t212_api_key = QLineEdit()
        self.t212_api_key.setPlaceholderText("Trading212 API key")
        self.t212_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.t212_secret_key = QLineEdit()
        self.t212_secret_key.setPlaceholderText("Trading212 secret (optional)")
        self.t212_secret_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.show_t212_secrets = QCheckBox("Show keys")
        self.show_t212_secrets.setToolTip("Reveal API key and secret on screen (disable when someone can see your display).")
        self.show_t212_secrets.toggled.connect(self._on_show_t212_secrets_toggled)  # type: ignore[arg-type]

        self.test_t212_btn = QPushButton("Test Trading212 connection")
        self.test_t212_btn.setToolTip("Call the broker API with the key fields above (does not save to disk).")
        self.test_t212_btn.clicked.connect(self.on_test_t212_clicked)  # type: ignore[arg-type]

        self.save_btn = QPushButton("Save keys (encrypted)")
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)

        self.save_btn.clicked.connect(self.on_save_clicked)  # type: ignore[arg-type]
        self.connect_btn.clicked.connect(self.on_connect_clicked)  # type: ignore[arg-type]
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)  # type: ignore[arg-type]

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.document().setMaximumBlockCount(500)
        _mono = QFont("Cascadia Mono", 10)
        if not _mono.exactMatch():
            _mono = QFont("Consolas", 10)
        self.event_log.setFont(_mono)

        self._last_bot_snapshot: dict[str, dict] = {}
        self._signal_rows: list[tuple[str, str, str, str, str]] = []
        self._market_rows: list[tuple[str, str]] = []

        self.activity_symbol_filter = QLineEdit()
        self.activity_symbol_filter.setPlaceholderText("Filter rows by symbol (substring)…")

        self.market_table = QTableWidget(0, 2)
        self.market_table.setHorizontalHeaderLabels(["Symbol", "Market state"])
        self._wire_activity_table(self.market_table)

        self.bot_table = QTableWidget(0, 7)
        self.bot_table.setHorizontalHeaderLabels(
            ["Symbol", "Ready", "Regime", "Trigger", "Side", "Blocked", "Reason"],
        )
        self._wire_activity_table(self.bot_table)

        self.signals_table = QTableWidget(0, 5)
        self.signals_table.setHorizontalHeaderLabels(["Time", "ID", "Dir", "Symbol", "Summary"])
        self._wire_activity_table(self.signals_table)

        self.exec_queue = QListWidget()
        self.exec_queue.addItem("Execution queue will appear here.")

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_connection_tab(), "Connection")
        self.tabs.addTab(self._build_activity_tab(), "Activity")
        self.tabs.addTab(self._build_execution_tab(), "Execution")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        root = QVBoxLayout()
        root.addLayout(self._build_top_bar())
        root.addWidget(splitter, 1)

        self.setLayout(root)
        self._set_status("OFFLINE")
        self._append_event("App started.")
        self._append_event(f"Version: {self._git_version()}")
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

        self.activity_symbol_filter.textChanged.connect(self._on_activity_filter_changed)  # type: ignore[arg-type]

    def _git_version(self) -> str:
        try:
            repo_root = Path(__file__).resolve().parents[2]
            out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo_root), text=True)
            return out.strip()
        except Exception:
            return "unknown"

    def _build_top_bar(self) -> QHBoxLayout:
        top = QHBoxLayout()
        top.addWidget(self.status_dot)
        top.addWidget(self.status_label)
        top.addSpacing(12)
        top.addWidget(self.t212_status)
        top.addWidget(self.exec_mode)
        top.addWidget(QLabel("WS:"))
        top.addWidget(self.ws_url, 1)
        top.addSpacing(8)
        top.addWidget(self.connect_btn)
        top.addWidget(self.disconnect_btn)
        return top

    def _build_connection_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout()
        form.addRow("License key", self.license_key)

        diag_row = QHBoxLayout()
        self.diagnostics_btn = QPushButton("Open backend health in browser")
        self.diagnostics_btn.setToolTip("Opens /health/supabase-smoke for the host/port in the WS URL (lengths only, no secrets).")
        self.diagnostics_btn.clicked.connect(self._open_backend_diagnostics)  # type: ignore[arg-type]
        diag_row.addWidget(self.diagnostics_btn)
        diag_row.addStretch(1)
        form.addRow("Diagnostics", diag_row)

        key_frame = QFrame()
        key_layout = QVBoxLayout()
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.t212_api_key)
        key_layout.addWidget(self.t212_secret_key)
        key_btns = QHBoxLayout()
        key_btns.addWidget(self.show_t212_secrets)
        key_btns.addWidget(self.test_t212_btn)
        key_btns.addStretch(1)
        key_layout.addLayout(key_btns)
        key_layout.addWidget(self.save_btn)
        key_frame.setLayout(key_layout)

        form.addRow("Trading212 keys", key_frame)
        w.setLayout(form)
        return w

    def _build_activity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        filt = QHBoxLayout()
        filt.addWidget(QLabel("Symbol filter"))
        filt.addWidget(self.activity_symbol_filter, 1)
        layout.addLayout(filt)
        layout.addWidget(QLabel("Trading212 market state"))
        layout.addWidget(self.market_table, 1)
        layout.addWidget(QLabel("Bot state (latest snapshot)"))
        layout.addWidget(self.bot_table, 2)
        layout.addWidget(QLabel("Recent signals"))
        layout.addWidget(self.signals_table, 2)
        w.setLayout(layout)
        return w

    def _build_execution_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Execution / position manager"))
        layout.addWidget(self.exec_queue, 1)
        w.setLayout(layout)
        return w

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        log_head = QHBoxLayout()
        log_head.addWidget(QLabel("Event log"))
        clear_log = QPushButton("Clear")
        clear_log.setToolTip("Clear the on-screen log (does not affect the server).")
        clear_log.clicked.connect(self.event_log.clear)  # type: ignore[arg-type]
        log_head.addStretch(1)
        log_head.addWidget(clear_log)
        layout.addLayout(log_head)
        layout.addWidget(self.event_log, 1)
        w.setLayout(layout)
        return w

    def _open_backend_diagnostics(self) -> None:
        url = QUrl(_smoke_health_url(self.ws_url.text()))
        if not QDesktopServices.openUrl(url):
            self._append_event(f"Could not open browser for {url.toString()}")

    def _on_show_t212_secrets_toggled(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.t212_api_key.setEchoMode(mode)
        self.t212_secret_key.setEchoMode(mode)

    @asyncSlot()
    async def on_test_t212_clicked(self) -> None:
        api = self.t212_api_key.text().strip()
        sec = self.t212_secret_key.text().strip() or None
        if not api:
            QMessageBox.warning(self, "API key required", "Enter your Trading212 API key to test the connection.")
            return
        self.test_t212_btn.setEnabled(False)
        try:
            async with T212Client(keys=T212Keys(api_key=api, secret_key=sec)) as client:
                funds = await client.get_free_funds()
                pending = len(await client.get_pending_orders())
            QMessageBox.information(
                self,
                "Trading212 connection OK",
                "API credentials were accepted.\n\n"
                f"Free funds: {funds:.2f}\n"
                f"Pending orders: {pending}\n\n"
                "Default client uses the Trading212 demo API host unless you change it in code.",
            )
            self._append_event(f"T212 test OK: freeFunds≈{funds:.2f}, pendingOrders={pending}")
        except T212APIError as exc:
            QMessageBox.critical(self, "Trading212 API error", str(exc))
            self._append_event(f"T212 test failed: {exc}")
        except Exception as exc:
            QMessageBox.critical(self, "Trading212 test failed", str(exc))
            self._append_event(f"T212 test failed: {exc}")
        finally:
            self.test_t212_btn.setEnabled(True)

    def _wire_activity_table(self, table: QTableWidget) -> None:
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._activity_table_context_menu)  # type: ignore[arg-type]
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        _tf = QFont("Cascadia Mono", 9)
        if not _tf.exactMatch():
            _tf = QFont("Consolas", 9)
        table.setFont(_tf)

    def _activity_table_context_menu(self, pos: QPoint) -> None:
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        idx = table.indexAt(pos)
        if not idx.isValid():
            return
        row = idx.row()
        parts: list[str] = []
        for c in range(table.columnCount()):
            it = table.item(row, c)
            parts.append(it.text() if it is not None else "")
        line = "\t".join(parts)
        menu = QMenu(self)
        act = QAction("Copy row", self)
        act.triggered.connect(lambda _checked=False, text=line: QApplication.clipboard().setText(text))
        menu.addAction(act)
        menu.exec(table.viewport().mapToGlobal(pos))

    def _symbol_filter_matches(self, symbol: str) -> bool:
        flt = self.activity_symbol_filter.text().strip()
        if not flt:
            return True
        return flt.upper() in str(symbol).upper()

    def _on_activity_filter_changed(self, _text: str) -> None:
        self._refresh_bot_table()
        self._refresh_signals_table()
        self._refresh_market_table()

    def _refresh_bot_table(self) -> None:
        rows: list[tuple[str, str, str, str, str, str, str]] = []
        for sym in sorted(self._last_bot_snapshot.keys()):
            if not self._symbol_filter_matches(sym):
                continue
            snap = self._last_bot_snapshot.get(sym) or {}
            if not isinstance(snap, dict):
                continue
            rows.append(
                (
                    sym,
                    str(snap.get("ready")),
                    str(snap.get("regime")),
                    str(snap.get("trigger")),
                    str(snap.get("signal_side")),
                    str(snap.get("entry_blocked")),
                    str(snap.get("reason")),
                ),
            )
        self.bot_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.bot_table.setItem(r, c, QTableWidgetItem(val))

    def _refresh_signals_table(self) -> None:
        rows = [t for t in self._signal_rows if self._symbol_filter_matches(t[3])]
        self.signals_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.signals_table.setItem(r, c, QTableWidgetItem(val))

    def _refresh_market_table(self) -> None:
        rows = [t for t in self._market_rows if self._symbol_filter_matches(t[0])]
        self.market_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.market_table.setItem(r, c, QTableWidgetItem(val))

    def _set_status(self, status: str) -> None:
        text, color = _status_text(status)
        self.status_label.setText(text)
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 20px;")

    def _on_ws_status(self, status: str) -> None:
        self._set_status(status)

    def _append_event(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.event_log.append(f"[{ts}] {message}")

    def _refresh_t212_status(self) -> None:
        stored = self._store.load()
        if stored and stored.t212_api_key:
            self.t212_status.setText("Trading212: Configured (encrypted)")
        else:
            self.t212_status.setText("Trading212: Not configured")

    async def _handle_signal(self, payload: dict) -> None:
        sid = payload.get("id")
        direction = payload.get("direction")
        symbol = payload.get("symbol")
        line = f"{sid} | {direction} | {symbol}"
        ts = datetime.now().strftime("%H:%M:%S")
        self._signal_rows.insert(
            0,
            (ts, str(sid), str(direction), str(symbol), line),
        )
        if len(self._signal_rows) > 200:
            self._signal_rows.pop()
        self._refresh_signals_table()

        self.exec_queue.insertItem(0, QListWidgetItem(f"Queued: {line}"))
        if self.exec_queue.count() > 200:
            self.exec_queue.takeItem(self.exec_queue.count() - 1)

        if not self.exec_mode.isChecked():
            self._append_event("SAFE MODE: signal queued but not executed.")
            return

        # Minimal execution prototype: place a market order + protective stop for LONG only.
        try:
            stored = self._store.load()
            if not stored or not stored.t212_api_key:
                self._append_event("Trading212 keys missing; cannot execute.")
                return

            async with T212Client(keys=T212Keys(api_key=stored.t212_api_key, secret_key=stored.t212_secret_key)) as client:
                symbol = str(payload.get("symbol") or "").strip()
                direction = str(payload.get("direction") or "LONG").strip().upper()
                rp = payload.get("risk_params") or {}
                stop_loss_pct = float(rp.get("stop_loss_pct") or 0.0)
                is_debug = bool(payload.get("debug"))

                if direction != "LONG":
                    self._append_event(f"Execution skipped (direction={direction}) — SHORT not implemented yet.")
                    return

                price = await client.get_price_from_positions(symbol)
                if price is None:
                    # If we can't read price from positions, still place a small order for smoke testing.
                    price = 0.0

                # Practice-mode smoke sizing: buy 1 share.
                qty = 1.0
                resp = await client.place_market_order(symbol, qty)
                self._append_event(f"Market order submitted: {resp}")

                # Wait for fill before placing protective stops or closing.
                # IMPORTANT: Do not infer fills from portfolio quantities (can include reserved/pending).
                # Only trust order status/filledQuantity (and positions later for management).
                order_id = resp.get("id") if isinstance(resp, dict) else None
                filled = False
                filled_qty = 0.0
                for _ in range(45):  # up to ~45s
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
                            # Trace the broker's view so we can debug premarket behavior.
                            self._append_event(f"Order poll: status={st} filledQuantity={filled_qty}")

                            if st in {"CANCELLED", "REJECTED"}:
                                break

                            if st in {"FILLED", "EXECUTED"} or filled_qty >= qty:
                                filled = True
                                break

                if not filled:
                    self._append_event("Order not filled yet (premarket/illiquid). Skipping stop placement for now.")
                else:
                    # Refresh price after fill if possible.
                    price2 = await client.get_price_from_positions(symbol)
                    if price2 is not None:
                        price = float(price2)

                    if price > 0 and stop_loss_pct > 0:
                        stop_price = price * (1.0 - stop_loss_pct / 100.0)
                        # Final guard: only place STOP if we actually have fills.
                        if filled_qty >= qty:
                            stop_resp = await client.place_stop_order(symbol, qty=-qty, stop_price=stop_price)
                            self._append_event(f"Protective STOP submitted: {stop_resp}")
                        else:
                            self._append_event("Protective STOP skipped (filledQuantity still 0).")
                    else:
                        self._append_event("Protective STOP skipped (missing price/stop_loss_pct).")

                if is_debug:
                    # Simple live test: wait for the position to appear, then close it.
                    if not filled and order_id:
                        try:
                            cancel_resp = await client.cancel_order(str(order_id))
                            self._append_event(f"Debug trade: cancelled unfilled order: {cancel_resp}")
                        except Exception as exc:
                            self._append_event(f"Debug trade: cancel failed: {exc}")
                        return

                    self._append_event("Debug trade: closing position...")
                    close_resp = await client.close_position(symbol)
                    self._append_event(f"Debug trade: close submitted: {close_resp}")
        except Exception as exc:
            self._append_event(f"EXECUTION ERROR: {exc}")

    def _handle_bot_snapshot(self, payload: dict) -> None:
        # payload: { "ASML.AS": {...}, ... }
        snap: dict[str, dict] = {}
        for symbol, raw in payload.items():
            if isinstance(raw, dict):
                snap[str(symbol)] = raw
        self._last_bot_snapshot = snap
        self._refresh_bot_table()

        # Update Trading212 market state panel for these symbols (best-effort).
        asyncio.create_task(self._refresh_market_state(list(payload.keys())))

    async def _refresh_market_state(self, symbols: list[str]) -> None:
        stored = self._store.load()
        if not stored or not stored.t212_api_key:
            return
        parsed: list[tuple[str, str]] = []
        try:
            async with T212Client(keys=T212Keys(api_key=stored.t212_api_key, secret_key=stored.t212_secret_key)) as client:
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

    @asyncSlot()
    async def on_connect_clicked(self) -> None:
        if self._ws_task and not self._ws_task.done():
            return
        lic = self.license_key.text().strip()
        if not lic:
            QMessageBox.information(self, "License required", "Enter your portal license key (UUID) before connecting.")
            return
        try:
            uuid.UUID(lic)
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid license format",
                "The license key must be a UUID, for example:\n550e8400-e29b-41d4-a716-446655440000",
            )
            return

        url = self.ws_url.text().strip()
        cfg = WsConfig(url=url, license_key=lic)
        self._settings_store.save(AppSettings(ws_url=url, license_key=lic))
        self._ws_client = ExecWsClient(
            cfg=cfg,
            on_status=self._on_ws_status,
            on_event=self._append_event,
            on_signal=self._handle_signal,
            on_bot_snapshot=self._handle_bot_snapshot,
        )
        self._ws_task = asyncio.create_task(self._ws_client.run_forever())
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)

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
        self._append_event("Disconnected by user.")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

    def on_save_clicked(self) -> None:
        payload = SecretPayload(
            t212_api_key=self.t212_api_key.text().strip(),
            t212_secret_key=(self.t212_secret_key.text().strip() or None),
        )
        if payload.t212_api_key:
            self._store.save(payload)
            self._append_event("Trading212 keys saved (encrypted).")
            self._refresh_t212_status()


def main() -> None:
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    w = MainWindow()
    w.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()

