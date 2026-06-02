"""
Technical-indicator feature engineering.

Computes ~35 numeric features on the primary (15 m) OHLCV DataFrame, plus a
handful of multi-timeframe features derived from the secondary (5 m) bars.

Every function takes a DataFrame **in-place** and returns the same object so
calls can be chained.  All column names are lower-snake_case.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from t212_miner_bot.config import (
    EMA_PERIODS,
    RSI_PERIOD,
    STOCH_K_PERIOD,
    STOCH_D_PERIOD,
    WILLIAMS_R_PERIOD,
    ROC_PERIODS,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    ADX_PERIOD,
    ATR_PERIOD,
    BBANDS_PERIOD,
    BBANDS_STD,
    MFI_PERIOD,
    OBV_SLOPE_PERIOD,
    VOLUME_SMA_PERIOD,
    HIST_VOL_PERIOD,
    SECONDARY_RSI_PERIOD,
    SECONDARY_EMA_SHORT,
    SECONDARY_VOLUME_SPIKE_MULT,
    US_SYMBOLS,
    SECTORS,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def _stoch_rsi_feat(
    close: pd.Series,
    rsi_period: int,
    stoch_period: int,
    fast_sma: int,
    slow_sma: int,
) -> tuple[pd.Series, pd.Series]:
    """
    Vectorised Stochastic RSI – identical maths to t212_miner_bot/indicators.py.
    Returns (fast_line, slow_line) both in [0, 100].
    """
    delta    = close.diff()
    gains    = delta.clip(lower=0.0)
    losses   = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1.0 / rsi_period,  min_periods=rsi_period,  adjust=False).mean()
    avg_loss = losses.ewm(alpha=1.0 / rsi_period, min_periods=rsi_period,  adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi      = 100.0 - (100.0 / (1.0 + rs))

    rsi_low  = rsi.rolling(stoch_period, min_periods=stoch_period).min()
    rsi_high = rsi.rolling(stoch_period, min_periods=stoch_period).max()
    denom    = (rsi_high - rsi_low).replace(0.0, np.nan)
    stoch    = 100.0 * (rsi - rsi_low) / denom

    fast = stoch.rolling(fast_sma, min_periods=fast_sma).mean()
    slow = fast.rolling(slow_sma,  min_periods=slow_sma).mean()
    return fast, slow


def _true_range(df: pd.DataFrame) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_prev_close = (df["high"] - df["close"].shift(1)).abs()
    low_prev_close = (df["low"] - df["close"].shift(1)).abs()
    return pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)


# ── Trend indicators ─────────────────────────────────────────────────────────

def add_ema_features(df: pd.DataFrame) -> pd.DataFrame:
    """EMA values + cross-over ratios between successive periods."""
    for p in EMA_PERIODS:
        df[f"ema_{p}"] = _ema(df["close"], p)

    # Pairwise ratios (e.g. ema_8 / ema_21 - 1) capture crossover strength
    for i in range(len(EMA_PERIODS) - 1):
        fast, slow = EMA_PERIODS[i], EMA_PERIODS[i + 1]
        df[f"ema_{fast}_{slow}_ratio"] = df[f"ema_{fast}"] / df[f"ema_{slow}"] - 1.0
    return df


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    ema_fast = _ema(df["close"], MACD_FAST)
    ema_slow = _ema(df["close"], MACD_SLOW)
    df["macd_line"] = ema_fast - ema_slow
    df["macd_signal"] = _ema(df["macd_line"], MACD_SIGNAL)
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]
    return df


def add_adx(df: pd.DataFrame) -> pd.DataFrame:
    """Average Directional Index and DI+/DI- spread."""
    high_diff = df["high"].diff()
    low_diff = -df["low"].diff()

    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)

    tr = _true_range(df)
    atr = tr.ewm(span=ADX_PERIOD, adjust=False).mean()

    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(span=ADX_PERIOD, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(span=ADX_PERIOD, adjust=False).mean() / atr

    dx = (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10) * 100
    df["adx"] = dx.ewm(span=ADX_PERIOD, adjust=False).mean()
    df["di_spread"] = plus_di - minus_di
    return df


# ── Momentum indicators ──────────────────────────────────────────────────────

def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(span=RSI_PERIOD, adjust=False).mean()
    avg_loss = loss.ewm(span=RSI_PERIOD, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["rsi"] = 100 - 100 / (1 + rs)
    return df


def add_stochastic(df: pd.DataFrame) -> pd.DataFrame:
    low_min = df["low"].rolling(STOCH_K_PERIOD).min()
    high_max = df["high"].rolling(STOCH_K_PERIOD).max()
    df["stoch_k"] = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-10)
    df["stoch_d"] = df["stoch_k"].rolling(STOCH_D_PERIOD).mean()
    return df


def add_williams_r(df: pd.DataFrame) -> pd.DataFrame:
    high_max = df["high"].rolling(WILLIAMS_R_PERIOD).max()
    low_min = df["low"].rolling(WILLIAMS_R_PERIOD).min()
    df["williams_r"] = -100 * (high_max - df["close"]) / (high_max - low_min + 1e-10)
    return df


def add_roc(df: pd.DataFrame) -> pd.DataFrame:
    for p in ROC_PERIODS:
        df[f"roc_{p}"] = df["close"].pct_change(p) * 100
    return df


# ── Volatility indicators ────────────────────────────────────────────────────

def add_atr(df: pd.DataFrame) -> pd.DataFrame:
    """ATR, ATR normalised by price, and ATR relative to its 50-bar median."""
    tr = _true_range(df)
    df["atr"] = tr.ewm(span=ATR_PERIOD, adjust=False).mean()
    df["atr_pct"] = df["atr"] / df["close"]

    # atr_vs_median: ratio of current ATR to its rolling 50-bar median.
    # Values >> 1.0 signal a volatility spike (earnings, macro shock).
    # Used by SwingStrategyV2 to skip entries during abnormal volatility.
    atr_median = df["atr"].rolling(50, min_periods=10).median()
    df["atr_vs_median"] = (df["atr"] / (atr_median + 1e-10)).clip(upper=5.0)
    return df


def add_bollinger(df: pd.DataFrame) -> pd.DataFrame:
    mid = _sma(df["close"], BBANDS_PERIOD)
    std = df["close"].rolling(BBANDS_PERIOD).std()
    upper = mid + BBANDS_STD * std
    lower = mid - BBANDS_STD * std
    df["bb_width"] = (upper - lower) / (mid + 1e-10)
    df["bb_pct_b"] = (df["close"] - lower) / (upper - lower + 1e-10)
    return df


def add_historical_volatility(df: pd.DataFrame) -> pd.DataFrame:
    log_ret = np.log(df["close"] / df["close"].shift(1))
    df["hist_vol"] = log_ret.rolling(HIST_VOL_PERIOD).std() * np.sqrt(252 * 26)
    return df


# ── Volume indicators ────────────────────────────────────────────────────────

def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    vol_sma = _sma(df["volume"], VOLUME_SMA_PERIOD)
    df["volume_ratio"] = df["volume"] / (vol_sma + 1e-10)

    # OBV and its short-term slope
    obv = (np.sign(df["close"].diff()) * df["volume"]).cumsum()
    df["obv_slope"] = obv.diff(OBV_SLOPE_PERIOD) / (OBV_SLOPE_PERIOD * (obv.rolling(OBV_SLOPE_PERIOD).std() + 1e-10))
    return df


def add_mfi(df: pd.DataFrame) -> pd.DataFrame:
    """Money Flow Index – volume-weighted RSI variant."""
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    money_flow = typical_price * df["volume"]
    delta = typical_price.diff()

    pos_flow = money_flow.where(delta > 0, 0.0).rolling(MFI_PERIOD).sum()
    neg_flow = money_flow.where(delta <= 0, 0.0).rolling(MFI_PERIOD).sum()
    df["mfi"] = 100 - 100 / (1 + pos_flow / (neg_flow + 1e-10))
    return df


def add_vwap_distance(df: pd.DataFrame, is_us: bool) -> pd.DataFrame:
    """
    Intraday session VWAP distance.  VWAP resets at each calendar day.

    Computed for all stocks (EU + US): EU stocks have sufficient intraday
    volume for VWAP to be a meaningful mean-reversion anchor. The signal
    captures how extended price is from the day's value area.
    """
    typical = (df["high"] + df["low"] + df["close"]) / 3
    dates = df.index.date
    cum_tp_vol = (typical * df["volume"]).groupby(dates).cumsum()
    cum_vol = df["volume"].groupby(dates).cumsum()
    vwap = cum_tp_vol / (cum_vol + 1e-10)
    df["vwap_dist"] = (df["close"] - vwap) / (vwap + 1e-10)
    return df


# ── Price action ──────────────────────────────────────────────────────────────

def add_price_action(df: pd.DataFrame) -> pd.DataFrame:
    body = (df["close"] - df["open"]).abs()
    full_range = df["high"] - df["low"] + 1e-10
    df["candle_body_ratio"] = body / full_range

    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
    df["upper_wick_ratio"] = upper_wick / full_range
    df["lower_wick_ratio"] = lower_wick / full_range

    # Distance from 20-day rolling high / low (in bars: 20 days ≈ 20*26 15-min bars)
    roll_bars = 20 * 26
    rolling_high = df["high"].rolling(roll_bars, min_periods=1).max()
    rolling_low = df["low"].rolling(roll_bars, min_periods=1).min()
    df["dist_from_high"] = (df["close"] - rolling_high) / (rolling_high + 1e-10)
    df["dist_from_low"] = (df["close"] - rolling_low) / (rolling_low + 1e-10)

    # Overnight gap (first bar of day vs previous day's last bar)
    prev_close = df["close"].shift(1)
    df["gap_pct"] = (df["open"] - prev_close) / (prev_close + 1e-10)
    return df


# ── Multi-timeframe (5 m → 15 m) ─────────────────────────────────────────────

def add_multi_timeframe_features(
    df_primary: pd.DataFrame,
    df_secondary: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Compute lightweight features on 5-minute bars, resample to 15-minute
    cadence, and attach to the primary DataFrame.

    If df_secondary is None (data unavailable), fills with neutral zeros.
    """
    if df_secondary is None or df_secondary.empty:
        df_primary["mtf_rsi_divergence"] = 0.0
        df_primary["mtf_volume_spike"] = 0.0
        df_primary["mtf_momentum_confirm"] = 0.0
        df_primary["mtf_micro_trend"] = 0.0
        return df_primary

    sec = df_secondary.copy()

    # 5 m RSI
    delta = sec["close"].diff()
    gain = delta.clip(lower=0).ewm(span=SECONDARY_RSI_PERIOD, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=SECONDARY_RSI_PERIOD, adjust=False).mean()
    sec["rsi_5m"] = 100 - 100 / (1 + gain / (loss + 1e-10))

    # 5 m EMA slope (micro-trend)
    ema_short = _ema(sec["close"], SECONDARY_EMA_SHORT)
    sec["ema_slope_5m"] = ema_short.pct_change(3)

    # Volume spike flag
    vol_ma = _sma(sec["volume"], 20)
    sec["vol_spike"] = (sec["volume"] / (vol_ma + 1e-10)).clip(upper=10)

    # Momentum: 5-bar rate of change
    sec["mom_5m"] = sec["close"].pct_change(5)

    # Resample to 15 m by taking the last value within each 15-min bucket
    agg = sec[["rsi_5m", "vol_spike", "mom_5m", "ema_slope_5m"]].resample(
        "15min", closed="right", label="right"
    ).last()

    agg.columns = [
        "mtf_rsi_5m_last",
        "mtf_volume_spike",
        "mtf_momentum_confirm",
        "mtf_micro_trend",
    ]

    df_primary = df_primary.join(agg, how="left")
    df_primary[agg.columns] = df_primary[agg.columns].ffill().fillna(0.0)

    # RSI divergence = primary RSI minus 5 m RSI (requires primary RSI computed first)
    if "rsi" in df_primary.columns:
        df_primary["mtf_rsi_divergence"] = df_primary["rsi"] - df_primary["mtf_rsi_5m_last"]
    else:
        df_primary["mtf_rsi_divergence"] = 0.0

    return df_primary


