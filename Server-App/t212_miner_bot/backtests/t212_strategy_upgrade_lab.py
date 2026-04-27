"""
Development lab runner for next strategy upgrades.

This file is intentionally separated from the live bot flow so we can
experiment safely via backtests (entry quality filter, per-symbol ATR tuning)
without changing production runtime behavior.
"""

from __future__ import annotations

import argparse

from t212_miner_bot.backtests import t212_strategy_compare_4stocks as core
from t212_miner_bot.config import StrategyParams


def _parse_atr_map(raw: str) -> dict[str, tuple[float, float, float]]:
    """
    Parse format:
    ASML.AS:2.8:4.2:2.2,SAP.DE:2.2:4.0:1.8,SHELL.AS:2.6:3.6:2.0,UNA.AS:2.3:4.0:1.8

    Returns:
        dict[symbol] = (stop_mult, tp_r, be_r)
    """
    out: dict[str, tuple[float, float, float]] = {}
    text = raw.strip()
    if not text:
        return out
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        pieces = token.split(":")
        if len(pieces) != 4:
            continue
        symbol = pieces[0].strip()
        try:
            stop_mult = float(pieces[1])
            tp_r = float(pieces[2])
            be_r = float(pieces[3])
        except ValueError:
            continue
        if not symbol:
            continue
        out[symbol] = (max(stop_mult, 0.1), max(tp_r, 0.1), max(be_r, 0.1))
    return out


def _parse_regime_profiles(raw: str) -> dict[str, tuple[float, float, float]]:
    """
    Parse format:
    TREND_STRONG:2.8:4.5:2.2,TREND_NORMAL:2.5:4.0:2.0,CHOP_WEAK:2.0:3.0:1.2
    """
    out: dict[str, tuple[float, float, float]] = {}
    text = raw.strip()
    if not text:
        return out
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        pieces = token.split(":")
        if len(pieces) != 4:
            continue
        key = pieces[0].strip().upper()
        try:
            stop_mult = float(pieces[1])
            tp_r = float(pieces[2])
            be_r = float(pieces[3])
        except ValueError:
            continue
        if key in {"TREND_STRONG", "TREND_NORMAL", "CHOP_WEAK"}:
            out[key] = (max(stop_mult, 0.1), max(tp_r, 0.1), max(be_r, 0.1))
    return out


def main() -> None:
    params = StrategyParams()
    parser = argparse.ArgumentParser(
        description="Development lab: compare current hybrid vs experimental hybrid."
    )
    parser.add_argument("--days", type=int, default=730, help="Backtest lookback days (default: 730).")
    parser.add_argument("--fee-bps", type=float, default=0.0, help="Per-side fee in bps (default: 0.0).")
    parser.add_argument("--slippage-bps", type=float, default=2.0, help="Per-side slippage in bps (default: 2.0).")
    parser.add_argument(
        "--max-trades-per-day",
        type=int,
        default=9999,
        help="Max new entries per symbol per day (default: 9999).",
    )
    parser.add_argument(
        "--atr-stop-mult",
        type=float,
        default=float(params.atr_dynamic_stop_mult),
        help="Current ATR stop multiplier baseline (default: StrategyParams value).",
    )
    parser.add_argument(
        "--atr-tp-r",
        type=float,
        default=float(params.atr_dynamic_tp_r),
        help="Current ATR take-profit in R baseline (default: StrategyParams value).",
    )
    parser.add_argument(
        "--atr-be-r",
        type=float,
        default=float(params.atr_dynamic_be_r),
        help="Current ATR break-even trigger in R baseline (default: StrategyParams value).",
    )
    parser.add_argument(
        "--symbol-modes",
        type=str,
        default="",
        help="Optional map, e.g. ASML.AS=BASE,SHELL.AS=BASE,SAP.DE=ATR,UNA.AS=ATR",
    )
    parser.add_argument(
        "--entry-filter-mode",
        type=str,
        default="BREAKOUT_ATR",
        help="Enhanced entry filter mode: NONE, BREAKOUT_ATR, PULLBACK_EMA, COMPRESSION_BREAK.",
    )
    parser.add_argument(
        "--entry-filter-param",
        type=float,
        default=0.10,
        help="Enhanced entry filter parameter (meaning depends on mode).",
    )
    parser.add_argument(
        "--enhanced-atr-map",
        type=str,
        default=(
            "ASML.AS:2.8:4.2:2.2,"
            "SAP.DE:2.2:4.0:1.8,"
            "SHELL.AS:2.6:3.6:2.0,"
            "UNA.AS:2.3:4.0:1.8"
        ),
        help=(
            "Experimental ATR map format: "
            "SYMBOL:stop_mult:tp_r:be_r separated by commas."
        ),
    )
    parser.add_argument(
        "--regime-adaptive",
        action="store_true",
        help="Enable regime-adaptive ATR risk for enhanced ATR mode.",
    )
    parser.add_argument(
        "--regime-profiles",
        type=str,
        default="TREND_STRONG:2.8:4.5:2.2,TREND_NORMAL:2.5:4.0:2.0,CHOP_WEAK:2.0:3.0:1.2",
        help="Regime profile map: REGIME:stop_mult:tp_r:be_r comma separated.",
    )
    parser.add_argument(
        "--profit-lock-trigger-pct",
        type=float,
        default=0.0,
        help="If unrealized profit reaches this pct, lift stop to profit-lock level.",
    )
    parser.add_argument(
        "--profit-lock-stop-pct",
        type=float,
        default=0.0,
        help="Profit-lock stop pct from entry once trigger is reached.",
    )
    args = parser.parse_args()

    parsed_map = _parse_atr_map(args.enhanced_atr_map)
    regime_profiles = _parse_regime_profiles(args.regime_profiles)

    config = core.SimConfig(
        fee_bps=max(args.fee_bps, 0.0),
        slippage_bps=max(args.slippage_bps, 0.0),
        max_trades_per_day=max(args.max_trades_per_day, 1),
        atr_stop_multiplier=max(args.atr_stop_mult, 0.1),
        atr_tp_r=max(args.atr_tp_r, 0.1),
        atr_be_r=max(args.atr_be_r, 0.1),
    )
    symbol_mode_map = core._parse_symbol_mode_map(args.symbol_modes)
    core.run_comparison(
        days=args.days,
        config=config,
        symbol_mode_map=symbol_mode_map,
        enhanced_entry_filter_mode=str(args.entry_filter_mode).strip().upper(),
        enhanced_entry_filter_param=max(args.entry_filter_param, 0.0),
        enhanced_atr_params_by_symbol=parsed_map if parsed_map else None,
        enhanced_regime_adaptive=bool(args.regime_adaptive),
        enhanced_regime_profiles=regime_profiles if regime_profiles else None,
        enhanced_profit_lock_trigger_pct=max(args.profit_lock_trigger_pct, 0.0),
        enhanced_profit_lock_stop_pct=max(args.profit_lock_stop_pct, 0.0),
    )


if __name__ == "__main__":
    main()
