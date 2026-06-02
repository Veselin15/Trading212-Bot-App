"""SwiftTrade desktop Qt stylesheet and palette tokens."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QStyleFactory

_BG       = "#09090f"   # body — deepest layer
_SURFACE  = "#12121a"   # cards / panels
_SURFACE2 = "#1a1a24"   # elevated cards, groupboxes
_BORDER   = "#262636"   # subtle borders
_BORDER2  = "#353548"   # interactive borders
_SKY      = "#14b8a6"   # teal — primary accent
_SKY_HVR  = "#2dd4bf"   # hover
_SKY_DIM  = "#042f2e"   # tint bg for tags/indicators
_TEXT     = "#f0f0f2"   # primary text (slightly softer white for long-read comfort)
_MUTED    = "#a0a0b4"   # secondary / hint text (slightly brighter for readability)
_SUCCESS  = "#22c55e"
_WARN     = "#f59e0b"
_DANGER   = "#ef4444"

_DESKTOP_QSS = f"""
/* ── globals ──────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 9.5pt;
    color: {_TEXT};
    background-color: {_BG};
}}

/* ── navbar ───────────────────────────────────────────────────────── */
QFrame#Navbar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #16161f, stop:1 {_SURFACE});
    border-bottom: 1px solid {_BORDER};
    min-height: 54px;
    max-height: 60px;
}}

QLabel#AppWordmark {{
    background: transparent;
    padding: 0 4px 0 0;
}}

QLabel#BrandLogoMark {{
    background: transparent;
}}

QFrame#NavSep {{
    background-color: {_BORDER};
    min-width: 1px;
    max-width: 1px;
    min-height: 20px;
    max-height: 28px;
    border: none;
    margin: 0 4px;
}}

/* ── status indicator inside navbar ─────────────────────────────── */
QFrame#StatusBadge {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 12px;
    padding: 0 2px;
}}

/* ── broker pill ─────────────────────────────────────────────────── */
QLabel#BrokerPill {{
    color: {_MUTED};
    background-color: transparent;
    border: none;
    padding: 0 4px;
    font-size: 8.5pt;
}}

/* ── nav settings button ─────────────────────────────────────────── */
QPushButton#NavSettingsBtn {{
    background-color: transparent;
    color: {_MUTED};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11pt;
    min-width: 28px;
    max-width: 32px;
    min-height: 22px;
    max-height: 28px;
}}
QPushButton#NavSettingsBtn:hover {{
    color: {_TEXT};
    border-color: {_BORDER2};
    background-color: {_SURFACE2};
}}

QPushButton#NavHelpBtn {{
    background-color: transparent;
    color: {_MUTED};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 8.5pt;
    font-weight: 600;
    min-height: 24px;
}}
QPushButton#NavHelpBtn:hover {{
    color: {_TEXT};
    border-color: {_SKY};
    background-color: {_SKY_DIM};
}}

/* ── top-bar status card — kept for backward compat ─────────────── */
QFrame#StatusCard {{
    background-color: transparent;
    border: none;
}}

/* ── labelled field labels (above each input) ───────────────────── */
QLabel#FieldLabel {{
    color: {_TEXT};
    font-size: 9.5pt;
    font-weight: 600;
    background: transparent;
    padding: 0;
    margin: 0;
}}

/* ── setup progress header ───────────────────────────────────────── */
QFrame#SetupChecklist {{
    background-color: {_SURFACE};
    border-bottom: 1px solid {_BORDER};
}}

QLabel#ChecklistTitle {{
    color: {_TEXT};
    font-size: 13pt;
    font-weight: 700;
    letter-spacing: -0.02em;
    background: transparent;
}}

QLabel#ChecklistSubtitle {{
    color: {_MUTED};
    font-size: 9pt;
    background: transparent;
    line-height: 1.4;
}}

QLabel#ChecklistPct {{
    color: {_SKY};
    font-size: 11pt;
    font-weight: 700;
    background: transparent;
    min-width: 88px;
}}

