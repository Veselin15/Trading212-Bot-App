"""
Data loading and multi-timeframe alignment.

Responsibilities:
  - Read raw OHLCV CSVs from the data/ directory.
  - Parse and normalise timestamps to UTC.
  - Provide aligned 15-minute (primary) and 5-minute (secondary) DataFrames.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from t212_miner_bot.config import (
    DATA_DIR,
    ALL_SYMBOLS,
    EU_SYMBOLS,
    PRIMARY_TIMEFRAME,
    SECONDARY_TIMEFRAME,
    TRAIN_END,
    TEST_START,
    EU_ONLY_MODE,
)


def _csv_path(symbol: str, timeframe: str) -> Path:
    """Resolve the CSV file path for a given symbol and timeframe."""
    return DATA_DIR / f"{symbol}_{timeframe}.csv"


def load_ohlcv(symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Load a single OHLCV CSV into a DatetimeIndex DataFrame.

    Returns columns: open, high, low, close, volume
    Index is a tz-aware (UTC) DatetimeIndex named 'timestamp'.
    """
    path = _csv_path(symbol, timeframe)
    if not path.exists():
        raise FileNotFoundError(f"No data file at {path}")

    df = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")
    df.index = pd.to_datetime(df.index, utc=True)
    df.sort_index(inplace=True)

    expected_cols = {"open", "high", "low", "close", "volume"}
    missing = expected_cols - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")

    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.dropna(subset=["close"], inplace=True)
    return df


def load_multi_timeframe(symbol: str) -> Dict[str, pd.DataFrame]:
    """
    Load both the primary (15 m) and secondary (5 m) data for a symbol.

    Returns {"15m": df_15m, "5m": df_5m}.
    If the secondary file doesn't exist the dict still contains the primary.
    """
    result: Dict[str, pd.DataFrame] = {}
    result[PRIMARY_TIMEFRAME] = load_ohlcv(symbol, PRIMARY_TIMEFRAME)

    secondary_path = _csv_path(symbol, SECONDARY_TIMEFRAME)
    if secondary_path.exists():
        result[SECONDARY_TIMEFRAME] = load_ohlcv(symbol, SECONDARY_TIMEFRAME)

    return result


def align_secondary_to_primary(
    df_primary: pd.DataFrame,
    df_secondary: pd.DataFrame,
    agg_suffix: str = "_5m",
) -> pd.DataFrame:
    """
    Aggregate 5-minute bars that fall within each 15-minute bar and merge
    selected summary statistics back onto the primary DataFrame.

    For every 15-min bar ending at time T we take the three 5-min bars in
    (T-15min, T] and compute:
      - mean close  → close_5m_mean
      - max volume  → volume_5m_max
      - last close  → close_5m_last

    These are attached as new columns to *df_primary*.
    """
    sec = df_secondary[["close", "volume"]].copy()
    sec_resampled = sec.resample("15min", closed="right", label="right").agg(
        {"close": ["mean", "last"], "volume": "max"}
    )
    sec_resampled.columns = [
        f"close{agg_suffix}_mean",
        f"close{agg_suffix}_last",
        f"volume{agg_suffix}_max",
    ]
    merged = df_primary.join(sec_resampled, how="left")
    merged.ffill(inplace=True)
    return merged


def split_train_test(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Strict chronological train / test split.
    Training: everything up to and including TRAIN_END.
    Testing : everything from TEST_START onwards.
    """
    train_end_ts = pd.Timestamp(TRAIN_END, tz="UTC")
    test_start_ts = pd.Timestamp(TEST_START, tz="UTC")
    return df.loc[:train_end_ts].copy(), df.loc[test_start_ts:].copy()


def get_available_symbols() -> List[str]:
    """
    Return symbols that have at least the primary-timeframe CSV on disk.
    Scans both the configured universe AND any additional CSVs in DATA_DIR.
    """
    # Start from configured universe
    configured = EU_SYMBOLS if EU_ONLY_MODE else ALL_SYMBOLS
    available = []

    # Also discover symbols directly from CSV filenames (catches new additions)
    discovered: set[str] = set()
    for path in DATA_DIR.glob(f"*_{PRIMARY_TIMEFRAME}.csv"):
        sym = path.stem.replace(f"_{PRIMARY_TIMEFRAME}", "")
        discovered.add(sym)

    # Merge: configured list order first, then discovered extras
    seen: set[str] = set()
    for sym in list(configured) + sorted(discovered):
        if sym not in seen and _csv_path(sym, PRIMARY_TIMEFRAME).exists():
            available.append(sym)
            seen.add(sym)

    return available


def load_all_symbols() -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Convenience: load every available symbol with both timeframes.

    Returns {symbol: {"15m": df, "5m": df}, ...}
    """
    symbols = get_available_symbols()
    return {sym: load_multi_timeframe(sym) for sym in symbols}
