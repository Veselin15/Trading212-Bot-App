from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta, time as dt_time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.config import ENABLE_TIME_FILTER, SYMBOLS_MAP, StrategyParams
from t212_miner_bot.indicators import add_indicators, cross_up


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(REPO_ROOT / ".env")

BACKTESTS_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BACKTESTS_DIR / "reports"
RUN_LOG_JSONL = BACKTESTS_DIR / "oos_regime_runs.jsonl"
RUN_LOG_MD = BACKTESTS_DIR / "oos_regime_journal.md"

NY_TZ = ZoneInfo("America/New_York")
CET_TZ = ZoneInfo("Europe/Berlin")


@dataclass(frozen=True)
class OOSConfig:
    strategy_name: str = "t212_miner_long_only_oos"
    strategy_description: str = (
        "Trading 212 Miner long-only strategy OOS by year using 5m bars, 15m regime filter, "
        "pending stop entries, virtual TP split, breakeven+ and ATR trailing."
    )
    symbols: tuple[str, ...] = tuple(SYMBOLS_MAP.keys())
    interval: str = "5m"
    max_chunk_days: int = 59
    ema_period: int = 200
    enable_time_filter: bool = ENABLE_TIME_FILTER
    atr_multiplier: float = StrategyParams().atr_multiplier
    unit1_tp_rr: float = StrategyParams().unit1_tp_rr
    atr_trail_mult: float = StrategyParams().atr_trail_mult
    breakeven_offset_pct: float = StrategyParams().breakeven_offset_pct


CFG = OOSConfig()

REGIMES = (
    {
        "year": "2022",
        "label": "Bear Market",
        "start": datetime(2022, 1, 1, tzinfo=UTC),
        "end": datetime(2022, 12, 31, 23, 59, 59, tzinfo=UTC),
    },
    {
        "year": "2023",
        "label": "Choppy Recovery",
        "start": datetime(2023, 1, 1, tzinfo=UTC),
        "end": datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC),
    },
    {
        "year": "2024",
        "label": "Bull Run",
        "start": datetime(2024, 1, 1, tzinfo=UTC),
        "end": datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    },
    {
        "year": "2025",
        "label": "Recent Market",
        "start": datetime(2025, 1, 1, tzinfo=UTC),
        "end": datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC),
    },
)


@dataclass
class Trade:
    symbol: str
    side: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    exit: float
    pnl_pct: float
    reason: str


def _flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def _normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    out = df.rename(columns=rename_map).copy()
    required = ["open", "high", "low", "close", "volume"]
    if any(col not in out.columns for col in required):
        return pd.DataFrame(columns=required)
    return out[required].dropna(subset=["open", "high", "low", "close"])


