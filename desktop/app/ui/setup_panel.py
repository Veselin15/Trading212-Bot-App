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

from .setup_checklist import SetupChecklist
from .setup_step_card import SetupStepCard
from .widgets import callout, field_label, hint, instruction_steps

if TYPE_CHECKING:
    from ..main_window import MainWindow


def build_setup_tab(win: MainWindow) -> QWidget:
    outer = QWidget()
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)

    win.setup_checklist = SetupChecklist()
    win.setup_checklist._help_btn.clicked.connect(win._show_quick_tips)  # type: ignore[arg-type]
    outer_layout.addWidget(win.setup_checklist)

    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(18, 14, 18, 18)
    layout.setSpacing(14)

    # ── Step 1: License ─────────────────────────────────────────────
    win._setup_step1 = SetupStepCard(
        1,
        "Pro license key (optional)",
        "Skip this for free paper trading. Add a key only when you subscribe to Pro.",
    )
    s1 = win._setup_step1.body_layout()
    s1.addWidget(
        instruction_steps([
            "Free users: leave this blank — connect with your Trading212 demo keys only.",
            "Pro users: sign in at swifttrade.io, open Dashboard, and copy your license key.",
            "Paste the key below and click Check license to unlock real-money trading.",
        ])
    )
    s1.addWidget(field_label("Your license key"))
    lic_row = QHBoxLayout()
    lic_row.setSpacing(10)
    lic_row.addWidget(win.license_key, 1)
    lic_row.addWidget(win.validate_btn)
    s1.addLayout(lic_row)
    s1.addWidget(win.tier_status_label)
    layout.addWidget(win._setup_step1)

    # ── Step 2: Broker keys ─────────────────────────────────────────
    win._setup_step2 = SetupStepCard(
        2,
        "Connect your Trading212 demo account",
        "Use a demo (practice) key first — no real money involved.",
    )
    s2 = win._setup_step2.body_layout()
    s2.addWidget(
        callout(
            "Your API keys stay on this computer only. SwiftTrade never sees them. "
            "Start with a demo key so you can watch signals safely before trading real money.",
            kind="info",
        )
    )
    s2.addWidget(
        instruction_steps([
            "Open the Trading212 app on your phone (or their website).",
            "Go to Settings → API (sometimes called 'API Key' or 'Developer').",
            "Create a new API key for your Demo / Practice account.",
            "Paste the key below and click Save demo keys.",
        ])
    )
    s2.addWidget(win._broker_keys_hint)

    demo_box = QFrame()
    demo_box.setObjectName("DemoKeyBox")
    demo_layout = QVBoxLayout(demo_box)
    demo_layout.setContentsMargins(16, 14, 16, 14)
    demo_layout.setSpacing(10)
    demo_layout.addWidget(field_label("Demo API key"))
    demo_layout.addWidget(win.practice_t212_api_key)
    demo_layout.addWidget(field_label("Secret (optional — leave blank if you only got one code)"))
    demo_layout.addWidget(win.practice_t212_secret_key)
    pr_row = QHBoxLayout()
    pr_row.setSpacing(10)
    win.save_practice_keys_btn.setMinimumWidth(140)
    win.test_t212_practice_btn.setMinimumWidth(130)
    pr_row.addWidget(win.save_practice_keys_btn)
    pr_row.addWidget(win.test_t212_practice_btn)
    pr_row.addStretch(1)
    demo_layout.addLayout(pr_row)
    s2.addWidget(demo_box)

    win._real_money_toggle = QPushButton("▸  I have Pro and want to add real-money keys")
    win._real_money_toggle.setObjectName("GhostBtn")
    win._real_money_toggle.setCheckable(True)
    win._real_money_toggle.setChecked(False)
    s2.addWidget(win._real_money_toggle, alignment=Qt.AlignmentFlag.AlignLeft)

    win._real_money_panel = QWidget()
    rm = QVBoxLayout(win._real_money_panel)
    rm.setContentsMargins(0, 0, 0, 0)
    rm.setSpacing(10)
    win._real_money_panel.setVisible(False)
    rm.addWidget(
        callout(
            "Only add these if you have a Pro subscription and want real trades. "
            "You can always do this later.",
            kind="warn",
        )
    )
    rm.addWidget(field_label("Real-money API key"))
    rm.addWidget(win.live_t212_api_key)
    rm.addWidget(field_label("Secret (optional)"))
    rm.addWidget(win.live_t212_secret_key)
    lv_row = QHBoxLayout()
    lv_row.setSpacing(10)
    lv_row.addWidget(win.save_live_keys_btn)
    lv_row.addWidget(win.test_t212_live_btn)
    lv_row.addStretch(1)
    rm.addLayout(lv_row)
    s2.addWidget(win._real_money_panel)

    reveal_row = QHBoxLayout()
    reveal_row.addWidget(win.show_t212_secrets)
    reveal_row.addStretch(1)
    s2.addLayout(reveal_row)

    def _toggle_real_money(checked: bool) -> None:
        win._real_money_panel.setVisible(checked)
        win._real_money_toggle.setText(
            "▾  Real-money keys (Pro only)" if checked else "▸  I have Pro and want to add real-money keys"
        )

    win._real_money_toggle.toggled.connect(_toggle_real_money)  # type: ignore[arg-type]
    layout.addWidget(win._setup_step2)

    # ── Step 3: Connect ─────────────────────────────────────────────
    win._setup_step3 = SetupStepCard(
        3,
        "Connect to SwiftTrade",
        "Link this app to the signal server — takes a few seconds.",
    )
    s3 = win._setup_step3.body_layout()
    s3.addWidget(
        instruction_steps([
            "Add your Trading212 practice API key in Step 2 (or skip Step 1 if you are on the free plan).",
            "Click the green Connect button below (or in the top bar).",
            "Wait until the status dot at the top turns green and says Connected.",
            "Demo mode (default) sends orders to your practice account when signals arrive.",
        ])
    )
    s3.addWidget(win._setup_trading_mode_hint)

    connect_row = QHBoxLayout()
    connect_row.setSpacing(12)
    win.setup_connect_btn = QPushButton("  Connect to SwiftTrade  ")
    win.setup_connect_btn.setObjectName("HeroBtn")
    win.setup_connect_btn.setMinimumHeight(44)
    win.setup_connect_btn.setMinimumWidth(220)
    win.setup_connect_btn.clicked.connect(win.on_connect_clicked)  # type: ignore[arg-type]
    connect_row.addWidget(win.setup_connect_btn)
    win.setup_disconnect_btn = QPushButton("Disconnect")
    win.setup_disconnect_btn.setObjectName("SecondaryBtn")
    win.setup_disconnect_btn.setMinimumHeight(44)
    win.setup_disconnect_btn.hide()
    win.setup_disconnect_btn.clicked.connect(win.on_disconnect_clicked)  # type: ignore[arg-type]
    connect_row.addWidget(win.setup_disconnect_btn)
    connect_row.addStretch(1)
    s3.addLayout(connect_row)

    s3.addWidget(
        callout(
            "Demo mode (top bar): orders go to your Trading212 practice account.\n"
            "Real trades (Pro only): orders go to your real-money account.",
            kind="info",
        )
    )
    layout.addWidget(win._setup_step3)

    # ── Advanced (collapsed) ──────────────────────────────────────────
    win._advanced_toggle = QPushButton("▸  Advanced / troubleshooting")
    win._advanced_toggle.setObjectName("GhostBtn")
    win._advanced_toggle.setCheckable(True)
    win._advanced_toggle.setChecked(False)
    layout.addWidget(win._advanced_toggle, alignment=Qt.AlignmentFlag.AlignLeft)

    win._advanced_panel = QWidget()
    adv = QVBoxLayout(win._advanced_panel)
    adv.setContentsMargins(0, 0, 0, 0)
    adv.setSpacing(16)
    win._advanced_panel.setVisible(False)

    grp_server = QGroupBox("Bot server address")
    sg = QVBoxLayout(grp_server)
    sg.setSpacing(8)
    sg.addWidget(hint("Leave the default unless SwiftTrade support gave you a different address."))
    sg.addWidget(win.ws_url)
    adv.addWidget(grp_server)

    grp_diag = QGroupBox("Troubleshooting")
    dg = QVBoxLayout(grp_diag)
    dg.setSpacing(8)
    dg.addWidget(hint("Opens a health-check page in your browser if the app cannot reach the backend."))
    win.diagnostics_btn = QPushButton("Open backend health check")
    win.diagnostics_btn.setObjectName("GhostBtn")
    win.diagnostics_btn.clicked.connect(win._open_backend_diagnostics)  # type: ignore[arg-type]
    dg.addWidget(win.diagnostics_btn, alignment=Qt.AlignmentFlag.AlignLeft)
    adv.addWidget(grp_diag)
    layout.addWidget(win._advanced_panel)

    def _toggle_advanced(checked: bool) -> None:
        win._advanced_panel.setVisible(checked)
        win._advanced_toggle.setText(
            "▾  Advanced / troubleshooting" if checked else "▸  Advanced / troubleshooting"
        )

    win._advanced_toggle.toggled.connect(_toggle_advanced)  # type: ignore[arg-type]

    layout.addStretch(1)

    win._setup_scroll = QScrollArea()
    win._setup_scroll.setWidget(inner)
    win._setup_scroll.setWidgetResizable(True)
    win._setup_scroll.setFrameShape(QFrame.Shape.NoFrame)
    win._setup_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    outer_layout.addWidget(win._setup_scroll, 1)

    return outer
