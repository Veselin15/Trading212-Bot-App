"""Shared tier-capability model for the FastAPI backend.

Mirrors ``web/src/lib/tier.ts`` and ``public.effective_tier`` in SQL. Tiers are
lowercase strings on the wire (``pro``/``starter``/``trial``/``expired``/``invalid``).

The headline Pro-vs-Starter difference is the **signal feed breadth**, enforced
server-side: every broadcast signal carries a minimum tier, and the WebSocket
manager only delivers a signal to a connection whose ``signal_level`` is high
enough. Starter therefore physically never receives the Pro-only "extended" feed.
"""
from __future__ import annotations

from dataclasses import dataclass

# Minimum signal level a connection must have to receive a signal.
#   1 = "core"     (highest-confidence picks) — Starter, Pro and Trial all receive these.
#   2 = "extended" (additional opportunities) — Pro and Trial only.
SIGNAL_LEVEL_CORE = 1
SIGNAL_LEVEL_EXTENDED = 2

# min_tier tag carried on each broadcast signal -> required signal level.
SIGNAL_MIN_TIER_TO_LEVEL = {
    "starter": SIGNAL_LEVEL_CORE,
    "pro": SIGNAL_LEVEL_EXTENDED,
}


@dataclass(frozen=True)
class TierCapabilities:
    live_trading: bool
    # Highest signal level this tier may receive (0 = none).
    signal_level: int
    max_open_positions: int


# Trial mirrors Pro's signal breadth (so users can evaluate the full feed) but is
# paper-only. Expired receives nothing.
_CAPS: dict[str, TierCapabilities] = {
    "pro": TierCapabilities(live_trading=True, signal_level=SIGNAL_LEVEL_EXTENDED, max_open_positions=10),
    "starter": TierCapabilities(live_trading=True, signal_level=SIGNAL_LEVEL_CORE, max_open_positions=3),
    "trial": TierCapabilities(live_trading=False, signal_level=SIGNAL_LEVEL_EXTENDED, max_open_positions=3),
    "expired": TierCapabilities(live_trading=False, signal_level=0, max_open_positions=0),
    "invalid": TierCapabilities(live_trading=False, signal_level=0, max_open_positions=0),
}

_DEFAULT = _CAPS["expired"]


def capabilities_for(tier: str) -> TierCapabilities:
    return _CAPS.get(str(tier or "").lower(), _DEFAULT)


def signal_level_for_tier(tier: str) -> int:
    return capabilities_for(tier).signal_level


def required_level_for_signal(min_tier: str | None) -> int:
    """Minimum connection signal level needed to receive a signal tagged ``min_tier``."""
    if not min_tier:
        return SIGNAL_LEVEL_CORE
    return SIGNAL_MIN_TIER_TO_LEVEL.get(str(min_tier).lower(), SIGNAL_LEVEL_CORE)