def _download_symbol_5m_range(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    # Yahoo limits intraday lookback, so we stitch consecutive chunks.
    frames: list[pd.DataFrame] = []
    cursor = start
    chunk_delta = timedelta(days=CFG.max_chunk_days)

    while cursor < end:
        chunk_end = min(cursor + chunk_delta, end)
        raw = yf.download(
            tickers=symbol,
            start=cursor,
            end=chunk_end + timedelta(days=1),
            interval=CFG.interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if not raw.empty:
            raw = _flatten_yf_columns(raw)
            bars = _normalize_ohlcv_columns(raw)
            if not bars.empty:
                frames.append(bars)
        cursor = chunk_end + timedelta(seconds=1)

    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    merged = pd.concat(frames).sort_index()
    merged = merged[~merged.index.duplicated(keep="last")]

    # Ensure UTC-aware index for time filters.
    if merged.index.tz is None:
        merged.index = merged.index.tz_localize("UTC")
    else:
        merged.index = merged.index.tz_convert("UTC")

    return merged[(merged.index >= start) & (merged.index <= end)].copy()


def _is_lunch_blocked(ts: pd.Timestamp) -> bool:
    if not CFG.enable_time_filter:
        return False
    ts_ny = ts.tz_convert(NY_TZ)
    t = ts_ny.time()
    return dt_time(11, 30) <= t < dt_time(13, 30)


def _is_eu_open_buffer(ts: pd.Timestamp) -> bool:
    ts_cet = ts.tz_convert(CET_TZ)
    t = ts_cet.time()
    return dt_time(9, 0) <= t < dt_time(9, 15)


def _max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    arr = np.array(equity_curve, dtype=float)
    run_max = np.maximum.accumulate(arr)
    dd = (arr - run_max) / run_max
    return float(dd.min())


def _profit_factor(trades: list[Trade]) -> float:
    gross_profit = sum(t.pnl_pct for t in trades if t.pnl_pct > 0)
    gross_loss = -sum(t.pnl_pct for t in trades if t.pnl_pct < 0)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _try_exit_position(
    symbol: str,
    trades: list[Trade],
    position: dict[str, Any] | None,
    ts: pd.Timestamp,
    row: pd.Series,
) -> tuple[dict[str, Any] | None, float | None]:
    if position is None:
        return None, None

    high_i = float(row["high"])
    low_i = float(row["low"])
    close_i = float(row["close"])
    atr_15m = float(row["atr_15m"]) if pd.notna(row["atr_15m"]) else 0.0

    entry = float(position["entry"])
    stop = float(position["stop"])
    qty_open = float(position["qty_open"])
    unit1_tp = float(position["unit1_tp"])
    unit1_done = bool(position["unit1_done"])
    high_since_entry = float(position["high_since_entry"])
    realized_pnl = 0.0

    # Conservative intrabar sequence: stop check happens before target check.
    if low_i <= stop:
        pnl = qty_open * ((stop - entry) / entry)
        trades.append(Trade(symbol, "long", position["entry_time"], ts, entry, stop, pnl, "stop_loss"))
        return None, pnl

    # Unit1 is virtual and closes at candle close when threshold is reached.
    if (not unit1_done) and close_i >= unit1_tp:
        closed_qty = 0.5
        pnl_unit1 = closed_qty * ((close_i - entry) / entry)
        realized_pnl += pnl_unit1
        trades.append(Trade(symbol, "long", position["entry_time"], ts, entry, close_i, pnl_unit1, "unit1_virtual_tp"))
        qty_open -= closed_qty
        unit1_done = True
        stop = entry * (1.0 + CFG.breakeven_offset_pct)

    # Trailing is active only for Unit2 after Unit1 is closed.
    if unit1_done and qty_open > 0:
        high_since_entry = max(high_since_entry, high_i)
        if atr_15m > 0:
            trail_stop = high_since_entry - (CFG.atr_trail_mult * atr_15m)
            stop = max(stop, trail_stop)
        if low_i <= stop:
            pnl = realized_pnl + qty_open * ((stop - entry) / entry)
            runner_pnl = qty_open * ((stop - entry) / entry)
            trades.append(
                Trade(symbol, "long", position["entry_time"], ts, entry, stop, runner_pnl, "unit2_trailing_stop")
            )
            return None, pnl

    position["stop"] = stop
    position["qty_open"] = qty_open
    position["unit1_done"] = unit1_done
    position["high_since_entry"] = high_since_entry
    if realized_pnl != 0.0:
        return position, realized_pnl
    return position, None


def _compute_signal(df: pd.DataFrame, i: int) -> dict[str, Any]:
    row = df.iloc[i]
    prev = df.iloc[i - 1]

    regime_long = bool(
        row["close"] > row["ema_15m"]
        and row["fast_15m"] > row["slow_15m"]
        and row["fast_15m"] < 75
    )
    long_trigger = bool(
        cross_up(prev["fast_5m"], prev["slow_5m"], row["fast_5m"], row["slow_5m"])
        and row["fast_5m"] < 75
    )

    long_signal = regime_long and long_trigger
    if _is_lunch_blocked(df.index[i]) or _is_eu_open_buffer(df.index[i]):
        long_signal = False

    return {
        "long_signal": long_signal,
        "signal_high": float(row["high"]),
        "atr_5m": float(row["atr_5m"]),
        "momentum_ok": bool(row["fast_5m"] > row["slow_5m"]),
    }


def run_backtest_for_symbol(symbol: str, bars_raw: pd.DataFrame) -> dict[str, Any]:
    df = add_indicators(bars_raw, ema_period=CFG.ema_period).dropna().copy()
    if df.empty or len(df) < 100:
        return {
            "symbol": symbol,
            "trades": [],
            "trades_count": 0,
            "total_return": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
        }

    trades: list[Trade] = []
    equity = 1.0
    equity_curve = [equity]
    pending: dict[str, Any] | None = None
    position: dict[str, Any] | None = None

    for i in range(2, len(df)):
        ts = df.index[i]
        row = df.iloc[i]

        # Manage active position first.
        position, realized = _try_exit_position(symbol, trades, position, ts, row)
        if realized is not None:
            equity *= 1.0 + realized
            equity_curve.append(equity)

        # Keep only one active state at a time.
        if position is not None:
            continue

        # Pending stop-entry management for long-only logic.
        if pending is not None:
            high_i = float(row["high"])
            signal_snapshot = _compute_signal(df, i)
            if high_i >= float(pending["entry_stop"]):
                entry = float(pending["entry_stop"])
                risk = float(pending["risk_distance"])
                if risk > 0:
                    position = {
                        "entry_time": ts,
                        "entry": entry,
                        "stop": entry - risk,
                        "unit1_tp": entry + CFG.unit1_tp_rr * risk,
                        "qty_open": 1.0,
                        "unit1_done": False,
                        "high_since_entry": float(row["high"]),
                    }
                pending = None
            else:
                # If momentum stays positive, pending stop can trail down to avoid overpaying.
                if signal_snapshot["momentum_ok"]:
                    pending["entry_stop"] = min(float(pending["entry_stop"]), high_i)
                else:
                    pending = None
            continue

        # Create new pending entry from current closed-candle signal.
        snapshot = _compute_signal(df, i)
        if not snapshot["long_signal"]:
            continue

        risk_distance = CFG.atr_multiplier * snapshot["atr_5m"]
        if risk_distance <= 0:
            continue

        pending = {
            "entry_stop": snapshot["signal_high"],
            "risk_distance": risk_distance,
        }

    # Close any open position at end of dataset.
    if position is not None:
        last_ts = df.index[-1]
        last_close = float(df["close"].iloc[-1])
        entry = float(position["entry"])
        qty_open = float(position["qty_open"])
        pnl = qty_open * ((last_close - entry) / entry)
        trades.append(Trade(symbol, "long", position["entry_time"], last_ts, entry, last_close, pnl, "eod_close"))
        equity *= 1.0 + pnl
        equity_curve.append(equity)

    n = len(trades)
    win_rate = (sum(1 for t in trades if t.pnl_pct > 0) / n * 100.0) if n > 0 else 0.0
    total_return = (equity - 1.0) * 100.0
    max_dd = _max_drawdown(equity_curve) * 100.0
    pf = _profit_factor(trades)

    return {
        "symbol": symbol,
        "trades": trades,
        "trades_count": n,
        "total_return": total_return,
        "win_rate": win_rate,
        "max_drawdown": max_dd,
        "profit_factor": pf,
    }


def _build_regime_table(rows: list[dict[str, Any]]) -> str:
    lines = []
    lines.append("T212 Miner Strategy Multi-Regime OOS Matrix")
    lines.append("")
    lines.append(
        f"{'Year':<6} {'Regime':<18} {'Total Return %':>16} {'Max Drawdown %':>16} "
        f"{'Win Rate %':>12} {'Profit Factor':>14} {'Total Trades':>14}"
    )
    lines.append("-" * 102)
    for row in rows:
        lines.append(
            f"{row['year']:<6} {row['regime']:<18} {row['total_return']:>16.2f} "
            f"{row['max_drawdown']:>16.2f} {row['win_rate']:>12.2f} "
            f"{row['profit_factor']:>14.2f} {row['total_trades']:>14d}"
        )
    return "\n".join(lines)


def _write_artifacts(results: list[dict[str, Any]], table: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now(tz=UTC)
    run_id = run_ts.strftime("%Y%m%d_%H%M%S")

    payload = {
        "run_id": run_id,
        "run_utc": run_ts.isoformat(),
        "script": str(Path(__file__).name),
        "strategy": CFG.strategy_name,
        "config": asdict(CFG),
        "regimes": [
            {
                "year": r["year"],
                "regime": r["regime"],
                "total_return": r["total_return"],
                "max_drawdown": r["max_drawdown"],
                "win_rate": r["win_rate"],
                "profit_factor": r["profit_factor"],
                "total_trades": r["total_trades"],
            }
            for r in results
        ],
    }

    with RUN_LOG_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")

    with RUN_LOG_MD.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## Run {run_id}\n")
        fh.write(f"- Script: `{Path(__file__).name}`\n")
        fh.write(f"- UTC: `{payload['run_utc']}`\n")
        fh.write(f"- Strategy: `{CFG.strategy_name}`\n")
        fh.write(f"- Universe: `{', '.join(CFG.symbols)}`\n")
        fh.write(
            "- Parameters: "
            f"`atr_mult={CFG.atr_multiplier}, unit1_rr={CFG.unit1_tp_rr}, ema={CFG.ema_period}, "
            f"trail_mult={CFG.atr_trail_mult}, be_offset={CFG.breakeven_offset_pct}, "
            f"time_filter={CFG.enable_time_filter}`\n"
        )
        fh.write("\n")
        fh.write("```text\n")
        fh.write(table)
        fh.write("\n```\n")

    report_path = REPORTS_DIR / f"{run_id}_t212_miner_oos_regimes.txt"
    report_path.write_text(
        "\n".join(
            [
                f"Run ID: {run_id}",
                f"Run UTC: {payload['run_utc']}",
                f"Script: {Path(__file__).name}",
                f"Strategy: {CFG.strategy_name}",
                "",
                table,
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    regime_rows: list[dict[str, Any]] = []

    for regime in REGIMES:
        year = str(regime["year"])
        label = str(regime["label"])
        start = regime["start"]
        end = regime["end"]
        print(f"Running {year} ({label})...", flush=True)

        per_symbol: list[dict[str, Any]] = []
        all_trade_pnls: list[float] = []
        for symbol in CFG.symbols:
            bars = _download_symbol_5m_range(symbol=symbol, start=start, end=end)
            if bars.empty:
                continue
            result = run_backtest_for_symbol(symbol, bars)
            per_symbol.append(result)
            all_trade_pnls.extend([t.pnl_pct for t in result["trades"]])

        if not per_symbol:
            regime_rows.append(
                {
                    "year": year,
                    "regime": label,
                    "total_return": 0.0,
                    "max_drawdown": 0.0,
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "total_trades": 0,
                }
            )
            continue

        # Regime metrics are aggregated across symbols to mirror portfolio-level behavior.
        avg_return = float(np.mean([x["total_return"] for x in per_symbol]))
        avg_dd = float(np.mean([x["max_drawdown"] for x in per_symbol]))
        total_trades = int(sum(x["trades_count"] for x in per_symbol))
        win_rate = (
            sum(1 for p in all_trade_pnls if p > 0) / len(all_trade_pnls) * 100.0 if all_trade_pnls else 0.0
        )
        gross_profit = sum(p for p in all_trade_pnls if p > 0)
        gross_loss = -sum(p for p in all_trade_pnls if p < 0)
        pf = (gross_profit / gross_loss) if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)

        regime_rows.append(
            {
                "year": year,
                "regime": label,
                "total_return": avg_return,
                "max_drawdown": avg_dd,
                "win_rate": win_rate,
                "profit_factor": pf,
                "total_trades": total_trades,
            }
        )

    table = _build_regime_table(regime_rows)
    print("\n" + table)
    _write_artifacts(regime_rows, table)
    print(
        "\nSaved artifacts:\n"
        f"- {RUN_LOG_MD}\n"
        f"- {RUN_LOG_JSONL}\n"
        f"- {REPORTS_DIR}"
    )


if __name__ == "__main__":
    main()

