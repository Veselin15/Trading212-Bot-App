"""Setup tab layout (license, T212 keys, execution hints)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .setup_checklist import SetupChecklist
from .setup_step_card import SetupStepCard
from .welcome_banner import WelcomeBanner
from .widgets import field_label, hint, instruction_steps

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

    # ── First-run welcome banner (dismissible) ──────────────────────
    win._welcome_banner = WelcomeBanner()
    win._welcome_banner.dismissed.connect(win._on_welcome_dismissed)  # type: ignore[arg-type]
    win._welcome_banner.hide()  # main window reveals it on first run
    layout.addWidget(win._welcome_banner)

    # ── Step 1: License ─────────────────────────────────────────────
    win._setup_step1 = SetupStepCard(
        1,
        "License key",
        "Optional — free plan users can skip this step entirely.",
    )
    s1 = win._setup_step1.body_layout()
    s1.addWidget(
        instruction_steps([
            "Visit swifttrade.app and log in to your dashboard to find your license key.",
            "Paste the key into the field below, then click Check license to activate Pro features.",
        ])
    )
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
        "Trading212 API Keys",
        "Two separate accounts in Trading212 — each needs its own API key.",
    )
    s2 = win._setup_step2.body_layout()
    s2.addWidget(hint(
        "Your keys are stored encrypted on this computer only. They are never sent to SwiftTrade servers."
    ))
    s2.addWidget(win._broker_keys_hint)

    # ─── Helper: build an account section header row ──────────────
    def _make_section_header(
        badge_text: str,
        badge_kind: str,
        title: str,
        url: str,
        *,
        pro_badge: bool = False,
    ) -> QFrame:
        header = QFrame()
        header.setObjectName("AccountSectionHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(8)

        badge = QLabel(badge_text)
        badge.setObjectName("AccountBadge")
        badge.setProperty("badgeKind", badge_kind)
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        row.addWidget(badge)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("AccountSectionTitle")
        row.addWidget(title_lbl)

        dot = QLabel("·")
        dot.setObjectName("AccountUrl")
        row.addWidget(dot)

        url_lbl = QLabel(url)
        url_lbl.setObjectName("AccountUrl")
        row.addWidget(url_lbl)

        row.addStretch(1)

        if pro_badge:
            pro = QLabel("PRO")
            pro.setObjectName("AccountBadge")
            pro.setProperty("badgeKind", "pro")
            pro.style().unpolish(pro)
            pro.style().polish(pro)
            row.addWidget(pro)

        return header

    # ─── Practice (Demo) Account ─────────────────────────────────
    demo_box = QFrame()
    demo_box.setObjectName("DemoKeyBox")
    demo_outer = QVBoxLayout(demo_box)
    demo_outer.setContentsMargins(0, 0, 0, 0)
    demo_outer.setSpacing(0)
    demo_outer.addWidget(_make_section_header("DEMO", "demo", "Practice account", "demo.trading212.com"))

    demo_body_w = QWidget()
    demo_body = QVBoxLayout(demo_body_w)
    demo_body.setContentsMargins(16, 12, 16, 14)
    demo_body.setSpacing(10)
    demo_body.addWidget(instruction_steps([
        "In the Trading212 app, make sure you are on the Practice account (not Invest/ISA)."
        "  Go to Settings \u2192 API \u2192 Generate key.",
        "Copy the key and paste it below, then click Save.",
    ]))
    demo_body.addWidget(field_label("API key"))
    demo_body.addWidget(win.practice_t212_api_key)
    _demo_warn = hint("Practice account key only \u2014 do NOT paste a real-money (Invest) key here.")
    _demo_warn.setStyleSheet(
        "color: #f59e0b; font-size: 7.5pt; background: transparent; padding: 0; margin: 0;"
    )
    demo_body.addWidget(_demo_warn)
    demo_body.addWidget(field_label("API secret (optional \u2014 leave blank if none)"))
    demo_body.addWidget(win.practice_t212_secret_key)
    pr_row = QHBoxLayout()
    pr_row.setSpacing(10)
    win.save_practice_keys_btn.setMinimumWidth(140)
    win.test_t212_practice_btn.setMinimumWidth(130)
    pr_row.addWidget(win.save_practice_keys_btn)
    pr_row.addWidget(win.test_t212_practice_btn)
    pr_row.addStretch(1)
    demo_body.addLayout(pr_row)
    demo_outer.addWidget(demo_body_w)
    s2.addWidget(demo_box)

    # ─── Real-Money (Live) Account ───────────────────────────────
    win._live_key_box = QFrame()
    win._live_key_box.setObjectName("LiveKeyBox")
    win._live_key_box.setProperty("locked", "true")
    live_outer = QVBoxLayout(win._live_key_box)
    live_outer.setContentsMargins(0, 0, 0, 0)
    live_outer.setSpacing(0)
    live_outer.addWidget(
        _make_section_header("LIVE", "live", "Real-money account", "live.trading212.com", pro_badge=True)
    )

    # Lock message — shown when tier is free
    win._live_key_lock_msg = QWidget()
    lock_layout = QVBoxLayout(win._live_key_lock_msg)
    lock_layout.setContentsMargins(16, 14, 16, 14)
    lock_lbl = QLabel(
        "Real-money trading requires an active Pro subscription.\n\n"
        "Upgrade at swifttrade.app — once your Pro license is confirmed in Step 1, "
        "this section unlocks automatically."
    )
    lock_lbl.setObjectName("LiveKeyLockMsg")
    lock_lbl.setWordWrap(True)
    lock_layout.addWidget(lock_lbl)
    live_outer.addWidget(win._live_key_lock_msg)

    # Fields — shown when tier is pro
    win._live_key_fields = QWidget()
    live_fields = QVBoxLayout(win._live_key_fields)
    live_fields.setContentsMargins(16, 12, 16, 14)
    live_fields.setSpacing(10)
    live_fields.addWidget(instruction_steps([
        "In the Trading212 app, switch to your real Invest or ISA account."
        "  Go to Settings \u2192 API \u2192 Generate key.",
        "Copy the key and paste it below, then click Save.",
    ]))
    live_fields.addWidget(field_label("API key"))
    live_fields.addWidget(win.live_t212_api_key)
    live_fields.addWidget(field_label("API secret (optional \u2014 leave blank if none)"))
    live_fields.addWidget(win.live_t212_secret_key)
    lv_row = QHBoxLayout()
    lv_row.setSpacing(10)
    lv_row.addWidget(win.save_live_keys_btn)
    lv_row.addWidget(win.test_t212_live_btn)
    lv_row.addStretch(1)
    live_fields.addLayout(lv_row)
    win._live_key_fields.setVisible(False)
    live_outer.addWidget(win._live_key_fields)
    s2.addWidget(win._live_key_box)

    reveal_row = QHBoxLayout()
    reveal_row.addWidget(win.show_t212_secrets)
    reveal_row.addStretch(1)
    s2.addLayout(reveal_row)

    layout.addWidget(win._setup_step2)

    # ── Step 3: Connect ─────────────────────────────────────────────
    win._setup_step3 = SetupStepCard(
        3,
        "Connect to the signal server",
        "The bot will start receiving trading signals once connected.",
    )
    s3 = win._setup_step3.body_layout()
    s3.addWidget(
        instruction_steps([
            "Leave the server address as is — the default is correct for most users.",
            "Click the Connect button below and wait a few seconds. The dot at the top of the window will turn green when you are online.",
        ])
    )
    s3.addWidget(field_label("Server address"))
    s3.addWidget(win.ws_url)
    s3.addWidget(hint("Only change this if the SwiftTrade support team gives you a different address."))
    s3.addWidget(win._setup_trading_mode_hint)

    connect_row = QHBoxLayout()
    connect_row.setSpacing(12)
    win.setup_connect_btn = QPushButton("Connect to SwiftTrade")
    win.setup_connect_btn.setObjectName("HeroBtn")
    win.setup_connect_btn.setMinimumHeight(44)
    win.setup_connect_btn.setMinimumWidth(160)
    win.setup_connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    win.setup_connect_btn.clicked.connect(win.on_connect_clicked)  # type: ignore[arg-type]
    connect_row.addWidget(win.setup_connect_btn)
    win.setup_disconnect_btn = QPushButton("Disconnect")
    win.setup_disconnect_btn.setObjectName("SecondaryBtn")
    win.setup_disconnect_btn.setMinimumHeight(44)
    win.setup_disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    win.setup_disconnect_btn.hide()
    win.setup_disconnect_btn.clicked.connect(win.on_disconnect_clicked)  # type: ignore[arg-type]
    connect_row.addWidget(win.setup_disconnect_btn)
    connect_row.addStretch(1)
    s3.addLayout(connect_row)

    legal_notice = QLabel(
        'By connecting you agree to the '
        '<a href="https://swifttrade.app/legal/terms">Terms of Service</a> and '
        '<a href="https://swifttrade.app/legal/risk">Risk Disclosure</a>. '
        'Trading involves risk of loss. API keys stay on your device only.'
    )
    legal_notice.setObjectName("LegalNotice")
    legal_notice.setOpenExternalLinks(True)
    legal_notice.setWordWrap(True)
    s3.addWidget(legal_notice)
    layout.addWidget(win._setup_step3)

    # ── Troubleshooting (collapsed) ─────────────────────────────────
    win._advanced_toggle = QPushButton("▸  Having trouble connecting?")
    win._advanced_toggle.setObjectName("GhostBtn")
    win._advanced_toggle.setCheckable(True)
    win._advanced_toggle.setChecked(False)
    win._advanced_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
    layout.addWidget(win._advanced_toggle, alignment=Qt.AlignmentFlag.AlignLeft)

    win._advanced_panel = QWidget()
    adv = QVBoxLayout(win._advanced_panel)
    adv.setContentsMargins(0, 0, 0, 0)
    win._advanced_panel.setVisible(False)
    win.diagnostics_btn = QPushButton("Open health check")
    win.diagnostics_btn.setObjectName("GhostBtn")
    win.diagnostics_btn.clicked.connect(win._open_backend_diagnostics)  # type: ignore[arg-type]
    adv.addWidget(win.diagnostics_btn, alignment=Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(win._advanced_panel)

    def _toggle_advanced(checked: bool) -> None:
        win._advanced_panel.setVisible(checked)
        win._advanced_toggle.setText(
            "▾  Having trouble connecting?" if checked else "▸  Having trouble connecting?"
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
