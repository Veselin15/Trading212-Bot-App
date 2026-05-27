"""Trades / signal queue tab."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .widgets import callout, hint, section_title

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_trades_tab(win: MainWindow) -> QWidget:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(16, 16, 16, 12)
    layout.setSpacing(12)
    layout.addWidget(
        callout(
            "Every signal from the bot appears here. In Demo mode nothing is bought or sold — "
            "check What happened on the right for details.",
            kind="info",
        )
    )
    layout.addWidget(section_title("Signal queue"))
    layout.addWidget(hint("Newest signals appear at the top."))
    layout.addWidget(win.exec_queue, 1)
    return w
