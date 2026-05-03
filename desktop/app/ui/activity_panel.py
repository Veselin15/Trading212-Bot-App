"""Markets & bot activity tab (tables + filter)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .widgets import divider, hint, section_title

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_activity_tab(win: MainWindow) -> QWidget:
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(12, 12, 12, 10)
    layout.setSpacing(10)

    filt_row = QHBoxLayout()
    filt_row.setSpacing(8)
    filt_row.addWidget(QLabel("Filter:"))
    filt_row.addWidget(win.activity_symbol_filter, 1)
    layout.addLayout(filt_row)

    layout.addWidget(divider())

    v_split = QSplitter(Qt.Orientation.Vertical)

    p_market = QWidget()
    lm = QVBoxLayout(p_market)
    lm.setContentsMargins(0, 0, 0, 0)
    lm.setSpacing(6)
    lm.addWidget(section_title("Market hours  (from Trading212)"))
    lm.addWidget(win.market_table, 1)
    v_split.addWidget(p_market)

    p_bot = QWidget()
    lb = QVBoxLayout(p_bot)
    lb.setContentsMargins(0, 0, 0, 0)
    lb.setSpacing(4)
    lb.addWidget(section_title("Bot state  (per symbol, latest snapshot)"))
    lb.addWidget(
        hint(
            "When the exchange is closed and the server has no cached price bars yet, "
            "you will see ready=False and reason like market_closed_no_cache — that is expected. "
            "After a session with data, cached bars allow richer fields even off-hours.",
        ),
    )
    lb.addWidget(win.bot_table, 1)
    v_split.addWidget(p_bot)

    p_sig = QWidget()
    ls = QVBoxLayout(p_sig)
    ls.setContentsMargins(0, 0, 0, 0)
    ls.setSpacing(6)
    ls.addWidget(section_title("Recent signals  (newest first)"))
    ls.addWidget(win.signals_table, 1)
    v_split.addWidget(p_sig)

    v_split.setStretchFactor(0, 1)
    v_split.setStretchFactor(1, 2)
    v_split.setStretchFactor(2, 2)
    v_split.setSizes([140, 220, 200])
    layout.addWidget(v_split, 1)
    return w
