"""
Information Coefficient (IC) Analysis  (idea #2)
=================================================

Institutional alpha research optimizes the Information Coefficient — the
Spearman rank correlation between a signal and the subsequent forward return —
rather than raw backtest PnL (which is prone to survivorship/selection bias).

This harness, computed on the TRAINING period only (no OOS leakage), reports:

  1. Model IC: rank-correlation of the ensemble's predicted probability against
     forward 5-bar and 15-bar returns, per symbol and pooled.  This is the
     model's true, path-independent edge.

  2. Per-feature IC: which raw features carry stable predictive alpha and which
     decay.  Features with near-zero or sign-unstable IC add variance without
     signal → candidates to prune (anti-overfit).

  3. IC decay curve: how IC changes across horizons [1,5,15,30,60] bars.  A fast-
     decaying signal must be traded quickly; a slow one tolerates wider exits.

Output: prints tables and writes ic_feature_ranking.csv (used by optimize3 to
build a pruned feature set).

    python -m t212_miner_bot.ic_analysis
"""

from __future__ import annotations

import logging, warnings
from typing import Dict, List
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
warnings.filterwarnings("ignore")

from t212_miner_bot.config import EU_SYMBOLS, TRAIN_END
from t212_miner_bot.data_loader import get_available_symbols, load_multi_timeframe
from t212_miner_bot.features import (
    compute_all_features, get_feature_columns,
    compute_sector_relative_strength, attach_sector_rs,
)
from t212_miner_bot.labeling import apply_triple_barrier_labels
from t212_miner_bot.ensemble_model import EnsembleModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

TRAIN_END_TS = pd.Timestamp(TRAIN_END, tz="UTC")
HORIZONS = [1, 5, 15, 30, 60]


def forward_return(close: pd.Series, h: int) -> pd.Series:
    return close.shift(-h) / close - 1.0


def _safe_ic(x: pd.Series, y: pd.Series) -> float:
    m = x.notna() & y.notna()
    if m.sum() < 50:
        return np.nan
    xv, yv = x[m], y[m]
    if xv.nunique() < 5 or yv.nunique() < 5:
        return np.nan
    ic, _ = spearmanr(xv, yv)
    return ic


def prepare_train(symbols: List[str]):
    raw_15m, raw_5m = {}, {}
    for s in symbols:
        try:
            d = load_multi_timeframe(s)
            raw_15m[s] = d["15m"]; raw_5m[s] = d.get("5m")
        except Exception as e:
            log.warning("[%s] load skip: %s", s, e)
    log.info("Sector RS…")
    sector_rs = compute_sector_relative_strength(raw_15m)
    log.info("Features + labels…")
    enriched, fcols_map = {}, {}
    for s, df in raw_15m.items():
        try:
            compute_all_features(df, raw_5m.get(s), symbol=s)
            attach_sector_rs(df, sector_rs.get(s))
            apply_triple_barrier_labels(df)
            fcols = [c for c in get_feature_columns(df) if not df[c].isna().all()]
            df[fcols] = df[fcols].fillna(0.0)
            enriched[s] = df; fcols_map[s] = fcols
        except Exception as e:
            log.warning("[%s] feat err: %s", s, e)
    return enriched, fcols_map


