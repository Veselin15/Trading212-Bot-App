"""Consolidated plain-English status pill for the top bar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class NavStatusPill(QFrame):
    """Single readable status line — replaces scattered broker/license labels."""

    _LABELS: dict[str, tuple[str, str]] = {
        "setup": ("Setup not complete", "setup"),
        "ready": ("Ready — click Connect", "ready"),
        "connecting": ("Connecting to server…", "connecting"),
        "online_demo": ("Online · Demo mode (safe)", "online"),
        "online_live": ("Online · Real money trading ON", "live"),
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("NavStatusPill")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 4, 12, 4)
        row.setSpacing(6)
        self._dot = QLabel("●")
        self._dot.setObjectName("NavStatusDot")
        self._dot.setFixedWidth(14)
        self._label = QLabel("Setup needed")
        self._label.setObjectName("NavStatusText")
        row.addWidget(self._dot)
        row.addWidget(self._label)
        self.set_kind("setup")

    def set_kind(self, kind: str, text: str = "") -> None:
        if kind == "custom" and text:
            label, kind_key = text, "ready"
        elif kind in self._LABELS:
            label, kind_key = self._LABELS[kind]
        else:
            label, kind_key = text or kind, "setup"
        self._label.setText(label)
        self.setProperty("statusKind", kind_key)
        self._dot.setProperty("statusKind", kind_key)
        for w in (self, self._dot):
            w.style().unpolish(w)
            w.style().polish(w)
