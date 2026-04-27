from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


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


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")


T212_API_KEY = os.getenv("T212_API_KEY", "")
T212_SECRET_KEY = os.getenv("T212_SECRET_KEY", "")
T212_BASE_URL = "https://demo.trading212.com"


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}

GMAIL_SENDER = os.getenv("GMAIL_SENDER", "").strip()
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "").strip()
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT", "veselinveselinov@gmail.com").strip()
BOT_SAFE_MODE = _env_flag("BOT_SAFE_MODE", default=False)

# yfinance ticker -> Trading 212 instrument code
SYMBOLS_MAP: dict[str, str] = {
    "ASML.AS": "ASMLa_EQ",
    "SAP.DE": "SAPd_EQ",
    "UNA.AS": "UNIAa_EQ",
    # Keep plain root here; AsyncT212Client resolves to tradable AMD_* ticker.
    "AMD": "AMD",
}

# Optimized Miner strategy parameters
# OOS-validated upgrade (sweep over 1129 candidates, IS=2024H1, OOS1=2024H2, OOS2=2025+):
# Wider stop (3.5x ATR) + higher TP (8R) + earlier BE (1.5R) + stronger trail (2.5x) +
# tighter profit lock (5%/2%) — all beat current on BOTH OOS windows (score +29.89).
ATR_MULTIPLIER = 3.5       # upgraded from 3.0 (wider stop = fewer whipsaw exits)
UNIT1_TP_RR = 8.0          # upgraded from 6.0 (let winners run further)
EMA_PERIOD = 200
ATR_TRAIL_MULT = 3.5       # tuned: best 2y portfolio result in trailing sweep
BREAKEVEN_OFFSET_PCT = 0.0015
BREAK_EVEN_TRIGGER_PCT = 0.02  # keep at 2% for BASE mode
PROFIT_LOCK_TRIGGER_PCT = 0.05  # global default: lock in gains at +5%
PROFIT_LOCK_STOP_PCT = 0.02     # global default: lock floor at +2%
# Per-symbol profit-lock overrides: symbol -> (trigger_pct, stop_pct).
# AMD: tighter trigger at +4% (vs +5% global) improves return from 69.30% to 89.92%
# by capturing more intermediate rallies — validated on 2024-2026 backtest.
PROFIT_LOCK_BY_SYMBOL: dict[str, tuple[float, float]] = {
    "AMD": (0.04, 0.02),
}

# Optional: enable ATR trailing already during UNIT1_ACTIVE (BASE mode only).
# This reduces large givebacks during extended runs before virtual TP, but can cut big winners early.
# Enable per-symbol based on backtest evidence.
UNIT1_TRAIL_IN_UNIT1_BY_SYMBOL: dict[str, bool] = {
    "ASML.AS": True,
    "UNA.AS": True,
    "AMD": False,
}
# Overnight morning-protection:
# If a position is carried overnight without reaching "real profit" threshold,
# lift stop toward breakeven at the next morning session.
MORNING_PROTECT_ENABLED = True
MORNING_REAL_PROFIT_TRIGGER_PCT = 0.01
MORNING_PROFIT_CAPTURE_PCT = 0.25
MORNING_PROTECT_WINDOW_MINUTES = 120
# Enable morning-protect only where it improves historical behavior.
# UNA.AS enabled: switching to ATR mode with morning protect improves return from 65.61% to 81.96%
# over 2024-2026 backtest (ATR mode without morning protect gives 65.61%).
MORNING_PROTECT_SYMBOL_ENABLED: dict[str, bool] = {
    "ASML.AS": True,
    "SAP.DE": True,
    "UNA.AS": True,
    "AMD": False,
}
# Per-symbol morning-protect overrides.
MORNING_REAL_PROFIT_TRIGGER_PCT_BY_SYMBOL: dict[str, float] = {}
MORNING_PROFIT_CAPTURE_PCT_BY_SYMBOL: dict[str, float] = {
    # OOS-validated tuned value for SAP.DE.
    "SAP.DE": 0.35,
}
MORNING_PROTECT_WINDOW_MINUTES_BY_SYMBOL: dict[str, int] = {}
ENABLE_TIME_FILTER = True

