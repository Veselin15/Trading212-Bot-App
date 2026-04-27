from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_stoch_rsi(
    close: pd.Series,
    rsi_period: int,
    stoch_period: int,
    fast_sma: int,
    slow_sma: int,
) -> tuple[pd.Series, pd.Series]:
    rsi = calculate_rsi(close, rsi_period)
    rsi_low = rsi.rolling(stoch_period, min_periods=stoch_period).min()
    rsi_high = rsi.rolling(stoch_period, min_periods=stoch_period).max()
    denom = (rsi_high - rsi_low).replace(0.0, np.nan)
    stoch_rsi = 100.0 * (rsi - rsi_low) / denom
    fast = stoch_rsi.rolling(fast_sma, min_periods=fast_sma).mean()
    slow = fast.rolling(slow_sma, min_periods=slow_sma).mean()
    return fast, slow


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def add_indicators(df_5m: pd.DataFrame, ema_period: int) -> pd.DataFrame:
    out = df_5m.copy()
    out["atr_5m"] = calculate_atr(out, period=14)

    # 5m DTosc: 8,5,3,3
    fast_5m, slow_5m = calculate_stoch_rsi(
        out["close"], rsi_period=8, stoch_period=5, fast_sma=3, slow_sma=3
    )
    out["fast_5m"] = fast_5m
    out["slow_5m"] = slow_5m

    # 15m aggregation with right-closed/right-labeled bars.
    df_15m = (
        out.resample("15min", label="right", closed="right")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
    )

    # 15m DTosc: 13,8,5,5
    fast_15m, slow_15m = calculate_stoch_rsi(
        df_15m["close"], rsi_period=13, stoch_period=8, fast_sma=5, slow_sma=5
    )
    df_15m["fast_15m"] = fast_15m
    df_15m["slow_15m"] = slow_15m
    df_15m["ema_15m"] = df_15m["close"].ewm(span=ema_period, adjust=False).mean()
    df_15m["atr_15m"] = calculate_atr(df_15m, period=14)

    # Forward-fill 15m values onto the 5m frame to avoid lookahead bias.
    mapped = df_15m[["fast_15m", "slow_15m", "ema_15m", "atr_15m"]].reindex(
        out.index, method="ffill"
    )
    out[["fast_15m", "slow_15m", "ema_15m", "atr_15m"]] = mapped
    return out


def cross_up(prev_a: float, prev_b: float, cur_a: float, cur_b: float) -> bool:
    return bool(prev_a <= prev_b and cur_a > cur_b)


def cross_down(prev_a: float, prev_b: float, cur_a: float, cur_b: float) -> bool:
    return bool(prev_a >= prev_b and cur_a < cur_b)
