"""
Backtest strongest next-layer portfolio logic on top of live strategy:
- Baseline (equal-weight)
- EWR only
- EWR + Regime exposure scaling + Drawdown throttle
"""

from __future__ import annotations

import argparse
import itertools
import math
import statistics
import sys
from dataclasses import dataclass
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


@dataclass
class ComboCfg:
    ewr_lookback: int
    ewr_alpha: float
    ewr_min_mult: float
    ewr_max_mult: float
    ewr_min_samples: int
    regime_lookback: int
    regime_vol_soft: float
    regime_vol_hard: float
    regime_win_soft: float
    regime_win_hard: float
    regime_exposure_soft: float
    regime_exposure_hard: float
    dd1: float
    dd2: float
    dd_exposure1: float
    dd_exposure2: float


def _edge_weights(
    history: dict[str, list[float]],
    symbols: list[str],
    *,
    lookback: int,
    alpha: float,
    min_mult: float,
    max_mult: float,
    min_samples: int,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for s in symbols:
        h = history.get(s, [])[-lookback:]
        if len(h) < min_samples:
            scores[s] = 0.0
            continue
        mean_r = sum(h) / len(h)
        std_r = statistics.pstdev(h) if len(h) > 1 else 0.0
        scores[s] = mean_r - (0.5 * std_r)

    vals = list(scores.values())
    mu = sum(vals) / len(vals) if vals else 0.0
    sigma = (statistics.pstdev(vals) if len(vals) > 1 else 1.0) or 1.0
    mults: dict[str, float] = {}
    for s in symbols:
        z = (scores[s] - mu) / sigma
        m = 1.0 + (alpha * z)
        mults[s] = min(max_mult, max(min_mult, m))
    total = sum(mults.values())
    if total <= 0:
        return {s: 1.0 / len(symbols) for s in symbols}
    return {s: mults[s] / total for s in symbols}


def _max_drawdown_pct(equity_curve: list[float]) -> float:
    peak = equity_curve[0] if equity_curve else 1.0
    max_dd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        dd = (peak - e) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd * 100.0


def _regime_exposure(trailing_portfolio_returns: list[float], cfg: ComboCfg) -> float:
    h = trailing_portfolio_returns[-cfg.regime_lookback :]
    if len(h) < cfg.regime_lookback:
        return 1.0
    vol = statistics.pstdev(h) if len(h) > 1 else 0.0
    win = sum(1 for x in h if x > 0.0) / len(h)
    if vol >= cfg.regime_vol_hard or win <= cfg.regime_win_hard:
        return cfg.regime_exposure_hard
    if vol >= cfg.regime_vol_soft or win <= cfg.regime_win_soft:
        return cfg.regime_exposure_soft
    return 1.0


def _dd_exposure(current_equity: float, peak_equity: float, cfg: ComboCfg) -> float:
    if peak_equity <= 0:
        return 1.0
    dd = (peak_equity - current_equity) / peak_equity
    if dd >= cfg.dd2:
        return cfg.dd_exposure2
    if dd >= cfg.dd1:
        return cfg.dd_exposure1
    return 1.0


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


def _run_equal(monthly: pd.DataFrame, symbols: list[str]) -> tuple[float, float]:
    eq = 1.0
    curve = [eq]
    for _, r in monthly.iterrows():
        ret = sum(float(r[s]) for s in symbols) / len(symbols)
        eq *= (1.0 + ret / 100.0)
        curve.append(eq)
    return (eq - 1.0) * 100.0, _max_drawdown_pct(curve)


def _run_combo(monthly: pd.DataFrame, symbols: list[str], cfg: ComboCfg, use_exposure_layers: bool) -> tuple[float, float]:
    eq = 1.0
    peak = 1.0
    curve = [eq]
    symbol_hist: dict[str, list[float]] = {s: [] for s in symbols}
    portfolio_hist: list[float] = []

    for _, r in monthly.iterrows():
        mret = {s: float(r[s]) for s in symbols}
        w = _edge_weights(
            symbol_hist,
            symbols,
            lookback=cfg.ewr_lookback,
            alpha=cfg.ewr_alpha,
            min_mult=cfg.ewr_min_mult,
            max_mult=cfg.ewr_max_mult,
            min_samples=cfg.ewr_min_samples,
        )
        base_ret = sum(w[s] * mret[s] for s in symbols)
        exposure = 1.0
        if use_exposure_layers:
            exposure = min(
                _regime_exposure(portfolio_hist, cfg),
                _dd_exposure(eq, peak, cfg),
            )
        realized = exposure * base_ret
        eq *= (1.0 + realized / 100.0)
        peak = max(peak, eq)
        curve.append(eq)
        portfolio_hist.append(realized)
        for s in symbols:
            symbol_hist[s].append(mret[s])

    return (eq - 1.0) * 100.0, _max_drawdown_pct(curve)


def run(days: int, slippage_bps: float) -> None:
    monthly, symbols = _monthly_symbol_returns(days=days, slippage_bps=slippage_bps)
    base_ret, base_dd = _run_equal(monthly, symbols)

    ewr_cfg = ComboCfg(
        ewr_lookback=4,
        ewr_alpha=0.25,
        ewr_min_mult=0.60,
        ewr_max_mult=1.40,
        ewr_min_samples=2,
        regime_lookback=4,
        regime_vol_soft=5.0,
        regime_vol_hard=6.5,
        regime_win_soft=0.50,
        regime_win_hard=0.40,
        regime_exposure_soft=0.85,
        regime_exposure_hard=0.60,
        dd1=0.10,
        dd2=0.18,
        dd_exposure1=0.80,
        dd_exposure2=0.60,
    )
    ewr_ret, ewr_dd = _run_combo(monthly, symbols, ewr_cfg, use_exposure_layers=False)

    regime_lookback = [3, 4]
    regime_vol_soft = [4.5, 5.5]
    regime_vol_hard = [6.0, 7.0]
    regime_exposure_soft = [0.85, 0.80]
    regime_exposure_hard = [0.65, 0.60]
    dd1_vals = [0.10, 0.12]
    dd2_vals = [0.18]
    dd_exposure2_vals = [0.60, 0.50]

    rows: list[dict[str, float]] = []
    tested = 0
    for (
        rg_lb,
        rg_vs,
        rg_vh,
        rg_es,
        rg_eh,
        dd1,
        dd2,
        dd_e2,
    ) in itertools.product(
        regime_lookback,
        regime_vol_soft,
        regime_vol_hard,
        regime_exposure_soft,
        regime_exposure_hard,
        dd1_vals,
        dd2_vals,
        dd_exposure2_vals,
    ):
        if rg_vs >= rg_vh:
            continue
        cfg = ComboCfg(
            ewr_lookback=4,
            ewr_alpha=0.25,
            ewr_min_mult=0.60,
            ewr_max_mult=1.40,
            ewr_min_samples=2,
            regime_lookback=rg_lb,
            regime_vol_soft=rg_vs,
            regime_vol_hard=rg_vh,
            regime_win_soft=0.50,
            regime_win_hard=0.40,
            regime_exposure_soft=rg_es,
            regime_exposure_hard=rg_eh,
            dd1=dd1,
            dd2=dd2,
            dd_exposure1=0.80,
            dd_exposure2=dd_e2,
        )
        ret, mdd = _run_combo(monthly, symbols, cfg, use_exposure_layers=True)
        score = ret - (0.6 * mdd)
        tested += 1
        rows.append(
            {
                "ret": ret,
                "mdd": mdd,
                "score": score,
                "rg_lb": float(rg_lb),
                "rg_vs": rg_vs,
                "rg_vh": rg_vh,
                "rg_es": rg_es,
                "rg_eh": rg_eh,
                "dd1": dd1,
                "dd2": dd2,
                "dd_e2": dd_e2,
            }
        )

    ranked = sorted(rows, key=lambda x: x["score"], reverse=True)
    best = ranked[0] if ranked else None

    print(
        f"[INFO] Done | months={len(monthly)} symbols={symbols} days={days} "
        f"slippage_bps={slippage_bps:.2f} tested={tested}"
    )
    print(f"[BASELINE] equal-weight: return={base_ret:.2f}% maxDD={base_dd:.2f}%")
    print(f"[EWR] tuned only:        return={ewr_ret:.2f}% maxDD={ewr_dd:.2f}%")
    if best is None:
        print("[WARN] No valid combo found.")
        return
    print(
        "[BEST LOGIC COMBO] "
        f"return={best['ret']:.2f}% maxDD={best['mdd']:.2f}% score={best['score']:.2f} | "
        f"rg_lb={int(best['rg_lb'])} rg_vs={best['rg_vs']:.2f} rg_vh={best['rg_vh']:.2f} "
        f"rg_es={best['rg_es']:.2f} rg_eh={best['rg_eh']:.2f} "
        f"dd1={best['dd1']:.2f} dd2={best['dd2']:.2f} dd_e2={best['dd_e2']:.2f}"
    )
    print(f"[DELTA VS BASELINE] {best['ret'] - base_ret:.2f} pp")
    print(f"[DELTA VS EWR]      {best['ret'] - ewr_ret:.2f} pp")

    top = ranked[:10]
    print("\nTop 10 by score:")
    print("-" * 108)
    print(
        f"{'rank':<5} {'ret%':>8} {'maxDD%':>8} {'score':>9} {'rg_lb':>6} {'rg_vs':>6} {'rg_vh':>6} "
        f"{'rg_es':>6} {'rg_eh':>6} {'dd1':>6} {'dd2':>6} {'dd_e2':>7}"
    )
    print("-" * 108)
    for i, x in enumerate(top, start=1):
        print(
            f"{i:<5} {x['ret']:>8.2f} {x['mdd']:>8.2f} {x['score']:>9.2f} "
            f"{int(x['rg_lb']):>6d} {x['rg_vs']:>6.2f} {x['rg_vh']:>6.2f} "
            f"{x['rg_es']:>6.2f} {x['rg_eh']:>6.2f} {x['dd1']:>6.2f} {x['dd2']:>6.2f} {x['dd_e2']:>7.2f}"
        )
    print("-" * 108)


def main() -> None:
    parser = argparse.ArgumentParser(description="Best logic combo backtest sweep.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    args = parser.parse_args()
    run(days=max(int(args.days), 120), slippage_bps=max(float(args.slippage_bps), 0.0))


if __name__ == "__main__":
    main()
