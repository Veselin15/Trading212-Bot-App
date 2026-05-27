"""Large visual step card for the setup wizard."""
from __future__ import annotations

from typing import Literal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

StepState = Literal["locked", "active", "done"]


class SetupStepCard(QFrame):
    """One setup step with a numbered badge, status, and collapsible body."""

    toggled = Signal(bool)

    def __init__(
        self,
        step_num: int,
        title: str,
        subtitle: str,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SetupStepCard")
        self._step_num = step_num
        self._state: StepState = "locked"
        self._expanded = False
        self._user_collapsed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = QFrame()
        self._header.setObjectName("SetupStepHeader")
        header = QHBoxLayout(self._header)
        header.setContentsMargins(16, 14, 16, 14)
        header.setSpacing(14)

        self._badge = QLabel(str(step_num))
        self._badge.setObjectName("SetupStepBadge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setFixedSize(42, 42)
        header.addWidget(self._badge)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("SetupStepTitle")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("SetupStepSubtitle")
        self._subtitle.setWordWrap(True)
        text_col.addWidget(self._title)
        text_col.addWidget(self._subtitle)
        header.addLayout(text_col, 1)

        self._status = QLabel("")
        self._status.setObjectName("SetupStepStatus")
        self._status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self._status)

        self._chevron = QLabel("▾")
        self._chevron.setObjectName("SetupStepChevron")
        self._chevron.setFixedWidth(16)
        header.addWidget(self._chevron)

        root.addWidget(self._header)

        self._body_wrap = QFrame()
        self._body_wrap.setObjectName("SetupStepBody")
        self._body = QVBoxLayout(self._body_wrap)
        self._body.setContentsMargins(20, 12, 20, 18)
        self._body.setSpacing(12)
        root.addWidget(self._body_wrap)

        self._header.mousePressEvent = self._on_header_clicked  # type: ignore[method-assign]
        self.set_state("locked")

    def body_layout(self) -> QVBoxLayout:
        return self._body

    def set_state(self, state: StepState, *, expand: bool | None = None) -> None:
        self._state = state
        self.setProperty("stepState", state)
        self._header.setProperty("stepState", state)
        self._badge.setProperty("stepState", state)

        if state == "done":
            self._badge.setText("✓")
            self._status.setText("Done")
            self._status.setProperty("statusKind", "done")
            self._header.setCursor(Qt.CursorShape.PointingHandCursor)
            self._header.setToolTip("Click to show or hide this step")
        elif state == "active":
            self._badge.setText(str(self._step_num))
            self._status.setText("Your turn")
            self._status.setProperty("statusKind", "active")
            self._header.setCursor(Qt.CursorShape.PointingHandCursor)
            self._header.setToolTip("")
        else:
            self._badge.setText(str(self._step_num))
            self._status.setText("Later")
            self._status.setProperty("statusKind", "locked")
            self._header.setCursor(Qt.CursorShape.ArrowCursor)
            self._header.setToolTip("Finish the step above first")

        if expand is not None:
            self._user_collapsed = not expand
            self._expanded = expand
        elif state == "active" and not self._user_collapsed:
            self._expanded = True
        elif state == "locked":
            self._expanded = False
            self._user_collapsed = False
        elif state == "done" and expand is None:
            # Keep user's expand/collapse choice for completed steps.
            pass

        self._apply_expand()
        self._polish()

    def _on_header_clicked(self, _event) -> None:
        if self._state == "locked":
            return
        self._expanded = not self._expanded
        self._user_collapsed = not self._expanded
        self._apply_expand()
        self.toggled.emit(self._expanded)

    def _apply_expand(self) -> None:
        self._body_wrap.setVisible(self._expanded)
        self._chevron.setText("▾" if self._expanded else "▸")

    def _polish(self) -> None:
        for w in (self, self._header, self._badge, self._status):
            w.style().unpolish(w)
            w.style().polish(w)
        self.update()
