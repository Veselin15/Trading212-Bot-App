from __future__ import annotations

from pathlib import Path


def backend_dotenv_candidate_paths(primary_backend_dotenv: Path) -> list[Path]:
    """Possible ``backend/.env`` locations when cwd and installed package paths disagree."""
    raw: list[Path] = [primary_backend_dotenv]
    cwd = Path.cwd()
    # Repo-root cwd: ``backend/.env``. Skip when cwd is already ``.../backend`` (avoids ``backend/backend/.env``).
    if (cwd / "backend").is_dir():
        raw.append(cwd / "backend" / ".env")
    raw.append(cwd / ".env")
    for ancestor in [cwd, *list(cwd.parents)[:20]]:
        raw.append(ancestor / "backend" / ".env")

    out: list[Path] = []
    seen: set[str] = set()
    for p in raw:
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out
