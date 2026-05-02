from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    # Match uvicorn ``--host 127.0.0.1``; ``localhost`` can prefer IPv6 (::1) and miss that listener.
    ws_url: str = "ws://127.0.0.1:8010/ws/exec"
    license_key: str = ""


class SettingsStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.base_dir / "settings.json"

    def load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()
        try:
            obj = json.loads(self._path.read_text(encoding="utf-8"))
            return AppSettings(
                ws_url=str(obj.get("ws_url") or AppSettings.ws_url),
                license_key=str(obj.get("license_key") or ""),
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        payload = {"ws_url": settings.ws_url, "license_key": settings.license_key}
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

