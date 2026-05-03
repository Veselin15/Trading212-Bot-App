"""Right-hand activity log panel."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from .widgets import section_title

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_log_panel(win: MainWindow) -> QWidget:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    head = QHBoxLayout()
    head.setContentsMargins(0, 0, 0, 0)
    head.setSpacing(6)
    head.addWidget(section_title("Activity log"))
    head.addStretch(1)

    clear_btn = QPushButton("Clear")
    clear_btn.setObjectName("GhostBtn")
    clear_btn.setFixedWidth(70)
    clear_btn.setToolTip("Clears this log view only — the server is not affected.")
    clear_btn.clicked.connect(win.event_log.clear)  # type: ignore[arg-type]
    head.addWidget(clear_btn)

    layout.addLayout(head)
    layout.addWidget(win.event_log, 1)
    return w