# ── Calendar / session features ───────────────────────────────────────────────

def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df["hour_of_day"] = df.index.hour
    df["day_of_week"] = df.index.dayofweek  # Monday=0
    df["minutes_since_midnight"] = df.index.hour * 60 + df.index.minute
    return df


# ── Swing-specific features (added in v2 for longer-horizon prediction) ──────

def add_return_lags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Multi-horizon log returns – capture momentum at hourly, daily and weekly scales.
    Periods are in 15-min bars: 4 = 1 h, 26 = 1 day, 130 = 5 days (1 week).
    """
    for period, name in [(4, "1h"), (26, "1d"), (52, "2d"), (130, "1w")]:
        df[f"ret_{name}"] = np.log(df["close"] / df["close"].shift(period))
    return df


def add_volatility_regime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect volatility regime by comparing short-window vol to long-window vol.

    A ratio > 1 means current volatility is elevated vs the longer baseline,
    which often precedes mean reversion.
    """
    log_ret = np.log(df["close"] / df["close"].shift(1))
    short_vol = log_ret.rolling(20).std()
    long_vol = log_ret.rolling(100).std()
    df["vol_regime"] = short_vol / (long_vol + 1e-10)
    return df


def add_trend_strength(df: pd.DataFrame) -> pd.DataFrame:
    """
    Composite trend-strength signals beyond raw EMA crossovers.
    These help the model distinguish "weakly trending" from "strongly trending".
    """
    if "ema_50" in df.columns and "ema_200" in df.columns:
        df["trend_50_200"] = (df["ema_50"] - df["ema_200"]) / (df["ema_200"] + 1e-10)
    else:
        df["trend_50_200"] = 0.0

    if "ema_200" in df.columns:
        df["above_ema_200"] = (df["close"] > df["ema_200"]).astype(int)
        df["dist_ema_200"] = (df["close"] - df["ema_200"]) / (df["ema_200"] + 1e-10)
    else:
        df["above_ema_200"] = 0
        df["dist_ema_200"] = 0.0

    # Persistence of close-above-MA in last 20 bars (proxy for trend stability)
    if "ema_50" in df.columns:
        above_ema50 = (df["close"] > df["ema_50"]).astype(int)
        df["pct_bars_above_ema50"] = above_ema50.rolling(20).mean()
    else:
        df["pct_bars_above_ema50"] = 0.5
    return df


