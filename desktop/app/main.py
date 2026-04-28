from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop, asyncSlot

from .crypto_store import CryptoStore, SecretPayload
from .settings_store import AppSettings, SettingsStore
from .t212_client import T212Client, T212Keys
from .ws_client import ExecWsClient, WsConfig


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

        self.license_key = QLineEdit()
        self.license_key.setPlaceholderText("License key (UUID)")

        self.ws_url = QLineEdit("ws://localhost:8000/ws/exec")

        self.t212_api_key = QLineEdit()
        self.t212_api_key.setPlaceholderText("Trading212 API key")

        self.t212_secret_key = QLineEdit()
        self.t212_secret_key.setPlaceholderText("Trading212 secret (optional)")

        self.save_btn = QPushButton("Save keys (encrypted)")
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)

        self.save_btn.clicked.connect(self.on_save_clicked)  # type: ignore[arg-type]
        self.connect_btn.clicked.connect(self.on_connect_clicked)  # type: ignore[arg-type]
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)  # type: ignore[arg-type]

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)

        self.signals_list = QListWidget()
        self.bot_state = QListWidget()
        self.market_state = QListWidget()

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

    def _build_top_bar(self) -> QHBoxLayout:
        top = QHBoxLayout()
        top.addWidget(self.status_dot)
        top.addWidget(self.status_label)
        top.addSpacing(12)
        top.addWidget(self.t212_status)
        top.addWidget(self.exec_mode)
        top.addStretch(1)
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

        key_frame = QFrame()
        key_layout = QVBoxLayout()
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.t212_api_key)
        key_layout.addWidget(self.t212_secret_key)
        key_layout.addWidget(self.save_btn)
        key_frame.setLayout(key_layout)

        form.addRow("Trading212 keys", key_frame)
        w.setLayout(form)
        return w

    def _build_activity_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Trading212 market state"))
        layout.addWidget(self.market_state, 1)
        layout.addWidget(QLabel("Bot state (latest snapshot)"))
        layout.addWidget(self.bot_state, 1)
        layout.addWidget(QLabel("Recent signals"))
        layout.addWidget(self.signals_list, 2)
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
        layout.addWidget(QLabel("Event log"))
        layout.addWidget(self.event_log, 1)
        w.setLayout(layout)
        return w

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
        self.signals_list.insertItem(0, QListWidgetItem(line))
        if self.signals_list.count() > 200:
            self.signals_list.takeItem(self.signals_list.count() - 1)

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

                # Wait for fill (owned qty > 0) before placing protective stops or closing.
                order_id = resp.get("id") if isinstance(resp, dict) else None
                filled = False
                for _ in range(30):  # up to ~30s
                    await asyncio.sleep(1.0)
                    pos_qty = await client.get_position_quantity(symbol)
                    if pos_qty >= qty:
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
                        stop_resp = await client.place_stop_order(symbol, qty=-qty, stop_price=stop_price)
                        self._append_event(f"Protective STOP submitted: {stop_resp}")
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
        self.bot_state.clear()
        for symbol in sorted(payload.keys()):
            snap = payload.get(symbol) or {}
            if not isinstance(snap, dict):
                continue
            ready = snap.get("ready")
            regime = snap.get("regime")
            trigger = snap.get("trigger")
            side = snap.get("signal_side")
            reason = snap.get("reason")
            blocked = snap.get("entry_blocked")
            line = f"{symbol} | ready={ready} | regime={regime} trigger={trigger} side={side} blocked={blocked} reason={reason}"
            self.bot_state.addItem(QListWidgetItem(line))

        # Update Trading212 market state panel for these symbols (best-effort).
        asyncio.create_task(self._refresh_market_state(list(payload.keys())))

    async def _refresh_market_state(self, symbols: list[str]) -> None:
        stored = self._store.load()
        if not stored or not stored.t212_api_key:
            return
        try:
            async with T212Client(keys=T212Keys(api_key=stored.t212_api_key, secret_key=stored.t212_secret_key)) as client:
                rows: list[str] = []
                for sym in sorted(set(symbols)):
                    try:
                        state = await client.get_market_state(sym)
                    except Exception:
                        state = "unknown"
                    rows.append(f"{sym}: {state}")
        except Exception:
            return

        self.market_state.clear()
        for r in rows:
            self.market_state.addItem(QListWidgetItem(r))

    @asyncSlot()
    async def on_connect_clicked(self) -> None:
        if self._ws_task and not self._ws_task.done():
            return
        lic = self.license_key.text().strip()
        if not lic:
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

