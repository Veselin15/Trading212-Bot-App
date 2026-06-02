"""
Global Portfolio Backtest Engine  (v4)

Key upgrades over v3:
  - Signal ranking ("traffic jam"):  when multiple symbols trigger a BUY on
    the same bar, they are sorted by score (highest conviction first) and
    capital is allocated in that order until cash / exposure is exhausted.
  - Flexible signal input:  accepts either pre-trained ML models or a
    pre-computed ``signal_cache`` dict (rule-based strategies) through the
    same code path.  The rest of the engine (position management, Kelly
    sizing, FX, reporting) is identical for both.
  - Explicit cash tracking:  ``self.cash`` is the single source of truth.
    Exposure is checked against portfolio-value-at-entry so a single large
    winner does not silently unlock extra leverage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from t212_miner_bot.config import (
    INITIAL_CAPITAL,
    MAX_TOTAL_EXPOSURE_PCT,
    MAX_OPEN_POSITIONS,
    FX_SPREAD_PCT,
    RISK_PER_TRADE_PCT,
    SYMBOL_THRESHOLDS,
    SYMBOL_RISK_PCT,
    SYMBOL_SECTOR,
    SCALE_OUT_ENABLED,
    SCALE_OUT_ATR_MULT,
    SCALE_OUT_FRACTION,
    MACRO_FILTER_ENABLED,
    MACRO_FILTER_MIN_UPTREND,
    PYRAMID_ENABLED,
    PYRAMID_ATR_MULT,
    PYRAMID_FRACTION,
    PYRAMID_SYMBOLS,
    SECTOR_CLAMPING_ENABLED,
    DYNAMIC_MACRO_RISK_ENABLED,
    MACRO_REGIME_BULL_THRESHOLD,
    MACRO_BULL_RISK_SCALE,
    MACRO_BEAR_RISK_SCALE,
)
from t212_miner_bot.strategy import SwingStrategy, Position
from t212_miner_bot.position_sizing import (
    calculate_position_size,
    adjust_for_available_cash,
)
from t212_miner_bot.tax_handler import fx_cost
from t212_miner_bot.portfolio_risk import PortfolioHeatGuard, DrawdownPositionScaler

logger = logging.getLogger(__name__)


# ── Trade record ──────────────────────────────────────────────────────────────

@dataclass
class TradeRecord:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    shares: float
    pnl_gross: float
    fx_costs: float
    pnl_net: float
    exit_reason: str
    bars_held: int
    entry_confidence: float = 0.0


# ── Engine ────────────────────────────────────────────────────────────────────

class BacktestEngine:
    """
    Single-portfolio, multi-symbol walk-forward simulator.

    Usage (ML path)::

        engine = BacktestEngine(strategy)
        equity = engine.run(test_data, models=models, feature_cols=fcols_map)

    Usage (rule-based path)::

        scores = {sym: pd.Series(...) for sym in test_data}
        engine = BacktestEngine(strategy)
        equity = engine.run(test_data, signal_cache=scores)
    """

    def __init__(
        self,
        strategy: SwingStrategy,
        initial_capital: float = INITIAL_CAPITAL,
        scale_out_enabled: bool = SCALE_OUT_ENABLED,
        scale_out_atr_mult: float = SCALE_OUT_ATR_MULT,
        scale_out_fraction: float = SCALE_OUT_FRACTION,
        macro_filter_enabled: bool = MACRO_FILTER_ENABLED,
        macro_filter_min_uptrend: float = MACRO_FILTER_MIN_UPTREND,
        pyramid_enabled: bool = PYRAMID_ENABLED,
        pyramid_atr_mult: float = PYRAMID_ATR_MULT,
        pyramid_fraction: float = PYRAMID_FRACTION,
        pyramid_symbols: Optional[set] = None,
        # Second pyramid: add another tranche when trade reaches +3.0R
        pyramid2_enabled: bool = False,
        pyramid2_atr_mult: float = 3.0,
        pyramid2_fraction: float = 0.25,
        risk_scale: float = 1.0,
        # Structural limits (overridable without config change)
        max_open_positions: int = MAX_OPEN_POSITIONS,
        # Sector clamping: reject BUY if same sector is already held
        sector_clamping_enabled: bool = SECTOR_CLAMPING_ENABLED,
        # Dynamic macro risk: scale position size by broad-market regime
        dynamic_macro_risk_enabled: bool = DYNAMIC_MACRO_RISK_ENABLED,
        macro_regime_bull_threshold: float = MACRO_REGIME_BULL_THRESHOLD,
        macro_bull_risk_scale: float = MACRO_BULL_RISK_SCALE,
        macro_bear_risk_scale: float = MACRO_BEAR_RISK_SCALE,
        # Portfolio risk guards (v2): optional, backward-compatible
        portfolio_heat_guard: Optional[PortfolioHeatGuard] = None,
        drawdown_position_scaler: Optional[DrawdownPositionScaler] = None,
        # Risk ceilings (v3): make the hard caps configurable so the
        # drawdown headroom can be converted into profit. Defaults preserve
        # the original behaviour exactly.
        max_total_exposure_pct: float = MAX_TOTAL_EXPOSURE_PCT,
        position_cap_ceiling: float = 0.70,   # max single-position % ceiling
        risk_cap_ceiling: float = 0.50,       # max per-trade risk % ceiling
        # GMM regime (v4): optional per-bar risk multiplier series. When given,
        # it REPLACES the binary bull/bear dynamic-macro scaling with a smooth,
        # probabilistic regime-driven multiplier (see regime_gmm.py).
        regime_risk_series: Optional[pd.Series] = None,
        # Fractional Kelly (v4): optional {symbol: risk_pct} dict that REPLACES
        # the static SYMBOL_RISK_PCT tiers with empirically-calibrated risk
        # weights (see kelly_sizing.py).  Still scaled by risk_scale & ceilings.
        symbol_risk_override: Optional[Dict[str, float]] = None,
        # Kelly-on-caps (v4): optional {symbol: cap_pct} dict that REPLACES
        # SYMBOL_MAX_POSITION_PCT.  Because the position cap is the binding
        # constraint in the aggressive config, varying the cap by edge is the
        # effective way to concentrate capital in the best setups.
        symbol_cap_override: Optional[Dict[str, float]] = None,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.scale_out_enabled = scale_out_enabled
        self.scale_out_atr_mult = scale_out_atr_mult
        self.scale_out_fraction = scale_out_fraction
        self.macro_filter_enabled = macro_filter_enabled
        self.macro_filter_min_uptrend = macro_filter_min_uptrend
        self.pyramid_enabled = pyramid_enabled
        self.pyramid_atr_mult = pyramid_atr_mult
        self.pyramid_fraction = pyramid_fraction
        self.pyramid_symbols = pyramid_symbols if pyramid_symbols is not None else PYRAMID_SYMBOLS
        self.pyramid2_enabled  = pyramid2_enabled
        self.pyramid2_atr_mult = pyramid2_atr_mult
        self.pyramid2_fraction = pyramid2_fraction
        self.risk_scale = risk_scale
        self.max_open_positions = max_open_positions
        self.sector_clamping_enabled     = sector_clamping_enabled
        self.dynamic_macro_risk_enabled  = dynamic_macro_risk_enabled
        self.macro_regime_bull_threshold = macro_regime_bull_threshold
        self.macro_bull_risk_scale       = macro_bull_risk_scale
        self.macro_bear_risk_scale       = macro_bear_risk_scale
        self.portfolio_heat_guard        = portfolio_heat_guard
        self.drawdown_position_scaler    = drawdown_position_scaler
        self.max_total_exposure_pct      = max_total_exposure_pct
        self.position_cap_ceiling        = position_cap_ceiling
        self.risk_cap_ceiling            = risk_cap_ceiling
        self.regime_risk_series          = regime_risk_series

        # Pre-scale the risk/cap dicts so _open_position doesn't recompute per call.
        # When a Kelly override is supplied, it replaces the static SYMBOL_RISK_PCT.
        from t212_miner_bot.config import SYMBOL_MAX_POSITION_PCT as _BASE_CAPS
        _risk_base = symbol_risk_override if symbol_risk_override is not None else SYMBOL_RISK_PCT
        _cap_base  = symbol_cap_override  if symbol_cap_override  is not None else _BASE_CAPS
        self._scaled_risk_pct: Dict[str, float] = {
            k: min(v * risk_scale, risk_cap_ceiling) for k, v in _risk_base.items()
        }
        self._scaled_max_pos_pct: Dict[str, float] = {
            k: min(v * risk_scale, position_cap_ceiling) for k, v in _cap_base.items()
        }
        self._scaled_default_risk = min(RISK_PER_TRADE_PCT * risk_scale, risk_cap_ceiling)

        self.cash: float = initial_capital
        self.equity_curve: List[Dict] = []
        self.trades: List[TradeRecord] = []
        self.open_positions: Dict[str, Position] = {}
        self.last_exit_bar_idx: Dict[str, int] = {}
        # Track whether the last full close for each symbol was profitable.
        # Used to apply a shorter cooldown after winning exits (momentum re-entry).
        self.last_exit_was_win: Dict[str, bool] = {}
        self._universe_regime: Optional[pd.Series] = None  # pre-computed macro signal

    # ── Public ────────────────────────────────────────────────────────────

    def run(
        self,
        test_data: Dict[str, pd.DataFrame],
        models: Optional[Dict] = None,
        feature_cols: Optional[Dict[str, List[str]]] = None,
        signal_cache: Optional[Dict[str, pd.Series]] = None,
        symbol_thresholds: Optional[Dict[str, float]] = None,
    ) -> pd.DataFrame:
        """
        Step through time chronologically across all symbols.

        Parameters
        ----------
        test_data         : {symbol: OHLCV+features DataFrame}
        models            : {symbol: EnsembleModel}  – supply for AI strategies
        feature_cols      : {symbol: list[str]}       – feature names for ML prediction
        signal_cache      : {symbol: pd.Series}       – pre-computed scores 0..1
                            (rule-based strategies supply this instead of models)
        symbol_thresholds : optional override for per-symbol confidence thresholds;
                            falls back to the global SYMBOL_THRESHOLDS from config

        Returns the equity curve as a DataFrame indexed by timestamp.
        """
        # ── Build score cache (one path for ML, one for rule-based) ──────
        proba_cache: Dict[str, pd.Series] = {}

        if signal_cache is not None:
            proba_cache = signal_cache

        elif models is not None and feature_cols is not None:
            for symbol, df in test_data.items():
                model = models.get(symbol)
                fcols = feature_cols.get(symbol, [])
                if model is None or not fcols:
                    continue
                try:
                    X = df[fcols].fillna(0.0)
                    probs = model.predict_proba(X)
                    proba_cache[symbol] = pd.Series(probs, index=df.index)
                except Exception as exc:
                    logger.warning("  [%s] predict_proba failed: %s", symbol, exc)

        else:
            raise ValueError(
                "Provide either (models + feature_cols) or signal_cache."
            )

        # Use caller-supplied thresholds or fall back to global config
        _thresholds = symbol_thresholds if symbol_thresholds is not None else SYMBOL_THRESHOLDS

        # ── Macro regime filter: pre-compute per-timestamp uptrend fraction ──
        if self.macro_filter_enabled:
            self._universe_regime = self._compute_universe_regime(test_data)

        # ── Dynamic macro risk: pre-compute bull/bear regime series ──────────
        # Uses the same EMA200 fraction but with a potentially different threshold.
        # Stored separately so macro_filter and dynamic_macro_risk can coexist.
        _dyn_regime: Optional[pd.Series] = None
        if self.dynamic_macro_risk_enabled:
            _dyn_regime = self._compute_regime_fraction(test_data)

        # ── Unified timeline ──────────────────────────────────────────────
        all_ts: set = set()
        for df in test_data.values():
            all_ts.update(df.index)
        timeline = sorted(all_ts)

        for bar_idx, ts in enumerate(timeline):

            # 1. Process exits first (before opening new positions)
            self._process_exits(ts, test_data, bar_idx)

            # Portfolio risk: refresh guards with current equity
            _current_equity = self._mark_to_market(ts, test_data)
            _ts_pd = pd.Timestamp(ts) if not isinstance(ts, pd.Timestamp) else ts
            if self.portfolio_heat_guard is not None:
                self.portfolio_heat_guard.update(_current_equity, _ts_pd)
            if self.drawdown_position_scaler is not None:
                self.drawdown_position_scaler.update_peak(_current_equity)

            # 2. Collect ALL buy signals at this timestamp with their scores
            open_syms = set(self.open_positions.keys())
            pending: List[Tuple[float, object, str]] = []   # (score, signal, symbol)

            # Sector clamping: build the set of sectors already held this bar
            open_sectors: set = set()
            if self.sector_clamping_enabled:
                open_sectors = {
                    SYMBOL_SECTOR[s]
                    for s in open_syms
                    if s in SYMBOL_SECTOR
                }

            for symbol, df in test_data.items():
                if ts not in df.index:
                    continue
                if symbol in open_syms:
                    continue
                if symbol not in proba_cache:
                    continue
                # Sector clamping: skip if this symbol's sector is already held
                if self.sector_clamping_enabled:
                    sym_sector = SYMBOL_SECTOR.get(symbol)
                    if sym_sector and sym_sector in open_sectors:
                        continue

                score_series = proba_cache[symbol]
                if ts not in score_series.index:
                    continue

                score = float(score_series.loc[ts])
                row = df.loc[ts]
                last_exit = self.last_exit_bar_idx.get(symbol, -10_000)
                bars_since = bar_idx - last_exit
                was_win = self.last_exit_was_win.get(symbol, True)

                signal = self.strategy.generate_signal(
                    symbol, row, score, open_syms,
                    bars_since_last_trade=bars_since,
                    threshold_override=_thresholds.get(symbol),
                    last_exit_was_win=was_win,
                )
                if signal is not None:
                    pending.append((score, signal, symbol))

            # 3. TRAFFIC-JAM RESOLUTION: highest conviction gets capital first
            pending.sort(key=lambda x: x[0], reverse=True)

            # Macro regime gate: skip all new entries when market is in downtrend
            macro_ok = True
            if self.macro_filter_enabled and self._universe_regime is not None:
                if ts in self._universe_regime.index:
                    macro_ok = bool(self._universe_regime.loc[ts])

            # Dynamic macro risk: determine per-bar effective risk scale.
            # Priority 1: GMM regime multiplier (smooth, probabilistic) if supplied.
            # Priority 2: binary bull/bear dynamic-macro scaling.
            effective_risk_scale = self.risk_scale
            if self.regime_risk_series is not None and ts in self.regime_risk_series.index:
                effective_risk_scale = float(self.regime_risk_series.loc[ts])
            elif self.dynamic_macro_risk_enabled and _dyn_regime is not None:
                if ts in _dyn_regime.index:
                    uptrend_frac = float(_dyn_regime.loc[ts])
                    if uptrend_frac >= self.macro_regime_bull_threshold:
                        effective_risk_scale = self.macro_bull_risk_scale
                    else:
                        effective_risk_scale = self.macro_bear_risk_scale

            # True compounding: size new positions off current mark-to-market
            # equity (cash + unrealized P&L of all open positions), not cost basis.
            # Recompute after every allocation – each fill reduces available cash.
            current_portfolio_value = self._mark_to_market(ts, test_data)

            # Daily circuit breaker: stop entries if today's loss exceeds limit
            _heat_ok = (
                self.portfolio_heat_guard is None
                or self.portfolio_heat_guard.can_open(current_portfolio_value)
            )

            # Drawdown scaler: multiplicative factor applied to risk %
            _dd_scale = 1.0
            if self.drawdown_position_scaler is not None:
                _dd_scale = self.drawdown_position_scaler.scale_factor(current_portfolio_value)

            for score, signal, symbol in pending:
                if not macro_ok or not _heat_ok:
                    break  # entire pending batch blocked
                # Re-check open positions after each allocation (a previous
                # iteration in this loop may have used up cash / slots)
                if len(self.open_positions) >= self.max_open_positions:
                    break
                self._open_position(signal, symbol,
                                    portfolio_value=current_portfolio_value,
                                    risk_scale_override=effective_risk_scale * _dd_scale)
                # Refresh MTM after each fill (cash changed, new position added)
                current_portfolio_value = self._mark_to_market(ts, test_data)

            # 4. Mark-to-market equity snapshot
            self.equity_curve.append({
                "timestamp": ts,
                "equity": self._mark_to_market(ts, test_data),
            })

        self._close_all_remaining(test_data)
        return pd.DataFrame(self.equity_curve).set_index("timestamp")

    # ── Private helpers ───────────────────────────────────────────────────

    def _process_exits(
        self,
        ts: datetime,
        test_data: Dict[str, pd.DataFrame],
        bar_idx: int,
    ) -> None:
        to_close: List[Tuple[str, str]] = []
        for symbol, pos in self.open_positions.items():
            df = test_data.get(symbol)
            if df is None or ts not in df.index:
                continue
            bar = df.loc[ts]

            # Pyramiding: add shares when trade proves itself at 1.5R profit
            if (
                self.pyramid_enabled
                and not pos.pyramid_done
                and pos.entry_atr > 0
                and symbol in self.pyramid_symbols
            ):
                pyramid_level = pos.entry_price + self.pyramid_atr_mult * pos.entry_atr
                if float(bar["high"]) >= pyramid_level:
                    add_shares = round(pos.original_shares * self.pyramid_fraction, 4)
                    add_cost   = add_shares * pyramid_level
                    if add_cost > 0 and add_cost <= self.cash:
                        self.cash -= add_cost
                        pos.shares += add_shares
                        pos.pyramid_done = True
                        # Move combined stop to original entry (breakeven for initial lot)
                        pos.stop_loss   = pos.entry_price
                        pos.trail_stop  = max(pos.trail_stop, pos.entry_price)
                        pos.trail_active = True
                        logger.debug(
                            "  [%s] pyramid add %.2f shares @ %.2f  (new total %.2f)",
                            symbol, add_shares, pyramid_level, pos.shares,
                        )

            # Second pyramid: add another tranche when trade reaches +3.0R
            # Only fires after the first pyramid (position already proven twice).
            # Stop is ratcheted to +1.5R to protect the first pyramid gain.
            if (
                self.pyramid2_enabled
                and pos.pyramid_done
                and not pos.pyramid2_done
                and pos.entry_atr > 0
                and symbol in self.pyramid_symbols
            ):
                pyramid2_level = pos.entry_price + self.pyramid2_atr_mult * pos.entry_atr
                if float(bar["high"]) >= pyramid2_level:
                    add2_shares = round(pos.original_shares * self.pyramid2_fraction, 4)
                    add2_cost   = add2_shares * pyramid2_level
                    if add2_cost > 0 and add2_cost <= self.cash:
                        self.cash -= add2_cost
                        pos.shares += add2_shares
                        pos.pyramid2_done = True
                        # Ratchet stop to +1.5R – locks in the first pyramid gain
                        lock_level = pos.entry_price + self.pyramid_atr_mult * pos.entry_atr
                        pos.stop_loss  = max(pos.stop_loss,  lock_level)
                        pos.trail_stop = max(pos.trail_stop, lock_level)
                        logger.debug(
                            "  [%s] pyramid2 add %.2f shares @ %.2f  (total %.2f)",
                            symbol, add2_shares, pyramid2_level, pos.shares,
                        )

            # Scale-out: partial exit at 1R profit, moves stop to breakeven
            if (
                self.scale_out_enabled
                and not pos.scale_out_done
                and pos.entry_atr > 0
            ):
                scale_target = pos.entry_price + self.scale_out_atr_mult * pos.entry_atr
                if float(bar["high"]) >= scale_target:
                    close_shares = round(pos.shares * self.scale_out_fraction, 4)
                    pos.shares = round(pos.shares - close_shares, 4)
                    pos.scale_out_done = True
                    # Lock in partial profit and return cash
                    self._close_partial(symbol, pos, close_shares, scale_target, "scale_out", ts)
                    # Move stop to breakeven; trail is now active from entry
                    pos.stop_loss   = pos.entry_price
                    pos.trail_stop  = pos.entry_price
                    pos.trail_active = True

            reason = self.strategy.check_exit(
                pos, bar["high"], bar["low"], bar["close"]
            )
            if reason:
                to_close.append((symbol, reason))

        for symbol, reason in to_close:
            pos = self.open_positions[symbol]
            bar = test_data[symbol].loc[ts]
            exit_price = self.strategy.exit_price(pos, reason, bar)
            self._close_position(symbol, pos, exit_price, reason, ts)
            self.last_exit_bar_idx[symbol] = bar_idx

    def _open_position(
        self,
        signal,
        symbol: str,
        portfolio_value: float = 0.0,
        risk_scale_override: Optional[float] = None,
    ) -> None:
        # Use caller-supplied mark-to-market equity when available (true compounding).
        # MTM equity = cash + current market value of all open positions.
        # Fall back to cost-basis calculation when called without the argument.
        if portfolio_value <= 0:
            invested_cost = sum(
                p.entry_price * p.shares for p in self.open_positions.values()
            )
            portfolio_value = self.cash + invested_cost

        # Current market value already invested = portfolio_value minus idle cash.
        # This correctly tracks unrealized gains/losses when MTM value is supplied.
        currently_invested = portfolio_value - self.cash

        # Dynamic macro risk: when an override is provided (e.g. bear regime),
        # rebuild the risk/cap dicts temporarily without mutating self's defaults.
        if risk_scale_override is not None and risk_scale_override != self.risk_scale:
            from t212_miner_bot.config import SYMBOL_MAX_POSITION_PCT as _BASE_CAPS
            eff_risk_pct = {k: min(v / self.risk_scale * risk_scale_override, self.risk_cap_ceiling)
                            for k, v in self._scaled_risk_pct.items()}
            eff_max_pct  = {k: min(v / self.risk_scale * risk_scale_override, self.position_cap_ceiling)
                            for k, v in self._scaled_max_pos_pct.items()}
            eff_default  = min(self._scaled_default_risk / self.risk_scale * risk_scale_override, self.risk_cap_ceiling)
        else:
            eff_risk_pct = self._scaled_risk_pct
            eff_max_pct  = self._scaled_max_pos_pct
            eff_default  = self._scaled_default_risk

        symbol_risk = eff_risk_pct.get(symbol, eff_default)
        sizing = calculate_position_size(
            portfolio_value=portfolio_value,            # grows with unrealized gains
            entry_price=signal.entry_price,
            atr=signal.atr,
            sl_atr_mult=self.strategy.sl_atr_mult,
            risk_pct=symbol_risk,
            confidence=signal.confidence,
            symbol=symbol,
            symbol_max_pct_override=eff_max_pct,
        )
        if sizing.shares <= 0:
            return

        # Hard exposure cap: keep invested ≤ max_total_exposure_pct of MTM equity
        if currently_invested + sizing.position_value > portfolio_value * self.max_total_exposure_pct:
            remaining_budget = portfolio_value * self.max_total_exposure_pct - currently_invested
            if remaining_budget < signal.entry_price:
                return  # not even one share fits in the budget
            sizing_shares = round(remaining_budget / signal.entry_price, 2)
            sizing_value  = sizing_shares * signal.entry_price
        else:
            sizing_shares = sizing.shares
            sizing_value  = sizing.position_value

        # Cash guard
        entry_fx = fx_cost(sizing_value, symbol)
        total_cost = sizing_value + entry_fx
        if total_cost > self.cash:
            sizing_shares = adjust_for_available_cash(
                self.cash - entry_fx, sizing_shares, signal.entry_price
            )
            if sizing_shares <= 0:
                return
            sizing_value = sizing_shares * signal.entry_price
            entry_fx = fx_cost(sizing_value, symbol)
            total_cost = sizing_value + entry_fx

        self.cash -= total_cost
        self.open_positions[symbol] = Position(
            symbol=symbol,
            entry_price=signal.entry_price,
            shares=sizing_shares,
            entry_time=signal.timestamp,
            take_profit=signal.take_profit,
            stop_loss=signal.stop_loss,
            entry_atr=signal.atr,
            high_since_entry=signal.entry_price,
            trail_stop=0.0,
            trail_active=False,
            scale_out_done=False,
            pyramid_done=False,
            pyramid2_done=False,
            original_shares=sizing_shares,
        )

    def _close_partial(
        self,
        symbol: str,
        pos: Position,
        shares: float,
        exit_price: float,
        reason: str,
        exit_time,
    ) -> None:
        """Book a partial exit, return cash, and record a trade – position stays open."""
        proceeds   = shares * exit_price
        entry_val  = shares * pos.entry_price
        exit_fx    = fx_cost(proceeds, symbol)
        entry_fx   = fx_cost(entry_val, symbol)
        total_fx   = entry_fx + exit_fx
        pnl_gross  = proceeds - entry_val
        pnl_net    = pnl_gross - total_fx

        self.cash += proceeds - exit_fx

        self.trades.append(TradeRecord(
            symbol=symbol,
            entry_time=pos.entry_time,
            exit_time=exit_time,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            shares=shares,
            pnl_gross=round(pnl_gross, 2),
            fx_costs=round(total_fx, 4),
            pnl_net=round(pnl_net, 2),
            exit_reason=reason,
            bars_held=pos.bars_held,
            entry_confidence=0.0,
        ))

    def _close_position(
        self,
        symbol: str,
        pos: Position,
        exit_price: float,
        reason: str,
        exit_time,
    ) -> None:
        proceeds = pos.shares * exit_price
        entry_value = pos.shares * pos.entry_price
        exit_fx = fx_cost(proceeds, symbol)
        entry_fx = fx_cost(entry_value, symbol)
        total_fx = entry_fx + exit_fx
        pnl_gross = proceeds - entry_value
        pnl_net = pnl_gross - total_fx

        self.cash += proceeds - exit_fx
        self.last_exit_was_win[symbol] = pnl_net > 0

        self.trades.append(TradeRecord(
            symbol=symbol,
            entry_time=pos.entry_time,
            exit_time=exit_time,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            shares=pos.shares,
            pnl_gross=round(pnl_gross, 2),
            fx_costs=round(total_fx, 4),
            pnl_net=round(pnl_net, 2),
            exit_reason=reason,
            bars_held=pos.bars_held,
        ))
        del self.open_positions[symbol]

    def _close_all_remaining(self, test_data: Dict[str, pd.DataFrame]) -> None:
        for symbol in list(self.open_positions.keys()):
            pos = self.open_positions[symbol]
            df = test_data.get(symbol)
            if df is None or df.empty:
                continue
            last_bar = df.iloc[-1]
            self._close_position(
                symbol, pos, last_bar["close"], "end_of_test", last_bar.name
            )

    def _compute_universe_regime(
        self, test_data: Dict[str, pd.DataFrame]
    ) -> pd.Series:
        """
        Pre-compute a boolean series (indexed by timestamp) that is True when the
        EU universe is in a broad uptrend.

        Regime = True  when fraction of symbols with close >= ema_200 at that
                        bar is >= self.macro_filter_min_uptrend.
        Regime = False otherwise → no new entries allowed.
        """
        fraction = self._compute_regime_fraction(test_data)
        return fraction >= self.macro_filter_min_uptrend

    def _compute_regime_fraction(
        self, test_data: Dict[str, pd.DataFrame]
    ) -> pd.Series:
        """
        Return a float Series (0..1) of the fraction of universe symbols
        whose close is above their EMA200 at each timestamp.
        Used by both the macro filter (boolean threshold) and dynamic
        macro risk scaling (continuous fraction).
        """
        frames = []
        for sym, df in test_data.items():
            if "ema_200" not in df.columns:
                continue
            uptrend = (df["close"] >= df["ema_200"]).rename(sym)
            frames.append(uptrend)

        if not frames:
            all_ts = sorted({ts for df in test_data.values() for ts in df.index})
            return pd.Series(1.0, index=all_ts)

        combined = pd.concat(frames, axis=1)
        return combined.mean(axis=1)    # fraction of symbols in uptrend (0..1)

    def _mark_to_market(
        self, ts: datetime, test_data: Dict[str, pd.DataFrame]
    ) -> float:
        mtm = self.cash
        for symbol, pos in self.open_positions.items():
            df = test_data.get(symbol)
            price = (
                df.loc[ts, "close"]
                if df is not None and ts in df.index
                else pos.entry_price
            )
            mtm += pos.shares * price
        return round(mtm, 2)

    # ── Reporting ─────────────────────────────────────────────────────────

    def performance_report(self) -> Dict:
        if not self.trades:
            return {"error": "No trades executed."}

        pnls  = np.array([t.pnl_net   for t in self.trades])
        gross = np.array([t.pnl_gross for t in self.trades])
        bars  = np.array([t.bars_held for t in self.trades])

        winners = pnls[pnls > 0]
        losers  = pnls[pnls <= 0]

        eq    = pd.DataFrame(self.equity_curve).set_index("timestamp")["equity"]
        peak  = eq.cummax()
        dd    = (eq - peak) / peak
        daily = eq.resample("1D").last().dropna()
        dr    = daily.pct_change().dropna()
        sharpe = (dr.mean() / dr.std() * np.sqrt(252)) if dr.std() > 0 else 0.0

        gp = winners.sum() if len(winners) else 0.0
        gl = abs(losers.sum()) if len(losers) else 0.0
        pf = gp / gl if gl > 0 else float("inf")

        return {
            "total_trades":   len(self.trades),
            "winners":        len(winners),
            "losers":         len(losers),
            "win_rate":       len(winners) / len(self.trades),
            "total_pnl_gross":round(gross.sum(), 2),
            "total_pnl_net":  round(pnls.sum(), 2),
            "total_fx_costs": round(sum(t.fx_costs for t in self.trades), 2),
            "avg_pnl_net":    round(pnls.mean(), 2),
            "avg_bars_held":  round(bars.mean(), 1),
            "max_drawdown":   round(dd.min(), 4),
            "sharpe_ratio":   round(sharpe, 3),
            "profit_factor":  round(pf, 3),
            "final_equity":   round(eq.iloc[-1], 2) if len(eq) else self.initial_capital,
            "return_pct":     round(
                (eq.iloc[-1] / self.initial_capital - 1) * 100, 2
            ) if len(eq) else 0.0,
        }

    def trades_dataframe(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame([t.__dict__ for t in self.trades])

    def per_symbol_summary(self) -> pd.DataFrame:
        df = self.trades_dataframe()
        if df.empty:
            return df
        return df.groupby("symbol").agg(
            trades   =("pnl_net", "count"),
            total_pnl=("pnl_net", "sum"),
            avg_pnl  =("pnl_net", "mean"),
            win_rate =("pnl_net", lambda x: (x > 0).mean()),
            avg_bars =("bars_held", "mean"),
            total_fx =("fx_costs", "sum"),
        ).round(2)