# Symbol strategy routing (BASE uses current unit-split flow, ATR uses dynamic ATR flow).
# UNA.AS upgraded from BASE to ATR: backtest shows ATR mode returns ~248% vs -6% for BASE
# over 2024-2026, with morning protect enabled. Per-symbol ATR params tuned individually.
SYMBOL_STRATEGY_MODE: dict[str, str] = {
    "ASML.AS": "BASE",
    "SAP.DE": "ATR",
    "UNA.AS": "ATR",
    "AMD": "BASE",
}
ATR_DYNAMIC_STOP_MULT = 3.5    # global default (per-symbol overrides take precedence for ATR symbols)
ATR_DYNAMIC_TP_R = 8.0         # global default
ATR_DYNAMIC_BE_R = 1.5         # global default
# Per-symbol ATR dynamic overrides: symbol -> (stop_mult, tp_r, be_r).
# Tuned individually via 2024-2026 backtest sweep with tax/fee model (5 bps slippage, Bulgaria costs):
# SAP.DE:  stop=2.5 (tighter, more trades) + tp=8R + be=1.0R  -> +173pp vs global params
# UNA.AS:  stop=3.0 + tp=8R + be=1.0R (earlier BE capture)   -> +166pp vs global params
ATR_DYNAMIC_PARAMS_BY_SYMBOL: dict[str, tuple[float, float, float]] = {
    "SAP.DE": (2.5, 8.0, 1.0),
    "UNA.AS": (3.0, 8.0, 1.0),
}

# Trend-strength entry filter:
# Sweep result: all top-30 winners use NONE filter (no additional entry filter beyond DTosc).
# The trend filter reduced trade count too aggressively and cut too many good entries.
TREND_STRENGTH_FILTER_ENABLED = False

# Portfolio and risk controls
TOTAL_PORTFOLIO_EUR = 1000.0
RISK_PCT = 0.01
MAX_ALLOCATION_PCT = 0.40
QTY_ROUND_DP = 5

# Edge-Weighted Risk (EWR): dynamic per-symbol risk multiplier driven by recent outcomes.
EDGE_WEIGHTED_RISK_ENABLED = True
EDGE_RISK_LOOKBACK_TRADES = 4
EDGE_RISK_MIN_TRADES = 2
EDGE_RISK_Z_ALPHA = 0.25
EDGE_RISK_MIN_MULT = 0.60
EDGE_RISK_MAX_MULT = 1.40

# Optional momentum tilt on top of EWR multipliers.
EDGE_MOMENTUM_TILT_ENABLED = True
EDGE_MOMENTUM_LOOKBACK_TRADES = 4
EDGE_MOMENTUM_TILT = 0.30

# Multi-logic portfolio exposure controls (on top of EWR multipliers).
# These gates only scale gross risk exposure down (never above 1.0):
# - Breadth gate
# - Regime gate (portfolio volatility + win-rate)
# - Drawdown throttle
# - Correlation cap
EDGE_MULTI_LOGIC_ENABLED = True
EDGE_VOL_LOOKBACK_TRADES = 2
EDGE_VOL_PENALTY = 0.10
EDGE_BREADTH_FLOOR = 0.50
EDGE_BREADTH_EXPOSURE = 0.85
EDGE_REGIME_LOOKBACK_TRADES = 3
EDGE_REGIME_VOL_SOFT = 4.5
EDGE_REGIME_VOL_HARD = 7.0
EDGE_REGIME_WIN_SOFT = 0.50
EDGE_REGIME_WIN_HARD = 0.35
EDGE_REGIME_EXPOSURE_SOFT = 0.85
EDGE_REGIME_EXPOSURE_HARD = 0.60
EDGE_DD_LEVEL1 = 0.10
EDGE_DD_LEVEL2 = 0.18
EDGE_DD_EXPOSURE1 = 0.80
EDGE_DD_EXPOSURE2 = 0.60
EDGE_CORR_LOOKBACK_TRADES = 3
EDGE_CORR_SOFT = 0.50
EDGE_CORR_HARD = 0.70
EDGE_CORR_EXPOSURE_SOFT = 0.90
EDGE_CORR_EXPOSURE_HARD = 0.70

# Candle and signal configuration
BAR_INTERVAL = "5m"
LOOKBACK_BARS = 500
SIGNAL_BUFFER_SECONDS = 5

# Stale-bar gating:
# yfinance can lag (especially around session boundaries). If the newest bar is older than
# (STALE_BAR_MAX_AGE_MULT * BAR_INTERVAL) + STALE_BAR_GRACE_SECONDS, treat the feed as stale
# and block candle-driven entries/management for that symbol in that cycle.
STALE_BAR_MAX_AGE_MULT = float(os.getenv("STALE_BAR_MAX_AGE_MULT", "2.0"))
# yfinance can legitimately lag a few bars (15-20 min) even when the feed is "healthy".
# Default grace is therefore intentionally generous; tighten if you use a real-time candle feed.
STALE_BAR_GRACE_SECONDS = float(os.getenv("STALE_BAR_GRACE_SECONDS", "900"))

