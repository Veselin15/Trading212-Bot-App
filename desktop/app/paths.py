"""Paths shared by the desktop app (repo root, assets)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QPixmap


def repo_root() -> Path:
    """Repository root (parent of ``desktop/``)."""
    return Path(__file__).resolve().parents[2]


def load_brand_icon() -> QPixmap | None:
    """Mark only — ``logo.png`` (chart + arrow, no words)."""
    p = repo_root() / "logo.png"
    if not p.is_file():
        return None
    pm = QPixmap(str(p))
    return pm if not pm.isNull() else None
