"""SwiftTrade desktop Qt stylesheet and palette tokens."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QStyleFactory

_BG       = "#0c0c10"   # body — deepest layer
_SURFACE  = "#13131a"   # cards / panels
_SURFACE2 = "#1c1c25"   # elevated cards, groupboxes
_BORDER   = "#2a2a38"   # subtle borders
_BORDER2  = "#3a3a4e"   # interactive borders
_SKY      = "#10b981"   # emerald-500 — primary accent
_SKY_HVR  = "#34d399"   # emerald-400 — hover
_SKY_DIM  = "#064e3b"   # emerald tint bg for tags/indicators
_TEXT     = "#f1f1f3"   # primary text
_MUTED    = "#8b8b9e"   # secondary / hint text
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
    background-color: {_SURFACE};
    border-bottom: 1px solid {_BORDER};
    min-height: 44px;
    max-height: 52px;
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

/* ── hint text ───────────────────────────────────────────────────── */
QLabel#HintLabel {{
    color: {_MUTED};
    font-size: 8.8pt;
    background: transparent;
    padding: 0;
    margin: 0;
}}

/* ── section headings inside tabs ────────────────────────────────── */
QLabel#SectionTitle {{
    color: {_TEXT};
    font-size: 9pt;
    font-weight: 600;
    background: transparent;
    padding: 0;
    margin: 0;
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
    border: 1px solid {_BORDER};
    border-radius: 0 8px 8px 8px;
    background-color: {_SURFACE};
    top: -1px;
    margin-top: 0;
}}
QTabBar::tab {{
    background-color: {_BG};
    color: {_MUTED};
    border: 1px solid {_BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 4px 14px;
    margin-right: 2px;
    min-width: 4.5em;
    font-size: 8.5pt;
}}
QTabBar::tab:selected {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border-bottom: 2px solid {_SKY};
    font-weight: 600;
    padding-bottom: 2px;
}}
QTabBar::tab:hover:!selected {{
    color: {_TEXT};
    background-color: {_SURFACE2};
}}

/* ── buttons ─────────────────────────────────────────────────────── */
QPushButton#PrimaryBtn {{
    background-color: {_SKY};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 22px;
    max-height: 28px;
    font-weight: 700;
    font-size: 8.5pt;
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
    padding: 5px 14px;
    min-height: 22px;
    max-height: 28px;
    font-weight: 600;
    font-size: 8.5pt;
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
