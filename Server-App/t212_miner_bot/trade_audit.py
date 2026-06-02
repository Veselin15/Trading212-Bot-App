"""
Persistent audit log for the live paper-trading engine.

Writes append-only records so you can review every trade, order attempt,
and key decision after the fact (profit analysis, debugging, compliance).

Files (under project logs/):
  live_audit.jsonl   — one JSON object per line (all event types)
  live_trades.csv    — flat ledger of fills / attempted orders (Excel-friendly)
"""

from __future__ import annotations

import csv
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(exist_ok=True)

AUDIT_JSONL = LOG_DIR / "live_audit.jsonl"
TRADES_CSV  = LOG_DIR / "live_trades.csv"

_TRADES_HEADER = [
    "timestamp_utc",
    "event",
    "symbol",
    "side",
    "shares",
    "price",
    "notional_eur",
    "reason",
    "confidence",
    "pnl_eur",
    "equity_eur",
    "free_cash_eur",
    "success",
    "error",
    "dry_run",
    "cycle",
    "extra",
]

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (str, int, float)) or obj is None:
        return obj
    if isinstance(obj, bool):
        return bool(obj)
    item = getattr(obj, "item", None)
    if callable(item):
        try:
            return _json_safe(item())
        except Exception:
            pass
    return str(obj)


class TradeAuditLogger:
    """Thread-safe append-only audit trail."""

    def __init__(
        self,
        jsonl_path: Path = AUDIT_JSONL,
        trades_csv_path: Path = TRADES_CSV,
        enabled: Optional[bool] = None,
    ) -> None:
        if enabled is None:
            enabled = os.getenv("BOT_AUDIT_LOG", "1").strip().lower() not in (
                "0", "false", "no", "off",
            )
        self.enabled = enabled
        self.jsonl_path = jsonl_path
        self.trades_csv_path = trades_csv_path
        self._ensure_trades_header()

    def _ensure_trades_header(self) -> None:
        if not self.enabled or self.trades_csv_path.exists():
            return
        with self.trades_csv_path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_TRADES_HEADER).writeheader()

    def log(self, event: str, **fields: Any) -> None:
        if not self.enabled:
            return
        record: Dict[str, Any] = {
            "ts": _now_iso(),
            "event": event,
            **_json_safe(fields),
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with _lock:
            with self.jsonl_path.open("a", encoding="utf-8") as f:
                f.write(line)

    def log_cycle(
        self,
        *,
        cycle: int,
        mode: str,
        equity: float,
        free_cash: float,
        open_positions: int,
        regime_frac: float,
        macro_scale: float,
        symbols_scored: int,
        allow_entries: bool,
        equity_is_live: bool,
    ) -> None:
        self.log(
            "cycle_summary",
            cycle=cycle,
            mode=mode,
            equity_eur=round(equity, 2),
            free_cash_eur=round(free_cash, 2),
            open_positions=open_positions,
            regime_frac=round(regime_frac, 4),
            macro_scale=macro_scale,
            symbols_scored=symbols_scored,
            allow_entries=allow_entries,
            equity_is_live=equity_is_live,
        )

    def log_order(
        self,
        *,
        cycle: int,
        symbol: str,
        side: str,
        shares: float,
        price: float,
        reason: str,
        success: bool,
        error: str = "",
        confidence: Optional[float] = None,
        equity: Optional[float] = None,
        free_cash: Optional[float] = None,
        dry_run: bool = False,
        pnl_eur: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        notional = round(abs(shares) * price, 2)
        self.log(
            "order",
            cycle=cycle,
            symbol=symbol,
            side=side,
            shares=shares,
            price=price,
            notional_eur=notional,
            reason=reason,
            success=success,
            error=error or None,
            confidence=confidence,
            equity_eur=equity,
            free_cash_eur=free_cash,
            dry_run=dry_run,
            pnl_eur=pnl_eur,
            extra=extra or {},
        )
        row = {
            "timestamp_utc": _now_iso(),
            "event": "order",
            "symbol": symbol,
            "side": side,
            "shares": shares,
            "price": price,
            "notional_eur": notional,
            "reason": reason,
            "confidence": confidence if confidence is not None else "",
            "pnl_eur": pnl_eur if pnl_eur is not None else "",
            "equity_eur": equity if equity is not None else "",
            "free_cash_eur": free_cash if free_cash is not None else "",
            "success": success,
            "error": error,
            "dry_run": dry_run,
            "cycle": cycle,
            "extra": json.dumps(extra or {}, ensure_ascii=False),
        }
        with _lock:
            with self.trades_csv_path.open("a", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=_TRADES_HEADER).writerow(row)

    def log_signal_rejected(
        self,
        *,
        cycle: int,
        symbol: str,
        score: float,
        reject_reason: str,
        equity: Optional[float] = None,
        free_cash: Optional[float] = None,
    ) -> None:
        self.log(
            "signal_rejected",
            cycle=cycle,
            symbol=symbol,
            score=round(score, 4),
            reject_reason=reject_reason,
            equity_eur=equity,
            free_cash_eur=free_cash,
        )

    def log_entry_skip(
        self,
        *,
        cycle: int,
        reason: str,
        equity: Optional[float] = None,
        free_cash: Optional[float] = None,
    ) -> None:
        self.log(
            "entry_skip",
            cycle=cycle,
            reason=reason,
            equity_eur=equity,
            free_cash_eur=free_cash,
        )

    def log_reconcile(
        self,
        *,
        removed_symbols: list,
        imported_symbols: Optional[list] = None,
    ) -> None:
        self.log(
            "reconcile",
            removed=removed_symbols,
            imported=imported_symbols or [],
        )


# Module-level singleton used by live_trader
audit = TradeAuditLogger()
