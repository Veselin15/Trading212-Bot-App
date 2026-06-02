"""
Triple-barrier labeling for the XGBoost swing-trading model.

For every bar we simulate a hypothetical entry at that bar's *close* price and
check which barrier is touched first:

  1. Upper barrier  (Take Profit) → label = 1  (profitable trade)
  2. Lower barrier  (Stop Loss)   → label = 0  (losing trade)
  3. Time barrier   (Max holding) → label = 1 if still in profit, else 0

This gives the model a realistic reward-risk framing and naturally handles
flexible holding periods.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from t212_miner_bot.config import (
    TP_ATR_MULT,
    SL_ATR_MULT,
    MAX_HOLDING_BARS,
)


def _triple_barrier_numpy(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr: np.ndarray,
    tp_mult: float,
    sl_mult: float,
    max_bars: int,
) -> np.ndarray:
    """
    Pure-numpy implementation of the triple-barrier scan.

    Returns an int array of labels (1 = profitable, 0 = not) aligned to *close*.
    The last ``max_bars`` rows will be labelled NaN (not enough future data).
    """
    n = len(close)
    labels = np.full(n, np.nan, dtype=np.float64)

    for i in range(n - max_bars):
        entry = close[i]
        tp_price = entry + tp_mult * atr[i]
        sl_price = entry - sl_mult * atr[i]

        hit = 0  # 0 = undecided
        for j in range(1, max_bars + 1):
            idx = i + j
            if high[idx] >= tp_price:
                hit = 1
                break
            if low[idx] <= sl_price:
                hit = -1
                break

        if hit == 1:
            labels[i] = 1.0
        elif hit == -1:
            labels[i] = 0.0
        else:
            # Time barrier reached – mark profitable if close is above entry
            labels[i] = 1.0 if close[i + max_bars] > entry else 0.0

    return labels


def apply_triple_barrier_labels(
    df: pd.DataFrame,
    tp_mult: float = TP_ATR_MULT,
    sl_mult: float = SL_ATR_MULT,
    max_bars: int = MAX_HOLDING_BARS,
) -> pd.DataFrame:
    """
    Add a ``label`` column (float 0/1) to *df*.

    Requires columns: close, high, low, atr  (atr from features.add_atr).
    Rows where the label cannot be computed (end of series) get NaN and
    should be dropped before training.
    """
    if "atr" not in df.columns:
        raise ValueError("DataFrame must contain an 'atr' column. Run features.add_atr first.")

    labels = _triple_barrier_numpy(
        close=df["close"].values,
        high=df["high"].values,
        low=df["low"].values,
        atr=df["atr"].values,
        tp_mult=tp_mult,
        sl_mult=sl_mult,
        max_bars=max_bars,
    )
    df["label"] = labels
    return df


def label_balance_report(df: pd.DataFrame) -> dict:
    """Return basic statistics about the label distribution."""
    valid = df["label"].dropna()
    total = len(valid)
    positives = int((valid == 1).sum())
    negatives = total - positives
    return {
        "total": total,
        "positives": positives,
        "negatives": negatives,
        "pos_rate": positives / total if total > 0 else 0.0,
    }
