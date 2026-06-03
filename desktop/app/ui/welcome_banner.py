"""Dismissible first-run welcome banner for the Setup tab.

Replaces the old modal QMessageBox welcome — inline, non-blocking, and
test-safe (no ``exec()``). Emits :pysig:`dismissed` when the user closes it
so the parent can persist ``seen_welcome``.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class WelcomeBanner(QFrame):
    """A friendly one-time intro shown above the setup steps."""

    dismissed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("WelcomeBanner")

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 12, 14)
        row.setSpacing(14)

        icon = QLabel("👋")
        icon.setObjectName("WelcomeBannerIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        icon.setFixedWidth(30)
        row.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        title = QLabel("Welcome to SwiftTrade")
        title.setObjectName("WelcomeBannerTitle")
        body = QLabel(
            "Set up in 3 quick steps below. You'll start in <b>Demo mode</b> — trades go to a "
            "practice account, so no real money is ever at risk while you learn the ropes."
        )
        body.setObjectName("WelcomeBannerBody")
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        text_col.addWidget(title)
        text_col.addWidget(body)
        row.addLayout(text_col, 1)

        self._dismiss_btn = QPushButton("Got it")
        self._dismiss_btn.setObjectName("SecondaryBtn")
        self._dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dismiss_btn.setToolTip("Hide this welcome message")
        self._dismiss_btn.clicked.connect(self._on_dismiss)  # type: ignore[arg-type]
        row.addWidget(self._dismiss_btn, alignment=Qt.AlignmentFlag.AlignTop)

    def _on_dismiss(self) -> None:
        self.hide()
        self.dismissed.emit()
