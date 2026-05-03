"""Resolve the default executor WebSocket URL (Setup tab).

Development: ``ws://127.0.0.1:8010/ws/exec``.

Release EXE: ``build-windows.ps1`` writes ``desktop/executor_defaults.json``; PyInstaller
bundles it next to ``logo.png`` at the extraction root so this module can read it when frozen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_DEV_DEFAULT = "ws://127.0.0.1:8010/ws/exec"


def _defaults_json_path() -> Path | None:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / "executor_defaults.json"  # type: ignore[attr-defined]
        return p if p.is_file() else None
    p = Path(__file__).resolve().parent.parent / "executor_defaults.json"
    return p if p.is_file() else None


def _load_default_ws() -> str:
    jpath = _defaults_json_path()
    if jpath is None:
        return _DEV_DEFAULT
    try:
        data = json.loads(jpath.read_text(encoding="utf-8"))
        u = str(data.get("default_executor_ws_url") or "").strip()
        return u if u else _DEV_DEFAULT
    except Exception:
        return _DEV_DEFAULT


DEFAULT_EXECUTOR_WS_URL = _load_default_ws()

__all__ = ["DEFAULT_EXECUTOR_WS_URL"]