def main():
    available = set(get_available_symbols())
    symbols = [s for s in EU_SYMBOLS if s in available]
    log.info("Universe: %d symbols", len(symbols))
    enriched, fcols_map = prepare_train(symbols)

    # ── 1. Model IC (train ensemble, score in-sample via TS split tail) ──────
    # Use the last 20% of training as a pseudo-validation slice so model IC is
    # not measured on the exact rows the model memorised.
    log.info("Computing model IC…")
    model_ic_5, model_ic_15 = [], []
    for s, df in enriched.items():
        tr = df.loc[:TRAIN_END_TS].dropna(subset=["label"])
        if len(tr) < 1000:
            continue
        cut = int(len(tr) * 0.8)
        fcols = fcols_map[s]
        m = EnsembleModel(s)
        m.train(tr.iloc[:cut][fcols], tr.iloc[:cut]["label"], early_stopping_rounds=0)
        val = tr.iloc[cut:]
        proba = pd.Series(m.predict_proba(val[fcols].fillna(0.0)), index=val.index)
        fr5 = forward_return(val["close"], 5)
        fr15 = forward_return(val["close"], 15)
        ic5, ic15 = _safe_ic(proba, fr5), _safe_ic(proba, fr15)
        if not np.isnan(ic5):  model_ic_5.append(ic5)
        if not np.isnan(ic15): model_ic_15.append(ic15)

    print("\n" + "=" * 60)
    print("  MODEL INFORMATION COEFFICIENT (in-sample validation tail)")
    print("=" * 60)
    print(f"  Forward 5-bar  IC: mean {np.mean(model_ic_5):+.4f}  "
          f"(IR {np.mean(model_ic_5)/ (np.std(model_ic_5)+1e-9):.2f}, n={len(model_ic_5)})")
    print(f"  Forward 15-bar IC: mean {np.mean(model_ic_15):+.4f}  "
          f"(IR {np.mean(model_ic_15)/(np.std(model_ic_15)+1e-9):.2f}, n={len(model_ic_15)})")
    print("  (IC > 0.03 is a usable signal; > 0.05 is strong for intraday equity)")

    # ── 2. Per-feature IC (pooled across symbols, train period) ──────────────
    log.info("Computing per-feature IC…")
    all_feats = sorted(set().union(*[set(v) for v in fcols_map.values()]))
    feat_ic5: Dict[str, list] = {f: [] for f in all_feats}
    feat_ic15: Dict[str, list] = {f: [] for f in all_feats}

    for s, df in enriched.items():
        tr = df.loc[:TRAIN_END_TS]
        fr5 = forward_return(tr["close"], 5)
        fr15 = forward_return(tr["close"], 15)
        for f in fcols_map[s]:
            ic5 = _safe_ic(tr[f], fr5)
            ic15 = _safe_ic(tr[f], fr15)
            if not np.isnan(ic5):  feat_ic5[f].append(ic5)
            if not np.isnan(ic15): feat_ic15[f].append(ic15)

    rows = []
    for f in all_feats:
        if not feat_ic5[f]:
            continue
        ic5_arr = np.array(feat_ic5[f]); ic15_arr = np.array(feat_ic15[f]) if feat_ic15[f] else np.array([0.0])
        mean5 = ic5_arr.mean()
        # sign consistency: fraction of symbols where IC has the dominant sign
        dom_sign = np.sign(mean5) if mean5 != 0 else 1
        consistency = float(np.mean(np.sign(ic5_arr) == dom_sign))
        rows.append({
            "feature": f,
            "ic_5": round(mean5, 4),
            "ic_15": round(ic15_arr.mean(), 4),
            "abs_ic_5": round(abs(mean5), 4),
            "sign_consistency": round(consistency, 3),
            "n_symbols": len(ic5_arr),
        })
    rank = pd.DataFrame(rows).sort_values("abs_ic_5", ascending=False).reset_index(drop=True)
    rank.to_csv("t212_miner_bot/ic_feature_ranking.csv", index=False)

    print("\n" + "=" * 78)
    print("  TOP 20 FEATURES BY |IC| (forward 5-bar, pooled, train period)")
    print("=" * 78)
    print(f"  {'feature':<26} {'IC_5':>8} {'IC_15':>8} {'|IC_5|':>8} {'sign_cons':>10}")
    print("  " + "-" * 74)
    for _, r in rank.head(20).iterrows():
        print(f"  {r['feature']:<26} {r['ic_5']:>+8.4f} {r['ic_15']:>+8.4f} "
              f"{r['abs_ic_5']:>8.4f} {r['sign_consistency']:>10.2f}")

    print("\n  BOTTOM 10 (weakest |IC| – prune candidates):")
    for _, r in rank.tail(10).iterrows():
        print(f"  {r['feature']:<26} {r['ic_5']:>+8.4f}  |IC|={r['abs_ic_5']:.4f}  cons={r['sign_consistency']:.2f}")

    # ── 3. IC decay curve (pooled, a few representative momentum features) ────
    print("\n" + "=" * 60)
    print("  IC DECAY CURVE  (pooled |IC| by horizon)")
    print("=" * 60)
    decay_feats = [f for f in ["macd_hist", "rsi", "roc_5", "donchian_pos_20",
                               "dtosc_momentum_15m", "sector_rs"] if f in all_feats]
    print(f"  {'feature':<22} " + " ".join(f"{h:>6}b" for h in HORIZONS))
    for f in decay_feats:
        ics = []
        for h in HORIZONS:
            vals = []
            for s, df in enriched.items():
                if f not in fcols_map[s]:
                    continue
                tr = df.loc[:TRAIN_END_TS]
                ic = _safe_ic(tr[f], forward_return(tr["close"], h))
                if not np.isnan(ic):
                    vals.append(abs(ic))
            ics.append(np.mean(vals) if vals else 0.0)
        print(f"  {f:<22} " + " ".join(f"{v:>6.3f}" for v in ics))

    n_strong = int((rank["abs_ic_5"] >= 0.01).sum())
    print(f"\n  Features with |IC_5| >= 0.01: {n_strong} / {len(rank)}")
    print(f"  Ranking saved -> t212_miner_bot/ic_feature_ranking.csv")
    log.info("Done.")


if __name__ == "__main__":
    main()
