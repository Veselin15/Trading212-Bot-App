"""
XGBoost + LightGBM ensemble model.

Both models are trained on the same feature set.  Final probability is a
weighted average (configurable via config.XGB_ENSEMBLE_WEIGHT).  Using two
diverse tree boosters reduces variance and generally improves AUC by 2-4
points compared to either model alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, log_loss, accuracy_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

# ── XGBoost ≥1.7 / sklearn ≥1.3 compatibility ────────────────────────────────
# sklearn's BaseEstimator.get_params() is called inside XGBoost's predict_proba
# via _can_use_inplace_predict → get_xgb_params → get_params.  It iterates
# __init__ parameter names and does getattr(self, key).  Models pickled with
# XGBoost ≤1.6 stored use_label_encoder in their state; newer XGBoost removes
# the attribute entirely, so getattr raises AttributeError and kills inference.
#
# Patching BaseEstimator.get_params to swallow AttributeErrors on missing keys
# is the only reliable fix — instance-level and class-level XGBClassifier dict
# writes are silently blocked by XGBoost's internal parameter machinery.
from sklearn.base import BaseEstimator as _BaseEstimator

_orig_get_params = _BaseEstimator.get_params

def _compat_get_params(self, deep: bool = True) -> dict:
    out: dict = {}
    for key in self._get_param_names():
        try:
            value = getattr(self, key)
        except AttributeError:
            continue
        if deep and hasattr(value, "get_params") and not isinstance(value, type):
            out.update((key + "__" + k, v) for k, v in value.get_params().items())
        out[key] = value
    return out

_BaseEstimator.get_params = _compat_get_params
# ─────────────────────────────────────────────────────────────────────────────

from t212_miner_bot.config import (
    MODEL_DIR,
    XGB_PARAMS,
    LGBM_PARAMS,
    XGB_ENSEMBLE_WEIGHT,
    TSCV_N_SPLITS,
)


class EnsembleModel:
    """
    Weighted average of XGBoost and LightGBM classifiers.

    Usage::

        model = EnsembleModel("ASML.AS")
        model.train(X_train, y_train)
        proba = model.predict_proba(X_test)   # float array 0..1
        model.save()

        loaded = EnsembleModel.load("ASML.AS")
    """

    def __init__(
        self,
        symbol: str,
        xgb_params: Optional[Dict] = None,
        lgbm_params: Optional[Dict] = None,
        xgb_weight: float = XGB_ENSEMBLE_WEIGHT,
    ):
        self.symbol = symbol
        self.xgb_weight = xgb_weight
        self.lgbm_weight = 1.0 - xgb_weight

        self.xgb_params = {**XGB_PARAMS, **(xgb_params or {})}
        self.lgbm_params = {**LGBM_PARAMS, **(lgbm_params or {})}

        self.xgb: Optional[XGBClassifier] = None
        self.lgbm: Optional[LGBMClassifier] = None
        self.feature_names: List[str] = []
        self.cv_scores: List[float] = []

    # ── Training ──────────────────────────────────────────────────────────

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        early_stopping_rounds: int = 50,
    ) -> "EnsembleModel":
        """
        Train both models.

        early_stopping_rounds : If > 0 and the training set is large enough,
            a 20 % chronological hold-out is used as an eval set for early
            stopping. This is an additional anti-overfit guard on top of the
            regularisation parameters.  Set to 0 to disable.
        """
        self.feature_names = list(X.columns)
        pos = int(y.sum())
        neg = len(y) - pos
        spw = neg / max(pos, 1)

        # Chronological hold-out for early stopping (no data leakage).
        # Only applied when the training set is large enough (>500 rows)
        # so that the eval set is meaningful.
        use_early_stop = early_stopping_rounds > 0 and len(X) > 500
        if use_early_stop:
            split_idx = int(len(X) * 0.80)
            X_tr, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_tr, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        else:
            X_tr, X_val, y_tr, y_val = X, None, y, None

        # XGBoost
        xgb_p = {**self.xgb_params, "scale_pos_weight": spw}
        self.xgb = XGBClassifier(**xgb_p)
        if use_early_stop:
            self.xgb.set_params(early_stopping_rounds=early_stopping_rounds)
            self.xgb.fit(
                X_tr, y_tr,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )
        else:
            self.xgb.fit(X_tr, y_tr, verbose=False)

        # LightGBM
        lgbm_p = {**self.lgbm_params, "scale_pos_weight": spw}
        self.lgbm = LGBMClassifier(**lgbm_p)
        if use_early_stop:
            self.lgbm.set_params(
                early_stopping_rounds=early_stopping_rounds,
                n_estimators=self.lgbm_params.get("n_estimators", 600),
            )
            self.lgbm.fit(
                X_tr, y_tr,
                eval_set=[(X_val, y_val)],
                callbacks=[],
            )
        else:
            self.lgbm.fit(X_tr, y_tr)

        return self

    # ── Prediction ────────────────────────────────────────────────────────

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return weighted-average probability of class 1."""
        assert self.xgb is not None and self.lgbm is not None, "Not trained."
        Xf = X[self.feature_names]
        xgb_p = self.xgb.predict_proba(Xf)[:, 1]
        lgbm_p = self.lgbm.predict_proba(Xf)[:, 1]
        return self.xgb_weight * xgb_p + self.lgbm_weight * lgbm_p

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)

    # ── Evaluation ────────────────────────────────────────────────────────

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        proba = self.predict_proba(X)
        preds = (proba >= 0.5).astype(int)
        return {
            "accuracy": accuracy_score(y, preds),
            "roc_auc": roc_auc_score(y, proba) if len(set(y)) > 1 else 0.0,
            "log_loss": log_loss(y, proba),
        }

    def time_series_cv(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = TSCV_N_SPLITS,
    ) -> List[float]:
        """Time-series CV using the ensemble probability on validation folds."""
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores: List[float] = []
        pos = int(y.sum()); neg = len(y) - pos; spw = neg / max(pos, 1)

        for tr_idx, val_idx in tscv.split(X):
            X_tr, X_val = X.iloc[tr_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[tr_idx], y.iloc[val_idx]
            if len(set(y_val)) < 2:
                continue

            xp = {**self.xgb_params, "scale_pos_weight": spw}
            lp = {**self.lgbm_params, "scale_pos_weight": spw}
            xclf = XGBClassifier(**xp)
            lclf = LGBMClassifier(**lp)
            xclf.fit(X_tr, y_tr, verbose=False)
            lclf.fit(X_tr, y_tr)

            xgb_p = xclf.predict_proba(X_val)[:, 1]
            lgbm_p = lclf.predict_proba(X_val)[:, 1]
            prob = self.xgb_weight * xgb_p + self.lgbm_weight * lgbm_p
            scores.append(roc_auc_score(y_val, prob))

        self.cv_scores = scores
        return scores

    # ── Feature importance (XGB gain, averaged where possible) ───────────

    def feature_importance(self, top_n: int = 15) -> pd.DataFrame:
        assert self.xgb is not None
        imp = self.xgb.get_booster().get_score(importance_type="gain")
        df = (
            pd.DataFrame.from_dict(imp, orient="index", columns=["xgb_gain"])
            .sort_values("xgb_gain", ascending=False)
            .head(top_n)
        )
        df.index.name = "feature"
        return df

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, directory: Optional[Path] = None) -> Path:
        out_dir = directory or MODEL_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.xgb,  out_dir / f"{self.symbol}_xgb.joblib")
        joblib.dump(self.lgbm, out_dir / f"{self.symbol}_lgbm.joblib")

        meta = {
            "symbol": self.symbol,
            "feature_names": self.feature_names,
            "cv_scores": self.cv_scores,
            "xgb_weight": self.xgb_weight,
            "xgb_params": {k: v for k, v in self.xgb_params.items() if k != "n_jobs"},
            "lgbm_params": {k: v for k, v in self.lgbm_params.items() if k != "n_jobs"},
        }
        (out_dir / f"{self.symbol}_ensemble_meta.json").write_text(
            json.dumps(meta, indent=2)
        )
        return out_dir / f"{self.symbol}_xgb.joblib"

    @staticmethod
    def _model_path(symbol: str, directory: Optional[Path] = None) -> Path:
        """Return the expected XGBoost model path (used to check if a model exists)."""
        src_dir = directory or MODEL_DIR
        return src_dir / f"{symbol}_xgb.joblib"

    @classmethod
    def load(cls, symbol: str, directory: Optional[Path] = None) -> "EnsembleModel":
        src_dir = directory or MODEL_DIR
        xgb_path  = src_dir / f"{symbol}_xgb.joblib"
        lgbm_path = src_dir / f"{symbol}_lgbm.joblib"
        meta_path = src_dir / f"{symbol}_ensemble_meta.json"

        if not xgb_path.exists():
            raise FileNotFoundError(f"No saved model at {xgb_path}")

        instance = cls(symbol)
        instance.xgb  = joblib.load(xgb_path)
        if lgbm_path.exists():
            instance.lgbm = joblib.load(lgbm_path)
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            instance.feature_names = meta.get("feature_names", [])
            instance.cv_scores     = meta.get("cv_scores", [])
            instance.xgb_weight    = meta.get("xgb_weight", XGB_ENSEMBLE_WEIGHT)
            instance.lgbm_weight   = 1.0 - instance.xgb_weight
        return instance
