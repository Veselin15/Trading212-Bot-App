from __future__ import annotations

import argparse
import asyncio
import ctypes
import os
import csv
import logging
from logging.handlers import RotatingFileHandler
import random
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from t212_miner_bot.api_client import AsyncT212Client, T212APIError
    from t212_miner_bot.config import (
        BOT_SAFE_MODE,
        ENABLE_TIME_FILTER,
        BOT_LOG_DIR,
        SIGNAL_BUFFER_SECONDS,
        SYMBOLS_MAP,
        StrategyParams,
        TOTAL_PORTFOLIO_EUR,
        WAIT_JITTER_MAX_SECONDS,
    )
    from t212_miner_bot.data_feed import get_latest_signals
    from t212_miner_bot.email_notifier import send_email_alert
    from t212_miner_bot.execution_manager import ExecutionManager
except ImportError:
    # Fallback when launched as a module in environments with package-relative resolution.
    from .api_client import AsyncT212Client, T212APIError
    from .config import (
        BOT_SAFE_MODE,
        ENABLE_TIME_FILTER,
        BOT_LOG_DIR,
        SIGNAL_BUFFER_SECONDS,
        SYMBOLS_MAP,
        StrategyParams,
        TOTAL_PORTFOLIO_EUR,
        WAIT_JITTER_MAX_SECONDS,
    )
    from .data_feed import get_latest_signals
    from .email_notifier import send_email_alert
    from .execution_manager import ExecutionManager


try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
except Exception:
    # Fallback when colorama is not available.
    class _NoColor:
        def __getattr__(self, _: str) -> str:
            return ""

    Fore = _NoColor()
    Style = _NoColor()


def _now_local() -> datetime:
    # Trading 212 servers are UTC-based; keep runtime timestamps in UTC for consistency.
    return datetime.now(tz=ZoneInfo("UTC"))