QProgressBar#SetupProgress {{
    background-color: {_BG};
    border: none;
    border-radius: 4px;
}}
QProgressBar#SetupProgress::chunk {{
    background-color: {_SKY};
    border-radius: 4px;
}}

QLabel#ChecklistChip {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 8.5pt;
    font-weight: 600;
    color: {_MUTED};
}}
QLabel#ChecklistChip[chipState="active"] {{
    background-color: {_SKY_DIM};
    border-color: {_SKY};
    color: {_SKY};
    font-weight: 700;
}}
QLabel#ChecklistChip[chipState="done"] {{
    background-color: #052e16;
    border-color: #166534;
    color: {_SUCCESS};
    font-weight: 700;
}}

QFrame#ChecklistCallout {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 10px;
}}
QFrame#ChecklistCallout[calloutKind="active"] {{
    background-color: {_SKY_DIM};
    border-color: {_SKY};
}}
QFrame#ChecklistCallout[calloutKind="success"] {{
    background-color: #052e16;
    border-color: #166534;
}}

QLabel#ChecklistCalloutIcon {{
    font-size: 14pt;
    background: transparent;
    padding-right: 6px;
}}
QLabel#ChecklistCalloutText {{
    color: {_TEXT};
    font-size: 9.5pt;
    background: transparent;
    line-height: 1.5;
}}

/* ── setup path overview (free vs pro) ───────────────────────────── */
QFrame#PathCard {{
    background-color: {_SURFACE};
    border: 1px solid {_BORDER};
    border-radius: 10px;
}}
QFrame#PathCard[pathKind="free"] {{
    border-color: {_SKY};
}}
QFrame#PathCard[pathKind="pro"] {{
    border-color: #a78bfa;
}}
QLabel#PathCardTitle {{
    color: {_TEXT};
    font-size: 10pt;
    font-weight: 700;
    background: transparent;
}}
QLabel#PathCardBody {{
    color: {_MUTED};
    font-size: 9pt;
    background: transparent;
    line-height: 1.45;
}}

/* ── setup step cards ────────────────────────────────────────────── */
QFrame#SetupStepCard {{
    background-color: {_SURFACE};
    border: 1px solid {_BORDER};
    border-radius: 14px;
}}
QFrame#SetupStepCard[stepState="active"] {{
    border: 1px solid {_SKY};
    background-color: {_SURFACE2};
}}
QFrame#SetupStepCard[stepState="done"] {{
    border: 1px solid #166534;
}}
QFrame#SetupStepCard[stepState="locked"] {{
    background-color: #0e0e14;
    border-color: {_BORDER};
}}

/* ── nav status pill ─────────────────────────────────────────────── */
QFrame#NavStatusPill {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 14px;
}}
QFrame#NavStatusPill[statusKind="setup"] {{
    border-color: {_BORDER2};
}}
QFrame#NavStatusPill[statusKind="ready"] {{
    background-color: {_SKY_DIM};
    border-color: {_SKY};
}}
QFrame#NavStatusPill[statusKind="connecting"] {{
    background-color: #422006;
    border-color: {_WARN};
}}
QFrame#NavStatusPill[statusKind="online"] {{
    background-color: #052e16;
    border-color: #166534;
}}
QFrame#NavStatusPill[statusKind="live"] {{
    background-color: #450a0a;
    border-color: {_DANGER};
}}
QLabel#NavStatusDot {{
    font-size: 10pt;
    background: transparent;
}}
QLabel#NavStatusDot[statusKind="setup"] {{ color: {_MUTED}; }}
QLabel#NavStatusDot[statusKind="ready"] {{ color: {_SKY}; }}
QLabel#NavStatusDot[statusKind="connecting"] {{ color: {_WARN}; }}
QLabel#NavStatusDot[statusKind="online"] {{ color: {_SUCCESS}; }}
QLabel#NavStatusDot[statusKind="live"] {{ color: {_DANGER}; }}
QLabel#NavStatusText {{
    color: {_TEXT};
    font-size: 8.5pt;
    font-weight: 600;
    background: transparent;
}}

