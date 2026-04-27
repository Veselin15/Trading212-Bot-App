"""
Try alternative portfolio allocation logics on top of current live strategy returns.
Goal: maximize total return % over 2-year window.
"""

from __future__ import annotations

import argparse
import itertools
import statistics
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests.t212_edge_weighted_risk_backtest import (  # noqa: E402
    _load_symbol_5m,
    _simulate_month,
)
from t212_miner_bot.config import StrategyParams  # noqa: E402


def _monthly_symbol_returns(days: int, slippage_bps: float) -> tuple[pd.DataFrame, list[str]]:
    params = StrategyParams()
    symbols = list(params.symbol_strategy_mode.keys())
    raw = {s: _load_symbol_5m(s) for s in symbols}
    if any(df.empty for df in raw.values()):
        missing = [s for s, df in raw.items() if df.empty]
        raise RuntimeError(f"Missing/empty local data for symbols: {missing}")

    max_end = min(df.index.max() for df in raw.values())
    start = max_end - pd.Timedelta(days=days)
    sliced = {s: df[(df.index >= start) & (df.index <= max_end)].copy() for s, df in raw.items()}

    first_month = min(df.index.min() for df in sliced.values()).tz_localize(None).to_period("M")
    last_month = max(df.index.max() for df in sliced.values()).tz_localize(None).to_period("M")
    months = pd.period_range(first_month, last_month, freq="M")

    rows: list[dict[str, float | str]] = []
    for m in months:
        m_start = pd.Timestamp(m.start_time, tz="UTC")
        m_end = pd.Timestamp(m.end_time, tz="UTC")
        row: dict[str, float | str] = {"month": str(m)}
        for s in symbols:
            bars = sliced[s][(sliced[s].index >= m_start) & (sliced[s].index <= m_end)].copy()
            ret, _ = _simulate_month(s, bars, params, slippage_bps=slippage_bps)
            row[s] = float(ret)
        rows.append(row)
    return pd.DataFrame(rows), symbols


def _norm_weights(raw: dict[str, float], symbols: list[str]) -> dict[str, float]:
    clipped = {s: max(raw.get(s, 0.0), 0.0001) for s in symbols}
    total = sum(clipped.values())
    if total <= 0:
        return {s: 1.0 / len(symbols) for s in symbols}
    return {s: clipped[s] / total for s in symbols}


