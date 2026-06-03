"""Consolidated plain-English status pill for the top bar."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel


class NavStatusPill(QFrame):
    """Single readable status line — replaces scattered broker/license labels.

    The status dot gently pulses while connecting and once online, giving the
    bar a live, "something is happening" feel without being distracting.
    """

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

        # Pulse animation on the dot's opacity.
        self._dot_effect = QGraphicsOpacityEffect(self._dot)
        self._dot_effect.setOpacity(1.0)
        self._dot.setGraphicsEffect(self._dot_effect)
        self._pulse = QPropertyAnimation(self._dot_effect, b"opacity", self)
        self._pulse.setStartValue(1.0)
        self._pulse.setKeyValueAt(0.5, 0.25)
        self._pulse.setEndValue(1.0)
        self._pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse.setLoopCount(-1)

        self.set_kind("setup")

    def _set_pulse(self, active: bool, period_ms: int = 1400) -> None:
        if active:
            self._pulse.setDuration(period_ms)
            if self._pulse.state() != QPropertyAnimation.State.Running:
                self._pulse.start()
        else:
            self._pulse.stop()
            self._dot_effect.setOpacity(1.0)

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

        # Fast attention pulse while connecting; slow, calm pulse once live.
        if kind_key == "connecting":
            self._set_pulse(True, 750)
        elif kind_key in ("online", "live"):
            self._set_pulse(True, 1700)
        else:
            self._set_pulse(False)