QLabel#TierStatusLabel {{
    font-size: 9pt;
    background: transparent;
    padding: 6px 0 0 0;
}}
QLabel#TierStatusLabel[tierKind="pro"] {{ color: {_SUCCESS}; font-weight: 600; }}
QLabel#TierStatusLabel[tierKind="starter"] {{ color: #38bdf8; font-weight: 600; }}
QLabel#TierStatusLabel[tierKind="trial"] {{ color: {_SUCCESS}; }}
QLabel#TierStatusLabel[tierKind="free"] {{ color: {_WARN}; }}
QLabel#TierStatusLabel[tierKind="expired"] {{ color: {_DANGER}; font-weight: 600; }}
QLabel#TierStatusLabel[tierKind="pending"] {{ color: {_MUTED}; }}

QFrame#SetupStepHeader {{
    background: transparent;
    border: none;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}}
QFrame#SetupStepHeader[stepState="active"] {{
    background-color: rgba(16, 185, 129, 0.06);
}}

QLabel#SetupStepBadge {{
    background-color: {_BG};
    border: 2px solid {_BORDER2};
    border-radius: 20px;
    color: {_MUTED};
    font-size: 14pt;
    font-weight: 800;
}}
QLabel#SetupStepBadge[stepState="active"] {{
    background-color: {_SKY};
    border-color: {_SKY};
    color: #ffffff;
}}
QLabel#SetupStepBadge[stepState="done"] {{
    background-color: #166534;
    border-color: {_SUCCESS};
    color: #ffffff;
    font-size: 16pt;
}}

QLabel#SetupStepTitle {{
    color: {_TEXT};
    font-size: 11pt;
    font-weight: 700;
    background: transparent;
    letter-spacing: -0.01em;
}}
QLabel#SetupStepSubtitle {{
    color: {_MUTED};
    font-size: 9pt;
    background: transparent;
    line-height: 1.4;
}}
QLabel#SetupStepStatus {{
    font-size: 8.5pt;
    font-weight: 700;
    background: transparent;
    min-width: 72px;
}}
QLabel#SetupStepStatus[statusKind="active"] {{
    color: {_SKY};
}}
QLabel#SetupStepStatus[statusKind="done"] {{
    color: {_SUCCESS};
}}
QLabel#SetupStepStatus[statusKind="locked"] {{
    color: {_MUTED};
}}
QLabel#SetupStepChevron {{
    color: {_MUTED};
    font-size: 10pt;
    background: transparent;
}}

QFrame#SetupStepBody {{
    background: transparent;
    border: none;
    border-top: 1px solid {_BORDER};
}}

QFrame#DemoKeyBox {{
    background-color: {_BG};
    border: 1px solid {_SKY};
    border-radius: 10px;
}}

/* ── account section headers (inside Demo/Live boxes) ────────── */
QFrame#AccountSectionHeader {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {_BORDER};
}}

QLabel#AccountBadge {{
    background-color: {_SKY_DIM};
    color: {_SKY};
    border-radius: 5px;
    font-size: 7pt;
    font-weight: 800;
    letter-spacing: 0.05em;
    padding: 2px 6px;
}}
QLabel#AccountBadge[badgeKind="live"] {{
    background-color: #450a0a;
    color: {_DANGER};
}}
QLabel#AccountBadge[badgeKind="pro"] {{
    background-color: #3b0764;
    color: #d8b4fe;
}}

QLabel#AccountSectionTitle {{
    color: {_TEXT};
    font-size: 9.5pt;
    font-weight: 700;
    background: transparent;
}}

QLabel#AccountUrl {{
    color: {_MUTED};
    font-size: 8pt;
    background: transparent;
    font-family: "Cascadia Mono", "Consolas", monospace;
}}

