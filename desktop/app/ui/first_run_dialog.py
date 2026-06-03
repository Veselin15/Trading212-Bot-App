"""First-run terms & risk acceptance dialog.

Shown once on the very first launch. The user must click Accept before the
main window opens. Declining exits the application immediately.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

_TERMS_URL = "https://swifttrade.app/legal/terms"
_RISK_URL = "https://swifttrade.app/legal/risk"
_PRIVACY_URL = "https://swifttrade.app/legal/privacy"

_BODY = (
    "<p style='margin-top:0'>"
    "Before using SwiftTrade you must read and accept the following:"
    "</p>"
    "<ul style='margin:0; padding-left:18px; line-height:1.7'>"
    "<li><b>SwiftTrade is a software tool, not a licensed investment firm</b> "
    "and does not provide investment advice.</li>"
    "<li><b>Trading in financial instruments involves substantial risk of loss.</b> "
    "You may lose all the money you invest.</li>"
    "<li>Past performance and backtested results do not guarantee future returns.</li>"
    "<li>Your Trading212 API keys are stored <b>encrypted on this device only</b> "
    "and are never transmitted to SwiftTrade servers.</li>"
    "<li>You are solely responsible for your Trading212 account and all orders "
    "placed through it.</li>"
    "<li>Only invest capital you can afford to lose entirely.</li>"
    "</ul>"
    "<p>"
    "By clicking <b>Accept</b> you confirm that you have read and agree to the "
    "<a href='" + _TERMS_URL + "'>Terms of Service</a>, "
    "<a href='" + _RISK_URL + "'>Risk Disclosure</a>, and "
    "<a href='" + _PRIVACY_URL + "'>Privacy Policy</a>."
    "</p>"
)


def run_first_run_dialog() -> bool:
    """Show the dialog and return True if the user accepted, False if declined."""
    dlg = QDialog()
    dlg.setWindowTitle("SwiftTrade — Terms & Risk Disclosure")
    dlg.setMinimumWidth(520)
    dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 20, 24, 20)
    root.setSpacing(16)

    # ── Title ────────────────────────────────────────────────────────
    title = QLabel("Please read before continuing")
    title.setObjectName("FirstRunTitle")
    root.addWidget(title)

    # ── Scrollable body ──────────────────────────────────────────────
    body_label = QLabel(_BODY)
    body_label.setObjectName("FirstRunBody")
    body_label.setWordWrap(True)
    body_label.setOpenExternalLinks(True)
    body_label.setTextFormat(Qt.TextFormat.RichText)
    body_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    scroll = QScrollArea()
    scroll.setWidget(body_label)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(scroll.Shape.NoFrame)
    scroll.setFixedHeight(260)
    root.addWidget(scroll)

    # ── Link buttons row ─────────────────────────────────────────────
    link_row = QHBoxLayout()
    link_row.setSpacing(12)
    for label, url in (
        ("Terms of Service", _TERMS_URL),
        ("Risk Disclosure", _RISK_URL),
        ("Privacy Policy", _PRIVACY_URL),
    ):
        btn = QPushButton(label)
        btn.setObjectName("GhostBtn")
        btn.setFixedHeight(28)
        btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))  # type: ignore[arg-type]
        link_row.addWidget(btn)
    link_row.addStretch(1)
    root.addLayout(link_row)

    # ── Accept / Decline ─────────────────────────────────────────────
    btn_box = QDialogButtonBox()
    accept_btn = btn_box.addButton("Accept", QDialogButtonBox.ButtonRole.AcceptRole)
    accept_btn.setObjectName("HeroBtn")
    accept_btn.setMinimumHeight(36)
    accept_btn.setMinimumWidth(100)
    decline_btn = btn_box.addButton("Decline", QDialogButtonBox.ButtonRole.RejectRole)
    decline_btn.setObjectName("SecondaryBtn")
    decline_btn.setMinimumHeight(36)
    btn_box.accepted.connect(dlg.accept)
    btn_box.rejected.connect(dlg.reject)
    root.addWidget(btn_box)

    return dlg.exec() == QDialog.DialogCode.Accepted
