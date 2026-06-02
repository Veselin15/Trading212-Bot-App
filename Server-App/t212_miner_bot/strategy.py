"""
Swing-trading strategy: signal generation and trade management.

All three strategy generations live in this single module:

  SwingStrategy    — v1 base (ATR trailing stop, session filter)
  SwingStrategyV2  — adds volatility-spike filter, RSI gate, asymmetric time
                     exit, EU-open guard.  Drop-in replacement for V1.
  SwingStrategyV3  — production strategy (BEST_SAFE deployment).  Extends V2
                     with trend-scaled take-profit, breakout tight stop, and
                     optional dToSC momentum confirmation.

Usage
-----
    from t212_miner_bot.strategy import SwingStrategyV3, Signal, Position
    strategy = SwingStrategyV3(trend_scaled_tp=True, breakout_tight_stop=True)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from t212_miner_bot.config import (
    SIGNAL_CONFIDENCE_THRESHOLD,
    EXEC_TP_ATR_MULT,
    EXEC_SL_ATR_MULT,
    MAX_HOLDING_BARS,
    REQUIRE_TREND_UP,
    MIN_ADX_FOR_ENTRY,
    COOLDOWN_BARS_AFTER_TRADE,
    ATR_TRAIL_MULT,
    ATR_TRAIL_ACTIVATE_R,
    SESSION_FILTER_ENABLED,
    SESSION_CLOSE_BLOCK_UTC_HOUR,
    SESSION_CLOSE_BLOCK_UTC_MINUTE,
    V2_TRAIL_MULT,
    V2_TRAIL_ACTIVATE_R,
    V2_VOL_SPIKE_MULT,
    V2_RSI_MIN_ENTRY,
    V2_MAX_HOLDING_BARS_LOSS,
    V2_SESSION_OPEN_GUARD_MIN,
)


# ── Shared data classes ───────────────────────────────────────────────────────

@dataclass
class Signal:
    """A BUY signal emitted by the strategy."""
    symbol: str
    timestamp: datetime
    entry_price: float
    confidence: float
    atr: float
    take_profit: float
    stop_loss: float


@dataclass
class Position:
    """Tracks an open long position including trailing-stop and scale-out state."""
    symbol: str
    entry_price: float
    shares: float
    entry_time: datetime
    take_profit: float
    stop_loss: float

    entry_atr: float = 0.0
    high_since_entry: float = 0.0
    trail_stop: float = 0.0
    trail_active: bool = False
    scale_out_done: bool = False
    pyramid_done: bool = False
    pyramid2_done: bool = False
    original_shares: float = 0.0
    bars_held: int = 0


# ── SwingStrategy (v1) ────────────────────────────────────────────────────────

class SwingStrategy:
    """
    Long-only swing strategy driven by model confidence scores.

    Entry rules (all must pass, evaluated in order):
      1. Cooldown since last exit for this symbol
      2. Confidence >= threshold
      3. ATR non-zero (market is active)
      4. Trend filter: close > EMA200 and EMA50 > EMA200 (if required_trend_up)
      5. ADX >= min_adx (avoid choppy markets)
      6. Session filter: not within the last 45 min of the EU session

    Exit rules (checked every bar, highest priority first):
      1. Take-profit ceiling hit
      2. ATR trailing stop triggered (once trail has activated)
      3. Initial stop-loss hit
      4. Max holding bars reached
    """

    def __init__(
        self,
        confidence_threshold: float = SIGNAL_CONFIDENCE_THRESHOLD,
        tp_atr_mult: float = EXEC_TP_ATR_MULT,
        sl_atr_mult: float = EXEC_SL_ATR_MULT,
        max_holding_bars: int = MAX_HOLDING_BARS,
        require_trend_up: bool = REQUIRE_TREND_UP,
        min_adx: float = MIN_ADX_FOR_ENTRY,
        cooldown_bars: int = COOLDOWN_BARS_AFTER_TRADE,
        cooldown_bars_win: Optional[int] = None,
        trail_mult: float = ATR_TRAIL_MULT,
        trail_activate_r: float = ATR_TRAIL_ACTIVATE_R,
        session_filter: bool = SESSION_FILTER_ENABLED,
        session_close_hour: int = SESSION_CLOSE_BLOCK_UTC_HOUR,
        session_close_minute: int = SESSION_CLOSE_BLOCK_UTC_MINUTE,
    ):
        self.confidence_threshold = confidence_threshold
        self.tp_atr_mult          = tp_atr_mult
        self.sl_atr_mult          = sl_atr_mult
        self.max_holding_bars     = max_holding_bars
        self.require_trend_up     = require_trend_up
        self.min_adx              = min_adx
        self.cooldown_bars        = cooldown_bars
        self.cooldown_bars_win    = cooldown_bars_win if cooldown_bars_win is not None else cooldown_bars
        self.trail_mult           = trail_mult
        self.trail_activate_r     = trail_activate_r
        self.session_filter       = session_filter
        self.session_close_hour   = session_close_hour
        self.session_close_minute = session_close_minute

    def generate_signal(
        self,
        symbol: str,
        row: pd.Series,
        confidence: float,
        open_symbols: set,
        bars_since_last_trade: int = 9999,
        threshold_override: Optional[float] = None,
        last_exit_was_win: bool = True,
    ) -> Optional[Signal]:
        if symbol in open_symbols:
            return None

        effective_cooldown = self.cooldown_bars_win if last_exit_was_win else self.cooldown_bars
        if bars_since_last_trade < effective_cooldown:
            return None

        effective_threshold = threshold_override if threshold_override is not None else self.confidence_threshold
        if confidence < effective_threshold:
            return None

        atr = row.get("atr", 0.0)
        if atr <= 0 or np.isnan(atr):
            return None

        if self.require_trend_up:
            close   = row["close"]
            ema_50  = row.get("ema_50",  close)
            ema_200 = row.get("ema_200", close)
            if pd.isna(ema_50) or pd.isna(ema_200):
                return None
            if close < ema_200 or ema_50 < ema_200:
                return None

        adx = row.get("adx", 0.0)
        if pd.isna(adx) or adx < self.min_adx:
            return None

        if self.session_filter:
            ts = row.name
            if hasattr(ts, "hour"):
                h, m = ts.hour, ts.minute
                if h > self.session_close_hour or (
                    h == self.session_close_hour and m >= self.session_close_minute
                ):
                    return None

        entry_price = row["close"]
        tp = entry_price + self.tp_atr_mult * atr
        sl = entry_price - self.sl_atr_mult * atr

        return Signal(
            symbol=symbol,
            timestamp=row.name if hasattr(row, "name") else datetime.utcnow(),
            entry_price=entry_price,
            confidence=confidence,
            atr=atr,
            take_profit=tp,
            stop_loss=sl,
        )

    def check_exit(
        self,
        position: Position,
        current_high: float,
        current_low: float,
        current_close: float,
    ) -> Optional[str]:
        position.bars_held += 1

        if current_high > position.high_since_entry:
            position.high_since_entry = current_high

        if current_high >= position.take_profit:
            return "take_profit"

        if position.entry_atr > 0:
            activate_at = position.entry_price + self.trail_activate_r * position.entry_atr
            if not position.trail_active and position.high_since_entry >= activate_at:
                position.trail_active = True

            if position.trail_active:
                new_trail = position.high_since_entry - self.trail_mult * position.entry_atr
                if new_trail > position.trail_stop:
                    position.trail_stop = new_trail
                if current_low <= position.trail_stop:
                    return "trail_stop"

        if current_low <= position.stop_loss:
            return "stop_loss"

        if position.bars_held >= self.max_holding_bars:
            return "time_exit"

        return None

    def exit_price(self, position: Position, reason: str, bar: pd.Series) -> float:
        if reason == "take_profit":
            return position.take_profit
        if reason == "trail_stop":
            return position.trail_stop
        if reason == "stop_loss":
            return position.stop_loss
        return bar["close"]


# ── SwingStrategyV2 ───────────────────────────────────────────────────────────

class SwingStrategyV2(SwingStrategy):
    """
    V1 + five additional entry/exit improvements:

      1. Trail params kept at v1 values (2.5R activation, 2.5 ATR trail).
         Earlier trail (1.5R, 2.0 ATR) hurt because trail fires below entry.
      2. Volatility spike filter — blocks entry when ATR > 1.8× 50-bar median.
      3. RSI quality gate — RSI > 40 at entry.
      4. Asymmetric time exit — losers cut at 80 bars, winners run to 200 bars.
      5. EU open guard — blocks first 15 min of EU open (09:00–09:15 UTC).
    """

    def __init__(
        self,
        *args,
        max_holding_bars_loss: int = V2_MAX_HOLDING_BARS_LOSS,
        vol_spike_mult: float = V2_VOL_SPIKE_MULT,
        rsi_min_entry: float = V2_RSI_MIN_ENTRY,
        session_open_guard_min: int = V2_SESSION_OPEN_GUARD_MIN,
        trail_mult: float = V2_TRAIL_MULT,
        trail_activate_r: float = V2_TRAIL_ACTIVATE_R,
        **kwargs,
    ):
        super().__init__(*args, trail_mult=trail_mult,
                         trail_activate_r=trail_activate_r, **kwargs)
        self.max_holding_bars_loss  = max_holding_bars_loss
        self.vol_spike_mult         = vol_spike_mult
        self.rsi_min_entry          = rsi_min_entry
        self.session_open_guard_min = session_open_guard_min

    def generate_signal(
        self,
        symbol: str,
        row: pd.Series,
        confidence: float,
        open_symbols: set,
        bars_since_last_trade: int = 9999,
        threshold_override: Optional[float] = None,
        last_exit_was_win: bool = True,
    ) -> Optional[Signal]:
        if symbol in open_symbols:
            return None

        effective_cooldown = self.cooldown_bars_win if last_exit_was_win else self.cooldown_bars
        if bars_since_last_trade < effective_cooldown:
            return None

        effective_threshold = threshold_override if threshold_override is not None else self.confidence_threshold
        if confidence < effective_threshold:
            return None

        atr = row.get("atr", 0.0)
        if atr <= 0 or np.isnan(atr):
            return None

        # Volatility spike filter
        atr_vs_median = row.get("atr_vs_median", 1.0)
        if not np.isnan(atr_vs_median) and atr_vs_median > self.vol_spike_mult:
            return None

        # RSI quality gate
        rsi = row.get("rsi", 50.0)
        if not np.isnan(rsi) and rsi < self.rsi_min_entry:
            return None

        # Trend filter
        if self.require_trend_up:
            close   = row["close"]
            ema_50  = row.get("ema_50",  close)
            ema_200 = row.get("ema_200", close)
            if pd.isna(ema_50) or pd.isna(ema_200):
                return None
            if close < ema_200 or ema_50 < ema_200:
                return None

        # ADX filter
        adx = row.get("adx", 0.0)
        if pd.isna(adx) or adx < self.min_adx:
            return None

        # Session filters
        if self.session_filter:
            ts = row.name
            if hasattr(ts, "hour"):
                h, m = ts.hour, ts.minute
                eu_open_minutes = h * 60 + m - (9 * 60)
                if 0 <= eu_open_minutes < self.session_open_guard_min:
                    return None
                if h > self.session_close_hour or (
                    h == self.session_close_hour and m >= self.session_close_minute
                ):
                    return None

        entry_price = row["close"]
        tp = entry_price + self.tp_atr_mult * atr
        sl = entry_price - self.sl_atr_mult * atr

        return Signal(
            symbol=symbol,
            timestamp=row.name if hasattr(row, "name") else datetime.utcnow(),
            entry_price=entry_price,
            confidence=confidence,
            atr=atr,
            take_profit=tp,
            stop_loss=sl,
        )

    def check_exit(
        self,
        position: Position,
        current_high: float,
        current_low: float,
        current_close: float,
    ) -> Optional[str]:
        position.bars_held += 1

        if current_high > position.high_since_entry:
            position.high_since_entry = current_high

        if current_high >= position.take_profit:
            return "take_profit"

        if position.entry_atr > 0:
            activate_at = position.entry_price + self.trail_activate_r * position.entry_atr
            if not position.trail_active and position.high_since_entry >= activate_at:
                position.trail_active = True
            if position.trail_active:
                new_trail = position.high_since_entry - self.trail_mult * position.entry_atr
                if new_trail > position.trail_stop:
                    position.trail_stop = new_trail
                if current_low <= position.trail_stop:
                    return "trail_stop"

        if current_low <= position.stop_loss:
            return "stop_loss"

        # Asymmetric time exit
        is_profitable = current_close > position.entry_price
        max_bars = self.max_holding_bars if is_profitable else self.max_holding_bars_loss
        if position.bars_held >= max_bars:
            return "time_exit"

        return None

    def exit_price(self, position: Position, reason: str, bar: pd.Series) -> float:
        if reason == "take_profit":
            return position.take_profit
        if reason == "trail_stop":
            return position.trail_stop
        if reason == "stop_loss":
            return position.stop_loss
        return bar["close"]


# ── SwingStrategyV3 (PRODUCTION) ──────────────────────────────────────────────

class SwingStrategyV3(SwingStrategyV2):
    """
    Production strategy — BEST_SAFE deployment config.

    Extends V2 with three toggleable improvements:

      trend_scaled_tp (default ON in production)
        TP distance widens with ADX strength at entry:
          ADX >= 35  →  7.0 ATR (very strong trend)
          ADX >= 25  →  6.0 ATR (strong trend)
          else       →  5.0 ATR (standard)

      breakout_tight_stop (default ON in production)
        On fresh Donchian-20 breakouts (donchian_pos_20 >= 0.95) the initial
        SL tightens to 2.0 ATR instead of 2.5 ATR.  Improves R:R on the
        highest-conviction breakout entries.

      require_dtosc_confirm (default OFF)
        Optional dual-timeframe StochRSI gate.  Not used in production
        (marginal gain in validation; off by default to limit complexity).

    Instantiate via production.build_strategy() for the correct defaults.
    """

    def __init__(
        self,
        *args,
        trend_scaled_tp: bool = False,
        require_dtosc_confirm: bool = False,
        breakout_tight_stop: bool = False,
        tp_strong_adx: float = 6.0,
        tp_very_strong_adx: float = 7.0,
        breakout_sl_mult: float = 2.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.trend_scaled_tp       = trend_scaled_tp
        self.require_dtosc_confirm = require_dtosc_confirm
        self.breakout_tight_stop   = breakout_tight_stop
        self.tp_strong_adx         = tp_strong_adx
        self.tp_very_strong_adx    = tp_very_strong_adx
        self.breakout_sl_mult      = breakout_sl_mult

    def generate_signal(
        self,
        symbol: str,
        row: pd.Series,
        confidence: float,
        open_symbols: set,
        bars_since_last_trade: int = 9999,
        threshold_override: Optional[float] = None,
        last_exit_was_win: bool = True,
    ) -> Optional[Signal]:
        sig = super().generate_signal(
            symbol, row, confidence, open_symbols,
            bars_since_last_trade=bars_since_last_trade,
            threshold_override=threshold_override,
            last_exit_was_win=last_exit_was_win,
        )
        if sig is None:
            return None

        # Optional dToSC momentum confirmation
        if self.require_dtosc_confirm:
            regime = row.get("dtosc_regime", 1)
            if not np.isnan(regime) and regime < 1:
                return None

        atr   = sig.atr
        entry = sig.entry_price

        # Trend-scaled take-profit
        if self.trend_scaled_tp:
            adx = row.get("adx", 0.0)
            if not np.isnan(adx) and adx >= 35:
                tp_mult = self.tp_very_strong_adx
            elif not np.isnan(adx) and adx >= 25:
                tp_mult = self.tp_strong_adx
            else:
                tp_mult = self.tp_atr_mult
            sig.take_profit = entry + tp_mult * atr

        # Breakout tight stop
        if self.breakout_tight_stop:
            donchian = row.get("donchian_pos_20", 0.0)
            if not np.isnan(donchian) and donchian >= 0.95:
                sig.stop_loss = entry - self.breakout_sl_mult * atr

        return sig
