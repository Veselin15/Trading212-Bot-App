"""Markets & bot activity tab (tables + filter)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .widgets import callout, field_label, hint, section_title

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_activity_tab(win: MainWindow) -> QWidget:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(16, 16, 16, 12)
    layout.setSpacing(12)

    layout.addWidget(
        callout(
            "This tab fills in after you connect. You'll see which markets are open, "
            "what the bot is watching, and any trading signals as they arrive.",
            kind="info",
        )
    )

    filt_row = QHBoxLayout()
    filt_row.setSpacing(8)
    filt_row.addWidget(field_label("Search by stock symbol"))
    filt_row.addWidget(win.activity_symbol_filter, 1)
    layout.addLayout(filt_row)

    v_split = QSplitter(Qt.Orientation.Vertical)

    p_market = QWidget()
    lm = QVBoxLayout(p_market)
    lm.setContentsMargins(0, 0, 0, 0)
    lm.setSpacing(6)
    lm.addWidget(section_title("Market hours"))
    lm.addWidget(hint("Whether each stock market is open right now (from Trading212)."))
    lm.addWidget(win.market_table, 1)
    v_split.addWidget(p_market)

    p_bot = QWidget()
    lb = QVBoxLayout(p_bot)
    lb.setContentsMargins(0, 0, 0, 0)
    lb.setSpacing(4)
    lb.addWidget(section_title("Bot status"))
    lb.addWidget(
        hint(
            "Shows what the bot is doing for each stock. "
            "If markets are closed, many rows will say not ready — that's normal."
        ),
    )
    lb.addWidget(win.bot_table, 1)
    v_split.addWidget(p_bot)

    p_sig = QWidget()
    ls = QVBoxLayout(p_sig)
    ls.setContentsMargins(0, 0, 0, 0)
    ls.setSpacing(6)
    ls.addWidget(section_title("Recent signals"))
    ls.addWidget(hint("Newest trading signals appear at the top."))
    ls.addWidget(win.signals_table, 1)
    v_split.addWidget(p_sig)

    v_split.setStretchFactor(0, 1)
    v_split.setStretchFactor(1, 2)
    v_split.setStretchFactor(2, 2)
    v_split.setSizes([140, 220, 200])
    layout.addWidget(v_split, 1)
    return w
