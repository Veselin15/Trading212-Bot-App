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

from .widgets import attach_empty_overlay, callout, field_label, hint, section_title

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_activity_tab(win: MainWindow) -> QWidget:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(16, 16, 16, 12)
    layout.setSpacing(12)

    layout.addWidget(
        callout(
            "This tab updates in real time once you are connected. "
            "You can see which stock markets are currently open, what the bot is monitoring, "
            "and any buy or sell signals as they arrive.",
            kind="info",
        )
    )

    filt_row = QHBoxLayout()
    filt_row.setSpacing(8)
    filt_row.addWidget(field_label("Filter by stock symbol:"))
    filt_row.addWidget(win.activity_symbol_filter, 1)
    layout.addLayout(filt_row)

    v_split = QSplitter(Qt.Orientation.Vertical)

    p_market = QWidget()
    lm = QVBoxLayout(p_market)
    lm.setContentsMargins(0, 0, 0, 0)
    lm.setSpacing(6)
    lm.addWidget(section_title("Market hours"))
    lm.addWidget(hint("Shows whether each stock exchange is currently open or closed. Data comes from Trading212."))
    lm.addWidget(win.market_table, 1)
    v_split.addWidget(p_market)

    p_bot = QWidget()
    lb = QVBoxLayout(p_bot)
    lb.setContentsMargins(0, 0, 0, 0)
    lb.setSpacing(4)
    lb.addWidget(section_title("Bot status per stock"))
    lb.addWidget(
        hint(
            "Shows exactly what the bot is doing for each stock right now. "
            "Rows showing 'not ready' when markets are closed is completely normal."
        ),
    )
    lb.addWidget(win.bot_table, 1)
    v_split.addWidget(p_bot)

    p_sig = QWidget()
    ls = QVBoxLayout(p_sig)
    ls.setContentsMargins(0, 0, 0, 0)
    ls.setSpacing(6)
    ls.addWidget(section_title("Recent signals"))
    ls.addWidget(hint("The latest buy and sell recommendations from SwiftTrade AI, newest at the top."))
    ls.addWidget(win.signals_table, 1)
    v_split.addWidget(p_sig)

    v_split.setStretchFactor(0, 1)
    v_split.setStretchFactor(1, 2)
    v_split.setStretchFactor(2, 2)
    v_split.setSizes([140, 220, 200])
    layout.addWidget(v_split, 1)

    # Friendly empty states while disconnected / before data arrives.
    attach_empty_overlay(win.market_table, "Connect to see which markets are open.")
    attach_empty_overlay(win.bot_table, "Bot activity appears here once you're connected.")
    attach_empty_overlay(win.signals_table, "No signals yet — they'll show up here in real time.")
    return w
