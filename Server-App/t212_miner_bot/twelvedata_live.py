"""
Twelve Data live intraday fetcher (fallback for flaky Yahoo symbols)
===================================================================

This module is used ONLY as a data-source fallback when yfinance fails to
deliver intraday candles for a symbol (common for some SIX Swiss tickers).

It does not change strategy logic; it only improves data reliability.

Env vars
--------
  TWELVEDATA_API_KEY   required to enable this fallback
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

# datetime.UTC was added in Python 3.11; fall back to timezone.utc on 3.8-3.10
try:
    from datetime import UTC  # type: ignore
except ImportError:  # pragma: no cover
    UTC = timezone.utc

import pandas as pd
import requests

_SUFFIX_TO_MIC = {
    ".SW": "XSWX",  # SIX Swiss Exchange
    ".DE": "XETR",  # XETRA
    ".PA": "XPAR",  # Euronext Paris
    ".AS": "XAMS",  # Euronext Amsterdam
}

_SUFFIX_NAME_HINTS: dict[str, tuple[str, ...]] = {
    ".SW": ("roche",),
}


@dataclass(frozen=True)
class TwelveDataConfig:
    api_key: str
    base_url: str = "https://api.twelvedata.com"


class MinuteCreditBudget:
    """Simple rolling-minute pacing (best-effort) for TwelveData free tiers."""

    def __init__(self, credits_per_minute: int = 8) -> None:
        self.credits_per_minute = max(int(credits_per_minute), 1)
        self._minute_index: int | None = None
        self._used_in_minute = 0

    def acquire(self, credits: int = 1) -> None:
        need = max(int(credits), 1)
        while True:
            now = time.time()
            minute_index = int(now // 60)
            if self._minute_index != minute_index:
                self._minute_index = minute_index
                self._used_in_minute = 0
            if self._used_in_minute + need <= self.credits_per_minute:
                self._used_in_minute += need
                return
            time.sleep(max(0.2, (minute_index + 1) * 60 - now))


def _config() -> Optional[TwelveDataConfig]:
    api_key = os.getenv("TWELVEDATA_API_KEY", "").strip()
    if not api_key:
        return None
    return TwelveDataConfig(api_key=api_key)


def _request_json(
    cfg: TwelveDataConfig,
    path: str,
    params: dict[str, Any],
    *,
    budget: MinuteCreditBudget,
    max_retries: int = 6,
) -> dict[str, Any]:
    url = f"{cfg.base_url}{path}"
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        budget.acquire(credits=1)
        try:
            resp = requests.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(min(30.0, 1.5**attempt))
            continue
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            sleep_s = float(retry_after) if retry_after else min(20.0, 2.0 * attempt)
            time.sleep(max(1.0, sleep_s))
            continue
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("status") == "error":
            raise RuntimeError(f"TwelveData error: {data.get('code')} {data.get('message')}")
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected TwelveData response type: {type(data)}")
        return data
    raise RuntimeError(f"TwelveData request failed: {last_exc}") from last_exc


def _resolve_instrument(
    cfg: TwelveDataConfig,
    requested: str,
    *,
    budget: MinuteCreditBudget,
) -> dict[str, str]:
    """
    Resolve a Yahoo-style symbol (e.g. ROG.SW) to a venue-qualified instrument
    using /symbol_search. Returns a dict containing symbol + mic_code (+ figi when available).
    """
    req = str(requested).strip().upper()
    root = req.split(".")[0]
    suffix = ""
    if "." in req:
        _, suffix = req.rsplit(".", 1)
        suffix = f".{suffix}"
    data = _request_json(
        cfg,
        "/symbol_search",
        {"symbol": root, "outputsize": 120, "apikey": cfg.api_key},
        budget=budget,
    )
    rows = data.get("data")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"No TwelveData matches for {requested}")

    preferred_mic = _SUFFIX_TO_MIC.get(suffix, "")
    name_hints = _SUFFIX_NAME_HINTS.get(suffix, ())

    def _score(r: dict[str, Any]) -> tuple[int, int, int]:
        sym = str(r.get("symbol") or "").strip().upper()
        mic = str(r.get("mic_code") or "").strip().upper()
        nm = str(r.get("instrument_name") or r.get("name") or "").strip().lower()
        exact = 1 if sym == req else 0
        mic_ok = 1 if (preferred_mic and mic == preferred_mic) else 0
        hint_ok = 1 if (name_hints and any(h in nm for h in name_hints)) else 0
        return (exact, mic_ok, hint_ok)

    candidates = [r for r in rows if isinstance(r, dict)]
    if not candidates:
        raise RuntimeError(f"No usable TwelveData rows for {requested}")
    best = max(candidates, key=_score)

    out: dict[str, str] = {}
    for k in ("symbol", "figi_code", "mic_code", "exchange", "country", "instrument_name", "name"):
        v = best.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()
    if not out.get("symbol") and not out.get("figi_code"):
        raise RuntimeError(f"Could not resolve instrument for {requested}")
    return out


def _time_series_params(instrument: dict[str, str]) -> dict[str, str]:
    params: dict[str, str] = {}
    if instrument.get("symbol"):
        params["symbol"] = instrument["symbol"]
    if instrument.get("mic_code"):
        params["mic_code"] = instrument["mic_code"]
    if not params.get("symbol") and instrument.get("figi_code"):
        params["figi"] = instrument["figi_code"]
    if not params.get("symbol") and not params.get("figi"):
        raise RuntimeError(f"No usable TwelveData identifier: {instrument}")
    return params


def fetch_intraday(
    yahoo_symbol: str,
    *,
    interval_min: int,
    outputsize: int = 5000,
    credits_per_minute: int = 8,
) -> Optional[pd.DataFrame]:
    """
    Fetch recent intraday candles for the given symbol at interval_min (5 or 15).

    Returns a DataFrame indexed by UTC timestamp with columns:
      open, high, low, close, volume
    """
    cfg = _config()
    if cfg is None:
        return None
    budget = MinuteCreditBudget(credits_per_minute=credits_per_minute)
    instrument = _resolve_instrument(cfg, yahoo_symbol, budget=budget)
    ident = _time_series_params(instrument)
    interval = f"{int(interval_min)}min"

    data = _request_json(
        cfg,
        "/time_series",
        {
            **ident,
            "interval": interval,
            "end_date": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S"),
            "timezone": "UTC",
            "order": "desc",
            "outputsize": int(outputsize),
            "apikey": cfg.api_key,
        },
        budget=budget,
    )
    values = data.get("values")
    if not isinstance(values, list) or not values:
        return None

    df = pd.DataFrame(values)
    dt_col = "datetime" if "datetime" in df.columns else ("date" if "date" in df.columns else None)
    if dt_col is None:
        return None
    df = df.rename(columns={dt_col: "timestamp"})
    keep = ["timestamp", "open", "high", "low", "close", "volume"]
    for c in keep:
        if c not in df.columns:
            df[c] = None
    df = df[keep].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    if df.empty:
        return None
    out = df.set_index("timestamp")[["open", "high", "low", "close", "volume"]].copy()
    out.index = out.index.tz_convert("UTC")
    return out