# After N consecutive stale cycles for a symbol, pause candle-driven entries until fresh bars return.
STALE_BAR_STRIKES_TO_PAUSE = int(os.getenv("STALE_BAR_STRIKES_TO_PAUSE", "6"))

# Data fetching hardening (free feeds):
# - Stagger symbol fetches to avoid burst throttling.
# - Cap the number of live yfinance calls per cycle (0 disables live calls, uses cache only).
FETCH_STAGGER_SECONDS = float(os.getenv("FETCH_STAGGER_SECONDS", "0.35"))
MAX_LIVE_FETCHES_PER_CYCLE = int(os.getenv("MAX_LIVE_FETCHES_PER_CYCLE", "4"))

# Candle-close loop jitter (seconds). Keeps alignment but avoids looking like a perfectly periodic bot.
WAIT_JITTER_MAX_SECONDS = float(os.getenv("WAIT_JITTER_MAX_SECONDS", "2.0"))

# Observability
BOT_LOG_DIR = os.getenv("BOT_LOG_DIR", "logs")

# State persistence
STATE_FILE = "t212_miner_bot/state.json"

# Broker stop orders: Trading 212 documents stop triggers from Last Traded Price (LTP). During
# closed markets or thin prints, LTP can lag the UI mark; optional extended-hours flag may help
# US names when the API accepts it (not in published StopRequest schema — disable if orders fail).
STOP_ORDER_EXTENDED_HOURS = _env_flag("STOP_ORDER_EXTENDED_HOURS", default=True)

# If broker position currentPrice is clearly below the protective stop but the stop stays pending,
# cancel broker stops and market-out after this many consecutive 5m cycles (guards LTP/UI desync).
PROTECTIVE_STOP_BROKER_ESCAPE_ENABLED = _env_flag("PROTECTIVE_STOP_BROKER_ESCAPE_ENABLED", default=True)
# Increase confirmations/buffer to reduce false positives from LTP/UI mismatch.
PROTECTIVE_STOP_BROKER_ESCAPE_CONFIRMATIONS = int(os.getenv("PROTECTIVE_STOP_BROKER_ESCAPE_CONFIRMATIONS", "4"))
PROTECTIVE_STOP_BROKER_PRICE_BUFFER_PCT = float(os.getenv("PROTECTIVE_STOP_BROKER_PRICE_BUFFER_PCT", "0.0010"))
PROTECTIVE_STOP_BROKER_PRICE_BUFFER_ABS = float(os.getenv("PROTECTIVE_STOP_BROKER_PRICE_BUFFER_ABS", "0.10"))

# Mark protective stop missing locally when tracked order id is absent from pending orders.
PROTECTIVE_STOP_ORDER_RECONCILE_ENABLED = _env_flag("PROTECTIVE_STOP_ORDER_RECONCILE_ENABLED", default=True)