def _ewr_weights(
    history: dict[str, list[float]],
    symbols: list[str],
    *,
    lookback: int = 4,
    alpha: float = 0.25,
    min_mult: float = 0.6,
    max_mult: float = 1.4,
    min_samples: int = 2,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for s in symbols:
        h = history[s][-lookback:]
        if len(h) < min_samples:
            scores[s] = 0.0
            continue
        mu = sum(h) / len(h)
        sigma = statistics.pstdev(h) if len(h) > 1 else 0.0
        scores[s] = mu - (0.5 * sigma)
    vals = list(scores.values())
    g_mu = sum(vals) / len(vals) if vals else 0.0
    g_sigma = (statistics.pstdev(vals) if len(vals) > 1 else 1.0) or 1.0
    raw: dict[str, float] = {}
    for s in symbols:
        z = (scores[s] - g_mu) / g_sigma
        raw[s] = min(max_mult, max(min_mult, 1.0 + alpha * z))
    return _norm_weights(raw, symbols)


def _simulate_logic(
    monthly: pd.DataFrame,
    symbols: list[str],
    *,
    mom_lookback: int,
    mom_tilt: float,
    vol_lookback: int,
    vol_penalty: float,
    breadth_floor: float,
    breadth_exposure: float,
) -> float:
    eq = 1.0
    hist: dict[str, list[float]] = {s: [] for s in symbols}
    for _, r in monthly.iterrows():
        ret = {s: float(r[s]) for s in symbols}
        w = _ewr_weights(hist, symbols)

        # Momentum tilt: overweight recent winners.
        if mom_tilt > 0:
            tilted: dict[str, float] = {}
            for s in symbols:
                h = hist[s][-mom_lookback:]
                mom = (sum(h) / len(h)) if h else 0.0
                mult = 1.0 + mom_tilt * max(min(mom / 10.0, 1.0), -1.0)
                tilted[s] = w[s] * max(mult, 0.2)
            w = _norm_weights(tilted, symbols)

        # Volatility penalty: trim unstable symbols.
        if vol_penalty > 0:
            vol_adj: dict[str, float] = {}
            for s in symbols:
                h = hist[s][-vol_lookback:]
                v = statistics.pstdev(h) if len(h) > 1 else 0.0
                mult = 1.0 / (1.0 + vol_penalty * (v / 10.0))
                vol_adj[s] = w[s] * max(mult, 0.3)
            w = _norm_weights(vol_adj, symbols)

        basket_ret = sum(w[s] * ret[s] for s in symbols)

        # Breadth exposure: if too few symbols have positive trailing edge, reduce gross exposure.
        if breadth_floor > 0:
            pos = 0
            for s in symbols:
                h = hist[s][-mom_lookback:]
                edge = (sum(h) / len(h)) if h else 0.0
                if edge > 0:
                    pos += 1
            breadth = pos / len(symbols)
            exposure = 1.0 if breadth >= breadth_floor else breadth_exposure
        else:
            exposure = 1.0

        realized = basket_ret * exposure
        eq *= (1.0 + realized / 100.0)

        for s in symbols:
            hist[s].append(ret[s])

    return (eq - 1.0) * 100.0


def run(days: int, slippage_bps: float) -> None:
    monthly, symbols = _monthly_symbol_returns(days=days, slippage_bps=slippage_bps)

    base_eq = 1.0
    for _, r in monthly.iterrows():
        base_eq *= (1.0 + (sum(float(r[s]) for s in symbols) / len(symbols)) / 100.0)
    baseline_ret = (base_eq - 1.0) * 100.0

    ewr_ret = _simulate_logic(
        monthly,
        symbols,
        mom_lookback=3,
        mom_tilt=0.0,
        vol_lookback=3,
        vol_penalty=0.0,
        breadth_floor=0.0,
        breadth_exposure=1.0,
    )

    rows: list[dict[str, float]] = []
    tested = 0
    for mom_lookback, mom_tilt, vol_lookback, vol_penalty, breadth_floor, breadth_exposure in itertools.product(
        [2, 3, 4, 6],
        [0.10, 0.15, 0.20, 0.25, 0.30],
        [2, 3, 4],
        [0.00, 0.10, 0.20, 0.30],
        [0.00, 0.50, 0.75],
        [0.70, 0.80, 0.90],
    ):
        if breadth_floor == 0.0 and breadth_exposure != 0.70:
            continue
        ret = _simulate_logic(
            monthly,
            symbols,
            mom_lookback=mom_lookback,
            mom_tilt=mom_tilt,
            vol_lookback=vol_lookback,
            vol_penalty=vol_penalty,
            breadth_floor=breadth_floor,
            breadth_exposure=breadth_exposure,
        )
        rows.append(
            {
                "ret": ret,
                "mom_lb": float(mom_lookback),
                "mom_tilt": mom_tilt,
                "vol_lb": float(vol_lookback),
                "vol_pen": vol_penalty,
                "breadth_floor": breadth_floor,
                "breadth_exp": breadth_exposure,
            }
        )
        tested += 1
        if tested % 120 == 0:
            print(f"[RUN] {tested} candidates complete", flush=True)

    ranked = sorted(rows, key=lambda x: x["ret"], reverse=True)
    best = ranked[0] if ranked else None

    print(
        f"[INFO] Alt logic lab done | months={len(monthly)} symbols={symbols} "
        f"days={days} slippage_bps={slippage_bps:.2f} tested={tested}"
    )
    print(f"[BASELINE] return={baseline_ret:.2f}%")
    print(f"[EWR]      return={ewr_ret:.2f}%")
    if best is None:
        print("[WARN] No valid candidates.")
        return
    print(
        "[BEST ALT LOGIC] "
        f"return={best['ret']:.2f}% | mom_lb={int(best['mom_lb'])} mom_tilt={best['mom_tilt']:.2f} "
        f"vol_lb={int(best['vol_lb'])} vol_pen={best['vol_pen']:.2f} "
        f"breadth_floor={best['breadth_floor']:.2f} breadth_exp={best['breadth_exp']:.2f}"
    )
    print(f"[DELTA VS BASELINE] {best['ret'] - baseline_ret:.2f} pp")
    print(f"[DELTA VS EWR]      {best['ret'] - ewr_ret:.2f} pp")

    print("\nTop 12 by return:")
    print("-" * 95)
    print(
        f"{'rank':<5} {'ret%':>8} {'mom_lb':>7} {'mom_tilt':>9} {'vol_lb':>7} {'vol_pen':>8} "
        f"{'breadth_floor':>13} {'breadth_exp':>11}"
    )
    print("-" * 95)
    for i, x in enumerate(ranked[:12], start=1):
        print(
            f"{i:<5} {x['ret']:>8.2f} {int(x['mom_lb']):>7d} {x['mom_tilt']:>9.2f} {int(x['vol_lb']):>7d} "
            f"{x['vol_pen']:>8.2f} {x['breadth_floor']:>13.2f} {x['breadth_exp']:>11.2f}"
        )
    print("-" * 95)


def main() -> None:
    parser = argparse.ArgumentParser(description="Alternative logic lab sweep for return %.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    args = parser.parse_args()
    run(days=max(int(args.days), 120), slippage_bps=max(float(args.slippage_bps), 0.0))


if __name__ == "__main__":
    main()
