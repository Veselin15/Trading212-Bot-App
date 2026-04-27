"""
Break-even trigger sweep for Trading 212 live-style strategy.

Runs the same 5m/15m strategy structure across all 4 T212 symbols and
evaluates multiple break-even trigger percentages to identify the best level.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests.t212_oos_regime_backtest import CFG, _compute_signal
from t212_miner_bot.config import EMA_PERIOD, SYMBOLS_MAP
from t212_miner_bot.indicators import add_indicators


ZERO_PNL_TOLERANCE = 1e-8


@dataclass
class SweepMetrics:
    trigger_pct: float
    portfolio_return_avg: float
    portfolio_win_rate: float
    portfolio_break_even_rate: float
    portfolio_trades: int
    portfolio_profit_factor: float


def _profit_factor(trade_pnls: list[float]) -> float:
    gross_profit = sum(p for p in trade_pnls if p > 0)
    gross_loss = -sum(p for p in trade_pnls if p < 0)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _load_local_5m_csv(symbol: str, days: int) -> pd.DataFrame:
    data_dir = REPO_ROOT / "data"
    candidates = [f"{symbol}_5m.csv"]
    if symbol == "SHELL.AS":
        candidates.append("SHEL.AS_5m.csv")

    source_path: Path | None = None
    for name in candidates:
        candidate = data_dir / name
        if candidate.exists():
            source_path = candidate
            break
    if source_path is None:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.read_csv(source_path)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    out = out.set_index("timestamp")

    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=days)
    out = out[(out.index >= start) & (out.index <= end)].copy()
    return out


def _simulate_symbol(df: pd.DataFrame, trigger_pct: float | None) -> tuple[float, float, float, int, float]:
    if df.empty or len(df) < 100:
        return 0.0, 0.0, 0.0, 0, 0.0

    equity = 1.0
    pending: dict[str, Any] | None = None
    position: dict[str, Any] | None = None
    trade_pnls: list[float] = []
    break_even_saved = 0

    for i in range(2, len(df)):
        row = df.iloc[i]
        high_i = float(row["high"])
        low_i = float(row["low"])
        close_i = float(row["close"])
        atr_15m = float(row["atr_15m"]) if pd.notna(row["atr_15m"]) else 0.0

        if position is not None:
            entry = float(position["entry"])
            stop = float(position["stop"])
            qty_open = float(position["qty_open"])
            unit1_tp = float(position["unit1_tp"])
            unit1_done = bool(position["unit1_done"])
            high_since_entry = float(position["high_since_entry"])
            realized_pnl = float(position["realized_pnl"])
            break_even_moved = bool(position.get("break_even_moved", False))

            if (trigger_pct is not None) and (not break_even_moved) and high_i >= entry * (1.0 + trigger_pct):
                stop = max(stop, entry)
                break_even_moved = True

            if low_i <= stop:
                pnl_total = realized_pnl + qty_open * ((stop - entry) / entry)
                equity *= 1.0 + pnl_total
                trade_pnls.append(pnl_total)
                if break_even_moved and abs(pnl_total) <= ZERO_PNL_TOLERANCE:
                    break_even_saved += 1
                position = None
                continue

            if (not unit1_done) and close_i >= unit1_tp:
                closed_qty = 0.5
                realized_pnl += closed_qty * ((close_i - entry) / entry)
                qty_open -= closed_qty
                unit1_done = True
                stop = max(stop, entry * (1.0 + CFG.breakeven_offset_pct))

            if unit1_done and qty_open > 0:
                high_since_entry = max(high_since_entry, high_i)
                if atr_15m > 0:
                    trail_stop = high_since_entry - (CFG.atr_trail_mult * atr_15m)
                    stop = max(stop, trail_stop)
                if low_i <= stop:
                    pnl_total = realized_pnl + qty_open * ((stop - entry) / entry)
                    equity *= 1.0 + pnl_total
                    trade_pnls.append(pnl_total)
                    if break_even_moved and abs(pnl_total) <= ZERO_PNL_TOLERANCE:
                        break_even_saved += 1
                    position = None
                    continue

            position["stop"] = stop
            position["qty_open"] = qty_open
            position["unit1_done"] = unit1_done
            position["high_since_entry"] = high_since_entry
            position["realized_pnl"] = realized_pnl
            position["break_even_moved"] = break_even_moved
            continue

        if pending is not None:
            signal_snapshot = _compute_signal(df, i)
            if high_i >= float(pending["entry_stop"]):
                entry = float(pending["entry_stop"])
                risk = float(pending["risk_distance"])
                if risk > 0:
                    position = {
                        "entry": entry,
                        "stop": entry - risk,
                        "unit1_tp": entry + CFG.unit1_tp_rr * risk,
                        "qty_open": 1.0,
                        "unit1_done": False,
                        "high_since_entry": high_i,
                        "realized_pnl": 0.0,
                        "break_even_moved": False,
                    }
                pending = None
            else:
                if signal_snapshot["momentum_ok"]:
                    pending["entry_stop"] = min(float(pending["entry_stop"]), high_i)
                else:
                    pending = None
            continue

        snapshot = _compute_signal(df, i)
        if not snapshot["long_signal"]:
            continue
        risk_distance = CFG.atr_multiplier * snapshot["atr_5m"]
        if risk_distance <= 0:
            continue
        pending = {"entry_stop": snapshot["signal_high"], "risk_distance": risk_distance}

    if position is not None:
        entry = float(position["entry"])
        qty_open = float(position["qty_open"])
        realized_pnl = float(position["realized_pnl"])
        last_close = float(df["close"].iloc[-1])
        pnl_total = realized_pnl + qty_open * ((last_close - entry) / entry)
        equity *= 1.0 + pnl_total
        trade_pnls.append(pnl_total)
        if bool(position.get("break_even_moved", False)) and abs(pnl_total) <= ZERO_PNL_TOLERANCE:
            break_even_saved += 1

    total_trades = len(trade_pnls)
    win_rate = (sum(1 for p in trade_pnls if p > 0) / total_trades * 100.0) if total_trades else 0.0
    break_even_rate = (break_even_saved / total_trades * 100.0) if total_trades else 0.0
    total_return = (equity - 1.0) * 100.0
    pf = _profit_factor(trade_pnls)
    return total_return, win_rate, break_even_rate, total_trades, pf


def _parse_trigger_list(raw: str) -> list[float]:
    values: list[float] = []
    for token in raw.split(","):
        clean = token.strip()
        if not clean:
            continue
        val = float(clean)
        if val <= 0:
            raise ValueError("Break-even trigger values must be > 0.")
        values.append(val)
    if not values:
        raise ValueError("No valid trigger values provided.")
    return sorted(set(values))


def run_sweep(days: int, trigger_values: list[float]) -> None:
    symbols = list(SYMBOLS_MAP.keys())
    datasets: dict[str, pd.DataFrame] = {}
    indicator_sets: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        datasets[symbol] = _load_local_5m_csv(symbol=symbol, days=days)
        if datasets[symbol].empty:
            indicator_sets[symbol] = pd.DataFrame()
            continue
        indicator_sets[symbol] = add_indicators(datasets[symbol], ema_period=EMA_PERIOD).dropna().copy()

    print(
        f"[INFO] Running break-even sweep | Days={days} | "
        f"Universe={', '.join(symbols)} | Triggers={', '.join(f'{v:.4f}' for v in trigger_values)}"
    )
    for symbol in symbols:
        print(f"[INFO] {symbol}: bars={len(datasets[symbol])}, indicator_bars={len(indicator_sets[symbol])}")

    # Include baseline (no extra BE move) as reference.
    all_rows: list[SweepMetrics] = []
    scenarios: list[float | None] = [None] + trigger_values

    for trigger in scenarios:
        per_symbol_returns: list[float] = []
        all_trade_count = 0
        weighted_wins = 0.0
        weighted_be = 0.0
        all_trade_pnls_for_pf: list[float] = []

        for symbol in symbols:
            df = indicator_sets[symbol]
            if df.empty:
                continue
            ret, win, be_rate, n_trades, pf_symbol = _simulate_symbol(df=df, trigger_pct=trigger)
            per_symbol_returns.append(ret)
            all_trade_count += n_trades
            weighted_wins += (win / 100.0) * n_trades
            weighted_be += (be_rate / 100.0) * n_trades
            # Approximate pooled PF by backing out using symbol PF is unreliable; rerun symbol pns not exposed.
            # Keep portfolio PF as NaN placeholder if there are no losses.
            if math.isfinite(pf_symbol):
                # proxy contribution: return percentage as synthetic pnl unit
                all_trade_pnls_for_pf.extend([ret / 100.0])

        portfolio_return_avg = float(np.mean(per_symbol_returns)) if per_symbol_returns else 0.0
        portfolio_win = (weighted_wins / all_trade_count * 100.0) if all_trade_count else 0.0
        portfolio_be = (weighted_be / all_trade_count * 100.0) if all_trade_count else 0.0
        portfolio_pf = _profit_factor(all_trade_pnls_for_pf) if all_trade_pnls_for_pf else 0.0

        all_rows.append(
            SweepMetrics(
                trigger_pct=0.0 if trigger is None else trigger,
                portfolio_return_avg=portfolio_return_avg,
                portfolio_win_rate=portfolio_win,
                portfolio_break_even_rate=portfolio_be,
                portfolio_trades=all_trade_count,
                portfolio_profit_factor=portfolio_pf,
            )
        )

    ranked = sorted(all_rows, key=lambda r: r.portfolio_return_avg, reverse=True)

    print("\n" + "=" * 110)
    print("BREAK-EVEN SWEEP RANKING (4 STOCK PORTFOLIO)")
    print("=" * 110)
    print(
        f"{'Rank':<6} {'Trigger%':>10} {'Avg Return%':>14} {'Win Rate%':>12} "
        f"{'BE Rate%':>10} {'Trades':>10} {'PF*':>10}"
    )
    print("-" * 110)
    for idx, row in enumerate(ranked, start=1):
        trigger_label = "BASELINE" if abs(row.trigger_pct) < 1e-12 else f"{row.trigger_pct * 100.0:.2f}"
        pf_text = f"{row.portfolio_profit_factor:.2f}" if math.isfinite(row.portfolio_profit_factor) else "inf"
        print(
            f"{idx:<6} {trigger_label:>10} {row.portfolio_return_avg:>14.2f} {row.portfolio_win_rate:>12.2f} "
            f"{row.portfolio_break_even_rate:>10.2f} {row.portfolio_trades:>10d} {pf_text:>10}"
        )
    print("=" * 110)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep break-even trigger percentages on all 4 T212 symbols.")
    parser.add_argument("--days", type=int, default=730, help="Lookback days (default: 730)")
    parser.add_argument(
        "--triggers",
        type=str,
        default="0.005,0.0075,0.01,0.0125,0.015,0.02",
        help="Comma-separated break-even trigger values (decimal form).",
    )
    args = parser.parse_args()
    run_sweep(days=args.days, trigger_values=_parse_trigger_list(args.triggers))


if __name__ == "__main__":
    main()
