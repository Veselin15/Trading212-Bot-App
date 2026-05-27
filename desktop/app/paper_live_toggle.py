from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

# SwiftTrade dark palette (kept local so this widget stays self-contained)
_BG_RAIL = "#1c1c25"
_BORDER = "#3a3a4e"
_TEXT = "#f1f1f3"
_MUTED = "#6b7280"
_EMERALD = "#10b981"
_EMERALD_HOVER = "#34d399"
_EMERALD_DIM = "#064e3b"
_WARN = "#f59e0b"
_WARN_DIM = "#78350f"
_DANGER = "#ef4444"
_DANGER_DIM = "#7f1d1d"


class PaperLiveToggle(QWidget):
    """
    Segmented control: Paper trading vs Live trading.
    Live side stays disabled until Pro tier is unlocked by the parent window.
    """

    mode_changed = Signal(bool)  # True = live trading, False = paper
    live_enable_requested = Signal()  # user clicked Live — parent runs confirm dialog, then set_live(True)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._live = False
        self._pro_unlocked = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(1)

        cap = QLabel("Order mode")
        cap.setStyleSheet(f"color: {_MUTED}; font-size: 7.5pt; background: transparent;")
        outer.addWidget(cap)

        rail = QFrame()
        rail.setObjectName("TradingModeRail")
        rail.setStyleSheet(
            f"QFrame#TradingModeRail {{"
            f" background-color: {_BG_RAIL};"
            f" border: 1px solid {_BORDER};"
            f" border-radius: 8px;"
            f" padding: 2px;"
            f"}}"
        )
        row = QHBoxLayout(rail)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(4)

        self._paper_btn = QPushButton("  Demo mode  ")
        self._paper_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._paper_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._paper_btn.setMinimumHeight(26)
        self._paper_btn.setToolTip(
            "Place orders on your Trading212 practice account when signals arrive."
        )
        self._paper_btn.clicked.connect(self._on_paper_clicked)  # type: ignore[arg-type]

        self._live_btn = QPushButton("  Real trades  ")
        self._live_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._live_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._live_btn.setMinimumHeight(26)
        self._live_btn.setToolTip(
            "Place real market orders on your Trading212 account when signals arrive (Pro required)."
        )
        self._live_btn.clicked.connect(self._on_live_clicked)  # type: ignore[arg-type]

        row.addWidget(self._paper_btn)
        row.addWidget(self._live_btn)
        outer.addWidget(rail)

        self.setMinimumWidth(240)
        self.setMaximumWidth(320)
        self._refresh_styles()

    def is_live(self) -> bool:
        return self._live

    def set_pro_unlocked(self, unlocked: bool) -> None:
        """Pro tier validated — allow switching to Live. Otherwise force Paper and lock Live."""
        self._pro_unlocked = unlocked
        if not unlocked and self._live:
            self._set_live_internal(False, emit=True)
        self._live_btn.setEnabled(unlocked)
        self._refresh_styles()

    def set_live(self, live: bool) -> None:
        """Programmatically set mode (e.g. after parent confirms Live). Emits mode_changed if changed."""
        if live and not self._pro_unlocked:
            return
        self._set_live_internal(live, emit=True)

    def _set_live_internal(self, live: bool, *, emit: bool) -> None:
        if self._live == live:
            self._refresh_styles()
            return
        self._live = live
        self._refresh_styles()
        if emit:
            self.mode_changed.emit(live)

    def _on_paper_clicked(self) -> None:
        self._set_live_internal(False, emit=True)

    def _on_live_clicked(self) -> None:
        if not self._pro_unlocked:
            return
        if self._live:
            return
        self.live_enable_requested.emit()

    def _refresh_styles(self) -> None:
        # Paper active: emerald rail on left; Live active: warm danger tint on right.
        if self._live:
            self._paper_btn.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {_MUTED}; "
                f"border: 1px solid {_BORDER}; border-radius: 6px; font-weight: 600; font-size: 8.5pt; padding: 4px 10px; }}"
                f"QPushButton:hover {{ color: {_TEXT}; border-color: #52525b; }}"
            )
            self._live_btn.setStyleSheet(
                f"QPushButton {{ background-color: {_DANGER_DIM}; color: {_DANGER}; "
                f"border: 1px solid {_DANGER}; border-radius: 6px; font-weight: 700; font-size: 8.5pt; padding: 4px 10px; }}"
                f"QPushButton:hover {{ background-color: #991b1b; color: #fecaca; }}"
            )
        else:
            self._paper_btn.setStyleSheet(
                f"QPushButton {{ background-color: {_EMERALD_DIM}; color: {_EMERALD_HOVER}; "
                f"border: 1px solid {_EMERALD}; border-radius: 6px; font-weight: 700; font-size: 8.5pt; padding: 4px 10px; }}"
                f"QPushButton:hover {{ background-color: {_EMERALD}; color: #ecfdf5; }}"
            )
            if self._pro_unlocked:
                self._live_btn.setStyleSheet(
                    f"QPushButton {{ background-color: transparent; color: {_MUTED}; "
                    f"border: 1px solid {_BORDER}; border-radius: 6px; font-weight: 600; font-size: 8.5pt; padding: 4px 10px; }}"
                    f"QPushButton:hover {{ color: {_WARN}; border-color: {_WARN_DIM}; }}"
                )
            else:
                self._live_btn.setStyleSheet(
                    f"QPushButton {{ background-color: #18181b; color: #52525b; "
                    f"border: 1px solid {_BORDER}; border-radius: 6px; font-weight: 600; font-size: 8.5pt; padding: 4px 10px; }}"
                    f"QPushButton:disabled {{ color: #52525b; }}"
                )