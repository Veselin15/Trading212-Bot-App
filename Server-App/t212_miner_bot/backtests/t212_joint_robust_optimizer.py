"""
Constrained joint robust optimizer for current 4-symbol live basket.

Goal:
- Search a small, safe parameter neighborhood around current live settings.
- Score candidates on OOS-style windows (2024 / 2025 / 2026 YTD).
- Prefer stability, not just max backtest return.
"""

from __future__ import annotations

import argparse
import itertools
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests import t212_strategy_compare_4stocks as core
from t212_miner_bot.backtests.t212_bulgaria_fee_tax_portfolio_test import (
    _discover_symbol_files,
    _fee_bps_per_side_for_symbol,
)
from t212_miner_bot.config import StrategyParams


DATA_DIR = REPO_ROOT / "data"
SYMBOLS = ["ASML.AS", "SAP.DE", "UNA.AS", "AMD"]
WINDOWS: list[tuple[str, pd.Timestamp, pd.Timestamp]] = [
    ("2024", pd.Timestamp("2024-01-01T00:00:00Z"), pd.Timestamp("2024-12-31T23:59:59Z")),
    ("2025", pd.Timestamp("2025-01-01T00:00:00Z"), pd.Timestamp("2025-12-31T23:59:59Z")),
    ("2026_YTD", pd.Timestamp("2026-01-01T00:00:00Z"), pd.Timestamp("2026-12-31T23:59:59Z")),
]


@dataclass(frozen=True)
class SymCfg:
    mode: str
    lock_trigger: float
    lock_stop: float
    morning_enabled: bool
    morning_real_trigger: float
    morning_capture: float
    morning_window_min: int
    atr_stop: float
    atr_tp: float
    atr_be: float


def _load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    req = {"timestamp", "open", "high", "low", "close", "volume"}
    if not req.issubset(df.columns):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    return out.set_index("timestamp")


def _score(window_rets: list[float]) -> float:
    avg = sum(window_rets) / len(window_rets)
    std = statistics.pstdev(window_rets) if len(window_rets) > 1 else 0.0
    worst = min(window_rets)
    return avg - (0.4 * std) + (0.2 * worst)


def _simulate(symbol: str, bars: pd.DataFrame, cfg: SymCfg, slippage_bps: float, max_trades: int):
    sim_cfg = core.SimConfig(
        fee_bps=_fee_bps_per_side_for_symbol(symbol),
        slippage_bps=slippage_bps,
        max_trades_per_day=max_trades,
        atr_stop_multiplier=cfg.atr_stop,
        atr_tp_r=cfg.atr_tp,
        atr_be_r=cfg.atr_be,
        morning_protect_enabled=cfg.morning_enabled,
        morning_real_profit_trigger_pct=cfg.morning_real_trigger,
        morning_profit_capture_pct=cfg.morning_capture,
        morning_protect_window_minutes=cfg.morning_window_min,
        morning_protect_symbol_enabled={symbol: cfg.morning_enabled},
    )
    if cfg.mode == "ATR":
        return core._simulate_atr_dynamic_variant(
            bars,
            symbol=symbol,
            config=sim_cfg,
            stop_mult=cfg.atr_stop,
            tp_r=cfg.atr_tp,
            be_r=cfg.atr_be,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            regime_adaptive=False,
            profit_lock_trigger_pct=cfg.lock_trigger,
            profit_lock_stop_pct=cfg.lock_stop,
        )
    return core._simulate_symbol_variant(
        bars,
        symbol=symbol,
        enable_break_even_1pct=False,
        config=sim_cfg,
        entry_filter_mode="NONE",
        entry_filter_param=0.0,
        profit_lock_trigger_pct=cfg.lock_trigger,
        profit_lock_stop_pct=cfg.lock_stop,
    )


def _cfg_key(c: SymCfg) -> tuple:
    return (
        c.mode,
        round(c.lock_trigger, 6),
        round(c.lock_stop, 6),
        int(c.morning_enabled),
        round(c.morning_real_trigger, 6),
        round(c.morning_capture, 6),
        int(c.morning_window_min),
        round(c.atr_stop, 6),
        round(c.atr_tp, 6),
        round(c.atr_be, 6),
    )


