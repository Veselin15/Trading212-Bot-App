"""Right-hand activity log panel."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from .widgets import callout, section_title

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_log_panel(win: MainWindow) -> QWidget:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    head = QHBoxLayout()
    head.setContentsMargins(0, 0, 0, 0)
    head.setSpacing(6)
    head.addWidget(section_title("What happened"))
    head.addStretch(1)

    clear_btn = QPushButton("Clear")
    clear_btn.setObjectName("GhostBtn")
    clear_btn.setFixedWidth(70)
    clear_btn.setToolTip("Clears this log view only — nothing is deleted on the server.")
    clear_btn.clicked.connect(win.event_log.clear)  # type: ignore[arg-type]
    head.addWidget(clear_btn)

    layout.addLayout(head)
    layout.addWidget(
        callout(
            "Messages about connecting, saving keys, and trading signals show up here. "
            "Green = success, yellow = warning, red = problem.",
            kind="info",
        )
    )
    layout.addWidget(win.event_log, 1)
    return w
