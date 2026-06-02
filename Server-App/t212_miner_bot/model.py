"""
XGBoost model wrapper: training, prediction, persistence, and evaluation.

One model instance is trained per symbol to capture each stock's unique
volatility/microstructure.  Time-series cross-validation is used for
hyperparameter sanity-checking on the training set.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    log_loss,
    roc_auc_score,
)
from xgboost import XGBClassifier

from t212_miner_bot.config import (
    MODEL_DIR,
    XGB_PARAMS,
    TSCV_N_SPLITS,
)


class XGBoostSwingModel:
    """Thin wrapper around ``XGBClassifier`` with persistence helpers."""

    def __init__(self, symbol: str, params: Optional[Dict] = None):
        self.symbol = symbol
        self.params = {**XGB_PARAMS, **(params or {})}
        self.model: Optional[XGBClassifier] = None
        self.feature_names: List[str] = []
        self.cv_scores: List[float] = []

    # ── Training ──────────────────────────────────────────────────────────

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        eval_set: Optional[Tuple[pd.DataFrame, pd.Series]] = None,
    ) -> "XGBoostSwingModel":
        """
        Fit the XGBoost classifier.

        *eval_set* is an optional (X_val, y_val) tuple for early stopping.
        ``scale_pos_weight`` is auto-adjusted from the label balance.
        """
        self.feature_names = list(X.columns)

        pos_count = int(y.sum())
        neg_count = len(y) - pos_count
        self.params["scale_pos_weight"] = neg_count / max(pos_count, 1)

        self.model = XGBClassifier(**self.params)

        fit_params: dict = {}
        if eval_set is not None:
            fit_params["eval_set"] = [eval_set]
            fit_params["verbose"] = False

        self.model.fit(X, y, **fit_params)
        return self

    # ── Prediction ────────────────────────────────────────────────────────

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return binary predictions (0 / 1)."""
        assert self.model is not None, "Model not trained yet."
        return self.model.predict(X[self.feature_names])

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return probability of class 1 (profitable trade)."""
        assert self.model is not None, "Model not trained yet."
        return self.model.predict_proba(X[self.feature_names])[:, 1]

    # ── Evaluation ────────────────────────────────────────────────────────

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Compute standard classification metrics on a held-out set."""
        preds = self.predict(X)
        proba = self.predict_proba(X)
        return {
            "accuracy": accuracy_score(y, preds),
            "roc_auc": roc_auc_score(y, proba) if len(set(y)) > 1 else 0.0,
            "log_loss": log_loss(y, proba),
            "report": classification_report(y, preds, output_dict=True),
        }

    def time_series_cv(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = TSCV_N_SPLITS,
    ) -> List[float]:
        """
        Run expanding-window time-series cross-validation and return the
        AUC scores for each fold.  Useful for sanity-checking before the
        final train on the full training window.
        """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores: List[float] = []

        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

            clone = XGBClassifier(**self.params)
            clone.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
            proba = clone.predict_proba(X_val)[:, 1]
            if len(set(y_val)) > 1:
                scores.append(roc_auc_score(y_val, proba))

        self.cv_scores = scores
        return scores

    # ── Feature importance ────────────────────────────────────────────────

    def feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """Return a sorted DataFrame of feature importances (gain)."""
        assert self.model is not None
        imp = self.model.get_booster().get_score(importance_type="gain")
        df = (
            pd.DataFrame.from_dict(imp, orient="index", columns=["gain"])
            .sort_values("gain", ascending=False)
            .head(top_n)
        )
        df.index.name = "feature"
        return df

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, directory: Optional[Path] = None) -> Path:
        """Persist the trained model + metadata to disk."""
        out_dir = directory or MODEL_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        model_path = out_dir / f"{self.symbol}_xgb.joblib"
        meta_path = out_dir / f"{self.symbol}_meta.json"

        joblib.dump(self.model, model_path)
        meta = {
            "symbol": self.symbol,
            "feature_names": self.feature_names,
            "cv_scores": self.cv_scores,
            "params": {k: v for k, v in self.params.items() if k != "n_jobs"},
        }
        meta_path.write_text(json.dumps(meta, indent=2))
        return model_path

    @classmethod
    def load(cls, symbol: str, directory: Optional[Path] = None) -> "XGBoostSwingModel":
        """Restore a previously saved model from disk."""
        src_dir = directory or MODEL_DIR
        model_path = src_dir / f"{symbol}_xgb.joblib"
        meta_path = src_dir / f"{symbol}_meta.json"

        if not model_path.exists():
            raise FileNotFoundError(f"No saved model at {model_path}")

        instance = cls(symbol)
        instance.model = joblib.load(model_path)
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            instance.feature_names = meta.get("feature_names", [])
            instance.cv_scores = meta.get("cv_scores", [])
        return instance
