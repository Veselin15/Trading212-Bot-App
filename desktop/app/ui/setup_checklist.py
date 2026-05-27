"""Getting-started progress header for the Setup tab."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout


class SetupChecklist(QFrame):
    """Progress header aligned with the 3 setup cards below."""

    _STEPS = (
        "License key",
        "Trading212 account",
        "Connect",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SetupChecklist")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Set up in 3 steps")
        title.setObjectName("ChecklistTitle")
        subtitle = QLabel(
            "Work through the cards below from top to bottom. "
            "You can expand a finished step anytime to change something."
        )
        subtitle.setObjectName("ChecklistSubtitle")
        subtitle.setWordWrap(True)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        head.addLayout(title_col, 1)

        self._help_btn = QPushButton("Need help?")
        self._help_btn.setObjectName("GhostBtn")
        self._help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        head.addWidget(self._help_btn, alignment=Qt.AlignmentFlag.AlignTop)

        self._pct_label = QLabel("0%")
        self._pct_label.setObjectName("ChecklistPct")
        self._pct_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(self._pct_label)
        outer.addLayout(head)

        self._progress = QProgressBar()
        self._progress.setObjectName("SetupProgress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        outer.addWidget(self._progress)

        steps_row = QHBoxLayout()
        steps_row.setSpacing(8)
        self._chip_labels: list[QLabel] = []
        for i, label in enumerate(self._STEPS):
            chip = QLabel(f"{i + 1}. {label}")
            chip.setObjectName("ChecklistChip")
            chip.setWordWrap(True)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            steps_row.addWidget(chip, 1)
            self._chip_labels.append(chip)
        outer.addLayout(steps_row)

        self._summary = QFrame()
        self._summary.setObjectName("ChecklistCallout")
        sum_layout = QHBoxLayout(self._summary)
        sum_layout.setContentsMargins(14, 10, 14, 10)
        self._summary_icon = QLabel("→")
        self._summary_icon.setObjectName("ChecklistCalloutIcon")
        self._summary_text = QLabel("")
        self._summary_text.setObjectName("ChecklistCalloutText")
        self._summary_text.setWordWrap(True)
        sum_layout.addWidget(self._summary_icon)
        sum_layout.addWidget(self._summary_text, 1)
        outer.addWidget(self._summary)

        self.update_state(
            license_validated=False,
            has_broker_keys=False,
            connected=False,
        )

    def update_state(
        self,
        *,
        license_validated: bool,
        has_broker_keys: bool,
        connected: bool,
    ) -> None:
        done = [license_validated, has_broker_keys, connected]
        completed = sum(done)
        pct = int(completed / len(done) * 100) if done else 0
        self._progress.setValue(pct)
        self._pct_label.setText(f"{pct}% done")

        current_idx = next((i for i, ok in enumerate(done) if not ok), len(done))

        for i, chip in enumerate(self._chip_labels):
            chip.setProperty("chipState", "done" if done[i] else ("active" if i == current_idx else "pending"))
            chip.style().unpolish(chip)
            chip.style().polish(chip)

        if completed == 3:
            self._summary_icon.setText("✓")
            self._summary_text.setText(
                "You're connected. Open the Live feed tab to watch the bot, "
                "or stay on Demo mode in the top bar until you're ready for real trades."
            )
            self._summary.setProperty("calloutKind", "success")
        elif not license_validated:
            self._summary_icon.setText("1")
            self._summary_text.setText(
                "Optional: paste a Pro license key in Step 1, or skip straight to Step 2 for free paper trading."
            )
            self._summary.setProperty("calloutKind", "active")
        elif not has_broker_keys:
            self._summary_icon.setText("2")
            self._summary_text.setText(
                "On your phone, open Trading212 → Settings → API → create a demo/practice key. "
                "Paste it in Step 2 and click Save demo keys."
            )
            self._summary.setProperty("calloutKind", "active")
        elif not connected:
            self._summary_icon.setText("3")
            self._summary_text.setText(
                "Almost there — click Connect in Step 3. The dot at the top will turn green when you're linked."
            )
            self._summary.setProperty("calloutKind", "active")
        else:
            self._summary_icon.setText("→")
            self._summary_text.setText(f"{len(done) - completed} step(s) left.")
            self._summary.setProperty("calloutKind", "neutral")

        self._summary.style().unpolish(self._summary)
        self._summary.style().polish(self._summary)
