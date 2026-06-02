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
    start_with_windows: bool = False
    seen_welcome: bool = False

    # Background / power
    close_to_tray: bool = True      # hide to tray on window-close instead of quitting
    keep_awake: bool = True         # prevent the PC from sleeping while connected

    # Layout
    splitter_sizes: list[int] = field(default_factory=lambda: [580, 440])

    def reset_preferences(self, *, keep: AppSettings) -> AppSettings:
        """Restore trading/log/connection prefs to factory defaults; keep setup-specific fields."""
        fresh = AppSettings()
        return AppSettings(
            ws_url=keep.ws_url,
            license_key=keep.license_key,
            seen_welcome=keep.seen_welcome,
            splitter_sizes=list(keep.splitter_sizes),
            reconnect_interval_s=fresh.reconnect_interval_s,
            max_reconnect_attempts=fresh.max_reconnect_attempts,
            order_quantity=fresh.order_quantity,
            max_daily_trades=fresh.max_daily_trades,
            signal_cooldown_s=fresh.signal_cooldown_s,
            default_stop_loss_pct=fresh.default_stop_loss_pct,
            confirm_before_trade=fresh.confirm_before_trade,
            skip_non_long_signals=fresh.skip_non_long_signals,
            log_font_size=fresh.log_font_size,
            log_max_lines=fresh.log_max_lines,
            log_auto_scroll=fresh.log_auto_scroll,
            log_show_timestamps=fresh.log_show_timestamps,
            log_level_filter=fresh.log_level_filter,
            notify_on_signal=fresh.notify_on_signal,
            notify_on_connect=fresh.notify_on_connect,
            auto_connect_on_start=fresh.auto_connect_on_start,
            start_minimized=fresh.start_minimized,
            start_with_windows=keep.start_with_windows,   # keep — touches OS state
            close_to_tray=fresh.close_to_tray,
            keep_awake=fresh.keep_awake,
        )


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
                start_with_windows=bool(obj.get("start_with_windows", False)),
                seen_welcome=bool(obj.get("seen_welcome", False)),
                close_to_tray=bool(obj.get("close_to_tray", True)),
                keep_awake=bool(obj.get("keep_awake", True)),
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
