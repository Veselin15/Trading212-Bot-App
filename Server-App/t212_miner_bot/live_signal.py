"""
Live Signal Generator  –  Option A (AI Ensemble, per-symbol tuned)

Usage
-----
    # 1. Refresh market data first (run once per day before market close):
    python alpaca_mtf_history_fetcher.py

    # 2. Generate today's signals:
    python -m t212_miner_bot.live_signal

    # 3. Override the portfolio value shown in sizing table:
    python -m t212_miner_bot.live_signal --capital 25000

What this script does
---------------------
  • Loads the latest OHLCV CSV data for each symbol in the EU universe.
  • Computes all features (including DTosc, sector RS, EMAs, ATR …).
  • Loads the saved XGB+LGBM ensemble models from disk.
  • Evaluates the LATEST COMPLETE 15-minute bar for each symbol.
  • Applies all entry filters (trend, ADX, session, per-symbol confidence).
  • Prints a ranked signal table and indicative position sizing.

Important
---------
  This script is READ-ONLY.  It does NOT place any orders.
  Order placement must be wired into execution.py (Trading212 API placeholders).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# ── Project imports ───────────────────────────────────────────────────────────

from t212_miner_bot.config import (
    EU_SYMBOLS,
    INITIAL_CAPITAL,
    EXEC_SL_ATR_MULT as SL_ATR_MULT,
    EXEC_TP_ATR_MULT as TP_ATR_MULT,
    ATR_TRAIL_ACTIVATE_R,
    ATR_TRAIL_MULT,
    SIGNAL_CONFIDENCE_THRESHOLD,
    SYMBOL_THRESHOLDS,
    SYMBOL_RISK_PCT,
    RISK_PER_TRADE_PCT,
    SESSION_FILTER_ENABLED,
    SESSION_CLOSE_BLOCK_UTC_HOUR,
    SESSION_CLOSE_BLOCK_UTC_MINUTE,
    REQUIRE_TREND_UP,
    MIN_ADX_FOR_ENTRY,
)
from t212_miner_bot.data_loader import load_multi_timeframe, get_available_symbols
from t212_miner_bot.features import (
    compute_all_features,
    get_feature_columns,
    compute_sector_relative_strength,
    attach_sector_rs,
)
from t212_miner_bot.ensemble_model import EnsembleModel
from t212_miner_bot.position_sizing import (
    calculate_position_size,
    confidence_kelly_multiplier,
)

logging.basicConfig(
    level=logging.WARNING,       # suppress library noise
    format="%(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_symbol(sym: str) -> Optional[Dict[str, pd.DataFrame]]:
    try:
        return load_multi_timeframe(sym)
    except Exception as exc:
        log.warning("[%s] failed to load data: %s", sym, exc)
        return None


def _load_model(sym: str) -> Optional[EnsembleModel]:
    try:
        return EnsembleModel.load(sym)
    except Exception as exc:
        log.warning("[%s] model not found – run_pipeline.py first: %s", sym, exc)
        return None


def _session_blocked(ts: pd.Timestamp) -> bool:
    """Return True if the bar falls within the blocked EU session window."""
    if not SESSION_FILTER_ENABLED:
        return False
    h, m = ts.hour, ts.minute
    return h > SESSION_CLOSE_BLOCK_UTC_HOUR or (
        h == SESSION_CLOSE_BLOCK_UTC_HOUR and m >= SESSION_CLOSE_BLOCK_UTC_MINUTE
    )


def _passes_entry_filters(row: pd.Series, symbol: str, confidence: float) -> tuple[bool, str]:
    """
    Evaluate all entry gates.
    Returns (passes: bool, reject_reason: str).
    """
    threshold = SYMBOL_THRESHOLDS.get(symbol, SIGNAL_CONFIDENCE_THRESHOLD)

    if confidence < threshold:
        return False, f"low conf ({confidence:.3f} < {threshold:.2f})"

    atr = row.get("atr", 0.0)
    if atr <= 0 or np.isnan(float(atr)):
        return False, "ATR=0"

    if REQUIRE_TREND_UP:
        close   = float(row["close"])
        ema_50  = float(row.get("ema_50",  close))
        ema_200 = float(row.get("ema_200", close))
        if pd.isna(ema_50) or pd.isna(ema_200):
            return False, "EMA missing"
        if close < ema_200 or ema_50 < ema_200:
            return False, "downtrend (below EMA200 or EMA50<EMA200)"

    adx = float(row.get("adx", 0.0))
    if pd.isna(adx) or adx < MIN_ADX_FOR_ENTRY:
        return False, f"weak trend (ADX {adx:.1f} < {MIN_ADX_FOR_ENTRY})"

    if _session_blocked(row.name):
        return False, f"session filter (after {SESSION_CLOSE_BLOCK_UTC_HOUR}:{SESSION_CLOSE_BLOCK_UTC_MINUTE:02d} UTC)"

    return True, "OK"


def _format_signal_table(signals: list[dict], capital: float) -> None:
    """Print the ranked signal table to stdout."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d  %H:%M UTC")

    print()
    print("=" * 90)
    print(f"  LIVE SIGNAL REPORT  –  {now_utc}")
    print(f"  Strategy: AI Ensemble v5  |  Portfolio: EUR {capital:,.0f}")
    print("=" * 90)
    print()

    buys = [s for s in signals if s["signal"] == "BUY"]
    holds = [s for s in signals if s["signal"] != "BUY"]

    if buys:
        print("  BUY SIGNALS  (ranked by confidence)")
        print("  " + "-" * 86)
        header = f"  {'Symbol':<12}{'Conf':>6}  {'Entry':>8}  {'TP':>8}  {'SL':>8}  "
        header += f"{'Shares':>8}  {'Stake EUR':>10}  {'Risk EUR':>9}  {'DTosc':>6}"
        print(header)
        print("  " + "-" * 86)
        for s in sorted(buys, key=lambda x: x["confidence"], reverse=True):
            print(
                f"  {s['symbol']:<12}"
                f"{s['confidence']:>6.3f}  "
                f"{s['entry']:>8.2f}  "
                f"{s['tp']:>8.2f}  "
                f"{s['sl']:>8.2f}  "
                f"{s['shares']:>8.2f}  "
                f"{s['stake']:>10.2f}  "
                f"{s['risk']:>9.2f}  "
                f"{'ON' if s['dtosc_regime'] else 'off':>6}"
            )
        print()

    if holds:
        print("  NO SIGNAL  (entry filter failed)")
        print("  " + "-" * 86)
        for s in sorted(holds, key=lambda x: x["symbol"]):
            bar_ts = s.get("bar_ts", "")
            print(f"  {s['symbol']:<12}  {s['reject_reason']}")
        print()

    # Session info
    if SESSION_FILTER_ENABLED:
        print(
            f"  Session filter: no new entries after "
            f"{SESSION_CLOSE_BLOCK_UTC_HOUR}:{SESSION_CLOSE_BLOCK_UTC_MINUTE:02d} UTC"
        )

    # Exit rule reminder
    print(
        f"\n  Exit rules:  TP={TP_ATR_MULT:.1f}×ATR  |  SL={SL_ATR_MULT:.1f}×ATR  |  "
        f"Trail activates at +{ATR_TRAIL_ACTIVATE_R:.1f}×ATR → trails {ATR_TRAIL_MULT:.1f}×ATR behind"
    )
    print("=" * 90)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main(capital: float = INITIAL_CAPITAL) -> None:
    # ── 1. Discover symbols ───────────────────────────────────────────────────
    from t212_miner_bot.production import PRODUCTION_BLOCKLIST
    available = set(get_available_symbols())
    symbols = [s for s in EU_SYMBOLS if s in available and s not in PRODUCTION_BLOCKLIST]
    if not symbols:
        print("No symbol data found.  Run alpaca_mtf_history_fetcher.py first.")
        sys.exit(1)

    print(f"\nLoading data for {len(symbols)} symbols…", end="", flush=True)

    # ── 2. Load raw OHLCV ────────────────────────────────────────────────────
    raw_15m: Dict[str, pd.DataFrame] = {}
    raw_5m:  Dict[str, Optional[pd.DataFrame]] = {}

    for sym in symbols:
        data = _load_symbol(sym)
        if data:
            raw_15m[sym] = data["15m"]
            raw_5m[sym]  = data.get("5m")

    if not raw_15m:
        print("\nNo data loaded."); sys.exit(1)

    print(f"  done ({len(raw_15m)} symbols).")

    # ── 3. Sector relative-strength (cross-asset, computed once) ─────────────
    print("Computing features…", end="", flush=True)
    sector_rs = compute_sector_relative_strength(raw_15m)

    # ── 4. Feature engineering ────────────────────────────────────────────────
    enriched: Dict[str, pd.DataFrame] = {}
    for sym in raw_15m:
        df = raw_15m[sym].copy()
        compute_all_features(df, raw_5m.get(sym), symbol=sym)
        attach_sector_rs(df, sector_rs[sym])
        df.dropna(subset=["atr"], inplace=True)   # need at minimum ATR
        enriched[sym] = df

    print("  done.")

    # ── 5. Load models ────────────────────────────────────────────────────────
    print("Loading models…", end="", flush=True)
    models: Dict[str, EnsembleModel] = {}
    for sym in enriched:
        m = _load_model(sym)
        if m:
            models[sym] = m
    print(f"  {len(models)} / {len(enriched)} loaded.")

    if not models:
        print("No models found.  Run run_pipeline.py to train the ensemble.")
        sys.exit(1)

    # ── 6. Score latest bar and apply filters ─────────────────────────────────
    print()
    signals: list[dict] = []

    for sym in sorted(enriched.keys()):
        if sym not in models:
            signals.append({"symbol": sym, "signal": "HOLD", "reject_reason": "model missing"})
            continue

        df = enriched[sym]
        model = models[sym]
        fcols = [c for c in get_feature_columns(df) if not df[c].isna().all()]
        X = df[fcols].fillna(0.0)

        # Get confidence score for every bar then focus on the latest
        try:
            probs = model.predict_proba(X)
            confidence_series = pd.Series(probs, index=df.index)
        except Exception as exc:
            signals.append({"symbol": sym, "signal": "HOLD",
                            "reject_reason": f"predict_proba error: {exc}"})
            continue

        # Use the last COMPLETE bar (second-to-last to avoid an open/partial bar)
        latest_idx = -2 if len(df) >= 2 else -1
        row  = df.iloc[latest_idx]
        conf = float(confidence_series.iloc[latest_idx])

        passes, reason = _passes_entry_filters(row, sym, conf)

        if not passes:
            signals.append({
                "symbol": sym, "signal": "HOLD",
                "reject_reason": reason,
                "bar_ts": row.name,
                "confidence": conf,
                "dtosc_regime": int(row.get("dtosc_regime", 0)),
            })
            continue

        # ── Position sizing ──────────────────────────────────────────────────
        entry = float(row["close"])
        atr   = float(row["atr"])
        tp    = entry + TP_ATR_MULT * atr
        sl    = entry - SL_ATR_MULT * atr

        sym_risk = SYMBOL_RISK_PCT.get(sym, RISK_PER_TRADE_PCT)
        sizing   = calculate_position_size(
            portfolio_value=capital,
            entry_price=entry,
            atr=atr,
            sl_atr_mult=SL_ATR_MULT,
            risk_pct=sym_risk,
            confidence=conf,
            symbol=sym,
        )

        signals.append({
            "symbol":       sym,
            "signal":       "BUY",
            "reject_reason": "",
            "bar_ts":       row.name,
            "confidence":   conf,
            "entry":        round(entry, 2),
            "tp":           round(tp, 2),
            "sl":           round(sl, 2),
            "shares":       sizing.shares,
            "stake":        round(sizing.position_value, 2),
            "risk":         round(sizing.risk_amount, 2),
            "dtosc_regime": int(row.get("dtosc_regime", 0)),
        })

    # ── 7. Print report ───────────────────────────────────────────────────────
    _format_signal_table(signals, capital)

    # Summary counts
    n_buy  = sum(1 for s in signals if s["signal"] == "BUY")
    n_hold = len(signals) - n_buy
    total_stake = sum(s.get("stake", 0) for s in signals if s["signal"] == "BUY")
    exposure_pct = (total_stake / capital * 100) if capital > 0 else 0

    print(f"  Summary:  {n_buy} BUY signals  |  {n_hold} HOLD  |  "
          f"Indicative new exposure: EUR {total_stake:,.2f}  ({exposure_pct:.1f}% of capital)")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Ensemble live signal scanner")
    parser.add_argument(
        "--capital", type=float, default=INITIAL_CAPITAL,
        help=f"Portfolio value in EUR for position sizing (default: {INITIAL_CAPITAL:,.0f})"
    )
    args = parser.parse_args()
    main(capital=args.capital)