def _seconds_until_next_candle_close(buffer_seconds: int = SIGNAL_BUFFER_SECONDS) -> float:
    now = _now_local()
    next_minute = ((now.minute // 5) + 1) * 5

    if next_minute >= 60:
        target = now.replace(minute=0, second=buffer_seconds, microsecond=0) + timedelta(hours=1)
    else:
        target = now.replace(minute=next_minute, second=buffer_seconds, microsecond=0)

    # If we are exactly at a scheduled second, continue to the next cycle.
    if target <= now:
        target += timedelta(minutes=5)
    base = max((target - now).total_seconds(), 0.5)
    jitter_max = max(float(WAIT_JITTER_MAX_SECONDS), 0.0)
    if jitter_max > 0:
        base += random.uniform(0.0, jitter_max)
    return base


def _setup_file_logging() -> logging.Logger:
    log_dir = Path(BOT_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("t212_miner_bot")
    logger.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        handler = RotatingFileHandler(
            log_dir / "t212_miner_bot.log",
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


def _append_cycle_csv_row(*, row: dict[str, object]) -> None:
    log_dir = Path(BOT_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "cycle_journal.csv"
    fieldnames = list(row.keys())
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerow(row)


def _log_info(msg: str) -> None:
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")


def _log_success(msg: str) -> None:
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} {msg}")


def _log_warn(msg: str) -> None:
    print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {msg}")


def _log_error(msg: str) -> None:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")


def _log_startup_settings(params: StrategyParams) -> None:
    # Print the active strategy profile at startup for fast operator verification.
    _log_info(
        "Strategy settings: "
        f"ATR_MULTIPLIER={params.atr_multiplier:.2f}, "
        f"UNIT1_TP_RR={params.unit1_tp_rr:.2f}, "
        f"EMA_PERIOD={params.ema_period}, "
        f"ATR_TRAIL_MULT={params.atr_trail_mult:.2f}, "
        f"BREAKEVEN_OFFSET_PCT={params.breakeven_offset_pct:.4f}, "
        f"BREAK_EVEN_TRIGGER_PCT={params.break_even_trigger_pct:.4f}, "
        f"PROFIT_LOCK_TRIGGER_PCT={params.profit_lock_trigger_pct:.4f}, "
        f"PROFIT_LOCK_STOP_PCT={params.profit_lock_stop_pct:.4f}, "
        f"PROFIT_LOCK_BY_SYMBOL={params.profit_lock_by_symbol}, "
        f"MORNING_PROTECT_ENABLED={params.morning_protect_enabled}, "
        f"MORNING_REAL_PROFIT_TRIGGER_PCT={params.morning_real_profit_trigger_pct:.4f}, "
        f"MORNING_PROFIT_CAPTURE_PCT={params.morning_profit_capture_pct:.4f}, "
        f"MORNING_PROTECT_WINDOW_MINUTES={params.morning_protect_window_minutes}, "
        f"MORNING_PROTECT_SYMBOL_ENABLED={params.morning_protect_symbol_enabled}, "
        f"MORNING_REAL_PROFIT_TRIGGER_PCT_BY_SYMBOL={params.morning_real_profit_trigger_pct_by_symbol}, "
        f"MORNING_PROFIT_CAPTURE_PCT_BY_SYMBOL={params.morning_profit_capture_pct_by_symbol}, "
        f"MORNING_PROTECT_WINDOW_MINUTES_BY_SYMBOL={params.morning_protect_window_minutes_by_symbol}, "
        f"ATR_DYNAMIC_STOP_MULT={params.atr_dynamic_stop_mult:.2f}, "
        f"ATR_DYNAMIC_TP_R={params.atr_dynamic_tp_r:.2f}, "
        f"ATR_DYNAMIC_BE_R={params.atr_dynamic_be_r:.2f}, "
        f"ATR_DYNAMIC_PARAMS_BY_SYMBOL={params.atr_dynamic_params_by_symbol}, "
        f"TREND_STRENGTH_FILTER_ENABLED={params.trend_strength_filter_enabled}, "
        f"EDGE_WEIGHTED_RISK_ENABLED={params.edge_weighted_risk_enabled}, "
        f"EDGE_RISK_LOOKBACK_TRADES={params.edge_risk_lookback_trades}, "
        f"EDGE_RISK_MIN_TRADES={params.edge_risk_min_trades}, "
        f"EDGE_RISK_Z_ALPHA={params.edge_risk_z_alpha:.3f}, "
        f"EDGE_RISK_MIN_MULT={params.edge_risk_min_mult:.2f}, "
        f"EDGE_RISK_MAX_MULT={params.edge_risk_max_mult:.2f}, "
        f"EDGE_MOMENTUM_TILT_ENABLED={params.edge_momentum_tilt_enabled}, "
        f"EDGE_MOMENTUM_LOOKBACK_TRADES={params.edge_momentum_lookback_trades}, "
        f"EDGE_MOMENTUM_TILT={params.edge_momentum_tilt:.2f}, "
        f"EDGE_MULTI_LOGIC_ENABLED={params.edge_multi_logic_enabled}, "
        f"EDGE_BREADTH_FLOOR={params.edge_breadth_floor:.2f}, "
        f"EDGE_BREADTH_EXPOSURE={params.edge_breadth_exposure:.2f}, "
        f"EDGE_REGIME_LOOKBACK_TRADES={params.edge_regime_lookback_trades}, "
        f"EDGE_REGIME_VOL_SOFT={params.edge_regime_vol_soft:.2f}, "
        f"EDGE_REGIME_VOL_HARD={params.edge_regime_vol_hard:.2f}, "
        f"EDGE_DD_LEVEL1={params.edge_dd_level1:.2f}, "
        f"EDGE_DD_LEVEL2={params.edge_dd_level2:.2f}, "
        f"EDGE_CORR_LOOKBACK_TRADES={params.edge_corr_lookback_trades}, "
        f"EDGE_CORR_SOFT={params.edge_corr_soft:.2f}, "
        f"EDGE_CORR_HARD={params.edge_corr_hard:.2f}, "
        f"ENABLE_TIME_FILTER={ENABLE_TIME_FILTER}"
    )
    _log_info(
        "Execution safeguards: "
        "OPEN_BUFFER_CET=09:00-09:15, "
        "MIN_STOP_DISTANCE_PCT=0.20%"
    )
    _log_info(f"Active symbols: {', '.join(SYMBOLS_MAP.keys())}")
    _log_info(f"Symbol strategy modes: {params.symbol_strategy_mode}")


LOCK_FILE = Path("t212_miner_bot/.bot_runtime.lock")


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        # Windows-compatible process existence check used by runtime lock.
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, int(pid))
        if handle == 0:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # On Windows this can happen for live processes we cannot signal.
        return True
    except OSError:
        return False
    return True


def _acquire_single_instance_lock() -> int:
    """
    Prevent multiple bot instances from running concurrently on the same machine.
    """
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    payload = f"{pid}\n"

    for _ in range(2):
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            return pid
        except FileExistsError:
            try:
                existing_raw = LOCK_FILE.read_text(encoding="utf-8").strip()
                existing_pid = int(existing_raw) if existing_raw else -1
            except Exception:
                existing_pid = -1

            if _pid_is_running(existing_pid):
                raise RuntimeError(
                    f"Another bot instance is already running (pid={existing_pid}). "
                    "Stop it before starting a new one."
                )
            # Stale lock file, remove and retry once.
            try:
                LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                raise RuntimeError("Could not remove stale bot lock file.")

    raise RuntimeError("Could not acquire bot runtime lock.")


def _release_single_instance_lock(owner_pid: int) -> None:
    try:
        existing_raw = LOCK_FILE.read_text(encoding="utf-8").strip()
        existing_pid = int(existing_raw) if existing_raw else -1
    except Exception:
        existing_pid = -1
    if existing_pid == owner_pid:
        LOCK_FILE.unlink(missing_ok=True)


async def _log_ticker_resolution(client: AsyncT212Client) -> None:
    _log_info("Validating Trading 212 ticker mapping before live loop...")
    resolution_errors: list[str] = []
    for yf_symbol, configured_ticker in SYMBOLS_MAP.items():
        try:
            # Resolve from user-facing symbol so mapping is validated against live metadata.
            resolved_ticker = await client.resolve_ticker(yf_symbol)
            if resolved_ticker != configured_ticker:
                _log_warn(f"{yf_symbol}: configured={configured_ticker} resolved={resolved_ticker}")
            else:
                _log_success(f"{yf_symbol}: ticker OK ({resolved_ticker})")
        except T212APIError as exc:
            resolution_errors.append(
                f"{yf_symbol}: configured={configured_ticker} error={exc}"
            )
    if resolution_errors:
        raise RuntimeError(
            "Ticker preflight validation failed:\n" + "\n".join(resolution_errors)
        )


async def run_bot(max_cycles: int | None = None, wait_for_candle: bool = True) -> None:
    params = StrategyParams()
    file_logger = _setup_file_logging()
    _log_info("Starting Miner DTosc Trading 212 paper bot.")
    _log_startup_settings(params)
    if BOT_SAFE_MODE:
        _log_warn("SAFE_MODE is enabled: no new orders will be submitted.")

    async with AsyncT212Client() as client:
        await _log_ticker_resolution(client)
        manager = ExecutionManager(client=client, params=params)
        try:
            reconcile_logs = await manager.startup_reconcile()
        except Exception as exc:
            _log_warn(f"Startup reconcile skipped due to error: {exc}")
            reconcile_logs = []
        for line in reconcile_logs:
            if line.startswith("[INFO] "):
                _log_info(line[len("[INFO] ") :])
            elif line.startswith("[WARN] "):
                _log_warn(line[len("[WARN] ") :])
            else:
                _log_warn(line)
        api_failure_streak = 0
        repeated_alert_threshold = 3
        cycle = 0

        while True:
            try:
                if wait_for_candle:
                    wait_seconds = _seconds_until_next_candle_close()
                    next_wake = _now_local() + timedelta(seconds=wait_seconds)
                    _log_info(f"Sleeping {wait_seconds:.1f}s until candle close cycle at {next_wake.isoformat()}")
                    await asyncio.sleep(wait_seconds)
                else:
                    _log_info("No-wait mode: running cycle immediately.")

                try:
                    equity = await client.get_equity()
                    api_failure_streak = 0
                except T212APIError as exc:
                    equity = TOTAL_PORTFOLIO_EUR
                    api_failure_streak += 1
                    _log_warn(f"Equity fetch failed, using fallback {TOTAL_PORTFOLIO_EUR:.2f} EUR: {exc}")
                    if api_failure_streak == repeated_alert_threshold:
                        asyncio.create_task(
                            send_email_alert(
                                subject="Critical Error - Repeated API Failures",
                                body=(
                                    f"Issue: Equity fetch failed {api_failure_streak} consecutive times.\n"
                                    f"Latest error: {exc}"
                                ),
                            )
                        )

                _log_info(f"Current Equity: {equity:.2f} EUR")
                signals = await get_latest_signals()

                for symbol, snap in signals.items():
                    if not snap.get("ready"):
                        reason = snap.get("reason", "signal_not_ready")
                        if reason == "stale_data":
                            bar_ts = snap.get("bar_ts")
                            bar_age = snap.get("bar_age_seconds")
                            extra = []
                            if bar_ts:
                                extra.append(f"bar_ts={bar_ts}")
                            if isinstance(bar_age, (int, float)):
                                extra.append(f"age_s={float(bar_age):.1f}")
                            suffix = f" ({', '.join(extra)})" if extra else ""
                            _log_warn(f"{symbol}: {reason}{suffix}")
                        else:
                            _log_warn(f"{symbol}: {reason}")
                        continue
                    _log_info(
                        f"{symbol} Regime={snap['regime']} Trigger={snap['trigger']} "
                        f"High={snap['signal_high']:.4f} Low={snap['signal_low']:.4f}"
                    )

                actions = await manager.process(
                    signals=signals,
                    equity=equity,
                )
                # Observability: write one compact row per cycle.
                try:
                    _append_cycle_csv_row(
                        row={
                            "ts_utc": _now_local().isoformat(),
                            "equity_eur": round(float(equity), 2),
                            "signals_ready": sum(1 for s in signals.values() if s.get("ready")),
                            "signals_total": len(signals),
                            "actions_count": len(actions or []),
                            "actions": " | ".join(actions or [])[:2000],
                        }
                    )
                except Exception as exc:
                    _log_warn(f"CSV journal write failed: {exc}")
                if actions:
                    for action in actions:
                        if "without confirmed protective sl" in action.lower():
                            # Highlight settlement-race recovery mode so operators can react quickly.
                            _log_warn(f"[RECOVERY] {action}")
                            continue
                        if action.startswith("[INFO] "):
                            _log_info(action[len("[INFO] ") :])
                            continue
                        if "failed" in action.lower() or "error" in action.lower():
                            _log_error(action)
                        elif "cancel" in action.lower() or "warn" in action.lower():
                            _log_warn(action)
                        else:
                            _log_success(action)
                else:
                    _log_info("No actions this cycle.")
                try:
                    file_logger.info(
                        "cycle equity=%.2f ready=%d/%d actions=%d",
                        float(equity),
                        sum(1 for s in signals.values() if s.get("ready")),
                        len(signals),
                        len(actions or []),
                    )
                except Exception:
                    pass

                # Reset streak after a successful cycle.
                api_failure_streak = 0
                cycle += 1
                if max_cycles is not None and cycle >= max_cycles:
                    _log_info(f"Reached max cycles ({max_cycles}), exiting.")
                    return
            except Exception as exc:
                _log_error(f"Main loop error: {exc}")
                api_failure_streak += 1
                if api_failure_streak == repeated_alert_threshold:
                    asyncio.create_task(
                        send_email_alert(
                            subject="Critical Error - Main Loop Failure",
                            body=(
                                f"Issue: Bot main loop failed {api_failure_streak} consecutive times.\n"
                                f"Latest error: {exc}"
                            ),
                        )
                    )
                await asyncio.sleep(2.0)
                cycle += 1
                if max_cycles is not None and cycle >= max_cycles:
                    _log_info(f"Reached max cycles ({max_cycles}) after error, exiting.")
                    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Miner DTosc Trading 212 bot.")
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Run only N cycles, then exit (default: infinite).",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Skip candle-close waiting (useful for smoke tests).",
    )
    args = parser.parse_args()
    lock_owner_pid = _acquire_single_instance_lock()
    try:
        asyncio.run(run_bot(max_cycles=args.max_cycles, wait_for_candle=not args.no_wait))
    finally:
        _release_single_instance_lock(lock_owner_pid)