/* ── live key box ────────────────────────────────────────────── */
QFrame#LiveKeyBox {{
    background-color: {_BG};
    border: 1px solid {_DANGER};
    border-radius: 10px;
}}
QFrame#LiveKeyBox[locked="true"] {{
    border-color: {_BORDER};
    background-color: #0c0c10;
}}

/* ── live key lock message ───────────────────────────────────── */
QLabel#LiveKeyLockMsg {{
    color: {_MUTED};
    font-size: 9pt;
    background: transparent;
    line-height: 1.5;
}}

/* ── callouts & instructions ─────────────────────────────────────── */
QFrame#Callout {{
    background-color: {_BG};
    border: 1px solid {_BORDER};
    border-radius: 10px;
}}
QFrame#Callout[calloutKind="info"] {{
    background-color: rgba(16, 185, 129, 0.08);
    border-color: rgba(16, 185, 129, 0.35);
}}
QFrame#Callout[calloutKind="warn"] {{
    background-color: rgba(245, 158, 11, 0.1);
    border-color: rgba(245, 158, 11, 0.35);
}}
QFrame#Callout[calloutKind="success"] {{
    background-color: rgba(34, 197, 94, 0.1);
    border-color: rgba(34, 197, 94, 0.35);
}}
QLabel#CalloutText {{
    color: {_TEXT};
    font-size: 9.5pt;
    background: transparent;
}}

QFrame#InstructionRow {{
    background-color: transparent;
    border: none;
    border-radius: 0;
}}
QLabel#InstructionBadge {{
    background-color: {_SKY_DIM};
    border: none;
    border-radius: 12px;
    color: {_SKY};
    font-size: 9pt;
    font-weight: 800;
}}
QLabel#InstructionText {{
    color: {_TEXT};
    font-size: 9.5pt;
    background: transparent;
    padding-top: 4px;
    line-height: 1.5;
}}

/* ── hero connect button ─────────────────────────────────────────── */
QPushButton#HeroBtn {{
    background-color: {_SKY};
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 800;
    font-size: 11pt;
    letter-spacing: 0.02em;
}}
QPushButton#HeroBtn:hover {{
    background-color: {_SKY_HVR};
}}
QPushButton#HeroBtn:pressed {{
    background-color: #059669;
}}
QPushButton#HeroBtn:disabled {{
    background-color: #166534;
    color: #d1fae5;
}}

/* ── hint text ───────────────────────────────────────────────────── */
QLabel#HintLabel {{
    color: {_MUTED};
    font-size: 9pt;
    background: transparent;
    padding: 0;
    margin: 0;
    line-height: 1.45;
}}

/* ── section headings inside tabs ────────────────────────────────── */
QLabel#SectionTitle {{
    color: {_TEXT};
    font-size: 10pt;
    font-weight: 700;
    background: transparent;
    padding: 0;
    margin: 0;
    letter-spacing: -0.01em;
}}

/* ── groupboxes ───────────────────────────────────────────────────── */
QGroupBox {{
    font-weight: 600;
    font-size: 9.5pt;
    color: {_TEXT};
    margin-top: 18px;
    padding: 20px 16px 14px 16px;
    border: 1px solid {_BORDER};
    border-radius: 10px;
    background-color: {_SURFACE2};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 1px;
    padding: 2px 10px;
    color: {_SKY};
    background-color: {_BG};
    border-radius: 4px;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 0.03em;
}}

/* ── line edits ───────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 8px;
    padding: 9px 12px;
    min-height: 18px;
    selection-background-color: {_SKY_DIM};
    selection-color: #ffffff;
    font-size: 9.5pt;
}}
QLineEdit:focus {{
    border: 1px solid {_SKY};
    background-color: {_SURFACE2};
}}
QLineEdit:disabled {{
    color: {_MUTED};
    border-color: {_BORDER};
}}

/* ── text log ────────────────────────────────────────────────────── */
QTextEdit {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {_SKY_DIM};
    selection-color: #ffffff;
}}

