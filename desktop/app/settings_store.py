from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .default_executor_url import DEFAULT_EXECUTOR_WS_URL


@dataclass
class AppSettings:
    # Connection
    ws_url: str = field(default_factory=lambda: DEFAULT_EXECUTOR_WS_URL)
    license_key: str = ""
    reconnect_interval_s: int = 5
    max_reconnect_attempts: int = 0  # 0 = unlimited

    # Trading / Risk
    order_quantity: float = 1.0
    max_daily_trades: int = 0  # 0 = unlimited
    signal_cooldown_s: int = 0  # 0 = no cooldown
    default_stop_loss_pct: float = 2.0
    confirm_before_trade: bool = False
    skip_non_long_signals: bool = True

    # Activity log
    log_font_size: int = 10
    log_max_lines: int = 600
    log_auto_scroll: bool = True
    log_show_timestamps: bool = True
    log_level_filter: str = "all"  # "all", "warn", "error"

    # Notifications
    notify_on_signal: bool = True
    notify_on_connect: bool = True

    # Startup
    auto_connect_on_start: bool = False
    start_minimized: bool = False
    seen_welcome: bool = False

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
            # If a release build baked in a server URL, migrate any stale localhost value
            # that was persisted from a previous dev/install.
            _saved_url = str(obj.get("ws_url") or "").strip()
            _dev_defaults = {"ws://127.0.0.1:8010/ws/exec", "ws://localhost:8010/ws/exec", "ws://127.0.0.1:8011/ws/exec", "ws://localhost:8011/ws/exec"}
            if not _saved_url or (
                _saved_url in _dev_defaults and DEFAULT_EXECUTOR_WS_URL not in _dev_defaults
            ):
                _saved_url = DEFAULT_EXECUTOR_WS_URL
            return AppSettings(
                ws_url=_saved_url,
                license_key=str(obj.get("license_key") or ""),
                reconnect_interval_s=int(obj.get("reconnect_interval_s") or 5),
                max_reconnect_attempts=int(obj.get("max_reconnect_attempts") or 0),
                order_quantity=float(obj.get("order_quantity") or 1.0),
                max_daily_trades=int(obj.get("max_daily_trades") or 0),
                signal_cooldown_s=int(obj.get("signal_cooldown_s") or 0),
                default_stop_loss_pct=float(obj.get("default_stop_loss_pct") or 2.0),
                confirm_before_trade=bool(obj.get("confirm_before_trade", False)),
                skip_non_long_signals=bool(obj.get("skip_non_long_signals", True)),
                log_font_size=int(obj.get("log_font_size") or 10),
                log_max_lines=int(obj.get("log_max_lines") or 600),
                log_auto_scroll=bool(obj.get("log_auto_scroll", True)),
                log_show_timestamps=bool(obj.get("log_show_timestamps", True)),
                log_level_filter=str(obj.get("log_level_filter") or "all"),
                notify_on_signal=bool(obj.get("notify_on_signal", True)),
                notify_on_connect=bool(obj.get("notify_on_connect", True)),
                auto_connect_on_start=bool(obj.get("auto_connect_on_start", False)),
                start_minimized=bool(obj.get("start_minimized", False)),
                seen_welcome=bool(obj.get("seen_welcome", False)),
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
