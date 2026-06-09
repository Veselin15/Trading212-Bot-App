"""Owner executor — runs the full live trading engine server-side.

Wraps the synchronous ``LiveTrader`` from ``t212_miner_bot.live_trader`` as a
FastAPI async background task so the server trades the owner's personal T212
account automatically without needing the desktop app to be open.

Architecture
------------
  - ``run_owner_executor_forever()`` is started as an ``asyncio.create_task``
    from ``main.py`` when ``OWNER_EXECUTOR_ENABLED=true``.
  - It sleeps asynchronously until the next 5-minute schedule tick (using
    ``asyncio.sleep`` so it never blocks the FastAPI event loop).
  - Each tick it offloads the synchronous ``LiveTrader._run_cycle()`` to a
    thread pool executor.  This keeps ML inference + yfinance HTTP calls off
    the async event loop entirely.
  - State is persisted to ``Server-App/t212_miner_bot/live_state.json``
    between cycles (same file as running the standalone live_trader script).

Environment variables
---------------------
  OWNER_EXECUTOR_ENABLED   "true" to enable (default: false)
  OWNER_T212_API_KEY       Your personal T212 API key  ← REQUIRED when enabled
  OWNER_T212_BASE_URL      Default: https://live.trading212.com
                           Use https://demo.trading212.com to paper-trade server-side

Example .env addition
---------------------
  OWNER_EXECUTOR_ENABLED=true
  OWNER_T212_API_KEY=your-key-here
  # OWNER_T212_BASE_URL=https://demo.trading212.com   ← uncomment to paper-trade
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

_log = logging.getLogger("uvicorn.error")

_SCHEDULE_MINUTES = int(os.getenv("BOT_SCHEDULE_MINUTES", "5").strip() or "5")
_SIGNAL_BUFFER_S  = int(os.getenv("BOT_SIGNAL_BUFFER_S", "20"))
_MAX_JITTER_S     = float(os.getenv("BOT_JITTER_S", "3.0"))


def _add_server_app_to_syspath() -> None:
    here      = Path(__file__).resolve()
    repo_root = here.parents[3]
    server_app = repo_root / "Server-App"
    if str(server_app) not in sys.path:
        sys.path.insert(0, str(server_app))


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _seconds_until_next_schedule() -> float:
    now     = _now_utc()
    rem     = now.minute % _SCHEDULE_MINUTES
    wait_min = (_SCHEDULE_MINUTES - rem) if rem > 0 else _SCHEDULE_MINUTES
    wait_sec = wait_min * 60 - (now.second + now.microsecond / 1e6)
    return max(wait_sec + _SIGNAL_BUFFER_S + random.uniform(0, _MAX_JITTER_S), 1.0)


def _is_new_15m_close(ts: datetime) -> bool:
    return (ts.minute % 15) == 0


def _apply_owner_env(api_key: str, base_url: str) -> None:
    """Inject owner T212 credentials into os.environ before LiveTrader reads them."""
    os.environ["T212_API_KEY"]  = api_key
    os.environ["T212_BASE_URL"] = base_url


async def run_owner_executor_forever(api_key: str, base_url: str) -> None:
    """FastAPI background task: trade the owner's T212 account server-side."""
    _add_server_app_to_syspath()

    # Inject credentials before LiveTrader / T212Client read os.getenv
    _apply_owner_env(api_key, base_url)

    try:
        from t212_miner_bot.live_trader import LiveTrader
    except ImportError as exc:
        _log.error(
            "owner_executor: failed to import LiveTrader (%s). "
            "Is Server-App/ present in the container with trained models?",
            exc,
        )
        return

    _log.info(
        "owner_executor: starting LiveTrader against %s …",
        base_url,
    )

    # Startup is synchronous (loads models, resolves tickers, syncs broker state)
    # Run it in a thread so it doesn't block the event loop during server startup.
    loop = asyncio.get_event_loop()
    try:
        trader: "LiveTrader" = LiveTrader(dry_run=False)
        await loop.run_in_executor(None, trader.startup)
    except Exception as exc:
        _log.exception("owner_executor: startup failed — executor will not run: %s", exc)
        return

    _log.info(
        "owner_executor: LiveTrader ready — %d open positions in state.",
        len(trader.positions),
    )

    while True:
        wait_s = _seconds_until_next_schedule()
        _log.debug("owner_executor: sleeping %.0fs until next 5m tick…", wait_s)
        await asyncio.sleep(wait_s)

        now_utc      = _now_utc()
        allow_entries = _is_new_15m_close(now_utc)
        tick_tag      = "ENTRY" if allow_entries else "MGMT"
        _log.info(
            "owner_executor cycle (%s UTC) [%s]",
            now_utc.strftime("%Y-%m-%d %H:%M"),
            tick_tag,
        )

        try:
            await loop.run_in_executor(
                None,
                trader._run_cycle,  # noqa: SLF001  (private, but same package)
                allow_entries,
            )
            # Save state synchronously (fast file write; inline is fine)
            trader._save_state()  # noqa: SLF001
        except Exception as exc:
            _log.exception("owner_executor cycle error: %s", exc)
            # Sleep briefly so a recurring error doesn't spin-loop
            await asyncio.sleep(30)
