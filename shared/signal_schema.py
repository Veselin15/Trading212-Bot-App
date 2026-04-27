from __future__ import annotations

from typing import Literal, TypedDict


class RiskParams(TypedDict):
    stop_loss_pct: float
    take_profit_pct: float


class SignalPayload(TypedDict):
    id: str
    type: Literal["ENTRY"]
    direction: Literal["LONG", "SHORT"]
    symbol: str
    risk_params: RiskParams

