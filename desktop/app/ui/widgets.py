"""Small Qt widget factories for tab layouts."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel

from .theme import _BORDER, _DANGER, _MUTED, _SUCCESS, _TEXT, _WARN


def field_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("FieldLabel")
    return lab


def hint(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("HintLabel")
    lab.setWordWrap(True)
    return lab


def section_title(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("SectionTitle")
    f = lab.font()
    f.setBold(True)
    lab.setFont(f)
    return lab


def divider() -> QFrame:
    d = QFrame()
    d.setFrameShape(QFrame.Shape.HLine)
    d.setStyleSheet(f"color: {_BORDER}; background: {_BORDER}; max-height: 1px; border: none;")
    return d


def status_text(status: str) -> tuple[str, str]:
    if status == "ONLINE":
        return ("Connected", _SUCCESS)
    if status == "CONNECTING":
        return ("Connecting…", _WARN)
    return ("Not connected", _DANGER)
