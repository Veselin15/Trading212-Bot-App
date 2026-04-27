from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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
        self.setMinimumWidth(520)

        self._store = CryptoStore(Path.home() / ".t212_executor")
        self._ws_task: asyncio.Task | None = None
        self._ws_client: ExecWsClient | None = None

        self.status_dot = QLabel("●")
        self.status_dot.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("Offline")

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

        top = QHBoxLayout()
        top.addWidget(self.status_dot)
        top.addWidget(self.status_label)
        top.addStretch(1)

        form = QFormLayout()
        form.addRow("Server WS URL", self.ws_url)
        form.addRow("License key", self.license_key)
        form.addRow("T212 API key", self.t212_api_key)
        form.addRow("T212 secret key", self.t212_secret_key)

        btns = QHBoxLayout()
        btns.addWidget(self.save_btn)
        btns.addStretch(1)
        btns.addWidget(self.connect_btn)
        btns.addWidget(self.disconnect_btn)

        root = QVBoxLayout()
        root.addLayout(top)
        root.addSpacing(8)
        root.addLayout(form)
        root.addSpacing(8)
        root.addLayout(btns)

        self.setLayout(root)
        self._set_status("OFFLINE")

        existing = self._store.load()
        if existing:
            self.t212_api_key.setText(existing.t212_api_key)
            self.t212_secret_key.setText(existing.t212_secret_key or "")

    def _set_status(self, status: str) -> None:
        text, color = _status_text(status)
        self.status_label.setText(text)
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 20px;")

    def _on_ws_status(self, status: str) -> None:
        self._set_status(status)

    async def _handle_signal(self, payload: dict) -> None:
        # Placeholder: real execution + position management will be wired next.
        # For now, we just acknowledge the pipeline by printing.
        print("SIGNAL:", payload)

    @asyncSlot()
    async def on_connect_clicked(self) -> None:
        if self._ws_task and not self._ws_task.done():
            return
        lic = self.license_key.text().strip()
        if not lic:
            return

        cfg = WsConfig(url=self.ws_url.text().strip(), license_key=lic)
        self._ws_client = ExecWsClient(cfg=cfg, on_status=self._on_ws_status, on_signal=self._handle_signal)
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
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

    def on_save_clicked(self) -> None:
        payload = SecretPayload(
            t212_api_key=self.t212_api_key.text().strip(),
            t212_secret_key=(self.t212_secret_key.text().strip() or None),
        )
        if payload.t212_api_key:
            self._store.save(payload)


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

