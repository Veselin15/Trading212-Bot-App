"""
Train & save the production models  (v4.0 / BEST_SAFE)
=======================================================

Trains one XGBoost+LightGBM ensemble per EU symbol on the current feature
pipeline (the exact setup the +32.5% OOS result was measured on) and saves them
to t212_miner_bot/models/ for the live trader to load.

This is the lightweight, deterministic training path (no hyperparameter tuning,
no walk-forward) used for deployment — it matches the optimization cache build.
Run this whenever the feature pipeline or training window changes.

    python -m t212_miner_bot.train_production_models
"""

from __future__ import annotations

import logging, time, warnings
import pandas as pd
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


def main() -> None:
    t0 = time.time()
    available = set(get_available_symbols())
    symbols = [s for s in EU_SYMBOLS if s in available]
    log.info("Training %d EU symbols (train window ends %s)…", len(symbols), TRAIN_END.date())

    raw_15m, raw_5m = {}, {}
    for s in symbols:
        try:
            d = load_multi_timeframe(s)
            raw_15m[s] = d["15m"]; raw_5m[s] = d.get("5m")
        except Exception as e:
            log.warning("[%s] load skip: %s", s, e)

    log.info("Computing sector RS + features…")
    sector_rs = compute_sector_relative_strength(raw_15m)

    saved = 0
    for s, df in raw_15m.items():
        try:
            compute_all_features(df, raw_5m.get(s), symbol=s)
            attach_sector_rs(df, sector_rs.get(s))
            apply_triple_barrier_labels(df)
            df.dropna(subset=["label"], inplace=True)
            fcols = [c for c in get_feature_columns(df) if not df[c].isna().all()]
            df[fcols] = df[fcols].fillna(0.0)

            train = df.loc[:TRAIN_END_TS].dropna(subset=["label"])
            if len(train) < 500:
                log.warning("[%s] too little train data (%d) — skipped", s, len(train))
                continue
            model = EnsembleModel(s)
            model.train(train[fcols], train["label"], early_stopping_rounds=0)
            model.save()
            saved += 1
            log.info("  [%s] trained on %d bars, %d features → saved", s, len(train), len(fcols))
        except Exception as e:
            log.warning("[%s] train error: %s", s, e)

    log.info("Saved %d / %d models in %.0fs → t212_miner_bot/models/",
             saved, len(symbols), time.time() - t0)


if __name__ == "__main__":
    main()
