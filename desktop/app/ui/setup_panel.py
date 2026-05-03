"""Setup tab layout (license, T212 keys, execution hints)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .widgets import divider, field_label, hint

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_setup_tab(win: MainWindow) -> QWidget:
    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(16)

    grp_sub = QGroupBox("License && server")
    g = QVBoxLayout(grp_sub)
    g.setSpacing(10)

    g.addWidget(field_label("License key"))
    lic_row = QHBoxLayout()
    lic_row.setSpacing(8)
    lic_row.addWidget(win.license_key, 1)
    lic_row.addWidget(win.validate_btn)
    g.addLayout(lic_row)
    g.addWidget(win.tier_status_label)
    g.addWidget(hint("Copy your key from the SwiftTrade portal, then click Validate to check your tier."))

    g.addSpacing(6)
    g.addWidget(field_label("Bot server address"))
    g.addWidget(win.ws_url)
    g.addWidget(
        hint(
            "Leave as default (ws://127.0.0.1:8010/ws/exec) if the SwiftTrade server runs on this computer."
        )
    )
    layout.addWidget(grp_sub)

    grp_keys = QGroupBox("Trading212 — Practice and Invest keys")
    k = QVBoxLayout(grp_keys)
    k.setSpacing(10)

    k.addWidget(
        hint(
            "Save both key pairs here. Whether the app uses Practice (demo) or Invest (live) follows "
            "the Paper / Live trading mode in the top bar — only one broker mode at a time."
        )
    )
    k.addWidget(win._broker_keys_hint)

    k.addWidget(divider())

    grp_pr = QGroupBox("Practice account (demo API)")
    kpr = QVBoxLayout(grp_pr)
    kpr.setSpacing(8)
    kpr.addWidget(field_label("API key"))
    kpr.addWidget(win.practice_t212_api_key)
    kpr.addWidget(field_label("API secret (optional)"))
    kpr.addWidget(win.practice_t212_secret_key)
    kpr.addWidget(win.save_practice_keys_btn, alignment=Qt.AlignmentFlag.AlignLeft)
    k.addWidget(grp_pr)

    grp_lv = QGroupBox("Real-money / Invest account (live API)")
    klv = QVBoxLayout(grp_lv)
    klv.setSpacing(8)
    klv.addWidget(field_label("API key"))
    klv.addWidget(win.live_t212_api_key)
    klv.addWidget(field_label("API secret (optional)"))
    klv.addWidget(win.live_t212_secret_key)
    klv.addWidget(win.save_live_keys_btn, alignment=Qt.AlignmentFlag.AlignLeft)
    k.addWidget(grp_lv)

    btns = QHBoxLayout()
    btns.setSpacing(10)
    btns.addWidget(win.show_t212_secrets)
    btns.addStretch(1)
    btns.addWidget(win.test_t212_practice_btn)
    btns.addWidget(win.test_t212_live_btn)
    k.addLayout(btns)
    layout.addWidget(grp_keys)

    grp_live = QGroupBox("Trade execution")
    lv = QVBoxLayout(grp_live)
    lv.setSpacing(10)
    lv.addWidget(win._setup_trading_mode_hint)
    lv.addWidget(
        hint(
            "Paper (default): signals are recorded in the log and queue — no orders are sent.\n"
            "Live: LONG signals place real market orders on your Trading212 account.\n"
            "The Paper / Live control is in the top bar; your tier is re-checked periodically against the server."
        )
    )
    layout.addWidget(grp_live)

    grp_diag = QGroupBox("Troubleshooting")
    dg = QVBoxLayout(grp_diag)
    dg.setSpacing(8)
    dg.addWidget(
        hint(
            "If the app cannot reach the SwiftTrade backend, use this to open a health check page in your browser "
            "(no secrets are shown)."
        )
    )
    win.diagnostics_btn = QPushButton("Open backend health check")
    win.diagnostics_btn.setObjectName("GhostBtn")
    win.diagnostics_btn.clicked.connect(win._open_backend_diagnostics)  # type: ignore[arg-type]
    dg.addWidget(win.diagnostics_btn, alignment=Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(grp_diag)

    layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidget(inner)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    outer = QWidget()
    QVBoxLayout(outer).addWidget(scroll)
    outer.layout().setContentsMargins(0, 0, 0, 0)  # type: ignore[union-attr]
    return outer
