"""Owner executor — trades the owner's T212 account with the momentum strategy.

Runs the validated cross-sectional momentum strategy (see
``t212_miner_bot.momentum``) server-side against the owner's personal T212
account, as a FastAPI async background task.  It rebalances MONTHLY: hold the
top-8 strongest global stocks equal-weight when the market regime is risk-on,
else cash.  Long-only.

Paper vs live is controlled ENTIRELY by which credentials are configured —
the strategy code is identical:

  OWNER_T212_API_KEY    owner's T212 key (a DEMO key → paper, a LIVE key → live)
  OWNER_T212_BASE_URL   https://demo.trading212.com  (paper)  ← set this for paper
                        https://live.trading212.com  (real money)
  OWNER_DRY_RUN         "true" to compute + log the rebalance but place NO orders
  OWNER_CHECK_INTERVAL_S  how often to wake and check the monthly gate (default 6h)

NOTE: T212 demo and live use DIFFERENT hostnames AND different API keys, so going
live means changing BOTH OWNER_T212_API_KEY and OWNER_T212_BASE_URL.

This module places real orders only when OWNER_DRY_RUN is not "true".  It does
NOT touch the customer signal feed (that is t212_miner_runner.py).
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

_log = logging.getLogger("uvicorn.error")

# Wake cadence: the strategy only acts on a monthly gate, so a few checks per day
# is plenty (and survives restarts — the gate is persisted in state).
_CHECK_INTERVAL_S = int(os.getenv("OWNER_CHECK_INTERVAL_S", str(6 * 3600)).strip() or str(6 * 3600))
_OWNER_DRY_RUN = os.getenv("OWNER_DRY_RUN", "false").strip().lower() in ("1", "true", "yes")


def _add_server_app_to_syspath() -> None:
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    server_app = repo_root / "Server-App"
    if str(server_app) not in sys.path:
        sys.path.insert(0, str(server_app))


def _apply_owner_env(api_key: str, base_url: str) -> None:
    """Inject owner T212 credentials before T212Client reads them."""
    os.environ["T212_API_KEY"] = api_key
    os.environ["T212_BASE_URL"] = base_url


async def run_owner_executor_forever(api_key: str, base_url: str) -> None:
    """FastAPI background task: trade the owner's T212 account with momentum."""
    _add_server_app_to_syspath()
    _apply_owner_env(api_key, base_url)

    try:
        from t212_miner_bot.momentum import MomentumExecutor, PROD
    except ImportError as exc:
        _log.error(
            "owner_executor: failed to import momentum strategy (%s). "
            "Is Server-App/ present? Owner executor will not run.",
            exc,
        )
        return

    loop = asyncio.get_event_loop()
    try:
        executor = MomentumExecutor(dry_run=_OWNER_DRY_RUN)
    except Exception as exc:
        _log.exception("owner_executor: init failed — executor will not run: %s", exc)
        return

    _log.info(
        "owner_executor: MOMENTUM v6 ready (%s) — top-%d, %s blend, "
        "monthly rebalance, against %s",
        "DRY-RUN (no orders)" if _OWNER_DRY_RUN else "LIVE ORDERS",
        PROD.top_k, "+".join(str(lb) for lb in PROD.lookbacks), base_url,
    )

    while True:
        try:
            result = await loop.run_in_executor(None, executor.maybe_rebalance)
            _log.info("owner_executor: %s", result)
        except Exception as exc:
            _log.exception("owner_executor cycle error: %s", exc)
            await asyncio.sleep(60)
        await asyncio.sleep(_CHECK_INTERVAL_S)