/* ── tabs ─────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    border-radius: 12px;
    background-color: {_SURFACE};
    top: 0;
    margin-top: 4px;
}}
QTabBar {{
    background: transparent;
    border-bottom: 2px solid {_BORDER};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {_MUTED};
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 10px 22px;
    margin-right: 2px;
    min-width: 5em;
    font-size: 9.5pt;
    font-weight: 500;
    letter-spacing: 0.01em;
}}
QTabBar::tab:selected {{
    background-color: transparent;
    color: {_TEXT};
    font-weight: 700;
    border-bottom: 2px solid {_SKY};
}}
QTabBar::tab:hover:!selected {{
    color: {_TEXT};
    background-color: rgba(255, 255, 255, 0.03);
}}

/* ── buttons ─────────────────────────────────────────────────────── */
QPushButton#PrimaryBtn {{
    background-color: {_SKY};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 26px;
    max-height: 32px;
    font-weight: 700;
    font-size: 9pt;
    letter-spacing: 0.01em;
}}
QPushButton#PrimaryBtn:hover {{ background-color: {_SKY_HVR}; }}
QPushButton#PrimaryBtn:pressed {{ background-color: #0284c7; }}
QPushButton#PrimaryBtn:disabled {{
    background-color: {_BORDER};
    color: {_MUTED};
}}

QPushButton#SecondaryBtn {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 26px;
    max-height: 32px;
    font-weight: 600;
    font-size: 9pt;
}}
QPushButton#SecondaryBtn:hover {{
    background-color: #252530;
    border-color: {_SKY};
    color: {_SKY_HVR};
}}
QPushButton#SecondaryBtn:pressed {{ background-color: {_SURFACE}; }}
QPushButton#SecondaryBtn:disabled {{ color: {_MUTED}; border-color: {_BORDER}; }}

QPushButton#GhostBtn {{
    background-color: transparent;
    color: {_MUTED};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    min-height: 20px;
    max-height: 26px;
    font-size: 8.5pt;
}}
QPushButton#GhostBtn:hover {{
    color: {_TEXT};
    border-color: {_BORDER2};
    background-color: {_SURFACE2};
}}

QPushButton#DangerBtn {{
    background-color: {_SURFACE};
    color: #fca5a5;
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 22px;
    max-height: 28px;
    font-weight: 600;
    font-size: 8.5pt;
}}
QPushButton#DangerBtn:hover {{
    background-color: #2d0f0f;
    border-color: {_DANGER};
    color: #fee2e2;
}}
QPushButton#DangerBtn:pressed {{ background-color: #450a0a; }}
QPushButton#DangerBtn:disabled {{ color: {_MUTED}; border-color: {_BORDER}; background-color: {_SURFACE}; }}

/* ── checkbox ────────────────────────────────────────────────────── */
QCheckBox {{
    color: {_TEXT};
    spacing: 6px;
    font-size: 8.5pt;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 4px;
    border: 1px solid {_BORDER2};
    background-color: {_SURFACE};
}}
QCheckBox::indicator:checked {{
    background-color: {_SKY};
    border-color: {_SKY};
}}
QCheckBox::indicator:hover {{
    border-color: {_SKY};
}}

/* ── tables ───────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {_SURFACE};
    alternate-background-color: {_SURFACE2};
    color: {_TEXT};
    gridline-color: {_BORDER};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    font-size: 9pt;
}}
QTableWidget::item:selected {{
    background-color: {_SKY_DIM};
    color: #e0f2fe;
}}
QHeaderView::section {{
    background-color: {_SURFACE2};
    color: {_MUTED};
    padding: 5px 8px;
    border: none;
    border-bottom: 1px solid {_BORDER};
    border-right: 1px solid {_BORDER};
    font-weight: 700;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
QHeaderView::section:last {{
    border-right: none;
}}

/* ── list widget ────────────────────────────────────────────────── */
QListWidget {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 4px;
    font-size: 9pt;
}}
QListWidget::item {{
    padding: 7px 10px;
    border-radius: 5px;
}}
QListWidget::item:selected {{
    background-color: {_SKY_DIM};
    color: #e0f2fe;
}}

