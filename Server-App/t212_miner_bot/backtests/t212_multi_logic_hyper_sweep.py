"""
Comprehensive multi-logic portfolio sweep on top of live symbol strategy returns.

Logic layers tested in combinations:
- EWR base allocation (fixed tuned core)
- Momentum tilt
- Volatility penalty
- Breadth exposure gate
- Regime exposure gate (portfolio volatility + win-rate)
- Drawdown throttle
- Correlation exposure cap
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


def _normalize_weights(raw: dict[str, float], symbols: list[str]) -> dict[str, float]:
    clipped = {s: max(raw.get(s, 0.0), 0.0001) for s in symbols}
    total = sum(clipped.values())
    if total <= 0:
        return {s: 1.0 / len(symbols) for s in symbols}
    return {s: clipped[s] / total for s in symbols}


def _ewr_weights(
    hist: dict[str, list[float]],
    symbols: list[str],
    lookback: int = 4,
    alpha: float = 0.25,
    min_mult: float = 0.6,
    max_mult: float = 1.4,
    min_samples: int = 2,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for s in symbols:
        h = hist[s][-lookback:]
        if len(h) < min_samples:
            scores[s] = 0.0
            continue
        mu = sum(h) / len(h)
        sigma = statistics.pstdev(h) if len(h) > 1 else 0.0
        scores[s] = mu - (0.5 * sigma)

    vals = list(scores.values())
    gmu = sum(vals) / len(vals) if vals else 0.0
    gsig = (statistics.pstdev(vals) if len(vals) > 1 else 1.0) or 1.0
    raw: dict[str, float] = {}
    for s in symbols:
        z = (scores[s] - gmu) / gsig
        raw[s] = min(max_mult, max(min_mult, 1.0 + alpha * z))
    return _normalize_weights(raw, symbols)


def _max_dd(equity_curve: list[float]) -> float:
    peak = equity_curve[0] if equity_curve else 1.0
    max_dd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        dd = (peak - e) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd * 100.0


def _avg_pair_corr(history_window: dict[str, list[float]], symbols: list[str]) -> float:
    series = [history_window[s] for s in symbols if len(history_window[s]) >= 2]
    if len(series) < 2:
        return 0.0
    cols = {}
    for s in symbols:
        cols[s] = pd.Series(history_window[s], dtype="float64")
    df = pd.DataFrame(cols).dropna()
    if df.shape[0] < 2:
        return 0.0
    corr = df.corr()
    vals: list[float] = []
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            c = float(corr.iloc[i, j])
            if c == c:
                vals.append(c)
    return sum(vals) / len(vals) if vals else 0.0


def _simulate(
    monthly: pd.DataFrame,
    symbols: list[str],
    *,
    mom_lb: int,
    mom_tilt: float,
    vol_lb: int,
    vol_pen: float,
    breadth_floor: float,
    breadth_exp: float,
    regime_lb: int,
    regime_vol_soft: float,
    regime_vol_hard: float,
    regime_win_soft: float,
    regime_win_hard: float,
    regime_exp_soft: float,
    regime_exp_hard: float,
    dd1: float,
    dd2: float,
    dd_exp1: float,
    dd_exp2: float,
    corr_lb: int,
    corr_soft: float,
    corr_hard: float,
    corr_exp_soft: float,
    corr_exp_hard: float,
) -> tuple[float, float]:
    eq = 1.0
    peak = 1.0
    curve = [eq]
    hist: dict[str, list[float]] = {s: [] for s in symbols}
    port_hist: list[float] = []

    for _, row in monthly.iterrows():
        ret = {s: float(row[s]) for s in symbols}
        w = _ewr_weights(hist, symbols)

        if mom_tilt > 0:
            tilted: dict[str, float] = {}
            for s in symbols:
                h = hist[s][-mom_lb:]
                mom = (sum(h) / len(h)) if h else 0.0
                scaled = max(min(mom / 10.0, 1.0), -1.0)
                tilted[s] = w[s] * max(0.2, 1.0 + (mom_tilt * scaled))
            w = _normalize_weights(tilted, symbols)

        if vol_pen > 0:
            adjusted: dict[str, float] = {}
            for s in symbols:
                h = hist[s][-vol_lb:]
                vol = statistics.pstdev(h) if len(h) > 1 else 0.0
                adjusted[s] = w[s] * max(0.3, 1.0 / (1.0 + vol_pen * (vol / 10.0)))
            w = _normalize_weights(adjusted, symbols)

        basket_ret = sum(w[s] * ret[s] for s in symbols)

        # Breadth gate.
        exposure = 1.0
        if breadth_floor > 0:
            pos = 0
            for s in symbols:
                h = hist[s][-mom_lb:]
                edge = (sum(h) / len(h)) if h else 0.0
                if edge > 0:
                    pos += 1
            breadth = pos / len(symbols)
            if breadth < breadth_floor:
                exposure = min(exposure, breadth_exp)

        # Regime gate.
        rh = port_hist[-regime_lb:]
        if len(rh) >= regime_lb:
            rvol = statistics.pstdev(rh) if len(rh) > 1 else 0.0
            win = sum(1 for x in rh if x > 0) / len(rh)
            if rvol >= regime_vol_hard or win <= regime_win_hard:
                exposure = min(exposure, regime_exp_hard)
            elif rvol >= regime_vol_soft or win <= regime_win_soft:
                exposure = min(exposure, regime_exp_soft)

        # Drawdown throttle.
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd >= dd2:
            exposure = min(exposure, dd_exp2)
        elif dd >= dd1:
            exposure = min(exposure, dd_exp1)

        # Correlation cap.
        corr_window = {s: hist[s][-corr_lb:] for s in symbols}
        avg_corr = _avg_pair_corr(corr_window, symbols)
        if avg_corr >= corr_hard:
            exposure = min(exposure, corr_exp_hard)
        elif avg_corr >= corr_soft:
            exposure = min(exposure, corr_exp_soft)

        realized = basket_ret * exposure
        eq *= (1.0 + realized / 100.0)
        peak = max(peak, eq)
        curve.append(eq)
        port_hist.append(realized)
        for s in symbols:
            hist[s].append(ret[s])

    return (eq - 1.0) * 100.0, _max_dd(curve)


def run(days: int, slippage_bps: float) -> None:
    monthly, symbols = _monthly_symbol_returns(days=days, slippage_bps=slippage_bps)

    # Baseline and current-live-ish references
    base_eq = 1.0
    for _, row in monthly.iterrows():
        base_eq *= (1.0 + (sum(float(row[s]) for s in symbols) / len(symbols)) / 100.0)
    baseline_ret = (base_eq - 1.0) * 100.0

    ewr_mom_ret, ewr_mom_dd = _simulate(
        monthly,
        symbols,
        mom_lb=4,
        mom_tilt=0.30,
        vol_lb=2,
        vol_pen=0.0,
        breadth_floor=0.0,
        breadth_exp=0.7,
        regime_lb=3,
        regime_vol_soft=99.0,
        regime_vol_hard=99.0,
        regime_win_soft=-1.0,
        regime_win_hard=-1.0,
        regime_exp_soft=1.0,
        regime_exp_hard=1.0,
        dd1=1.0,
        dd2=1.0,
        dd_exp1=1.0,
        dd_exp2=1.0,
        corr_lb=4,
        corr_soft=2.0,
        corr_hard=2.0,
        corr_exp_soft=1.0,
        corr_exp_hard=1.0,
    )

    rows: list[dict[str, float]] = []
    tested = 0
    for (
        mom_lb,
        mom_tilt,
        vol_lb,
        vol_pen,
        breadth_floor,
        breadth_exp,
        regime_lb,
        regime_vol_soft,
        regime_vol_hard,
        regime_exp_soft,
        regime_exp_hard,
        dd1,
        dd2,
        dd_exp1,
        dd_exp2,
        corr_lb,
        corr_soft,
        corr_hard,
        corr_exp_soft,
        corr_exp_hard,
    ) in itertools.product(
        [3, 4],
        [0.25, 0.30, 0.35],
        [2],
        [0.0, 0.1],
        [0.0, 0.5],
        [0.85],
        [3],
        [4.5, 5.5],
        [7.0],
        [0.85],
        [0.60],
        [0.10],
        [0.18],
        [0.80],
        [0.60],
        [3],
        [0.50],
        [0.70],
        [0.90],
        [0.70],
    ):
        if regime_vol_soft >= regime_vol_hard:
            continue
        if corr_soft >= corr_hard:
            continue
        if dd1 >= dd2:
            continue
        if breadth_floor == 0.0 and breadth_exp != 0.80:
            continue

        ret, mdd = _simulate(
            monthly,
            symbols,
            mom_lb=mom_lb,
            mom_tilt=mom_tilt,
            vol_lb=vol_lb,
            vol_pen=vol_pen,
            breadth_floor=breadth_floor,
            breadth_exp=breadth_exp,
            regime_lb=regime_lb,
            regime_vol_soft=regime_vol_soft,
            regime_vol_hard=regime_vol_hard,
            regime_win_soft=0.50,
            regime_win_hard=0.35,
            regime_exp_soft=regime_exp_soft,
            regime_exp_hard=regime_exp_hard,
            dd1=dd1,
            dd2=dd2,
            dd_exp1=dd_exp1,
            dd_exp2=dd_exp2,
            corr_lb=corr_lb,
            corr_soft=corr_soft,
            corr_hard=corr_hard,
            corr_exp_soft=corr_exp_soft,
            corr_exp_hard=corr_exp_hard,
        )
        # Weighted score prioritizing return while penalizing drawdown.
        score = ret - (0.50 * mdd)
        rows.append(
            {
                "ret": ret,
                "mdd": mdd,
                "score": score,
                "mom_lb": float(mom_lb),
                "mom_tilt": mom_tilt,
                "vol_lb": float(vol_lb),
                "vol_pen": vol_pen,
                "breadth_floor": breadth_floor,
                "breadth_exp": breadth_exp,
                "regime_lb": float(regime_lb),
                "regime_vs": regime_vol_soft,
                "regime_vh": regime_vol_hard,
                "regime_es": regime_exp_soft,
                "regime_eh": regime_exp_hard,
                "dd1": dd1,
                "dd2": dd2,
                "dd_e1": dd_exp1,
                "dd_e2": dd_exp2,
                "corr_lb": float(corr_lb),
                "corr_soft": corr_soft,
                "corr_hard": corr_hard,
                "corr_es": corr_exp_soft,
                "corr_eh": corr_exp_hard,
            }
        )
        tested += 1
        if tested % 50 == 0:
            print(f"[RUN] {tested} candidates complete", flush=True)

    ranked_by_return = sorted(rows, key=lambda x: x["ret"], reverse=True)
    ranked_by_score = sorted(rows, key=lambda x: x["score"], reverse=True)
    best_ret = ranked_by_return[0] if ranked_by_return else None
    best_score = ranked_by_score[0] if ranked_by_score else None

    print(
        f"[INFO] Multi-logic sweep done | months={len(monthly)} symbols={symbols} "
        f"days={days} slippage_bps={slippage_bps:.2f} tested={tested}"
    )
    print(f"[BASELINE] return={baseline_ret:.2f}%")
    print(f"[EWR+MOM current] return={ewr_mom_ret:.2f}% maxDD={ewr_mom_dd:.2f}%")
    if best_ret is None or best_score is None:
        print("[WARN] No valid candidates.")
        return

    print(
        "[BEST BY RETURN] "
        f"ret={best_ret['ret']:.2f}% maxDD={best_ret['mdd']:.2f}% score={best_ret['score']:.2f} | "
        f"mom_lb={int(best_ret['mom_lb'])} mom_tilt={best_ret['mom_tilt']:.2f} "
        f"vol_pen={best_ret['vol_pen']:.2f} breadth_floor={best_ret['breadth_floor']:.2f} "
        f"regime_lb={int(best_ret['regime_lb'])} regime_vs={best_ret['regime_vs']:.2f} regime_vh={best_ret['regime_vh']:.2f} "
        f"dd1={best_ret['dd1']:.2f} dd2={best_ret['dd2']:.2f} "
        f"corr_soft={best_ret['corr_soft']:.2f} corr_hard={best_ret['corr_hard']:.2f}"
    )
    print(f"[DELTA VS BASELINE] {best_ret['ret'] - baseline_ret:.2f} pp")
    print(f"[DELTA VS EWR+MOM]  {best_ret['ret'] - ewr_mom_ret:.2f} pp")

    print(
        "[BEST BY SCORE] "
        f"ret={best_score['ret']:.2f}% maxDD={best_score['mdd']:.2f}% score={best_score['score']:.2f} | "
        f"mom_lb={int(best_score['mom_lb'])} mom_tilt={best_score['mom_tilt']:.2f} "
        f"vol_pen={best_score['vol_pen']:.2f} breadth_floor={best_score['breadth_floor']:.2f} "
        f"regime_lb={int(best_score['regime_lb'])} regime_vs={best_score['regime_vs']:.2f} regime_vh={best_score['regime_vh']:.2f} "
        f"dd1={best_score['dd1']:.2f} dd2={best_score['dd2']:.2f} "
        f"corr_soft={best_score['corr_soft']:.2f} corr_hard={best_score['corr_hard']:.2f}"
    )

    print("\nTop 10 by return:")
    print("-" * 118)
    print(
        f"{'rank':<5} {'ret%':>8} {'maxDD%':>8} {'score':>9} {'mom_tilt':>9} {'vol_pen':>8} "
        f"{'breadth':>8} {'reg_vs':>7} {'reg_vh':>7} {'dd1':>6} {'dd2':>6} {'corr_s':>7} {'corr_h':>7}"
    )
    print("-" * 118)
    for i, x in enumerate(ranked_by_return[:10], start=1):
        print(
            f"{i:<5} {x['ret']:>8.2f} {x['mdd']:>8.2f} {x['score']:>9.2f} "
            f"{x['mom_tilt']:>9.2f} {x['vol_pen']:>8.2f} {x['breadth_floor']:>8.2f} "
            f"{x['regime_vs']:>7.2f} {x['regime_vh']:>7.2f} {x['dd1']:>6.2f} {x['dd2']:>6.2f} "
            f"{x['corr_soft']:>7.2f} {x['corr_hard']:>7.2f}"
        )
    print("-" * 118)


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprehensive multi-logic hyper sweep.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    args = parser.parse_args()
    run(days=max(int(args.days), 120), slippage_bps=max(float(args.slippage_bps), 0.0))


if __name__ == "__main__":
    main()
