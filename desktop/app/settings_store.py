from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AppSettings:
    # Connection
    ws_url: str = "ws://127.0.0.1:8010/ws/exec"
    license_key: str = ""

    # Activity log
    log_font_size: int = 10
    log_max_lines: int = 600
    log_auto_scroll: bool = True
    log_show_timestamps: bool = True

    # Layout
    splitter_sizes: list[int] = field(default_factory=lambda: [580, 440])


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
                log_font_size=int(obj.get("log_font_size") or 10),
                log_max_lines=int(obj.get("log_max_lines") or 600),
                log_auto_scroll=bool(obj.get("log_auto_scroll", True)),
                log_show_timestamps=bool(obj.get("log_show_timestamps", True)),
                splitter_sizes=list(obj.get("splitter_sizes") or [580, 440]),
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        payload = asdict(settings)
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
