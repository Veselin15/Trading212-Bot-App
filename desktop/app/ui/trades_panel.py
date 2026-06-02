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
            "Every trading recommendation (signal) from SwiftTrade AI is listed here as it arrives. "
            "In Demo mode the bot logs what it would do but does not place real orders — "
            "check the Activity log on the right for a full breakdown.",
            kind="info",
        )
    )
    layout.addWidget(section_title("Incoming signals"))
    layout.addWidget(hint("Each row is one AI recommendation. Newest signals appear at the top of the list."))
    layout.addWidget(win.exec_queue, 1)
    return w