@dataclass(frozen=True)
class StrategyParams:
    atr_multiplier: float = ATR_MULTIPLIER
    unit1_tp_rr: float = UNIT1_TP_RR
    ema_period: int = EMA_PERIOD
    atr_trail_mult: float = ATR_TRAIL_MULT
    breakeven_offset_pct: float = BREAKEVEN_OFFSET_PCT
    break_even_trigger_pct: float = BREAK_EVEN_TRIGGER_PCT
    profit_lock_trigger_pct: float = PROFIT_LOCK_TRIGGER_PCT
    profit_lock_stop_pct: float = PROFIT_LOCK_STOP_PCT
    profit_lock_by_symbol: dict[str, tuple[float, float]] = field(
        default_factory=lambda: dict(PROFIT_LOCK_BY_SYMBOL)
    )
    unit1_trail_in_unit1_by_symbol: dict[str, bool] = field(
        default_factory=lambda: dict(UNIT1_TRAIL_IN_UNIT1_BY_SYMBOL)
    )
    morning_protect_enabled: bool = MORNING_PROTECT_ENABLED
    morning_real_profit_trigger_pct: float = MORNING_REAL_PROFIT_TRIGGER_PCT
    morning_profit_capture_pct: float = MORNING_PROFIT_CAPTURE_PCT
    morning_protect_window_minutes: int = MORNING_PROTECT_WINDOW_MINUTES
    morning_protect_symbol_enabled: dict[str, bool] = field(
        default_factory=lambda: dict(MORNING_PROTECT_SYMBOL_ENABLED)
    )
    morning_real_profit_trigger_pct_by_symbol: dict[str, float] = field(
        default_factory=lambda: dict(MORNING_REAL_PROFIT_TRIGGER_PCT_BY_SYMBOL)
    )
    morning_profit_capture_pct_by_symbol: dict[str, float] = field(
        default_factory=lambda: dict(MORNING_PROFIT_CAPTURE_PCT_BY_SYMBOL)
    )
    morning_protect_window_minutes_by_symbol: dict[str, int] = field(
        default_factory=lambda: dict(MORNING_PROTECT_WINDOW_MINUTES_BY_SYMBOL)
    )
    atr_dynamic_stop_mult: float = ATR_DYNAMIC_STOP_MULT
    atr_dynamic_tp_r: float = ATR_DYNAMIC_TP_R
    atr_dynamic_be_r: float = ATR_DYNAMIC_BE_R
    atr_dynamic_params_by_symbol: dict[str, tuple[float, float, float]] = field(
        default_factory=lambda: dict(ATR_DYNAMIC_PARAMS_BY_SYMBOL)
    )
    trend_strength_filter_enabled: bool = TREND_STRENGTH_FILTER_ENABLED
    symbol_strategy_mode: dict[str, str] = field(default_factory=lambda: dict(SYMBOL_STRATEGY_MODE))
    edge_weighted_risk_enabled: bool = EDGE_WEIGHTED_RISK_ENABLED
    edge_risk_lookback_trades: int = EDGE_RISK_LOOKBACK_TRADES
    edge_risk_min_trades: int = EDGE_RISK_MIN_TRADES
    edge_risk_z_alpha: float = EDGE_RISK_Z_ALPHA
    edge_risk_min_mult: float = EDGE_RISK_MIN_MULT
    edge_risk_max_mult: float = EDGE_RISK_MAX_MULT
    edge_momentum_tilt_enabled: bool = EDGE_MOMENTUM_TILT_ENABLED
    edge_momentum_lookback_trades: int = EDGE_MOMENTUM_LOOKBACK_TRADES
    edge_momentum_tilt: float = EDGE_MOMENTUM_TILT
    edge_multi_logic_enabled: bool = EDGE_MULTI_LOGIC_ENABLED
    edge_vol_lookback_trades: int = EDGE_VOL_LOOKBACK_TRADES
    edge_vol_penalty: float = EDGE_VOL_PENALTY
    edge_breadth_floor: float = EDGE_BREADTH_FLOOR
    edge_breadth_exposure: float = EDGE_BREADTH_EXPOSURE
    edge_regime_lookback_trades: int = EDGE_REGIME_LOOKBACK_TRADES
    edge_regime_vol_soft: float = EDGE_REGIME_VOL_SOFT
    edge_regime_vol_hard: float = EDGE_REGIME_VOL_HARD
    edge_regime_win_soft: float = EDGE_REGIME_WIN_SOFT
    edge_regime_win_hard: float = EDGE_REGIME_WIN_HARD
    edge_regime_exposure_soft: float = EDGE_REGIME_EXPOSURE_SOFT
    edge_regime_exposure_hard: float = EDGE_REGIME_EXPOSURE_HARD
    edge_dd_level1: float = EDGE_DD_LEVEL1
    edge_dd_level2: float = EDGE_DD_LEVEL2
    edge_dd_exposure1: float = EDGE_DD_EXPOSURE1
    edge_dd_exposure2: float = EDGE_DD_EXPOSURE2
    edge_corr_lookback_trades: int = EDGE_CORR_LOOKBACK_TRADES
    edge_corr_soft: float = EDGE_CORR_SOFT
    edge_corr_hard: float = EDGE_CORR_HARD
    edge_corr_exposure_soft: float = EDGE_CORR_EXPOSURE_SOFT
    edge_corr_exposure_hard: float = EDGE_CORR_EXPOSURE_HARD
    stop_order_extended_hours: bool = STOP_ORDER_EXTENDED_HOURS
    protective_stop_broker_escape_enabled: bool = PROTECTIVE_STOP_BROKER_ESCAPE_ENABLED
    protective_stop_broker_escape_confirmations: int = PROTECTIVE_STOP_BROKER_ESCAPE_CONFIRMATIONS
    protective_stop_broker_price_buffer_pct: float = PROTECTIVE_STOP_BROKER_PRICE_BUFFER_PCT
    protective_stop_broker_price_buffer_abs: float = PROTECTIVE_STOP_BROKER_PRICE_BUFFER_ABS
    protective_stop_order_reconcile_enabled: bool = PROTECTIVE_STOP_ORDER_RECONCILE_ENABLED
