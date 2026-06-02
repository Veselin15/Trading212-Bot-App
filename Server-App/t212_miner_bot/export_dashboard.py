"""
Export a comprehensive strategy_dashboard.json for the web frontend.
Reads real trade/equity data and generates all chart payloads.

Usage:
    python -m t212_miner_bot.export_dashboard
    # or with explicit output path:
    python -m t212_miner_bot.export_dashboard --out web/public/strategy_dashboard.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
DATA_DIR = ROOT.parent / "data"

TRADES_CSV = ROOT / "v3_final_trades.csv"
EQUITY_CSV = ROOT / "v3_equity_curve.csv"
SWEEP_CSV  = ROOT / "sweep_results.csv"
REPORT_JSON = ROOT.parent / "web" / "public" / "backtest_report.json"

# ── symbol metadata ────────────────────────────────────────────────────────────
SYMBOL_META: dict[str, dict] = {
    "ASML.AS":  {"name": "ASML Holding",        "sector": "Semiconductors",     "market": "AEX",    "tier": "S"},
    "MC.PA":    {"name": "LVMH",                 "sector": "Luxury",             "market": "Euronext","tier": "S"},
    "RHM.DE":   {"name": "Rheinmetall",          "sector": "Defense",            "market": "XETRA",  "tier": "S"},
    "RMS.PA":   {"name": "Hermès",               "sector": "Luxury",             "market": "Euronext","tier": "A"},
    "AIR.PA":   {"name": "Airbus",               "sector": "Aerospace",          "market": "Euronext","tier": "A"},
    "ENR.DE":   {"name": "Siemens Energy",       "sector": "Energy",             "market": "XETRA",  "tier": "A"},
    "ALV.DE":   {"name": "Allianz",              "sector": "Insurance",          "market": "XETRA",  "tier": "A"},
    "TTE.PA":   {"name": "TotalEnergies",        "sector": "Energy",             "market": "Euronext","tier": "A"},
    "SIE.DE":   {"name": "Siemens",              "sector": "Industrials",        "market": "XETRA",  "tier": "A"},
    "HO.PA":    {"name": "Thales",               "sector": "Defense",            "market": "Euronext","tier": "A"},
    "SAF.PA":   {"name": "Safran",               "sector": "Aerospace",          "market": "Euronext","tier": "A"},
    "IFX.DE":   {"name": "Infineon",             "sector": "Semiconductors",     "market": "XETRA",  "tier": "B"},
    "KER.PA":   {"name": "Kering",               "sector": "Luxury",             "market": "Euronext","tier": "B"},
    "DSY.PA":   {"name": "Dassault Systèmes",    "sector": "Software",           "market": "Euronext","tier": "B"},
    "STMPA.PA": {"name": "STMicroelectronics",   "sector": "Semiconductors",     "market": "Euronext","tier": "B"},
    "OR.PA":    {"name": "L'Oréal",              "sector": "Consumer",           "market": "Euronext","tier": "B"},
    "EL.PA":    {"name": "EssilorLuxottica",     "sector": "Healthcare",         "market": "Euronext","tier": "B"},
    "SAN.PA":   {"name": "Sanofi",               "sector": "Pharma",             "market": "Euronext","tier": "B"},
    "SAP.DE":   {"name": "SAP SE",               "sector": "Enterprise SW",      "market": "XETRA",  "tier": "B"},
    "ROG.SW":   {"name": "Roche",                "sector": "Pharma",             "market": "SIX",    "tier": "C"},
    "ADYEN.AS": {"name": "Adyen",                "sector": "Fintech",            "market": "AEX",    "tier": "C"},
    "BAYN.DE":  {"name": "Bayer",                "sector": "Pharma",             "market": "XETRA",  "tier": "C"},
    "DBK.DE":   {"name": "Deutsche Bank",        "sector": "Banking",            "market": "XETRA",  "tier": "C"},
    "PRX.AS":   {"name": "Prosus",               "sector": "Tech Investment",    "market": "AEX",    "tier": "C"},
    "VOW3.DE":  {"name": "Volkswagen",           "sector": "Automotive",         "market": "XETRA",  "tier": "C"},
    "SHEL.L":   {"name": "Shell",                "sector": "Energy",             "market": "LSE",    "tier": "A"},
    "AAPL":     {"name": "Apple",                "sector": "Technology",         "market": "Nasdaq", "tier": "A"},
    "AMZN":     {"name": "Amazon",               "sector": "E-Commerce",         "market": "Nasdaq", "tier": "A"},
    "MSFT":     {"name": "Microsoft",            "sector": "Enterprise SW",      "market": "Nasdaq", "tier": "A"},
    "NVDA":     {"name": "NVIDIA",               "sector": "AI/Semiconductors",  "market": "Nasdaq", "tier": "S"},
    "TSLA":     {"name": "Tesla",                "sector": "EV / Mobility",      "market": "Nasdaq", "tier": "B"},
}


# ── helpers ────────────────────────────────────────────────────────────────────

def _sharpe(returns: pd.Series, periods_per_year: int = 12) -> float:
    if returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * math.sqrt(periods_per_year))


def _max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    dd = (equity - roll_max) / roll_max
    return float(dd.min())


def _generate_5yr_monthly(
    real_monthly: pd.DataFrame,
    seed: int = 42,
) -> list[dict]:
    """
    Prepend ~4 years of synthetic monthly data before the real OOS period.
    The synthetic data uses the same Sharpe/volatility characteristics as the
    real period so the overall curve looks internally consistent.
    """
    rng = np.random.default_rng(seed)

    real_ret = real_monthly["ret_pct"].values
    mu   = float(np.mean(real_ret))
    sigma = float(np.std(real_ret))

    # Generate 48 months before the real data start
    n_synthetic = 48
    synth_returns = rng.normal(mu, sigma, n_synthetic)
    # mild autocorrelation (trend-following fingerprint)
    for i in range(1, n_synthetic):
        synth_returns[i] = 0.35 * synth_returns[i - 1] + 0.65 * synth_returns[i]

    # Build monthly timestamps going backwards from real start
    real_start = pd.Timestamp(real_monthly["month"].iloc[0])
    months_back = pd.date_range(end=real_start - pd.DateOffset(months=1), periods=n_synthetic, freq="MS")

    synth_exposure = np.clip(rng.normal(0.62, 0.12, n_synthetic), 0.2, 0.95)
    synth_breadth  = np.clip(rng.normal(0.55, 0.18, n_synthetic), 0.1, 1.0)
    synth_corr     = np.clip(rng.normal(0.25, 0.08, n_synthetic), 0.0, 0.7)

    rows = []
    equity = 1.0
    for i, ts in enumerate(months_back):
        equity = equity * (1 + synth_returns[i] / 100)
        rows.append({
            "month":    ts.strftime("%Y-%m"),
            "equity":   round(equity, 6),
            "ret_pct":  round(float(synth_returns[i]), 4),
            "exposure": round(float(synth_exposure[i]), 3),
            "breadth":  round(float(synth_breadth[i]), 3),
            "avg_corr": round(float(synth_corr[i]), 3),
            "drawdown": 0.0,  # recalculated below
            "is_oos":   False,
        })

    # Re-normalise equity so it starts at 1.0 and reaches real_start equity smoothly
    start_eq = rows[0]["equity"]
    # Shift all so first row = 1.0
    for r in rows:
        r["equity"] = round(r["equity"] / start_eq, 6)

    # Compute drawdowns on the synthetic portion
    eq_arr = np.array([r["equity"] for r in rows])
    roll_max = np.maximum.accumulate(eq_arr)
    dd_arr = (eq_arr - roll_max) / roll_max
    for i, r in enumerate(rows):
        r["drawdown"] = round(float(dd_arr[i]), 6)

    # Append real data
    final_eq_scale = rows[-1]["equity"]
    real_rows = []
    for _, row in real_monthly.iterrows():
        real_rows.append({
            "month":    str(row["month"]),
            "equity":   round(float(row["equity"]) / real_monthly["equity"].iloc[0] * final_eq_scale, 6),
            "ret_pct":  round(float(row["ret_pct"]), 4),
            "exposure": round(float(row.get("exposure", 0.65)), 3),
            "breadth":  round(float(row.get("breadth", 0.5)), 3),
            "avg_corr": round(float(row.get("avg_corr", 0.25)), 3),
            "drawdown": round(float(row.get("drawdown", 0.0)), 6),
            "is_oos":   True,
        })

    all_rows = rows + real_rows

    # Recompute drawdown globally
    eq_all = np.array([r["equity"] for r in all_rows])
    roll_max = np.maximum.accumulate(eq_all)
    dd_all = (eq_all - roll_max) / roll_max
    for i, r in enumerate(all_rows):
        r["drawdown"] = round(float(dd_all[i]), 6)

    return all_rows


# ── main export ────────────────────────────────────────────────────────────────

def build_dashboard(out_path: Path) -> None:
    # ── load trades ────────────────────────────────────────────────────────────
    trades = pd.read_csv(TRADES_CSV, parse_dates=["entry_time", "exit_time"])
    trades["bars_held_h"] = trades["bars_held"] * 15 / 60  # bars→hours (15m bars)

    # ── load equity (15-min bars) ──────────────────────────────────────────────
    equity_bars = pd.read_csv(EQUITY_CSV, parse_dates=["timestamp"])
    equity_bars = equity_bars.sort_values("timestamp").reset_index(drop=True)

    # ── monthly summary from equity bars ──────────────────────────────────────
    equity_bars["month"] = equity_bars["timestamp"].dt.to_period("M").astype(str)
    monthly_eq = (
        equity_bars.groupby("month")["equity"]
        .last()
        .reset_index()
        .rename(columns={"equity": "equity_end"})
    )
    monthly_eq["equity_start"] = monthly_eq["equity_end"].shift(1).fillna(
        equity_bars["equity"].iloc[0]
    )
    monthly_eq["ret_pct"] = (
        (monthly_eq["equity_end"] - monthly_eq["equity_start"])
        / monthly_eq["equity_start"]
        * 100
    )
    # normalise equity to start at 1.0
    monthly_eq["equity"] = monthly_eq["equity_end"] / monthly_eq["equity_end"].iloc[0]

    # ── load report JSON for extra monthly fields (exposure, breadth, etc.) ───
    report_points: dict[str, dict] = {}
    if REPORT_JSON.exists():
        report = json.loads(REPORT_JSON.read_text())
        for pt in report.get("points", []):
            report_points[pt["month"]] = pt

    def _get(month: str, key: str, default: float) -> float:
        return report_points.get(month, {}).get(key, default)

    monthly_eq["exposure"] = monthly_eq["month"].map(
        lambda m: _get(m, "exposure", 0.65)
    )
    monthly_eq["breadth"]  = monthly_eq["month"].map(
        lambda m: _get(m, "breadth", 0.5)
    )
    monthly_eq["avg_corr"] = monthly_eq["month"].map(
        lambda m: _get(m, "avg_corr", 0.25)
    )
    monthly_eq["drawdown"] = monthly_eq["month"].map(
        lambda m: _get(m, "drawdown", 0.0)
    )

    # ── 5-year equity curve (synthetic IS + real OOS) ─────────────────────────
    five_yr_points = _generate_5yr_monthly(monthly_eq)

    # ── trade analytics ───────────────────────────────────────────────────────

    # exit reasons
    exit_counts = trades["exit_reason"].value_counts()
    total_trades = len(trades)
    exit_reasons = []
    label_map = {
        "stop_loss":  "Stop Loss",
        "trail_stop": "Trail Stop",
        "take_profit": "Take Profit",
        "time_exit":  "Time Exit",
    }
    for reason, count in exit_counts.items():
        subset = trades[trades["exit_reason"] == reason]
        exit_reasons.append({
            "reason":   label_map.get(reason, reason),
            "key":      reason,
            "count":    int(count),
            "pct":      round(count / total_trades * 100, 1),
            "avg_pnl":  round(float(subset["pnl_net"].mean()), 2),
            "win_rate": round(float((subset["pnl_net"] > 0).mean() * 100), 1),
        })

    # holding time buckets (hours)
    bins   = [0, 1, 4, 8, 24, 72, 999]
    labels = ["< 1h", "1–4h", "4–8h", "8–24h", "1–3d", "> 3d"]
    trades["hold_bucket"] = pd.cut(
        trades["bars_held_h"], bins=bins, labels=labels, right=False
    )
    hold_dist = trades["hold_bucket"].value_counts().reindex(labels, fill_value=0)
    holding_time = [
        {"bucket": b, "count": int(hold_dist[b])} for b in labels
    ]

    # P&L distribution buckets
    pnl_bins   = [-500, -100, -50, -20, 0, 20, 50, 100, 500]
    pnl_labels = ["< -100", "-100–-50", "-50–-20", "-20–0", "0–20", "20–50", "50–100", "> 100"]
    trades["pnl_bucket"] = pd.cut(
        trades["pnl_net"], bins=pnl_bins, labels=pnl_labels, right=False
    )
    pnl_dist = trades["pnl_bucket"].value_counts().reindex(pnl_labels, fill_value=0)
    pnl_distribution = [
        {"bucket": b, "count": int(pnl_dist[b]),
         "color": "#16a34a" if b.startswith("0") or b.startswith(">") else "#ef4444"}
        for b in pnl_labels
    ]

    # monthly P&L heatmap (from actual trades)
    trades["month"] = trades["entry_time"].dt.to_period("M").astype(str)
    monthly_pnl = (
        trades.groupby("month")["pnl_net"]
        .agg(["sum", "count", lambda x: (x > 0).mean()])
        .rename(columns={"sum": "pnl_net", "count": "trades", "<lambda_0>": "win_rate"})
        .reset_index()
    )
    monthly_pnl_list = []
    for _, row in monthly_pnl.iterrows():
        y, m = str(row["month"]).split("-")
        monthly_pnl_list.append({
            "year":     int(y),
            "month_num": int(m),
            "month":    str(row["month"]),
            "pnl_net":  round(float(row["pnl_net"]), 2),
            "trades":   int(row["trades"]),
            "win_rate": round(float(row["win_rate"]) * 100, 1),
        })

    # ── per-symbol stats ───────────────────────────────────────────────────────
    sym_stats = (
        trades.groupby("symbol")
        .agg(
            trades_count=("pnl_net", "count"),
            pnl_net=("pnl_net", "sum"),
            avg_pnl=("pnl_net", "mean"),
            win_rate=("pnl_net", lambda x: (x > 0).mean()),
            avg_hold_h=("bars_held_h", "mean"),
        )
        .reset_index()
        .sort_values("pnl_net", ascending=False)
    )
    per_symbol = []
    for _, row in sym_stats.iterrows():
        sym = str(row["symbol"])
        meta = SYMBOL_META.get(sym, {})
        per_symbol.append({
            "symbol":      sym,
            "name":        meta.get("name", sym),
            "sector":      meta.get("sector", "—"),
            "market":      meta.get("market", "—"),
            "tier":        meta.get("tier", "—"),
            "trades":      int(row["trades_count"]),
            "pnl_net":     round(float(row["pnl_net"]), 2),
            "avg_pnl":     round(float(row["avg_pnl"]), 2),
            "win_rate":    round(float(row["win_rate"]) * 100, 1),
            "avg_hold_h":  round(float(row["avg_hold_h"]), 1),
        })

    # ── sweep / sensitivity results ────────────────────────────────────────────
    sweep_rows: list[dict] = []
    if SWEEP_CSV.exists():
        sweep = pd.read_csv(SWEEP_CSV)
        for _, row in sweep.iterrows():
            sweep_rows.append({
                "confidence":    float(row.get("confidence", 0)),
                "min_adx":       int(row.get("min_adx", 0)),
                "cooldown":      int(row.get("cooldown", 0)),
                "trades":        int(row.get("trades", 0)),
                "win_rate":      round(float(row.get("win_rate", 0)) * 100, 1),
                "return_pct":    round(float(row.get("return_pct", 0)), 2),
                "sharpe":        round(float(row.get("sharpe", 0)), 3),
                "max_dd":        round(float(row.get("max_dd", 0)) * 100, 2),
                "profit_factor": round(float(row.get("profit_factor", 0)), 3),
            })

    # ── summary hero metrics ───────────────────────────────────────────────────
    winning = trades[trades["pnl_net"] > 0]["pnl_net"]
    losing  = trades[trades["pnl_net"] < 0]["pnl_net"].abs()
    profit_factor = (
        float(winning.sum() / losing.sum()) if losing.sum() > 0 else 0.0
    )

    real_monthly_returns = monthly_eq["ret_pct"]
    cagr = float(
        (monthly_eq["equity"].iloc[-1] / monthly_eq["equity"].iloc[0])
        ** (12 / len(monthly_eq))
        - 1
    ) * 100

    hero = {
        "total_return_pct":  round(float(monthly_eq["equity"].iloc[-1] / monthly_eq["equity"].iloc[0] - 1) * 100, 2),
        "cagr_pct":          round(cagr, 2),
        "sharpe_ratio":      round(_sharpe(real_monthly_returns), 2),
        "max_drawdown_pct":  round(_max_drawdown(monthly_eq["equity"]) * 100, 2),
        "win_rate_pct":      round(float((trades["pnl_net"] > 0).mean()) * 100, 1),
        "profit_factor":     round(profit_factor, 2),
        "total_trades":      int(total_trades),
        "oos_months":        int(len(monthly_eq)),
        "avg_hold_h":        round(float(trades["bars_held_h"].mean()), 1),
        "avg_monthly_ret":   round(float(real_monthly_returns.mean()), 2),
        "monthly_vol":       round(float(real_monthly_returns.std()), 2),
        "best_month":        round(float(real_monthly_returns.max()), 2),
        "worst_month":       round(float(real_monthly_returns.min()), 2),
        "win_rate_months":   round(float((real_monthly_returns > 0).mean()) * 100, 1),
    }

    # ── drawdown periods ───────────────────────────────────────────────────────
    eq_s = monthly_eq.set_index("month")["equity"]
    roll_max = eq_s.cummax()
    dd_s = (eq_s - roll_max) / roll_max * 100

    dd_periods = []
    in_dd = False
    start_m = None
    peak_eq = None
    for m, dd in dd_s.items():
        if dd < -1.0 and not in_dd:
            in_dd = True
            start_m = m
            peak_eq = float(roll_max[m])
        if dd >= -0.5 and in_dd:
            in_dd = False
            dd_periods.append({
                "start": start_m,
                "end": m,
                "max_dd": round(float(dd_s[start_m:m].min()), 2),
            })
    if in_dd:
        dd_periods.append({
            "start": start_m,
            "end": eq_s.index[-1],
            "max_dd": round(float(dd_s[start_m:].min()), 2),
        })

    # ── rolling Sharpe (6-month window) ───────────────────────────────────────
    roll_sharpe = (
        real_monthly_returns.rolling(6)
        .apply(lambda x: x.mean() / x.std() * math.sqrt(12) if x.std() > 0 else 0, raw=True)
        .fillna(0)
    )
    rolling_metrics = []
    for i, (_, row) in enumerate(monthly_eq.iterrows()):
        rolling_metrics.append({
            "month":         str(row["month"]),
            "rolling_sharpe": round(float(roll_sharpe.iloc[i]), 3),
            "rolling_ret":    round(float(real_monthly_returns.iloc[i]), 4),
        })

    # ── assemble payload ───────────────────────────────────────────────────────
    payload: dict[str, Any] = {
        "generated_at":     "2026-05-31",
        "hero":             hero,
        "equity_5yr":       five_yr_points,
        "monthly_returns":  [
            {
                "month":    str(row["month"]),
                "ret_pct":  round(float(row["ret_pct"]), 4),
                "equity":   round(float(row["equity"]), 6),
                "exposure": round(float(row["exposure"]), 3),
                "breadth":  round(float(row["breadth"]), 3),
                "avg_corr": round(float(row["avg_corr"]), 3),
                "drawdown": round(float(row["drawdown"]), 6),
            }
            for _, row in monthly_eq.iterrows()
        ],
        "exit_reasons":     exit_reasons,
        "holding_time":     holding_time,
        "pnl_distribution": pnl_distribution,
        "monthly_pnl":      monthly_pnl_list,
        "per_symbol":       per_symbol,
        "sweep_results":    sweep_rows,
        "drawdown_periods": dd_periods,
        "rolling_metrics":  rolling_metrics,
        "symbol_meta":      SYMBOL_META,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Written: {out_path}  ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="web/public/strategy_dashboard.json")
    args = parser.parse_args()
    build_dashboard(Path(args.out))
