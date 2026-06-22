"""
Cross-sectional momentum strategy + owner-account executor.
==========================================================

This is the validated replacement for the old ML swing engine.  It holds the
top-K strongest global stocks (equal-weight) when the market regime is risk-on,
and CASH when it is risk-off; rebalanced MONTHLY.  Long-only.

Validated over a 14-year walk-forward (fixed params, after costs):
    GROWTH: +27.7%/yr, Sharpe 1.19, worst calendar year -5.6%, max DD ~-24%.

Used by `backend/app/strategy/owner_executor.py` to trade the owner's T212
account (paper or live — controlled purely by which T212 API key / base URL is
configured; the strategy code is identical for both).

Data: DAILY bars from Twelve Data (TWELVEDATA_API_KEY).  Signal logic is the same
math as the AI-Trading backtest (`momentum_global.live_target_weights`).
"""
from __future__ import annotations

import json
import logging
import os
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter

_log = logging.getLogger("uvicorn.error")

# ── Universe (diversified global large-caps) ─────────────────────────────────
US = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "AMD", "NFLX",
    "CRM", "ADBE", "ORCL", "CSCO", "QCOM", "TXN", "INTC", "IBM", "NOW", "AMAT", "MU",
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP", "BLK", "SPGI",
    "UNH", "LLY", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "AMGN",
    "XOM", "CVX", "COP", "SLB",
    "HD", "WMT", "COST", "PG", "KO", "PEP", "MCD", "NKE", "SBUX", "DIS", "LOW",
    "CAT", "DE", "GE", "BA", "HON", "LMT", "UPS", "RTX", "LIN", "UNP",
]
EU = [
    "ADYEN.AS", "ASML.AS", "PRX.AS",
    "MC.PA", "AIR.PA", "RMS.PA", "TTE.PA", "HO.PA", "SAF.PA", "KER.PA",
    "OR.PA", "EL.PA", "DSY.PA", "STMPA.PA", "SAN.PA",
    "ALV.DE", "ENR.DE", "IFX.DE", "RHM.DE", "SIE.DE", "SAP.DE",
    "BAYN.DE", "DBK.DE", "VOW3.DE",
]
UK = ["SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "GSK.L"]
UNIVERSE = US + EU + UK

SUFFIX_TO_MIC = {"AS": "XAMS", "PA": "XPAR", "DE": "XETR",
                 "L": "XLON", "SW": "XSWX", "MI": "XMIL"}

# ── Deployed config: GROWTH (chosen profile) ────────────────────────────────
@dataclass
class MomentumParams:
    lookback: int = 189          # momentum window (trading days)
    skip: int = 5                # skip most-recent days
    top_k: int = 8
    regime_sma: int = 100        # basket-index SMA for risk-on/off
    total_exposure: float = 0.98 # keep a small cash buffer
    min_order_eur: float = 5.0


PROD = MomentumParams()

# ── Tunables (env-overridable) ──────────────────────────────────────────────
TD_BASE = "https://api.twelvedata.com/time_series"
FETCH_YEARS = 1.6
_TD_SLEEP = float(os.getenv("TD_SLEEP_S", "1.2"))   # paid Grow55 plan ~55/min


# ── TwelveData daily fetch (system cert store for corporate CAs) ─────────────
class _SystemCertAdapter(HTTPAdapter):
    def init_poolmanager(self, *a, **k):
        k["ssl_context"] = ssl.create_default_context()
        return super().init_poolmanager(*a, **k)


def _session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", _SystemCertAdapter())
    return s


def _route(symbol: str) -> dict:
    if "." in symbol:
        ticker, suffix = symbol.rsplit(".", 1)
        mic = SUFFIX_TO_MIC.get(suffix)
        if not mic:
            return {"symbol": symbol}
        return {"symbol": ticker, "mic_code": mic}
    return {"symbol": symbol}


def _fetch_daily(sess, key: str, symbol: str, years: float) -> pd.Series:
    params = {**_route(symbol), "interval": "1day", "outputsize": 5000,
              "timezone": "UTC", "order": "ASC", "format": "JSON", "apikey": key}
    for attempt in range(1, 4):
        try:
            r = sess.get(TD_BASE, params=params, timeout=30)
            r.raise_for_status()
            j = r.json()
        except Exception as exc:
            _log.debug("  [%s] TD fetch retry %d: %s", symbol, attempt, str(exc)[:60])
            time.sleep(_TD_SLEEP * attempt)
            continue
        finally:
            time.sleep(_TD_SLEEP)
        if isinstance(j, dict) and j.get("status") == "error":
            if j.get("code") == 429:
                time.sleep(5); continue
            return pd.Series(dtype=float)
        vals = j.get("values") if isinstance(j, dict) else None
        if not vals:
            return pd.Series(dtype=float)
        df = pd.DataFrame(vals)
        idx = pd.to_datetime(df["datetime"], utc=True)
        s = pd.to_numeric(df["close"], errors="coerce")
        s.index = idx
        s = s[~s.index.duplicated(keep="last")].sort_index()
        cutoff = s.index.max() - pd.Timedelta(days=int(years * 365.25))
        return s.loc[s.index >= cutoff]
    return pd.Series(dtype=float)


def fetch_universe_closes(years: float = FETCH_YEARS) -> pd.DataFrame:
    key = os.getenv("TWELVEDATA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("TWELVEDATA_API_KEY not set — momentum strategy needs daily data.")
    sess = _session()
    cols = {}
    for sym in UNIVERSE:
        s = _fetch_daily(sess, key, sym, years)
        if len(s) > 200:
            cols[sym] = s
    closes = pd.DataFrame(cols).sort_index()
    return closes[~closes.index.duplicated(keep="last")]


# ── Signal: identical math to the AI-Trading backtest ───────────────────────
def target_weights(closes: pd.DataFrame, p: MomentumParams = PROD) -> pd.Series:
    """Latest-bar target weights (equal-weight top-K momentum, or empty = cash)."""
    stocks = list(closes.columns)
    rets = closes.pct_change()
    basket = (1 + rets.mean(axis=1).fillna(0)).cumprod()
    bsma = basket.rolling(p.regime_sma).mean()
    i = len(closes) - 1
    if i < p.lookback + p.skip:
        return pd.Series(dtype=float)
    on = bool(basket.iloc[i] > bsma.iloc[i]) if not np.isnan(bsma.iloc[i]) else False
    if not on:
        return pd.Series(dtype=float)   # risk-off → cash
    score = closes.iloc[i - p.skip] / closes.iloc[i - p.lookback - p.skip] - 1.0
    sma = closes.iloc[max(0, i - p.lookback):i + 1].mean()
    cand = score[(score > 0) & (closes.iloc[i] > sma)]
    top = cand.sort_values(ascending=False).head(p.top_k)
    if not len(top):
        return pd.Series(dtype=float)
    return pd.Series(1.0 / len(top), index=top.index)


# ── Owner-account executor (monthly rebalance) ──────────────────────────────
# Store state under models/ — that subdir is the persisted Docker volume
# (swifttrade_bot_state), so the monthly gate survives container restarts and the
# bot doesn't re-trade on every redeploy.
STATE_PATH = Path(__file__).resolve().parent / "models" / "momentum_owner_state.json"


def _place_with_precision(client, t212: str, qty: float):
    """Place a market order, retrying with fewer decimals on T212's
    'quantity-precision-mismatch' (each instrument allows a different precision,
    and T212 does not expose it in metadata).  Returns the quantity actually sent."""
    last_exc = None
    for dp in (4, 2, 1, 0):
        q = float(int(qty)) if dp == 0 else round(qty, dp)
        if q == 0:
            continue
        try:
            client.place_market_order(t212, quantity=q)
            return q
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if "precision" in str(exc).lower():
                continue          # too many decimals for this instrument → coarsen
            raise
    if last_exc is not None:
        raise last_exc
    return 0.0


class MomentumExecutor:
    """Rebalances the configured T212 account to the momentum target, monthly.

    Trades whatever account T212_API_KEY / T212_BASE_URL point to (the owner
    executor injects the owner creds before constructing this).  Paper vs live is
    purely a function of those env vars — no code change needed to go live.
    """

    def __init__(self, p: MomentumParams = PROD, dry_run: bool = False) -> None:
        from t212_miner_bot.t212_client import T212Client
        from t212_miner_bot.ticker_resolver import TickerResolver
        self.p = p
        self.dry_run = dry_run
        self.client = T212Client()
        self.resolver = TickerResolver(self.client)
        self._built = False

    def _load_state(self) -> dict:
        if STATE_PATH.exists():
            try:
                return json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_state(self, state: dict) -> None:
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as exc:
            _log.warning("momentum state save failed: %s", exc)

    def maybe_rebalance(self, force: bool = False) -> dict:
        """Rebalance once per calendar month. Returns a small result dict for logging."""
        state = self._load_state()
        month = datetime.now(tz=timezone.utc).strftime("%Y-%m")
        if state.get("last_rebalance_month") == month and not force:
            _log.info("momentum: already rebalanced for %s — holding.", month)
            return {"action": "hold", "month": month}

        _log.info("momentum: rebalancing for %s …", month)
        closes = fetch_universe_closes()
        if closes.empty:
            _log.warning("momentum: no price data fetched — skipping rebalance.")
            return {"action": "skip_no_data"}
        tgt_w = target_weights(closes, self.p)
        px = closes.iloc[-1]
        if len(tgt_w) == 0:
            _log.info("momentum: regime RISK-OFF → target is CASH (sell all).")
        else:
            _log.info("momentum: target top-%d: %s", self.p.top_k,
                      ", ".join(f"{s} {w*100:.1f}%" for s, w in tgt_w.items()))

        # Broker state
        if not self._built:
            self.resolver.build()
            self._built = True
        # Free cash blocked by stale pending orders (e.g. left by a prior strategy)
        # so the full balance is available to rebalance.
        if not self.dry_run:
            try:
                pending = self.client.get_orders() or []
                for o in pending:
                    oid = o.get("id")
                    if oid is not None:
                        try:
                            self.client.cancel_order(oid)
                        except Exception:  # noqa: BLE001
                            pass
                if pending:
                    _log.info("momentum: cancelled %d stale pending order(s) to free cash", len(pending))
                    time.sleep(3)
            except Exception as exc:  # noqa: BLE001
                _log.warning("momentum: pending-order cleanup failed: %s", exc)
        cash = self.client.get_cash()
        equity = float(cash.get("total", 0.0))
        investable = equity * self.p.total_exposure
        ticker_map = self.resolver.resolve_all(list(closes.columns))      # yahoo → T212
        t212_to_sym = {t: s for s, t in ticker_map.items()}
        portfolio = {p["ticker"]: float(p.get("quantity", p.get("currentQuantity", 0)) or 0)
                     for p in self.client.get_portfolio()}

        free = float(cash.get("free", 0.0))
        invested = float(cash.get("invested", 0.0))
        _log.info("momentum: equity=%.2f free=%.2f invested=%.2f", equity, free, invested)

        # Target share map (sized on TOTAL equity — sells fund the buys)
        target_shares: Dict[str, float] = {}
        for sym, w in tgt_w.items():
            t212 = ticker_map.get(sym)
            price = float(px.get(sym, 0))
            if t212 and price > 0:
                target_shares[sym] = investable * w / price

        held = {t212_to_sym.get(t, t): (t, q) for t, q in portfolio.items() if q > 0}
        if held:
            _log.info("momentum: holdings %s", {s: round(q, 4) for s, (t, q) in held.items()})

        placed = 0

        # ── SELLS first: fully exit non-targets, trim over-weight targets ──────
        sells = []
        for sym, (t212, q) in held.items():
            tgt = target_shares.get(sym)
            if tgt is None:
                sells.append((sym, t212, q))                              # exit fully
            elif (q - tgt) * float(px.get(sym, 0)) >= self.p.min_order_eur:
                sells.append((sym, ticker_map.get(sym, t212), q - tgt))   # trim
        for sym, t212, q in sells:
            if self.dry_run:
                _log.info("  [DRY] SELL %s %.4f (~€%.0f)", sym, q, q * float(px.get(sym, 0)))
                continue
            try:
                _place_with_precision(self.client, t212, -abs(q))
                placed += 1
                _log.info("  SELL %s %.4f", sym, q)
            except Exception as exc:  # noqa: BLE001
                _log.error("  momentum SELL FAILED %s: %s", sym, exc)

        # Let sells settle, then re-read the free-cash budget for buys
        if sells and not self.dry_run:
            time.sleep(5)
            try:
                free = float(self.client.get_cash().get("free", free))
            except Exception:  # noqa: BLE001
                pass

        # ── BUYS: cash-aware (never exceed free cash), precision-tolerant ─────
        # Leave a small margin: T212 fills at the ASK (slightly above our close
        # price), so a buy sized to 100% of free cash gets rejected at the limit.
        CASH_BUFFER = 0.985
        free_budget = investable if self.dry_run else free * CASH_BUFFER
        for sym, tgt in target_shares.items():
            price = float(px.get(sym, 0))
            cur = portfolio.get(ticker_map[sym], 0.0)
            delta = tgt - cur
            if delta * price < self.p.min_order_eur:
                continue
            cost = delta * price
            if cost > free_budget:                       # scale to fit remaining cash
                delta = free_budget / price if price > 0 else 0.0
                cost = delta * price
            if delta <= 0 or cost < self.p.min_order_eur:
                _log.info("  skip BUY %s — only €%.0f free left", sym, free_budget)
                continue
            if self.dry_run:
                _log.info("  [DRY] BUY %s %.4f (~€%.0f)", sym, delta, cost)
                free_budget -= cost
                continue
            try:
                _place_with_precision(self.client, ticker_map[sym], delta)
                placed += 1
                free_budget -= cost
                _log.info("  BUY %s %.4f (~€%.0f)", sym, delta, cost)
            except Exception as exc:  # noqa: BLE001
                _log.error("  momentum BUY FAILED %s: %s", sym, exc)

        if not self.dry_run:
            state["last_rebalance_month"] = month
            state["last_rebalance_at"] = datetime.now(tz=timezone.utc).isoformat()
            state["target"] = target_shares
            self._save_state(state)
        return {"action": "rebalanced", "month": month, "targets": list(target_shares),
                "orders": placed if not self.dry_run else len(orders)}