/* ── splitter ────────────────────────────────────────────────────── */
QSplitter::handle:horizontal {{
    background-color: {_BORDER};
    width: 3px;
    margin: 6px 2px;
    border-radius: 2px;
}}
QSplitter::handle:horizontal:hover {{
    background-color: {_SKY};
}}

QSplitter::handle:vertical {{
    background-color: {_BORDER};
    height: 4px;
    margin: 2px 6px;
    border-radius: 2px;
}}
QSplitter::handle:vertical:hover {{
    background-color: {_SKY};
}}

/* ── scrollbars ───────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {_SURFACE};
    width: 10px;
    margin: 4px 2px 4px 0;
    border-radius: 5px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER2};
    min-height: 28px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{ background: {_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background: {_SURFACE};
    height: 10px;
    margin: 0 4px 2px 4px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {_BORDER2};
    min-width: 28px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{ background: {_MUTED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── scroll area ─────────────────────────────────────────────────── */
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* ── menu bar (hidden — replaced by custom navbar) ───────────────── */
QMenuBar {{
    min-height: 0;
    max-height: 0;
    padding: 0;
    margin: 0;
    border: none;
    background: transparent;
}}
QMenuBar::item {{ max-height: 0; min-height: 0; padding: 0; margin: 0; }}
QMenu {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 8px;
    padding: 6px 4px;
    font-size: 9.5pt;
}}
QMenu::item {{ padding: 8px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: {_SKY_DIM}; color: #e0f2fe; }}
QMenu::separator {{
    height: 1px;
    background: {_BORDER};
    margin: 4px 10px;
}}

/* ── settings dialog ─────────────────────────────────────────────── */
QDialog {{
    background-color: {_SURFACE};
    border: 1px solid {_BORDER2};
    border-radius: 10px;
}}
QDialog QLabel#PrefSectionLabel {{
    color: {_SKY};
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    background: transparent;
}}
QSpinBox {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 9pt;
    selection-background-color: {_SKY_DIM};
}}
QSpinBox:focus {{ border-color: {_SKY}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {_SURFACE2};
    border: none;
    width: 18px;
    border-radius: 3px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {_BORDER2};
}}

QDoubleSpinBox {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 9pt;
    selection-background-color: {_SKY_DIM};
}}
QDoubleSpinBox:focus {{ border-color: {_SKY}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {_SURFACE2};
    border: none;
    width: 18px;
    border-radius: 3px;
}}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {_BORDER2};
}}

QComboBox {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 9pt;
}}
QComboBox:focus {{ border-color: {_SKY}; }}
QComboBox::drop-down {{
    border: none;
    background-color: {_SURFACE2};
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    selection-background-color: {_SKY_DIM};
    selection-color: #e0f2fe;
    padding: 4px;
}}
QDialogButtonBox QPushButton {{
    background-color: {_SURFACE2};
    color: {_TEXT};
    border: 1px solid {_BORDER2};
    border-radius: 6px;
    padding: 6px 18px;
    font-size: 9pt;
    font-weight: 600;
    min-height: 22px;
}}
QDialogButtonBox QPushButton:default {{
    background-color: {_SKY};
    color: #fff;
    border: none;
}}
QDialogButtonBox QPushButton:hover {{
    background-color: {_SURFACE};
    border-color: {_SKY};
    color: {_SKY_HVR};
}}
QDialogButtonBox QPushButton:default:hover {{ background-color: {_SKY_HVR}; color: #fff; }}

/* ── status bar at the bottom ─────────────────────────────────────── */
QStatusBar {{
    background-color: {_BG};
    color: {_MUTED};
    border-top: 1px solid {_BORDER};
    font-size: 8pt;
    padding: 0 4px;
    min-height: 18px;
    max-height: 22px;
}}
"""


def apply_desktop_styles(app: QApplication) -> None:
    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:
        app.setStyle(fusion)
    app.setStyleSheet(_DESKTOP_QSS)
