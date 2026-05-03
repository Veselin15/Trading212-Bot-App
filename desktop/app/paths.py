"""Paths shared by the desktop app (repo root, assets)."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QPixmap


def repo_root() -> Path:
    """Repository root — or the PyInstaller extraction directory when frozen.

    When packaged as a one-file executable, ``sys._MEIPASS`` is the temp
    directory where bundled data files (logo.png, etc.) are extracted.
    In development the function walks up from this source file.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def load_brand_icon() -> QPixmap | None:
    """Mark only — ``logo.png`` (chart + arrow, no words)."""
    p = repo_root() / "logo.png"
    if not p.is_file():
        return None
    pm = QPixmap(str(p))
    return pm if not pm.isNull() else None
