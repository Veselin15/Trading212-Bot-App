"""Trades / signal queue tab."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .widgets import hint, section_title

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_trades_tab(win: MainWindow) -> QWidget:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(12, 12, 12, 10)
    layout.setSpacing(10)
    layout.addWidget(
        hint(
            "Every signal the SwiftTrade bot sends appears here. With live mode off, "
            "nothing is traded — check the activity log on the right for detail."
        )
    )
    layout.addWidget(section_title("Signal queue"))
    layout.addWidget(win.exec_queue, 1)
    return w