def add_breakout_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Donchian-channel-style breakout signals on multiple lookbacks.
    A close near the rolling high is a momentum signal favoured by swing systems.
    """
    for period in [20, 50, 100]:
        rolling_high = df["high"].rolling(period).max()
        rolling_low = df["low"].rolling(period).min()
        rng = rolling_high - rolling_low + 1e-10
        df[f"donchian_pos_{period}"] = (df["close"] - rolling_low) / rng
    return df


# ── DTosc (Dual-Timeframe Stochastic RSI) – ported from t212_miner_bot ───────

def add_dtosc_features(
    df: pd.DataFrame,
    df_5m: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    DTosc features so XGBoost/LightGBM can learn the dual-timeframe StochRSI
    regime and trigger signals that the Miner Bot uses for live trading.

    15-minute features (always computed on df):
        dtosc_fast_15m     StochRSI(13,8,5,5) fast line  [0-100]
        dtosc_slow_15m     StochRSI(13,8,5,5) slow line  [0-100]
        dtosc_momentum_15m fast − slow (signed, captures crossover speed)
        dtosc_regime       1 if (close > EMA200) AND (fast > slow) AND (fast < 75)

    5-minute features (resampled to 15m, zeros if no 5m data):
        dtosc_fast_5m      last StochRSI(8,5,3,3) fast per 15m window [0-100]
        dtosc_slow_5m      last StochRSI(8,5,3,3) slow per 15m window [0-100]
        dtosc_cross_5m     1 if a fresh bullish crossover occurred in the window
        dtosc_cross_depth  fast_5m level at the cross (lower = deeper oversold)

    Look-ahead safety
    -----------------
    - 15m StochRSI uses only past 15m bars via rolling/EWM → no future data.
    - 5m StochRSI is resampled with `.last()` which takes the final 5m bar
      inside each 15m window.  That bar closes at the same moment as the 15m
      bar (not a future bar) → zero look-ahead.
    - EMA-200 must already be in df (added by add_ema_features, called before
      this function in compute_all_features).
    """
    # ── 15m StochRSI ──────────────────────────────────────────────────────────
    fast_15m, slow_15m = _stoch_rsi_feat(
        df["close"], rsi_period=13, stoch_period=8, fast_sma=5, slow_sma=5
    )
    df["dtosc_fast_15m"]     = fast_15m
    df["dtosc_slow_15m"]     = slow_15m
    df["dtosc_momentum_15m"] = (fast_15m - slow_15m).fillna(0.0)

    # Use pre-computed EMA-200 if available (avoids recomputing 200-bar EWM)
    ema200 = df["ema_200"] if "ema_200" in df.columns else _ema(df["close"], 200)
    regime = (
        (df["close"] > ema200) &
        (fast_15m > slow_15m) &
        (fast_15m < 75.0)
    )
    df["dtosc_regime"] = regime.astype(int).fillna(0)

    # ── 5m StochRSI → resample to 15m ─────────────────────────────────────────
    if df_5m is not None and not df_5m.empty:
        fast_5m, slow_5m = _stoch_rsi_feat(
            df_5m["close"], rsi_period=8, stoch_period=5, fast_sma=3, slow_sma=3
        )

        # Fresh bullish crossover on 5m: fast crossed above slow (not overbought)
        cross_up = (
            (fast_5m.shift(1) <= slow_5m.shift(1)) &
            (fast_5m > slow_5m) &
            (fast_5m < 75.0)
        )

        # Depth of signal: fast_5m value AT the cross (NaN otherwise, for min-agg)
        cross_depth = fast_5m.where(cross_up, np.nan)

        agg_5m = pd.DataFrame({
            "fast_5m":      fast_5m,
            "slow_5m":      slow_5m,
            "cross_5m":     cross_up.astype(float),
            "cross_depth":  cross_depth,
        }).resample("15min", closed="right", label="right").agg({
            "fast_5m":     "last",  # latest 5m fast at the 15m bar close
            "slow_5m":     "last",  # latest 5m slow at the 15m bar close
            "cross_5m":    "max",   # 1 if any cross-up in this 15m window
            "cross_depth": "min",   # lowest (most oversold) fast_5m at a cross
        })
        # When no cross fired, cross_depth stays NaN → fill with 75 (neutral)
        agg_5m["cross_depth"] = agg_5m["cross_depth"].fillna(75.0)

        agg_5m = agg_5m.rename(columns={
            "fast_5m":    "dtosc_fast_5m",
            "slow_5m":    "dtosc_slow_5m",
            "cross_5m":   "dtosc_cross_5m",
            "cross_depth":"dtosc_cross_depth",
        })

        df_joined = df.join(agg_5m, how="left")
        for col in ["dtosc_fast_5m", "dtosc_slow_5m", "dtosc_cross_5m", "dtosc_cross_depth"]:
            df[col] = df_joined[col].ffill().fillna(50.0 if "depth" not in col else 75.0)

    else:
        # No 5m data: mirror 15m values so XGB always has the columns
        df["dtosc_fast_5m"]     = fast_15m.fillna(50.0)
        df["dtosc_slow_5m"]     = slow_15m.fillna(50.0)
        df["dtosc_cross_5m"]    = 0.0
        df["dtosc_cross_depth"] = 75.0

    return df