def run(slippage_bps: float, max_trades: int) -> None:
    params = StrategyParams()
    files = _discover_symbol_files(DATA_DIR)
    bars_raw: dict[str, pd.DataFrame] = {}
    for s in SYMBOLS:
        if s not in files:
            raise RuntimeError(f"Missing CSV for {s}")
        bars = _load_csv(files[s])
        if bars.empty:
            raise RuntimeError(f"No bars for {s}")
        bars_raw[s] = bars

    bars_prepared: dict[str, pd.DataFrame] = {}
    for s, df in bars_raw.items():
        bars_prepared[s] = core.add_indicators(df, ema_period=params.ema_period).dropna().copy()
    core.add_indicators = lambda df_raw, ema_period: df_raw

    # Read live baseline with existing per-symbol overrides.
    profit_lock_map = dict(getattr(params, "profit_lock_by_symbol", {}))
    atr_map = dict(getattr(params, "atr_dynamic_params_by_symbol", {}))
    morning_capture_map = dict(getattr(params, "morning_profit_capture_pct_by_symbol", {}))
    morning_enabled_map = dict(getattr(params, "morning_protect_symbol_enabled", {}))

    def live_cfg(symbol: str, mode: str) -> SymCfg:
        trig, stop = profit_lock_map.get(symbol, (params.profit_lock_trigger_pct, params.profit_lock_stop_pct))
        a_stop, a_tp, a_be = atr_map.get(
            symbol,
            (params.atr_dynamic_stop_mult, params.atr_dynamic_tp_r, params.atr_dynamic_be_r),
        )
        return SymCfg(
            mode=mode,
            lock_trigger=float(trig),
            lock_stop=float(stop),
            morning_enabled=bool(morning_enabled_map.get(symbol, False)),
            morning_real_trigger=float(params.morning_real_profit_trigger_pct),
            morning_capture=float(morning_capture_map.get(symbol, params.morning_profit_capture_pct)),
            morning_window_min=int(params.morning_protect_window_minutes),
            atr_stop=float(a_stop),
            atr_tp=float(a_tp),
            atr_be=float(a_be),
        )

    base = {
        "ASML.AS": live_cfg("ASML.AS", "BASE"),
        "SAP.DE": live_cfg("SAP.DE", "ATR"),
        "UNA.AS": live_cfg("UNA.AS", "BASE"),
        "AMD": live_cfg("AMD", "BASE"),
    }

    # Constrained neighborhoods.
    asml_set = [base["ASML.AS"]]  # keep stable winner fixed
    sap_set = [
        SymCfg(**{**base["SAP.DE"].__dict__, "morning_capture": mc, "atr_tp": tp, "atr_be": be})
        for mc, tp, be in itertools.product([0.30, 0.35], [4.5, 5.0], [1.2, 1.4])
    ]
    una_set = [
        SymCfg(**{**base["UNA.AS"].__dict__, "lock_stop": s})
        for s in [0.014, 0.016, 0.018]
    ]
    amd_set = [
        SymCfg(**{**base["AMD"].__dict__, "lock_trigger": t, "lock_stop": s})
        for t, s in itertools.product([0.04, 0.045], [0.018, 0.02])
        if s < t
    ]

    candidates = list(itertools.product(asml_set, sap_set, una_set, amd_set))
    print(f"[INFO] Joint robust optimizer candidates={len(candidates)}")

    # Cache symbol/window/cfg simulation results.
    cache: dict[tuple[str, str, tuple], float] = {}

    def get_ret(window_name: str, start: pd.Timestamp, end: pd.Timestamp, symbol: str, cfg: SymCfg) -> float:
        key = (window_name, symbol, _cfg_key(cfg))
        if key in cache:
            return cache[key]
        bars = bars_prepared[symbol]
        sliced = bars[(bars.index >= start) & (bars.index <= end)].copy()
        if sliced.empty:
            ret = 0.0
        else:
            ret = float(_simulate(symbol, sliced, cfg, slippage_bps=slippage_bps, max_trades=max_trades).total_return)
        cache[key] = ret
        return ret

    ranked: list[dict[str, float | str | SymCfg]] = []
    for idx, (c_asml, c_sap, c_una, c_amd) in enumerate(candidates, start=1):
        if idx == 1 or idx % 10 == 0 or idx == len(candidates):
            print(f"[RUN] {idx}/{len(candidates)}")
        win_rets: list[float] = []
        for wname, start, end in WINDOWS:
            vals = [
                get_ret(wname, start, end, "ASML.AS", c_asml),
                get_ret(wname, start, end, "SAP.DE", c_sap),
                get_ret(wname, start, end, "UNA.AS", c_una),
                get_ret(wname, start, end, "AMD", c_amd),
            ]
            win_rets.append(sum(vals) / 4.0)
        ranked.append(
            {
                "ret_2024": win_rets[0],
                "ret_2025": win_rets[1],
                "ret_2026": win_rets[2],
                "avg": sum(win_rets) / 3.0,
                "worst": min(win_rets),
                "score": _score(win_rets),
                "asml": c_asml,
                "sap": c_sap,
                "una": c_una,
                "amd": c_amd,
            }
        )

    ranked = sorted(ranked, key=lambda x: float(x["score"]), reverse=True)
    top = ranked[:10]
    print("\nTop 10 joint robust candidates:")
    print("-" * 105)
    print(f"{'Rank':<5} {'2024%':>8} {'2025%':>8} {'2026%':>8} {'Avg%':>8} {'Worst%':>8} {'Score':>10}")
    print("-" * 105)
    for i, row in enumerate(top, start=1):
        print(
            f"{i:<5} {float(row['ret_2024']):>8.2f} {float(row['ret_2025']):>8.2f} {float(row['ret_2026']):>8.2f} "
            f"{float(row['avg']):>8.2f} {float(row['worst']):>8.2f} {float(row['score']):>10.2f}"
        )
    print("-" * 105)

    baseline = next(
        x
        for x in ranked
        if x["asml"] == base["ASML.AS"] and x["sap"] == base["SAP.DE"] and x["una"] == base["UNA.AS"] and x["amd"] == base["AMD"]
    )
    best = ranked[0]
    print(
        f"[RESULT] Baseline avg={float(baseline['avg']):.2f}% worst={float(baseline['worst']):.2f}% | "
        f"Best avg={float(best['avg']):.2f}% worst={float(best['worst']):.2f}% | "
        f"delta_avg={float(best['avg']) - float(baseline['avg']):.2f} pp"
    )
    print("BEST_CFG_SAP", best["sap"])
    print("BEST_CFG_UNA", best["una"])
    print("BEST_CFG_AMD", best["amd"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrained joint robust optimizer.")
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--max-trades-per-day", type=int, default=9999)
    args = parser.parse_args()
    run(slippage_bps=max(float(args.slippage_bps), 0.0), max_trades=max(int(args.max_trades_per_day), 1))


if __name__ == "__main__":
    main()
