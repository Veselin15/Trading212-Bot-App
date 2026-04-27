"""
Strategy Lab Backtest (Trading 212 core logic only).

This script intentionally reuses the live Trading 212 signal path
(EMA200 + DTosc from the current bot) and excludes AI sentiment gating.
Current upgrade focus: move stop-loss to break-even after +1% favorable move.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.config import EMA_PERIOD
from t212_miner_bot.data_feed import _build_signal_snapshot  # Reuse live signal logic.
from t212_miner_bot.indicators import add_indicators


INITIAL_CAPITAL = 10_000.0
RISK_PER_TRADE = 0.02
ATR_STOP_MULTIPLIER = 1.5
TAKE_PROFIT_R_MULTIPLIER = 3.0
BREAK_EVEN_R_MULTIPLIER = 1.0
ZERO_PNL_TOLERANCE = 1e-8


@dataclass
class Position:
    entry_time: pd.Timestamp
    entry_price: float
    qty: float
    stop_price: float
    take_profit_price: float
    risk_distance: float
    break_even_activated: bool = False


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    exit_reason: str
    break_even_activated: bool
    closed_at_break_even: bool


def _flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df


def _fetch_5m_bars(symbol: str, period_days: int) -> pd.DataFrame:
    # Build 5m history in chunks because Yahoo limits intraday lookback per request.
    end = datetime.now(tz=UTC)
    start = end - timedelta(days=period_days)
    cursor = start
    frames: list[pd.DataFrame] = []

    while cursor < end:
        chunk_end = min(cursor + timedelta(days=59), end)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            raw = yf.download(
                tickers=symbol,
                start=cursor,
                end=chunk_end + timedelta(days=1),
                interval="5m",
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        if not raw.empty:
            frames.append(raw)
        cursor = chunk_end + timedelta(seconds=1)

    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    bars = pd.concat(frames).sort_index()
    bars = bars[~bars.index.duplicated(keep="last")]
    bars = _flatten_yf_columns(bars)
    bars = bars.rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    required = ["open", "high", "low", "close", "volume"]
    if any(col not in bars.columns for col in required):
        return pd.DataFrame(columns=required)

    out = bars[required].dropna(subset=["open", "high", "low", "close"]).sort_index()
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out[(out.index >= start) & (out.index <= end)].copy()


def _evaluate_exit(position: Position, row: pd.Series) -> tuple[float, str] | None:
    high = float(row["high"])
    low = float(row["low"])
    # Conservative intrabar order: stop first, then target.
    if low <= position.stop_price:
        return position.stop_price, "SL"
    if high >= position.take_profit_price:
        return position.take_profit_price, "TP"
    return None


def run_backtest(symbol: str, days: int) -> None:
    bars = _fetch_5m_bars(symbol=symbol, period_days=days)
    if bars.empty:
        print(f"[ERROR] No 5m bars found for {symbol}.")
        return

    data = add_indicators(bars, ema_period=EMA_PERIOD).dropna().copy()
    if len(data) < 5:
        print(f"[ERROR] Not enough indicator-ready bars for {symbol}.")
        return

    capital = INITIAL_CAPITAL
    position: Position | None = None
    trades: list[Trade] = []

    print(
        f"[INFO] Running T212 strategy lab backtest | Symbol={symbol} | "
        f"Bars={len(data)} | Initial Capital=${INITIAL_CAPITAL:,.2f}"
    )

    for i in range(2, len(data)):
        current_slice = data.iloc[: i + 1]
        row = current_slice.iloc[-1]
        ts = current_slice.index[-1]

        if position is not None:
            high = float(row["high"])
            if not position.break_even_activated:
                target_price = position.entry_price + (BREAK_EVEN_R_MULTIPLIER * position.risk_distance)
                if high >= target_price:
                    position.stop_price = position.entry_price
                    position.break_even_activated = True
                    print("[UPDATE] Price reached +1R profit. Stop Loss moved to break-even (Entry Price).")

            exit_result = _evaluate_exit(position, row)
            if exit_result is None:
                continue

            exit_price, exit_reason = exit_result
            pnl = (exit_price - position.entry_price) * position.qty
            capital += pnl
            closed_at_break_even = position.break_even_activated and abs(pnl) <= ZERO_PNL_TOLERANCE
            trades.append(
                Trade(
                    entry_time=position.entry_time,
                    exit_time=ts,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    qty=position.qty,
                    pnl=pnl,
                    exit_reason=exit_reason,
                    break_even_activated=position.break_even_activated,
                    closed_at_break_even=closed_at_break_even,
                )
            )
            position = None
            continue

        snapshot = _build_signal_snapshot(current_slice)
        if not snapshot.get("ready"):
            continue

        # Live Trading 212 execution is long-only; mirror that in this strategy lab version.
        if str(snapshot.get("signal_side", "none")) != "long":
            continue

        entry_price = float(snapshot["close"])
        atr_5m = float(snapshot.get("atr_5m", 0.0))
        if not math.isfinite(atr_5m) or atr_5m <= 0:
            continue
        risk_distance = ATR_STOP_MULTIPLIER * atr_5m
        if risk_distance <= 0:
            continue

        risk_amount = capital * RISK_PER_TRADE
        qty = risk_amount / risk_distance
        if qty <= 0:
            continue

        position = Position(
            entry_time=ts,
            entry_price=entry_price,
            qty=qty,
            stop_price=entry_price - risk_distance,
            take_profit_price=entry_price + (TAKE_PROFIT_R_MULTIPLIER * risk_distance),
            risk_distance=risk_distance,
        )

    if position is not None:
        last_row = data.iloc[-1]
        exit_price = float(last_row["close"])
        pnl = (exit_price - position.entry_price) * position.qty
        capital += pnl
        closed_at_break_even = position.break_even_activated and abs(pnl) <= ZERO_PNL_TOLERANCE
        trades.append(
            Trade(
                entry_time=position.entry_time,
                exit_time=data.index[-1],
                entry_price=position.entry_price,
                exit_price=exit_price,
                qty=position.qty,
                pnl=pnl,
                exit_reason="EOD",
                break_even_activated=position.break_even_activated,
                closed_at_break_even=closed_at_break_even,
            )
        )

    total_trades = len(trades)
    wins = sum(1 for t in trades if t.pnl > 0)
    break_even_saved = sum(1 for t in trades if t.closed_at_break_even)
    win_rate = (wins / total_trades * 100.0) if total_trades else 0.0
    break_even_rate = (break_even_saved / total_trades * 100.0) if total_trades else 0.0
    net_pnl = capital - INITIAL_CAPITAL

    print("\n" + "=" * 64)
    print("T212 STRATEGY LAB BACKTEST REPORT")
    print("=" * 64)
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Final Capital:   ${capital:,.2f}")
    print(f"Net PnL:         ${net_pnl:,.2f}")
    print(f"Total Trades:    {total_trades}")
    print(f"Win Rate:        {win_rate:.2f}%")
    print(f"Break-Even Rate: {break_even_rate:.2f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trading 212 strategy lab backtest (no AI).")
    parser.add_argument("--symbol", type=str, default="SHELL.AS", help="Yahoo symbol (default: SHELL.AS)")
    parser.add_argument("--days", type=int, default=730, help="Lookback days for 5m bars (default: 730)")
    args = parser.parse_args()
    run_backtest(symbol=args.symbol, days=args.days)


if __name__ == "__main__":
    main()
