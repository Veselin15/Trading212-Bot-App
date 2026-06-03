"""Small Qt widget factories for tab layouts."""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QTableWidget, QVBoxLayout, QWidget

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


def callout(text: str, *, kind: str = "info") -> QFrame:
    """Colored instruction box (info | success | warn)."""
    frame = QFrame()
    frame.setObjectName("Callout")
    frame.setProperty("calloutKind", kind)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    lab = QLabel(text)
    lab.setObjectName("CalloutText")
    lab.setWordWrap(True)
    layout.addWidget(lab)
    return frame


def instruction_steps(steps: list[str]) -> QWidget:
    """Numbered how-to list — number on the left, text on the right."""
    wrap = QWidget()
    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    for i, text in enumerate(steps, start=1):
        row = QFrame()
        row.setObjectName("InstructionRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 10, 12, 10)
        row_layout.setSpacing(12)
        num = QLabel(str(i))
        num.setObjectName("InstructionBadge")
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setFixedSize(28, 28)
        body = QLabel(text)
        body.setObjectName("InstructionText")
        body.setWordWrap(True)
        row_layout.addWidget(num, alignment=Qt.AlignmentFlag.AlignTop)
        row_layout.addWidget(body, 1)
        layout.addWidget(row)
    return wrap


class _TableEmptyOverlay(QLabel):
    """Centered placeholder shown over a table while it has no rows.

    Purely cosmetic — it lives on the viewport and never alters ``rowCount``.
    """

    def __init__(self, table: QTableWidget, text: str) -> None:
        super().__init__(text, table.viewport())
        self.setObjectName("TableEmptyOverlay")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._table = table
        table.viewport().installEventFilter(self)
        model = table.model()
        model.rowsInserted.connect(self._refresh)  # type: ignore[arg-type]
        model.rowsRemoved.connect(self._refresh)  # type: ignore[arg-type]
        model.modelReset.connect(self._refresh)  # type: ignore[arg-type]
        self._refresh()

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if obj is self._table.viewport() and event.type() == QEvent.Type.Resize:
            self._reposition()
        return False

    def _reposition(self) -> None:
        vp = self._table.viewport()
        self.setGeometry(0, 0, vp.width(), vp.height())

    def _refresh(self, *_args) -> None:
        self._reposition()
        self.setVisible(self._table.rowCount() == 0)


def attach_empty_overlay(table: QTableWidget, text: str) -> _TableEmptyOverlay:
    """Show a friendly placeholder over ``table`` whenever it is empty."""
    return _TableEmptyOverlay(table, text)


def status_text(status: str) -> tuple[str, str]:
    if status == "ONLINE":
        return ("Connected", _SUCCESS)
    if status == "CONNECTING":
        return ("Connecting…", _WARN)
    return ("Not connected", _DANGER)
