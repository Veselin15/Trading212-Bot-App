"""
Per-position cap sweep
======================

Answers one question: **how much of the account should a single position be
allowed to consume?**

The live owner-executor and this backtest share the exact same sizing path
(`calculate_position_size` + `position_cap_ceiling`), so the numbers here are a
faithful preview of what changing ``PROD_POS_CEILING`` does to live behaviour.

It runs the production engine (same strategy, same 4.2x bull tilt, same slots /
exposure) once per candidate ceiling and prints a comparison on the strict
out-of-sample year — the honest benchmark.  Lower ceiling = more diversified,
smaller single trades; higher ceiling = the current "concentrate into one name"
behaviour.

Usage
-----
    python -m t212_miner_bot.sim_position_cap
    python -m t212_miner_bot.sim_position_cap --caps 0.15,0.20,0.25,0.30,0.40,0.90
    python -m t212_miner_bot.sim_position_cap --full   # also show full 5-year

Requires the historical OHLCV CSVs in ``Server-App/data`` and trained models in
``Server-App/t212_miner_bot/models`` (same inputs as five_year_portfolio_sim).
"""
from __future__ import annotations

import argparse
import logging
import time
from typing import Dict, List

import pandas as pd

from t212_miner_bot.config import (
    EU_SYMBOLS,
    TRAIN_END,
    TEST_START,
    INITIAL_CAPITAL,
    SYMBOL_THRESHOLDS,
)
from t212_miner_bot.data_loader import get_available_symbols
from t212_miner_bot.production import build_engine, PROD_SLOTS, PROD_RISK_CEILING
from t212_miner_bot.five_year_portfolio_sim import (
    _prepare_full_data,
    _score_all,
    _slice_by_dates,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_CAPS = [0.15, 0.20, 0.25, 0.30, 0.40, 0.90]


def _run_cap(
    data_slice: Dict[str, pd.DataFrame],
    proba_cache: Dict[str, pd.Series],
    cap: float,
) -> Dict:
    """Run the production engine with a given per-position ceiling."""
    engine = build_engine(
        initial_capital=INITIAL_CAPITAL,
        mode="safe",                       # live-recommended (throttles on)
        position_cap_ceiling=cap,
        risk_cap_ceiling=PROD_RISK_CEILING,
    )
    engine.run(
        data_slice,
        signal_cache=proba_cache,
        symbol_thresholds=SYMBOL_THRESHOLDS,
    )
    rep = engine.performance_report()

    # Largest single position the engine actually opened (entry notional in EUR),
    # expressed as % of starting capital — the concentration number the user
    # cares about ("don't buy everything").  Approximate once equity drifts from
    # the start value, but a faithful guide to how binding the cap is.
    max_notional = 0.0
    for t in getattr(engine, "trades", []) or []:
        entry = getattr(t, "entry_price", 0.0) or 0.0
        shares = getattr(t, "shares", 0.0) or 0.0
        max_notional = max(max_notional, entry * shares)
    rep["max_position_eur"] = max_notional
    rep["max_position_weight"] = max_notional / INITIAL_CAPITAL if INITIAL_CAPITAL else 0.0
    return rep


def _print_table(title: str, rows: List[tuple]) -> None:
    print("\n" + "=" * 100)
    print(f"  {title}   (PROD_SLOTS={PROD_SLOTS}, bull tilt 4.2x kept)")
    print("=" * 100)
    print(f"  {'cap %':>6} | {'return %':>9} | {'max DD %':>8} | {'Sharpe':>7} | "
          f"{'win %':>6} | {'trades':>6} | {'PF':>5} | {'final EUR':>11} | {'max pos %':>9}")
    print("  " + "-" * 96)
    for cap, r in rows:
        if "error" in r:
            print(f"  {cap*100:>5.0f}% | {r['error']}")
            continue
        mw = r.get("max_position_weight", 0.0) * 100
        print(
            f"  {cap*100:>5.0f}% | {r['return_pct']:>9.2f} | {r['max_drawdown']*100:>8.2f} | "
            f"{r['sharpe_ratio']:>7.2f} | {r['win_rate']*100:>6.1f} | {r['total_trades']:>6} | "
            f"{r['profit_factor']:>5.2f} | {r['final_equity']:>11,.0f} | {mw:>8.1f}%"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-position cap sweep")
    parser.add_argument("--caps", type=str, default=None,
                        help="comma-separated ceilings, e.g. 0.15,0.20,0.30,0.90")
    parser.add_argument("--full", action="store_true",
                        help="also run the full 5-year window (in+out of sample)")
    args = parser.parse_args()

    caps = (
        [float(x) for x in args.caps.split(",")]
        if args.caps else list(DEFAULT_CAPS)
    )

    t0 = time.time()
    available = set(get_available_symbols())
    symbols = [s for s in EU_SYMBOLS if s in available]
    log.info("Universe: %d symbols", len(symbols))
    if len(symbols) < 5:
        raise RuntimeError(f"Too few symbols found: {symbols}")

    full_data = _prepare_full_data(symbols)
    proba_cache = _score_all(full_data)
    if not proba_cache:
        raise RuntimeError(
            "No models found / scored. Run `python -m t212_miner_bot.run_pipeline` "
            "and ensure Server-App/data CSVs exist."
        )

    test_start_ts = pd.Timestamp(TEST_START, tz="UTC")
    oos_slice = _slice_by_dates(full_data, test_start_ts, None)

    log.info("Sweeping caps on OOS year: %s", caps)
    oos_rows = [(c, _run_cap(oos_slice, proba_cache, c)) for c in caps]
    _print_table("OUT-OF-SAMPLE YEAR (production benchmark)", oos_rows)

    if args.full:
        full_slice = _slice_by_dates(full_data, None, None)
        full_rows = [(c, _run_cap(full_slice, proba_cache, c)) for c in caps]
        _print_table("FULL 5-YEAR WINDOW", full_rows)

    print("  How to read this:")
    print("   - 'max pos %' is the largest single position the bot actually took.")
    print(f"     At cap 0.90 that's ~90% (your Sanofi trade). Aim for ~{100/PROD_SLOTS:.0f}% "
          f"(= 100/PROD_SLOTS) for a balanced {PROD_SLOTS}-slot book.")
    print("   - Pick the lowest cap whose return/Sharpe stays close to the 0.90 row")
    print("     while max-DD and concentration drop. Set it live with:")
    print("       PROD_POS_CEILING=<chosen>   (env var on the homeserver)")
    log.info("Done in %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()
