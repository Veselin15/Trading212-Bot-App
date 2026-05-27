from __future__ import annotations

import uuid


def normalize_license_key(raw: str | None) -> str | None:
    """Return a trimmed UUID string, or None for paper / guest mode."""
    text = str(raw or "").strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    try:
        return str(uuid.UUID(text))
    except ValueError:
        return None
