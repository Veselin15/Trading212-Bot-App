"""
Probabilistic Regime Detection via Gaussian Mixture Model  (idea #1)
=====================================================================

Replaces the bot's binary EMA200-breadth regime flag with an unsupervised
Gaussian Mixture Model that classifies the EU universe into hidden states
(e.g. low-vol drift, high-vol mean-reversion, crash) and outputs a *smooth,
probabilistic* risk multiplier per bar.

Why GMM over HMM here
---------------------
HMM (hmmlearn) is not available in this environment, and for risk *scaling*
a GMM is actually preferable: we want the posterior probability of each state
at the current bar (a soft membership) to blend risk continuously, rather than
a hard Viterbi-decoded path.  The GMM is fit purely unsupervised on market-
state features — no labels, no look-ahead.

Pipeline
--------
1. compute_market_features(): cross-sectional aggregates over the universe at
   each timestamp — breadth, volatility level, return dispersion, momentum,
   trend strength.  These describe the *market*, not any single stock.
2. fit(): fit a K-state GMM on the TRAINING slice of those features, then map
   each learned state to a risk multiplier by measuring the universe's average
   forward return while in that state (train data only).  Profitable, calm
   states → size up; volatile, negative states → size down.
3. risk_multiplier_series(): posterior-weighted blend of per-state risk
   scalars → one smooth multiplier per bar, ready to feed the engine.

No OOS data is ever used for fitting or state→risk mapping.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MARKET_FEATURES = ["breadth", "avg_atr_pct", "dispersion", "avg_roc20", "avg_trend"]


def compute_market_features(all_dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build a per-timestamp market-state feature matrix from the universe.

    Columns:
      breadth      fraction of symbols with close > EMA200      (trend participation)
      avg_atr_pct  mean ATR% across symbols                     (volatility level)
      dispersion   cross-sectional std of 1-day returns         (idiosyncratic spread)
      avg_roc20    mean 20-bar rate-of-change                   (momentum)
      avg_trend    mean (EMA50-EMA200)/EMA200                   (trend strength)
    """
    breadth, atr_pct, roc20, trend = [], [], [], []
    ret_frames = []

    for sym, df in all_dfs.items():
        if "ema_200" in df.columns:
            breadth.append((df["close"] >= df["ema_200"]).astype(float).rename(sym))
        if "atr_pct" in df.columns:
            atr_pct.append(df["atr_pct"].rename(sym))
        if "roc_20" in df.columns:
            roc20.append(df["roc_20"].rename(sym))
        if "trend_50_200" in df.columns:
            trend.append(df["trend_50_200"].rename(sym))
        if "ret_1d" in df.columns:
            ret_frames.append(df["ret_1d"].rename(sym))

    def _mean(frames):
        if not frames:
            return None
        return pd.concat(frames, axis=1).mean(axis=1)

    feats = pd.DataFrame({
        "breadth":     _mean(breadth),
        "avg_atr_pct": _mean(atr_pct),
        "avg_roc20":   _mean(roc20),
        "avg_trend":   _mean(trend),
    })
    if ret_frames:
        feats["dispersion"] = pd.concat(ret_frames, axis=1).std(axis=1)
    else:
        feats["dispersion"] = 0.0

    feats = feats[MARKET_FEATURES].replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)
    return feats


def universe_forward_return(all_dfs: Dict[str, pd.DataFrame], horizon: int = 15) -> pd.Series:
    """Equal-weight universe forward return over `horizon` bars (for state mapping)."""
    frs = []
    for sym, df in all_dfs.items():
        fr = (df["close"].shift(-horizon) / df["close"] - 1.0).rename(sym)
        frs.append(fr)
    return pd.concat(frs, axis=1).mean(axis=1)


class GMMRegimeModel:
    """Unsupervised market-regime classifier driving a smooth risk multiplier."""

    def __init__(
        self,
        n_states: int = 4,
        min_risk: float = 0.6,
        max_risk: float = 4.2,
        random_state: int = 42,
    ):
        self.n_states   = n_states
        self.min_risk   = min_risk
        self.max_risk   = max_risk
        self.random_state = random_state
        self.scaler: Optional[StandardScaler] = None
        self.gmm: Optional[GaussianMixture] = None
        self.state_risk: Dict[int, float] = {}   # state index → risk multiplier
        self.state_fwd_ret: Dict[int, float] = {} # diagnostics

    def fit(self, market_feats: pd.DataFrame, fwd_ret: pd.Series) -> "GMMRegimeModel":
        """Fit GMM on market features; map each state to a risk multiplier."""
        X = market_feats[MARKET_FEATURES].values
        self.scaler = StandardScaler().fit(X)
        Xs = self.scaler.transform(X)

        self.gmm = GaussianMixture(
            n_components=self.n_states,
            covariance_type="full",
            random_state=self.random_state,
            max_iter=200,
            n_init=3,
        ).fit(Xs)

        states = self.gmm.predict(Xs)
        fr = fwd_ret.reindex(market_feats.index)

        # Average forward return per state (train data) → ranking
        for st in range(self.n_states):
            mask = states == st
            self.state_fwd_ret[st] = float(np.nanmean(fr[mask])) if mask.any() else 0.0

        # Map states to risk by forward-return rank: best → max_risk, worst → min_risk
        ordered = sorted(self.state_fwd_ret, key=lambda s: self.state_fwd_ret[s])
        if self.n_states == 1:
            self.state_risk = {ordered[0]: (self.min_risk + self.max_risk) / 2}
        else:
            for rank, st in enumerate(ordered):
                t = rank / (self.n_states - 1)            # 0 (worst) → 1 (best)
                self.state_risk[st] = self.min_risk + t * (self.max_risk - self.min_risk)

        logger.info("GMM states (fwd_ret → risk): %s",
                    {st: (round(self.state_fwd_ret[st], 5), round(self.state_risk[st], 2))
                     for st in range(self.n_states)})
        return self

    def risk_multiplier_series(self, market_feats: pd.DataFrame) -> pd.Series:
        """Posterior-weighted risk multiplier per bar (smooth blend across states)."""
        assert self.gmm is not None and self.scaler is not None, "Not fitted."
        Xs = self.scaler.transform(market_feats[MARKET_FEATURES].values)
        proba = self.gmm.predict_proba(Xs)                # (n_bars, n_states)
        risk_vec = np.array([self.state_risk[s] for s in range(self.n_states)])
        blended = proba @ risk_vec                        # weighted average
        return pd.Series(blended, index=market_feats.index, name="regime_risk")

    def state_series(self, market_feats: pd.DataFrame) -> pd.Series:
        """Hard-assigned state per bar (for diagnostics)."""
        Xs = self.scaler.transform(market_feats[MARKET_FEATURES].values)
        return pd.Series(self.gmm.predict(Xs), index=market_feats.index, name="regime_state")
