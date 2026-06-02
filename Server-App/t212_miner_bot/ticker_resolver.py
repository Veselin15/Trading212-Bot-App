"""
Yahoo Finance → Trading 212 Ticker Resolver
============================================

T212 uses its own internal ticker symbols (e.g. "ASMLa_EQ") that differ
from Yahoo Finance symbols (e.g. "ASML.AS").  This module resolves the
mapping by fetching the full instrument list from T212 at startup and
matching against known patterns and a manual override table.

Resolution strategy (in order):
  1. Manual override table  MANUAL_T212_MAP  (fastest, most reliable)
  2. ISIN lookup             match against KNOWN_ISINS dict
  3. Short-name fuzzy match  "ASML" appears in T212 shortName or ticker
  4. Skip + warn             symbol is traded on an exchange T212 doesn't support

The resolved mapping is cached in memory for the session lifetime.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

log = logging.getLogger(__name__)

# ── Manual overrides ────────────────────────────────────────────────────────
# Confirmed T212 tickers for our 25-symbol universe.
# Format: "yahoo_symbol": "t212_ticker"
# These are the most reliable entries – fill in / correct after running
# `python -m t212_miner_bot.ticker_resolver --dump` to see the live list.
MANUAL_T212_MAP: Dict[str, str] = {
    # ── Amsterdam (Euronext, suffix 'a_EQ') ──────────────────────────────
    "ADYEN.AS":  "ADYENa_EQ",
    "ASML.AS":   "ASMLa_EQ",    # confirmed from live state.json
    "PRX.AS":    "PRXa_EQ",
    # ── Paris (Euronext, suffix 'p_EQ') ──────────────────────────────────
    "AIR.PA":    "AIp_EQ",
    "DSY.PA":    "DSYp_EQ",
    "EL.PA":     "ELp_EQ",
    "ENR.DE":    "ENRl_EQ",     # NOTE: ENR trades on Xetra (Frankfurt)
    "HO.PA":     "HOp_EQ",
    "KER.PA":    "KERp_EQ",
    "MC.PA":     "MCp_EQ",
    "OR.PA":     "ORp_EQ",
    "RMS.PA":    "RMSp_EQ",
    "SAF.PA":    "SAFp_EQ",
    "SAN.PA":    "SANp_EQ",
    "STMPA.PA":  "STMPAp_EQ",
    "TTE.PA":    "TTEp_EQ",
    # ── Frankfurt / Xetra (suffix 'l_EQ') ────────────────────────────────
    "ALV.DE":    "ALVl_EQ",
    "BAYN.DE":   "BAYNl_EQ",
    "DBK.DE":    "DBKl_EQ",
    "IFX.DE":    "IFXl_EQ",
    "RHM.DE":    "RHMl_EQ",
    "SAP.DE":    "SAPl_EQ",
    "SIE.DE":    "SIEl_EQ",
    "VOW3.DE":   "VOW3l_EQ",
    # ── Swiss (SIX, suffix 's_EQ') ────────────────────────────────────────
    "ROG.SW":    "ROGs_EQ",
}

# ── Known ISINs for auto-resolution fallback ───────────────────────────────
# Only needed for symbols NOT in MANUAL_T212_MAP.  Extend as needed.
KNOWN_ISINS: Dict[str, str] = {
    "ASML.AS":   "NL0010273215",
    "ADYEN.AS":  "NL0012969182",
    "MC.PA":     "FR0000121014",
    "RMS.PA":    "FR0000052292",
    "RHM.DE":    "DE0007030009",
    "AIR.PA":    "NL0000235190",
    "ALV.DE":    "DE0008404005",
    "SIE.DE":    "DE0007236101",
    "TTE.PA":    "FR0014000MR3",
    "SAP.DE":    "DE0007164600",
    "IFX.DE":    "DE0006231004",
    "ENR.DE":    "DE000ENER6Y0",
    "ROG.SW":    "CH0012221716",
    "KER.PA":    "FR0000121485",
    "OR.PA":     "FR0000120321",
    "EL.PA":     "FR0000121667",
    "DSY.PA":    "FR0000130650",
    "STMPA.PA":  "NL0000226223",
    "SAN.PA":    "FR0000120578",
    "BAYN.DE":   "DE000BAY0017",
    "DBK.DE":    "DE0005140008",
    "PRX.AS":    "NL0013654783",
    "VOW3.DE":   "DE0007664039",
    "HO.PA":     "FR0000120271",
    "SAF.PA":    "FR0000073272",
}


class TickerResolver:
    """
    Resolves Yahoo Finance symbols to T212 instrument tickers.

    Usage
    -----
        resolver = TickerResolver(client)
        resolver.build()                          # fetches instruments once
        t212_ticker = resolver.resolve("ASML.AS") # returns "ASMLa_EQ"
    """

    def __init__(self, client=None) -> None:
        """
        Parameters
        ----------
        client : T212Client instance (optional).
                 When None, only manual overrides are available.
        """
        self._client   = client
        self._map: Dict[str, str] = {}
        self._instruments: list   = []
        self._isin_index: Dict[str, str] = {}   # isin → t212_ticker
        self._name_index: Dict[str, str] = {}   # lowered_short_name → t212_ticker
        self._ticker_set: set[str] = set()      # known valid tickers from instruments

    def build(self) -> None:
        """
        Fetch instruments from T212 and build the resolution index.
        Call once at startup.
        """
        # We'll validate manual overrides against the live instruments list when available.
        manual = dict(MANUAL_T212_MAP)

        if self._client is None:
            log.info("TickerResolver: no T212 client – using manual overrides only (%d entries)",
                     len(self._map))
            return

        try:
            log.info("TickerResolver: fetching instrument list from T212…")
            self._instruments = self._client.get_instruments()
            log.info("  Retrieved %d instruments", len(self._instruments))

            # Build secondary indexes for auto-resolution
            for inst in self._instruments:
                ticker    = inst.get("ticker", "")
                isin      = inst.get("isin", "")
                short_name = inst.get("shortName", "")
                if ticker:
                    self._ticker_set.add(str(ticker))
                if isin:
                    self._isin_index[isin.upper()] = ticker
                if short_name:
                    self._name_index[short_name.upper()] = ticker

        except Exception as exc:
            log.warning("TickerResolver: instrument fetch failed (%s) – manual overrides only", exc)
            # No live validation possible; fall back to manual table as-is.
            self._map.update(manual)
            return

        # Validate manual overrides against live tickers, drop stale ones.
        kept = 0
        dropped: list[str] = []
        for ysym, tticker in manual.items():
            if tticker in self._ticker_set:
                self._map[ysym] = tticker
                kept += 1
            else:
                dropped.append(f"{ysym}->{tticker}")
        if dropped:
            log.warning("TickerResolver: dropped stale manual tickers: %s", dropped)

        log.info("TickerResolver: %d symbols mapped, %d ISINs indexed",
                 len(self._map), len(self._isin_index))

    def resolve(self, yahoo_symbol: str) -> Optional[str]:
        """
        Return the T212 ticker for a Yahoo Finance symbol, or None if not found.
        """
        # 1. Manual override (most reliable)
        if yahoo_symbol in self._map:
            return self._map[yahoo_symbol]

        # 2. ISIN lookup
        isin = KNOWN_ISINS.get(yahoo_symbol, "")
        if isin and isin.upper() in self._isin_index:
            t = self._isin_index[isin.upper()]
            log.debug("  ISIN match  %s → %s", yahoo_symbol, t)
            self._map[yahoo_symbol] = t   # cache for next call
            return t

        # 3. Short-name fuzzy match: strip exchange suffix from Yahoo symbol
        base_name = re.split(r"[._]", yahoo_symbol)[0].upper()
        if base_name in self._name_index:
            t = self._name_index[base_name]
            log.debug("  Name match  %s → %s", yahoo_symbol, t)
            self._map[yahoo_symbol] = t
            return t

        log.warning("TickerResolver: cannot resolve %s → T212 ticker (add to MANUAL_T212_MAP)",
                    yahoo_symbol)
        return None

    def resolve_all(self, yahoo_symbols: list) -> Dict[str, str]:
        """
        Resolve a list of Yahoo symbols. Returns {yahoo: t212} for resolved ones only.
        Logs a warning for each unresolved symbol.
        """
        result: Dict[str, str] = {}
        for sym in yahoo_symbols:
            t = self.resolve(sym)
            if t:
                result[sym] = t
        resolved = len(result)
        total    = len(yahoo_symbols)
        log.info("Ticker resolution: %d / %d symbols resolved", resolved, total)
        if resolved < total:
            missing = [s for s in yahoo_symbols if s not in result]
            log.warning("  Unresolved symbols: %s", missing)
        return result

    def dump(self) -> None:
        """Print all resolved mappings (useful for verifying / filling gaps)."""
        print("\n  Current Yahoo → T212 ticker map:")
        print("  " + "-" * 48)
        for y, t in sorted(self._map.items()):
            src = "manual" if y in MANUAL_T212_MAP else "auto  "
            print(f"  [{src}]  {y:<14} → {t}")
        print()


# ── CLI utility ─────────────────────────────────────────────────────────────

def main() -> None:
    """
    Run as:  python -m t212_miner_bot.ticker_resolver [--dump]

    Connects to T212 (requires T212_API_KEY), resolves all 25 EU symbols,
    and prints the mapping table so you can verify / correct entries.
    """
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    from t212_miner_bot.config import EU_SYMBOLS
    from t212_miner_bot.t212_client import T212Client

    with T212Client() as client:
        resolver = TickerResolver(client)
        resolver.build()
        resolver.resolve_all(EU_SYMBOLS)
        resolver.dump()


if __name__ == "__main__":
    main()
