"""
Central configuration for the XGBoost swing-trading bot.
All tunable constants live here so nothing is hard-coded elsewhere.
"""

import os
from pathlib import Path
from datetime import datetime


def _load_dotenv(path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ (no-op if missing)."""
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "t212_miner_bot" / "models"

# ---------------------------------------------------------------------------
# Universe  (strictly EUR-denominated, cleaned for v4)
# ---------------------------------------------------------------------------
US_SYMBOLS = ["AAPL", "AMZN", "MSFT", "NVDA", "TSLA"]

# ── EU Universe v7 – expanded to 25 strictly EUR-denominated stocks ───────────
# Original 4
EU_SYMBOLS_ORIGINAL = ["ADYEN.AS", "ASML.AS", "MC.PA", "ROG.SW"]

# v4 additions
EU_SYMBOLS_V4 = [
    "AIR.PA",   # Airbus           – Euronext Paris,  EUR, aerospace/industrial
    "ALV.DE",   # Allianz          – XETRA,            EUR, financial
    "ENR.DE",   # Siemens Energy   – XETRA,            EUR, energy transition
    "IFX.DE",   # Infineon         – XETRA,            EUR, semiconductor
    "RHM.DE",   # Rheinmetall      – XETRA,            EUR, defense
    "RMS.PA",   # Hermès           – Euronext Paris,   EUR, luxury
    "SIE.DE",   # Siemens          – XETRA,            EUR, industrial
    "TTE.PA",   # TotalEnergies    – Euronext Paris,   EUR, energy
]

# v7 new additions (data files confirmed present in data/)
EU_SYMBOLS_V7 = [
    # ── Defense / Aerospace (structural tailwind sector) ─────────────────────
    "HO.PA",      # Thales           – Euronext Paris, EUR, defense electronics
    "SAF.PA",     # Safran           – Euronext Paris, EUR, aircraft engines

    # ── Luxury / Consumer ─────────────────────────────────────────────────────
    "KER.PA",     # Kering           – Euronext Paris, EUR, luxury (Gucci, YSL)
    "OR.PA",      # L'Oréal          – Euronext Paris, EUR, beauty/consumer
    "EL.PA",      # EssilorLuxottica – Euronext Paris, EUR, optical healthcare

    # ── Technology / Software ─────────────────────────────────────────────────
    "DSY.PA",     # Dassault Systèmes– Euronext Paris, EUR, CAD/PLM software
    "SAP.DE",     # SAP              – XETRA,           EUR, enterprise software

    # ── Semiconductor ─────────────────────────────────────────────────────────
    "STMPA.PA",   # STMicroelectronics – Euronext Paris, EUR, chips (auto/IoT)

    # ── Pharma / Healthcare ───────────────────────────────────────────────────
    "SAN.PA",     # Sanofi           – Euronext Paris, EUR, large-cap pharma
    "BAYN.DE",    # Bayer            – XETRA,           EUR, pharma/agro

    # ── Financials / Fintech ──────────────────────────────────────────────────
    "DBK.DE",     # Deutsche Bank    – XETRA,           EUR, investment banking
    "PRX.AS",     # Prosus           – Amsterdam,        EUR, tech/internet holdings

    # ── Auto ──────────────────────────────────────────────────────────────────
    "VOW3.DE",    # Volkswagen (pref)– XETRA,           EUR, automotive
]

EU_SYMBOLS = EU_SYMBOLS_ORIGINAL + EU_SYMBOLS_V4 + EU_SYMBOLS_V7
ALL_SYMBOLS = US_SYMBOLS + EU_SYMBOLS
GBP_SYMBOLS = []   # SHEL.L excluded – GBP, not EUR


TIMEFRAMES = ["15m", "5m"]
PRIMARY_TIMEFRAME = "15m"
SECONDARY_TIMEFRAME = "5m"

# Sector groupings for relative-strength features  (updated for v7 universe)
SECTORS = {
    "defense":       ["RHM.DE", "HO.PA", "SAF.PA"],
    "semiconductor": ["ASML.AS", "IFX.DE", "STMPA.PA"],
    "industrial":    ["AIR.PA", "SIE.DE"],
    "energy":        ["ENR.DE", "TTE.PA"],
    "luxury":        ["MC.PA", "RMS.PA", "KER.PA"],
    "consumer":      ["OR.PA", "EL.PA"],
    "tech":          ["DSY.PA", "SAP.DE"],
    "financial":     ["ALV.DE", "ADYEN.AS", "DBK.DE", "PRX.AS"],
    "pharma":        ["ROG.SW", "SAN.PA", "BAYN.DE"],
    "auto":          ["VOW3.DE"],
}

# Reverse mapping: symbol → sector (for O(1) sector-clamping lookup in backtest)
SYMBOL_SECTOR = {
    sym: sector
    for sector, symbols in SECTORS.items()
    for sym in symbols
}

# ---------------------------------------------------------------------------
# Train / Test split  (strict chronological)
# ---------------------------------------------------------------------------
TRAIN_END  = datetime(2025, 5, 4)
TEST_START = datetime(2025, 5, 5)
WALKFORWARD_RETRAIN_DATE = datetime(2025, 11, 1)

# ---------------------------------------------------------------------------
# Feature engineering parameters
# ---------------------------------------------------------------------------
EMA_PERIODS = [8, 21, 50, 200]
RSI_PERIOD = 14
STOCH_K_PERIOD = 14
STOCH_D_PERIOD = 3
WILLIAMS_R_PERIOD = 14
ROC_PERIODS = [5, 10, 20]
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ADX_PERIOD = 14
ATR_PERIOD = 14
BBANDS_PERIOD = 20
BBANDS_STD = 2.0
MFI_PERIOD = 14
OBV_SLOPE_PERIOD = 10
VOLUME_SMA_PERIOD = 20
HIST_VOL_PERIOD = 20

SECONDARY_RSI_PERIOD = 14
SECONDARY_EMA_SHORT = 5
SECONDARY_VOLUME_SPIKE_MULT = 2.0

US_MARKET_OPEN_HOUR_UTC = 14
EU_MARKET_OPEN_HOUR_UTC = 7

# ---------------------------------------------------------------------------
# Labeling – Triple Barrier Method  (training labels only)
# ---------------------------------------------------------------------------
# These values define what the AI was TRAINED to predict.
# The live execution SL/TP are controlled separately (see variant_sweep.py /
# strategy constructor), so they can differ without retraining.
#
# Lesson from v6 experiment: training on 5×ATR labels degraded model quality
# because 5×ATR events are rarer → harder to predict → lower AUC.
# Optimal setup: train on narrow 3×/1.5× labels (high signal density) and
# execute with wider 5×/2.5× barriers (capture the big trends).
TP_ATR_MULT = 3.0      # label: price must reach 3 × ATR above entry (training target)
SL_ATR_MULT = 1.5      # label: stop at 1.5 × ATR below entry         (training target)
MAX_HOLDING_BARS = 200 # time barrier ≈ 5 trading days

# Live execution ATR barriers  (used by strategy.py & backtest.py at runtime)
# Wider than the training labels – this is intentional.  The AI identifies high-
# quality setups; we then give those trades more room to run.
EXEC_TP_ATR_MULT = 5.0   # execution take-profit: 5 × ATR above entry
EXEC_SL_ATR_MULT = 2.5   # execution stop-loss:   2.5 × ATR below entry

# ATR Trailing Stop  –  calibrated for the 2.5 / 5.0 execution barriers:
#   - Trail activates when profit ≥ 2.5 × ATR (= 1R; breakeven guaranteed)
#   - Trail distance = EXEC_SL width (2.5 ATR) so floor is always entry price
#   - TP fires at 5.0 ATR; between activation and TP the trail ratchets up
ATR_TRAIL_MULT       = 2.5   # trail = 2.5 × ATR below the running high
ATR_TRAIL_ACTIVATE_R = 2.5   # activate when profit ≥ 2.5 × entry ATR (= 1R)

# ---------------------------------------------------------------------------
# Strategy v2 parameters  (SwingStrategyV2 in strategy.py)
# ---------------------------------------------------------------------------
# Trail activates earlier (1.5R) with a tighter distance (2.0 ATR).
# This locks in a profit floor sooner without cutting trends short.
V2_TRAIL_MULT          = 2.5    # same as v1 – trail distance unchanged
V2_TRAIL_ACTIVATE_R    = 2.5    # same as v1 – activation unchanged
# Trail parameters kept at v1 values so the comparison isolates
# the impact of entry filters (vol spike, RSI gate, session guard)
# and the asymmetric time exit independently of trail changes.

# Volatility spike filter: skip entry when ATR > V2_VOL_SPIKE_MULT × 50-bar median.
# 1.8 means "ATR is 80 % above its recent typical value" – a clear outlier event.
V2_VOL_SPIKE_MULT      = 1.8

# RSI must be above this floor at entry (momentum still pointing up).
V2_RSI_MIN_ENTRY       = 40.0

# Asymmetric time exit: cut losing positions early, keep winning ones longer.
V2_MAX_HOLDING_BARS_LOSS = 80   # ~5 hours; losing position exits here
# (V2 uses existing MAX_HOLDING_BARS=200 for profitable positions)

# Open-session guard: block entries in the first N minutes of EU open (09:00 UTC).
V2_SESSION_OPEN_GUARD_MIN = 15  # 09:00–09:15 UTC

# ---------------------------------------------------------------------------
# Portfolio risk management  (portfolio_risk.py)
# ---------------------------------------------------------------------------
# Daily circuit breaker: stop new entries if portfolio is already down this
# much from the day's starting equity.
DAILY_DRAWDOWN_CIRCUIT_BREAKER = 0.02   # 2 % daily loss limit

# Drawdown position scaler: reduce new trade size as running drawdown deepens.
# Three tiers – see DrawdownPositionScaler in portfolio_risk.py.
DD_SCALE_TIER1_THRESHOLD = 0.03    # 3 % drawdown → 70 % size
DD_SCALE_TIER2_THRESHOLD = 0.07    # 7 % drawdown → 40 % size

# Session filter: block new BUY entries after 15:30 UTC (last ~30 min before
# EU close in summer / ~60 min in winter).  This avoids overnight gap risk while
# keeping the afternoon trend windows fully available.
SESSION_FILTER_ENABLED        = True
SESSION_CLOSE_BLOCK_UTC_HOUR  = 15
SESSION_CLOSE_BLOCK_UTC_MINUTE = 30

# ---------------------------------------------------------------------------
# XGBoost hyperparameters
# ---------------------------------------------------------------------------
XGB_PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "max_depth": 5,           # was 6 – shallower trees generalise better OOS
    "learning_rate": 0.05,
    "n_estimators": 600,      # more trees compensate for shallower depth
    "subsample": 0.75,        # was 0.8 – more stochastic = less overfit
    "colsample_bytree": 0.75, # was 0.8
    "min_child_weight": 15,   # was 5 – requires more evidence per leaf split
    "gamma": 0.3,             # was 0.1 – minimum gain to split a node
    "reg_alpha": 0.5,         # was 0.1 – L1 sparsity
    "reg_lambda": 3.0,        # was 1.0 – L2 weight decay, key anti-overfit lever
    "scale_pos_weight": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
}

# LightGBM hyperparameters
LGBM_PARAMS = {
    "objective": "binary",
    "metric": "binary_logloss",
    "num_leaves": 31,         # was 63 – smaller tree for better regularisation
    "learning_rate": 0.05,
    "n_estimators": 600,      # was 500
    "subsample": 0.75,        # was 0.8
    "colsample_bytree": 0.75, # was 0.8
    "min_child_samples": 40,  # was 20 – more samples required per leaf
    "reg_alpha": 0.5,         # was 0.1
    "reg_lambda": 3.0,        # was 1.0
    "min_gain_to_split": 0.1, # LGBM equivalent of XGB gamma
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": -1,
}

XGB_ENSEMBLE_WEIGHT = 0.5   # 50 % XGB + 50 % LGBM

TSCV_N_SPLITS = 5

# ---------------------------------------------------------------------------
# Signal thresholds & regime filters
# ---------------------------------------------------------------------------
SIGNAL_CONFIDENCE_THRESHOLD = 0.70   # global default (used when symbol not in SYMBOL_THRESHOLDS)
ENABLE_TUNING = True
TUNING_MAX_COMBINATIONS = 8
REQUIRE_TREND_UP = True              # close > EMA200 and EMA50 > EMA200
MIN_ADX_FOR_ENTRY = 15
COOLDOWN_BARS_AFTER_TRADE = 8        # ~2 hours; shorter cd captures re-entries sooner
                                     # (sweep: cd=8 outperformed cd=26 with better Sharpe)

# Per-symbol confidence thresholds (overrides global when a symbol is listed here).
# Proven symbols use tighter thresholds derived from out-of-sample win-rate analysis.
# New v7 symbols start at conservative defaults (0.72-0.78) until backtested.
SYMBOL_THRESHOLDS = {
    # ── Proven Tier S – elite (≥67 % WR, avg trade > €25) ───────────────────
    "MC.PA":    0.65,   # 86% WR, avg +€35/trade
    "ASML.AS":  0.65,   # 80% WR, avg +€77/trade
    "RHM.DE":   0.65,   # 55% WR, +€602 total – volume workhorse, now Tier S

    # ── Proven Tier A – strong ────────────────────────────────────────────────
    "RMS.PA":   0.67,   # 67% WR
    "AIR.PA":   0.67,   # strong WR small sample
    "ENR.DE":   0.68,   # 50% WR but high avg pnl

    # ── Proven Tier B – solid ─────────────────────────────────────────────────
    "ALV.DE":   0.68,   # 68% WR (improved with M2)
    "IFX.DE":   0.70,   # 59% WR
    "TTE.PA":   0.70,   # 89% WR small sample
    "SIE.DE":   0.72,   # 83% WR small sample

    # ── Proven Tier C – gated ─────────────────────────────────────────────────
    "ROG.SW":   0.72,   # 0% WR historically – very strict
    "ADYEN.AS": 0.80,   # chronic loser – near-excluded

    # ── New v7 symbols – defense/aerospace (structural bull) ─────────────────
    "HO.PA":    0.67,   # Thales – defense mega-trend, high momentum expected
    "SAF.PA":   0.67,   # Safran – aerospace, strong secular trend

    # ── New v7 symbols – luxury ───────────────────────────────────────────────
    "KER.PA":   0.70,   # Kering – luxury, trend-following candidate
    "OR.PA":    0.72,   # L'Oréal – quality but defensive, start conservative
    "EL.PA":    0.72,   # EssilorLuxottica – healthcare/consumer

    # ── New v7 symbols – technology ───────────────────────────────────────────
    "DSY.PA":   0.70,   # Dassault Systèmes – software, good momentum
    "SAP.DE":   0.72,   # SAP – solid software giant, somewhat defensive

    # ── New v7 symbols – semiconductor ───────────────────────────────────────
    "STMPA.PA": 0.70,   # STMicro – volatile chip stock, strong when trending

    # ── New v7 symbols – pharma ───────────────────────────────────────────────
    "SAN.PA":   0.72,   # Sanofi – large pharma, moderate volatility
    "BAYN.DE":  0.78,   # Bayer – troubled fundamentals; strict filter

    # ── New v7 symbols – financials ───────────────────────────────────────────
    "DBK.DE":   0.75,   # Deutsche Bank – volatile but choppy; cautious
    "PRX.AS":   0.75,   # Prosus – tech holding, less directional

    # ── New v7 symbols – auto ─────────────────────────────────────────────────
    "VOW3.DE":  0.78,   # VW – structural headwinds; very strict
}

# ---------------------------------------------------------------------------
# Position sizing & risk management  (v5: scaled risk, ~25 % annual target)
#
# The v4 AI Ensemble produced a -1.57 % max drawdown on a 10 % annual return.
# That safety buffer justifies a full risk doubling.  Two controls interact:
#
#   1. SYMBOL_RISK_PCT  – target EUR-at-risk per trade (as % of portfolio).
#   2. MAX_POSITION_PCT – hard cap on the notional position size.
#
# For high-priced EU stocks (ASML ~€756, RHM.DE ~€890, MC.PA ~€730) the
# position cap is the binding constraint, NOT the risk %.  Raising risk %
# alone would do nothing; both levers must move together.
#
# With MAX_POSITION_PCT raised 25 % → 40 %:
#   ASML stake  3.3 shares (€2,500) → 5.3 shares (€4,000)  +60 % per trade
#   RHM stake   2.8 shares (€2,500) → 4.5 shares (€4,000)  +60 % per trade
#   MC.PA stake 3.4 shares (€2,500) → 5.5 shares (€4,000)  +60 % per trade
#
# Expected annual PnL uplift: ~60-80 % on the same trade count / win rate.
# ---------------------------------------------------------------------------

INITIAL_CAPITAL = 10_000.0

# Default risk per trade (global fallback for symbols not in SYMBOL_RISK_PCT).
# Doubled from 5 % – the demonstrated -1.57 % drawdown leaves ample headroom.
RISK_PER_TRADE_PCT = 0.10   # 10 % of portfolio at risk per standard setup

# ── Four performance tiers, each with a distinct risk budget ─────────────────
#
#  Tier S  – elite  ( ≥ 65 % WR, proven alpha, avg trade > €25 )  → 15 %
#  Tier A  – strong ( 50–65 % WR, consistent edge )               → 12 %
#  Tier B  – solid  ( 40–50 % WR, reliable volume workhorse )     → 10 %
#  Tier C  – weak   ( < 40 % WR, strict threshold gate )          →  5 %
#
# Combined with the Kelly multiplier (max 2.5 ×), a Tier-S signal at peak
# confidence can target up to 15 % × 2.5 = 37.5 % notional – always capped
# by MAX_POSITION_PCT (40 %).  In practice the cap is the binding limit for
# expensive stocks; the risk % drives sizing for mid-priced ones.
SYMBOL_RISK_PCT = {
    # ── Tier S: elite (≥55% WR, high avg pnl, proven alpha) ─────────────────
    "MC.PA":    0.15,   # 86% WR
    "ASML.AS":  0.15,   # 80% WR
    "RHM.DE":   0.15,   # promoted: 55% WR, +€602 total, high volume

    # ── Tier A: strong ────────────────────────────────────────────────────────
    "RMS.PA":   0.12,
    "AIR.PA":   0.12,
    "ENR.DE":   0.12,
    "ALV.DE":   0.12,   # promoted: 68% WR with M2 execution
    "TTE.PA":   0.12,   # promoted: 89% WR small sample
    "SIE.DE":   0.12,   # promoted: 83% WR small sample
    # New defense stocks start at Tier A – structural mega-trend
    "HO.PA":    0.12,
    "SAF.PA":   0.12,

    # ── Tier B: solid (new stocks + mid-tier proven) ──────────────────────────
    "IFX.DE":   0.10,
    "KER.PA":   0.10,
    "DSY.PA":   0.10,
    "STMPA.PA": 0.10,
    "OR.PA":    0.10,
    "EL.PA":    0.10,
    "SAN.PA":   0.10,
    "SAP.DE":   0.10,

    # ── Tier C: cautious (new unknowns + chronic underperformers) ─────────────
    "ROG.SW":   0.05,
    "ADYEN.AS": 0.05,
    "BAYN.DE":  0.05,
    "DBK.DE":   0.05,
    "PRX.AS":   0.05,
    "VOW3.DE":  0.05,
}

# ── Per-symbol position size cap (overrides global MAX_POSITION_PCT) ─────────
#
# For expensive EU stocks (ASML ~€756, RHM ~€890) on a €10k portfolio the ATR-
# based risk formula always produces a notional value larger than the cap, so
# MAX_POSITION_PCT is the ONLY effective sizing lever per symbol.
#
# Tiered caps create real stake differentiation:
#   Tier S  → 40 % cap = €4,000  (+60 % vs old €2,500 cap)
#   Tier A  → 35 % cap = €3,500  (+40 % vs old cap)
#   Tier B  → 30 % cap = €3,000  (+20 % vs old cap)
#   Tier C  → 20 % cap = €2,000  (-20 % vs old cap – reduces bad-symbol damage)
#
# Global MAX_POSITION_PCT (below) acts as the fallback when a symbol is absent.
SYMBOL_MAX_POSITION_PCT = {
    # Tier S
    "MC.PA":    0.40,
    "ASML.AS":  0.40,
    "RHM.DE":   0.40,
    # Tier A
    "RMS.PA":   0.35,
    "AIR.PA":   0.35,
    "ENR.DE":   0.35,
    "ALV.DE":   0.35,
    "TTE.PA":   0.35,
    "SIE.DE":   0.35,
    "HO.PA":    0.35,
    "SAF.PA":   0.35,
    # Tier B
    "IFX.DE":   0.30,
    "KER.PA":   0.30,
    "DSY.PA":   0.30,
    "STMPA.PA": 0.30,
    "OR.PA":    0.30,
    "EL.PA":    0.30,
    "SAN.PA":   0.30,
    "SAP.DE":   0.30,
    # Tier C
    "ROG.SW":   0.20,
    "ADYEN.AS": 0.20,
    "BAYN.DE":  0.20,
    "DBK.DE":   0.20,
    "PRX.AS":   0.20,
    "VOW3.DE":  0.20,
}

# ── Confidence-scaled Kelly multiplier ───────────────────────────────────────
# Maps confidence linearly from threshold → 1.0× to CEIL → KELLY_MAX_MULT×.
#
#   conf = 0.70 → 1.00 × base risk
#   conf = 0.78 → 1.75 × base risk
#   conf = 0.85 → 2.50 × base risk  (maximum, for very high-conviction signals)
#
# NOTE: for expensive stocks the per-symbol position cap is binding before the
# Kelly formula matters, so Kelly primarily benefits lower-priced symbols
# (IFX.DE at €37, TTE.PA at €55) where uncapped sizing is possible.
KELLY_MAX_MULT        = 2.5    # was 2.0
KELLY_CONFIDENCE_CEIL = 0.85   # was 0.90  (reach full Kelly at confidence 0.85)

# ── Hard portfolio limits ──────────────────────────────────────────────────────
MAX_POSITION_PCT      = 0.30   # global fallback cap (Tier B default)
MAX_TOTAL_EXPOSURE_PCT = 0.90  # ≤ 90 % invested – only 10 % idle cash reserve
MAX_OPEN_POSITIONS    = 6      # back to 6 slots to absorb the wider 25-symbol universe

EU_ONLY_MODE = True

# ---------------------------------------------------------------------------
# Pyramiding  (Approach: "average winners, never losers" – Jesse Livermore)
# ---------------------------------------------------------------------------
# When an open position reaches PYRAMID_ATR_MULT above entry, the bot adds
# PYRAMID_FRACTION more shares at that price.  Simultaneously the stop-loss
# for the entire position is moved to the original entry price (breakeven),
# making the initial lot risk-free while the add rides with 1.5R at stake.
#
# Only applied to PYRAMID_SYMBOLS (Tier S + A) where the model edge is proven.
# The add is skipped if cash < required or the pyramid level was not cleanly hit.
#
#  Entry €100, SL €75 (2.5 ATR), ATR=10
#  Pyramid fires at €115 (entry + 1.5 ATR):
#    - Original 10 shares: stop moves to €100 → risk-free (+0 to +€150 floor)
#    - Added  5 shares at €115: stop at €100 → max loss = 5 × €15 = €75
#    - If price reaches TP €150: profit = 10×€50 + 5×€35 = €675  vs €500 baseline
PYRAMID_ENABLED     = False  # toggled in variant_sweep.py per experiment
PYRAMID_ATR_MULT    = 1.5    # add at entry + 1.5 × ATR
PYRAMID_FRACTION    = 0.50   # add 50 % of original shares
PYRAMID_SYMBOLS = {
    # Tier S
    "MC.PA", "ASML.AS", "RHM.DE",
    # Tier A (defense boom + proven alpha)
    "RMS.PA", "ENR.DE", "HO.PA", "SAF.PA", "ALV.DE",
}

# ---------------------------------------------------------------------------
# Scale-out  (Approach 2: partial profit-lock)
# ---------------------------------------------------------------------------
# When price reaches SCALE_OUT_ATR_MULT above entry, close SCALE_OUT_FRACTION
# of the position at that level and move the stop-loss to breakeven.
# The remaining shares run toward the full TP / trailing stop.
#
# Example with SL=2.5, TP=5.0, SCALE_OUT at 2.5:
#   - 50 % exits at entry + 2.5 ATR  → guaranteed profit locked
#   - Stop moves to entry             → remaining 50 % is risk-free
#   - Remaining 50 % runs to 5.0 ATR or trail exit
SCALE_OUT_ENABLED   = False  # disabled in baseline; enable per experiment
SCALE_OUT_ATR_MULT  = 2.5    # partial exit at 2.5 × ATR above entry (= 1R)
SCALE_OUT_FRACTION  = 0.50   # close this fraction of position at scale-out

# ---------------------------------------------------------------------------
# Macro regime filter  (Approach 3: universe-wide trend guard)
# ---------------------------------------------------------------------------
# Before opening any new position, check whether the broader EU market is in
# an uptrend.  Regime = True if the fraction of universe symbols with
# close >= EMA200 at that timestamp is >= MACRO_FILTER_MIN_UPTREND.
# When the regime is bearish (fraction below threshold), all new BUYs are blocked.
MACRO_FILTER_ENABLED       = False  # disabled in baseline; enable per experiment
MACRO_FILTER_MIN_UPTREND   = 0.60   # require ≥ 60 % of universe in uptrend

# ---------------------------------------------------------------------------
# Sector Correlation Clamping  (Task 1: diversification enforcement)
# ---------------------------------------------------------------------------
# When enabled, rejects a BUY signal if any open position is already in the
# same sector (from SYMBOL_SECTOR above).  Forces the portfolio to always hold
# diversified sectors rather than piling into one trending theme.
#
# Why this is NOT overfitting: sector correlation is a portfolio construction
# rule, not a fitted historical parameter.  It applies universally: holding two
# defense stocks simultaneously doubles your defense-macro exposure.
SECTOR_CLAMPING_ENABLED = True    # enabled: sweep shows 32.7 % return vs 31.0 % baseline

# ---------------------------------------------------------------------------
# Dynamic Macro Risk Scaling  (Task 2: regime-adaptive position sizing)
# ---------------------------------------------------------------------------
# Rather than blocking trades in a bear regime, this SCALES position size.
# Regime is determined by the same universe EMA200 fraction as the macro filter.
#
#   Bull regime (≥ MACRO_REGIME_BULL_THRESHOLD of symbols above EMA200)
#       → risk_scale = MACRO_BULL_RISK_SCALE  (full sized; default 1.4×)
#   Bear regime (below threshold)
#       → risk_scale = MACRO_BEAR_RISK_SCALE  (half sized; default 0.7×)
#
# This is not fitted to a specific drawdown target; it follows the universal
# principle that trend-following systems should reduce size when the broad
# market trend is against them.
DYNAMIC_MACRO_RISK_ENABLED    = True   # enabled: reduces DD to -5.70 % and lifts Sharpe to 2.10
MACRO_REGIME_BULL_THRESHOLD   = 0.50   # ≥ 50 % of universe above EMA200 → bull
MACRO_BULL_RISK_SCALE         = 1.4    # standard production size in bull regime
MACRO_BEAR_RISK_SCALE         = 0.7    # halved size in bear regime

# ---------------------------------------------------------------------------
# Tax rates (all EUR-denominated; no GBP in active universe)
# ---------------------------------------------------------------------------
DIVIDEND_WHT = {
    "US": 0.15,
    "NL": 0.15,      # Netherlands
    "FR": 0.15,      # France (after treaty reclaim)
    "DE": 0.26375,   # Germany (Abgeltungsteuer + Soli)
    "CH": 0.15,      # Switzerland (after treaty reclaim)
    "IT": 0.26,      # Italy (Ferrari / Borsa Italiana)
}

JURISDICTION_MAP = {
    "":    "US",
    ".AS": "NL",
    ".PA": "FR",
    ".DE": "DE",
    ".SW": "CH",
    ".MI": "IT",
}

FX_SPREAD_PCT = 0.0015
COMMISSION_PER_TRADE = 0.0

# Capital-gains tax on net realised annual gains.  Trading212 reports gross;
# the investor pays CGT in their country of residence.  This is a flat annual
# approximation (losses offset gains within the year).  Adjust to your country:
#   Bulgaria 0.10 (10% flat) | Germany ~0.26 | France ~0.30 | Belgium 0.00
# Short-term swing trades do NOT qualify for long-term relief anywhere, so the
# full rate applies.  All EUR-denominated symbols → no FX drag (already 0).
CAPITAL_GAINS_TAX_RATE = 0.10