# ── Orchestrator ──────────────────────────────────────────────────────────────

FEATURE_COLUMNS: list[str] = []  # populated at first call


def compute_all_features(
    df_primary: pd.DataFrame,
    df_secondary: pd.DataFrame | None = None,
    symbol: str = "",
) -> pd.DataFrame:
    """
    Run the full feature-engineering pipeline on *df_primary* (15 m OHLCV).
    Optionally merges multi-timeframe features from *df_secondary* (5 m).

    Returns the enriched DataFrame.  Feature column names are stored in
    ``FEATURE_COLUMNS`` for downstream consumers.
    """
    global FEATURE_COLUMNS

    is_us = symbol in US_SYMBOLS

    cols_before = set(df_primary.columns)

    # Trend
    add_ema_features(df_primary)
    add_macd(df_primary)
    add_adx(df_primary)

    # Momentum
    add_rsi(df_primary)
    add_stochastic(df_primary)
    add_williams_r(df_primary)
    add_roc(df_primary)

    # Volatility
    add_atr(df_primary)
    add_bollinger(df_primary)
    add_historical_volatility(df_primary)

    # Volume
    add_volume_features(df_primary)
    add_mfi(df_primary)
    add_vwap_distance(df_primary, is_us=is_us)

    # Price action
    add_price_action(df_primary)

    # Multi-timeframe
    add_multi_timeframe_features(df_primary, df_secondary)

    # Calendar
    add_calendar_features(df_primary)

    # Swing-specific (v2): return lags, vol regime, trend strength, breakouts
    add_return_lags(df_primary)
    add_volatility_regime(df_primary)
    add_trend_strength(df_primary)
    add_breakout_features(df_primary)

    # DTosc (v4): dual-timeframe StochRSI features (must come after add_ema_features)
    add_dtosc_features(df_primary, df_secondary)

    new_cols = sorted(set(df_primary.columns) - cols_before)
    if not FEATURE_COLUMNS:
        FEATURE_COLUMNS = new_cols
    return df_primary


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return the list of feature column names present in *df*."""
    base_ohlcv = {"open", "high", "low", "close", "volume"}
    return [c for c in df.columns if c not in base_ohlcv and c != "label"]


# ── Cross-asset: sector relative-strength (computed across all symbols) ───────

def compute_sector_relative_strength(
    all_dfs: dict[str, pd.DataFrame],
    lookback_bars: int = 130,   # 5 trading days in 15-min bars
) -> dict[str, pd.Series]:
    """
    For each symbol, compute its normalised return rank within its sector
    over a rolling window.

    Returns {symbol: Series(float 0..1)} aligned to the symbol's index.
    A value near 1.0 means the stock is outperforming sector peers;
    near 0.0 means underperforming.

    This function is called *once* on the full dataset before per-symbol
    feature engineering, so the sector RS can be attached as an extra feature.
    """
    # Build a sector → list-of-symbols map using only available data
    symbol_to_sector: dict[str, str] = {}
    for sector, members in SECTORS.items():
        for sym in members:
            if sym in all_dfs:
                symbol_to_sector[sym] = sector

    # Rolling return for every symbol
    rolling_returns: dict[str, pd.Series] = {}
    for sym, df in all_dfs.items():
        close = df["close"]
        rolling_returns[sym] = close.pct_change(lookback_bars)

    result: dict[str, pd.Series] = {}
    for sym in all_dfs:
        sector = symbol_to_sector.get(sym)
        if sector is None:
            # No sector defined – set neutral
            result[sym] = pd.Series(0.5, index=all_dfs[sym].index)
            continue

        peers = [s for s in SECTORS[sector] if s in rolling_returns and s != sym]
        if not peers:
            result[sym] = pd.Series(0.5, index=all_dfs[sym].index)
            continue

        # Align all peer returns to this symbol's timestamp index, then rank
        sym_ret = rolling_returns[sym]
        peer_rets = [rolling_returns[p].reindex(sym_ret.index, method="ffill") for p in peers]

        # Row-wise percentile rank (0 = worst in sector, 1 = best)
        all_rets = pd.concat([sym_ret] + peer_rets, axis=1)
        all_rets.columns = [sym] + peers
        rank_pct = all_rets.rank(axis=1, pct=True)[sym]
        result[sym] = rank_pct.fillna(0.5)

    return result


def attach_sector_rs(df: pd.DataFrame, rs_series: pd.Series) -> pd.DataFrame:
    """Merge pre-computed sector RS values onto a symbol's DataFrame."""
    df["sector_rs"] = rs_series.reindex(df.index, method="ffill").fillna(0.5)
    return df
