from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
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

        self._store = CryptoStore(Path.home() / ".t212_executor")
        self._ws_task: asyncio.Task | None = None
        self._ws_client: ExecWsClient | None = None

        self.status_dot = QLabel("●")
        self.status_dot.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("Offline")
        self.status_label.setMinimumWidth(120)
        self.t212_status = QLabel("Trading212: Not configured")
        self.t212_status.setMinimumWidth(220)

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

    @asyncSlot()
    async def on_connect_clicked(self) -> None:
        if self._ws_task and not self._ws_task.done():
            return
        lic = self.license_key.text().strip()
        if not lic:
            return

        cfg = WsConfig(url=self.ws_url.text().strip(), license_key=lic)
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

