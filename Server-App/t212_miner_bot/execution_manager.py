from __future__ import annotations

import asyncio
import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any, Awaitable, Callable
from zoneinfo import ZoneInfo

from .api_client import AsyncT212Client, T212APIError
from .config import (
    BAR_INTERVAL,
    BOT_SAFE_MODE,
    MAX_ALLOCATION_PCT,
    RISK_PCT,
    STALE_BAR_GRACE_SECONDS,
    STALE_BAR_MAX_AGE_MULT,
    STATE_FILE,
    StrategyParams,
    SYMBOLS_MAP,
)
from .email_notifier import send_email_alert
try:
    # Telegram is optional; failures must never crash the bot.
    from .telegram_notifier import send_telegram_message
except Exception:  # pragma: no cover
    send_telegram_message = None  # type: ignore[assignment]


def _bar_interval_seconds(interval: str) -> float:
    raw = str(interval or "").strip().lower()
    try:
        if raw.endswith("m"):
            return max(float(raw[:-1]) * 60.0, 1.0)
        if raw.endswith("h"):
            return max(float(raw[:-1]) * 3600.0, 1.0)
    except ValueError:
        pass
    return 300.0


def _max_stale_age_seconds() -> float:
    return float(STALE_BAR_MAX_AGE_MULT) * _bar_interval_seconds(BAR_INTERVAL) + float(
        STALE_BAR_GRACE_SECONDS
    )


_UTC = ZoneInfo("UTC")
_NY_TZ = ZoneInfo("America/New_York")
_AMS_TZ = ZoneInfo("Europe/Amsterdam")
_BERLIN_TZ = ZoneInfo("Europe/Berlin")

# Extended-hours windows (coarse). Used only to downgrade "stale candle" warnings when the market
# is expected to be closed (e.g. stale last bar from prior session is normal overnight).
_US_EXT_OPEN = dt_time(4, 0)
_US_EXT_CLOSE = dt_time(20, 0)
_EU_EXT_OPEN = dt_time(8, 0)
_EU_EXT_CLOSE = dt_time(18, 0)


def _is_market_open_now(yf_symbol: str, now_utc: datetime | None = None) -> bool:
    now = now_utc if now_utc is not None else datetime.now(tz=_UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=_UTC)
    if now.weekday() >= 5:
        return False

    sym = str(yf_symbol or "").upper()
    if sym.endswith(".AS"):
        t = now.astimezone(_AMS_TZ).time()
        return _EU_EXT_OPEN <= t < _EU_EXT_CLOSE
    if sym.endswith(".DE"):
        t = now.astimezone(_BERLIN_TZ).time()
        return _EU_EXT_OPEN <= t < _EU_EXT_CLOSE

    t = now.astimezone(_NY_TZ).time()
    return _US_EXT_OPEN <= t < _US_EXT_CLOSE


@dataclass
class SymbolState:
    status: str = "SCANNING"
    side: str | None = None
    pending_order_id: str | None = None
    pending_stop_price: float | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    risk_distance: float | None = None
    qty_total: float = 0.0
    unit1_qty: float = 0.0
    unit2_qty: float = 0.0
    unit1_order_id: str | None = None
    unit2_stop_order_id: str | None = None
    missing_protective_stop: bool = False
    unit1_tp_price: float | None = None
    highest_high_since_entry: float | None = None
    lowest_low_since_entry: float | None = None
    break_even_moved: bool = False
    profit_lock_moved: bool = False
    entry_timestamp_utc: str | None = None
    morning_protect_applied: bool = False
    last_bar_date_utc: str | None = None
    session_open_bar_timestamp_utc: str | None = None
    flat_sync_miss_count: int = 0
    protective_stop_anomaly_streak: int = 0
    pending_entry_cross_streak: int = 0
    forced_exit_order_id: str | None = None
    forced_exit_attempts: int = 0
    forced_exit_last_attempt_timestamp_utc: str | None = None
    recent_trade_returns_pct: list[float] = field(default_factory=list)


class ExecutionManager:
    def __init__(self, client: AsyncT212Client, params: StrategyParams, state_file: str = STATE_FILE) -> None:
        self.client = client
        self.params = params
        self.state_file = Path(state_file)
        self.state: dict[str, SymbolState] = {
            symbol: SymbolState() for symbol in SYMBOLS_MAP.keys()
        }
        self._risk_mult_by_symbol: dict[str, float] = {symbol: 1.0 for symbol in SYMBOLS_MAP.keys()}
        self._portfolio_exposure_mult: float = 1.0
        self._risk_profile_summary: str = "exposure=1.00"
        self._load_state()

    async def startup_reconcile(self) -> list[str]:
        """
        Best-effort startup reconciliation:
        - If broker is flat but local state thinks ACTIVE -> reset (after quick confirmation).
        - If broker has a position while local is SCANNING -> adopt broker position (already supported).
        - If protective stop exists at broker but local lost it -> re-link it.
        This does not change strategy logic; it just improves recovery after restarts/API hiccups.
        """
        logs: list[str] = []
        for symbol in list(SYMBOLS_MAP.keys()):
            st = self.state.get(symbol)
            if st is None:
                continue
            ticker = SYMBOLS_MAP[symbol]
            try:
                qty = await self.client.get_position_quantity(ticker=ticker)
            except T212APIError as exc:
                logs.append(f"[WARN] {ticker} Startup reconcile qty fetch failed: {exc}")
                continue
            whole = self._to_whole_shares(qty)

            if whole <= 0 and st.status in {"UNIT1_ACTIVE", "UNIT2_ACTIVE", "ATR_ACTIVE"}:
                stale_status = st.status
                self._reset_symbol(symbol)
                logs.append(f"[WARN] {ticker} Startup reconcile reset stale local state ({stale_status}); broker is flat.")
                continue

            if whole >= 1 and st.status == "SCANNING":
                # Adopt broker position with minimal info; bar/ATR will be refined on next candle cycle.
                strategy_mode = self._strategy_mode_for_symbol(symbol)
                # For ATR mode adoption we still need a stop multiplier; use per-symbol override if present.
                atr_stop_mult = float(
                    self.params.atr_dynamic_params_by_symbol.get(symbol, (self.params.atr_dynamic_stop_mult, 0.0, 0.0))[0]
                )
                adopted = await self._adopt_broker_position_if_needed(
                    symbol=symbol,
                    ticker=ticker,
                    st=st,
                    bar_ts=datetime.now(tz=ZoneInfo("UTC")),
                    high=0.0,
                    atr_5m=0.0,
                    strategy_mode=strategy_mode,
                    atr_stop_mult=atr_stop_mult,
                    logs=logs,
                )
                if adopted:
                    continue

            # Re-link broker protective stop if local says it's missing.
            if st.status in {"UNIT1_ACTIVE", "UNIT2_ACTIVE", "ATR_ACTIVE"} and (
                st.missing_protective_stop or not st.unit2_stop_order_id
            ):
                oid, stop_price = await self._find_existing_protective_stop_order_id_and_price(
                    ticker=ticker
                )
                if oid and stop_price:
                    st.unit2_stop_order_id = oid
                    st.stop_loss = float(stop_price)
                    st.missing_protective_stop = False
                    logs.append(
                        f"[INFO] {ticker} Startup reconcile linked broker protective stop (order_id={oid})."
                    )
        if logs and not BOT_SAFE_MODE:
            self._persist_state()
        return logs

    @staticmethod
    def _extract_entry_price_from_position_row(row: dict[str, Any]) -> float | None:
        """
        Best-effort extraction of average/entry price from Trading212 /positions row.
        Field names can vary between environments (demo/live) and API revisions.
        """
        candidates = (
            "averagePrice",
            "avgPrice",
            "averageOpenPrice",
            "openPrice",
            "entryPrice",
            "price",
        )
        for key in candidates:
            for container in (row, row.get("instrument") if isinstance(row.get("instrument"), dict) else None):
                if not isinstance(container, dict):
                    continue
                raw = container.get(key)
                try:
                    val = float(raw) if raw is not None else None
                except (TypeError, ValueError):
                    val = None
                if val is not None and math.isfinite(val) and val > 0:
                    return val
        return None

    async def _find_existing_protective_stop_order_id_and_price(
        self, *, ticker: str
    ) -> tuple[str | None, float | None]:
        """
        Best-effort: find an existing protective STOP order for a long position by scanning broker pending orders.
        Returns (order_id, stop_price) if found.
        """
        try:
            pending = await self.client.get_pending_orders()
        except T212APIError:
            return None, None

        try:
            resolved = await self.client.resolve_ticker(ticker)
        except T212APIError:
            resolved = str(ticker).strip()

        best_id: str | None = None
        best_price: float | None = None
        for row in pending:
            if not isinstance(row, dict):
                continue
            row_ticker = row.get("ticker")
            if row_ticker is None and isinstance(row.get("instrument"), dict):
                row_ticker = row["instrument"].get("ticker")
            if str(row_ticker or "").strip() != str(resolved).strip():
                continue

            qty_raw = row.get("quantity")
            if qty_raw is None:
                qty_raw = row.get("qty")
            try:
                qty = float(qty_raw) if qty_raw is not None else 0.0
            except (TypeError, ValueError):
                qty = 0.0

            typ = str(row.get("type") or row.get("orderType") or row.get("order_type") or "").upper()
            # Protective stop for LONG is a SELL (negative qty).
            if qty >= 0:
                continue

            stop_raw = row.get("stopPrice")
            if stop_raw is None:
                stop_raw = row.get("stop_price")
            if stop_raw is None:
                stop_raw = row.get("price")
            if stop_raw is None and isinstance(row.get("instrument"), dict):
                stop_raw = row["instrument"].get("stopPrice") or row["instrument"].get("price")
            try:
                stop_price = float(stop_raw) if stop_raw is not None else None
            except (TypeError, ValueError):
                stop_price = None
            if stop_price is None or not math.isfinite(stop_price) or stop_price <= 0:
                continue

            # If broker provides explicit order type, require stop-like. Otherwise accept presence of stopPrice.
            if typ and ("STOP" not in typ):
                continue

            oid = row.get("id")
            if oid is None:
                continue
            best_id = str(oid)
            best_price = stop_price
            # Prefer the first valid match; if multiple exist, any is better than none.
            break

        return best_id, best_price

    async def _adopt_broker_position_if_needed(
        self,
        *,
        symbol: str,
        ticker: str,
        st: SymbolState,
        bar_ts: datetime,
        high: float,
        atr_5m: float,
        strategy_mode: str,
        atr_stop_mult: float,
        logs: list[str],
    ) -> bool:
        """
        When local state is SCANNING but broker reports an open position, reconstruct a minimal safe
        local state so stop management can resume (avoids "SCANNING but still holding" limbo).

        Returns True if adoption succeeded and local state was updated.
        """
        try:
            row = await self.client.get_open_position_row(ticker)
        except T212APIError as exc:
            logs.append(f"[WARN] [{symbol}] Broker position adoption failed (/positions): {exc}")
            return False
        entry_price: float | None = None
        if row:
            entry_price = self._extract_entry_price_from_position_row(row)

        # Demo environments sometimes omit average/entry price from /positions; try /portfolio row too.
        if entry_price is None:
            try:
                prow = await self.client.get_portfolio_row(ticker)
            except T212APIError:
                prow = None
            if isinstance(prow, dict):
                entry_price = self._extract_entry_price_from_position_row(prow)

        if entry_price is None:
            logs.append(
                f"[WARN] [{symbol}] Broker position adoption skipped: entry/avg price missing in broker payloads."
            )
            return False

        try:
            live_qty = await self.client.get_position_quantity(ticker=ticker)
        except T212APIError as exc:
            logs.append(f"[WARN] [{symbol}] Broker position adoption failed (/portfolio): {exc}")
            return False
        qty_total = self._to_whole_shares(live_qty)
        if qty_total < 1:
            return False

        # Determine an initial risk distance from current ATR if we don't have a broker stop.
        if strategy_mode == "ATR":
            risk_distance = float(atr_stop_mult) * float(atr_5m)
        else:
            risk_distance = float(self.params.atr_multiplier) * float(atr_5m)
        risk_distance = max(float(risk_distance), 0.0)
        stop_loss = entry_price - risk_distance if risk_distance > 0 else None

        existing_stop_id, existing_stop_price = await self._find_existing_protective_stop_order_id_and_price(
            ticker=ticker
        )
        if existing_stop_price is not None:
            stop_loss = float(existing_stop_price)

        # Minimal BASE-mode split defaults (used only for management; exits are reconciled with broker quantity).
        unit1_qty = int(math.floor(qty_total * 0.5))
        unit2_qty = max(qty_total - unit1_qty, 0)

        st.side = "long"
        st.status = "ATR_ACTIVE" if strategy_mode == "ATR" else "UNIT1_ACTIVE"
        st.pending_order_id = None
        st.pending_stop_price = entry_price
        st.entry_price = entry_price
        st.entry_timestamp_utc = bar_ts.isoformat()
        st.qty_total = float(qty_total)
        st.unit1_qty = float(unit1_qty)
        st.unit2_qty = float(unit2_qty)
        st.risk_distance = float(risk_distance) if risk_distance > 0 else None
        st.stop_loss = float(stop_loss) if stop_loss is not None else None
        st.unit2_stop_order_id = existing_stop_id
        st.missing_protective_stop = existing_stop_id is None or st.stop_loss is None
        st.unit1_tp_price = (
            entry_price + (float(self.params.unit1_tp_rr) * float(risk_distance))
            if risk_distance > 0
            else None
        )
        st.highest_high_since_entry = max(float(high), float(entry_price))
        st.lowest_low_since_entry = min(float(high), float(entry_price))
        st.break_even_moved = False
        st.profit_lock_moved = False
        st.flat_sync_miss_count = 0
        st.protective_stop_anomaly_streak = 0

        logs.append(
            f"[WARN] [{symbol}] Adopted broker position into local state "
            f"(mode={st.status}, qty={qty_total}, entry≈{entry_price:.4f}, "
            f"stop={'none' if st.stop_loss is None else f'{float(st.stop_loss):.4f}'})."
        )
        return True

    @staticmethod
    def _schedule_email_alert(subject: str, body: str) -> None:
        """Schedule non-blocking email delivery for critical state changes."""
        asyncio.create_task(send_email_alert(subject=subject, body=body))

    @staticmethod
    def _schedule_telegram_alert(message: str) -> None:
        """
        Schedule non-blocking Telegram delivery.
        Runs in a background thread to avoid blocking the asyncio event loop.
        """
        if send_telegram_message is None:
            return
        asyncio.create_task(asyncio.to_thread(send_telegram_message, message))

    def _load_state(self) -> None:
        if not self.state_file.exists():
            self._persist_state()
            return

        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
            for symbol, raw_state in payload.items():
                if symbol in self.state:
                    self.state[symbol] = SymbolState(**raw_state)
        except Exception:
            # If state cannot be loaded, restart from clean states.
            self.state = {symbol: SymbolState() for symbol in SYMBOLS_MAP.keys()}
            self._persist_state()

    def _persist_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {symbol: asdict(st) for symbol, st in self.state.items()}
        self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _reset_symbol(self, symbol: str) -> None:
        self.state[symbol] = SymbolState()

    @staticmethod
    def _to_whole_shares(qty: float) -> int:
        # Trading 212 accepts integer share quantities for stop/limit equity orders.
        return int(math.floor(max(qty, 0.0)))

    async def _place_stop_order(self, ticker: str, qty: float, stop_price: float) -> dict[str, Any]:
        # extendedHours is only valid for US-listed instruments (resolved ticker ends with _US_EQ).
        # Sending it for European instruments (Xetra: SAPd_EQ, Euronext: ASMLa_EQ / UNIAa_EQ, etc.)
        # causes Trading 212 to return 400 Invalid payload — those markets have no extended hours.
        us_ticker = ticker.endswith("_US_EQ")
        ext = True if (self.params.stop_order_extended_hours and us_ticker) else None
        return await self.client.place_stop_order(
            ticker=ticker,
            qty=qty,
            stop_price=stop_price,
            extended_hours=ext,
        )

    async def _broker_current_price_safe(self, *, ticker: str) -> float | None:
        """
        Best-effort broker mark (currentPrice) fetch.
        Used only as a fallback for managing OPEN positions when candle feed lags.
        """
        try:
            row = await self.client.get_open_position_row(ticker)
        except T212APIError:
            return None
        if not row:
            return None
        cp_raw = row.get("currentPrice")
        try:
            cp = float(cp_raw) if cp_raw is not None else None
        except (TypeError, ValueError):
            return None
        if cp is None or not math.isfinite(cp) or cp <= 0:
            return None
        return cp

    async def _broker_open_quantity_stable(self, ticker: str) -> float:
        """
        Poll quantity briefly to reduce false 'flat' reads when the broker API glitches for one tick.
        """
        for _ in range(3):
            q = await self.client.get_position_quantity(ticker=ticker)
            if self._to_whole_shares(q) >= 1:
                return float(q)
            await asyncio.sleep(0.35)
        return 0.0

    async def _cancel_all_stop_orders_for_instrument(
        self,
        *,
        symbol: str,
        ticker: str,
        resolved_ticker: str,
        logs: list[str],
    ) -> None:
        try:
            orders = await self.client.get_pending_orders()
        except T212APIError as exc:
            logs.append(f"[WARN] {ticker} Could not list orders for STOP cleanup: {exc}")
            return
        for o in orders:
            if not isinstance(o, dict):
                continue
            if str(o.get("ticker", "")).strip() != resolved_ticker:
                continue
            if o.get("type") != "STOP":
                continue
            oid = o.get("id")
            if oid is None:
                continue
            await self._cancel_order_if_exists(
                str(oid),
                symbol=symbol,
                ticker=ticker,
                logs=logs,
                context_label="broker STOP cleanup",
            )

    async def _maybe_reconcile_broker_protective_stop(
        self,
        *,
        symbol: str,
        ticker: str,
        st: SymbolState,
        logs: list[str],
    ) -> bool:
        """
        Return True if the symbol cycle should end (e.g. emergency flatten executed).
        """
        if BOT_SAFE_MODE:
            return False
        if st.status not in {"UNIT1_ACTIVE", "UNIT2_ACTIVE", "ATR_ACTIVE"}:
            return False
        if st.side != "long" or st.stop_loss is None:
            return False

        try:
            live_qty = await self.client.get_position_quantity(ticker=ticker)
        except T212APIError as exc:
            logs.append(f"[WARN] {ticker} Protective-stop broker audit skipped (qty sync): {exc}")
            return False

        if self._to_whole_shares(live_qty) <= 0:
            st.protective_stop_anomaly_streak = 0
            return False

        try:
            resolved = await self.client.resolve_ticker(ticker)
        except T212APIError as exc:
            logs.append(f"[WARN] {ticker} Protective-stop broker audit skipped (ticker resolve): {exc}")
            return False

        if self.params.protective_stop_order_reconcile_enabled and st.unit2_stop_order_id:
            oid = st.unit2_stop_order_id
            if oid and oid != "unknown":
                try:
                    pending = await self.client.get_pending_orders()
                except T212APIError as exc:
                    logs.append(f"[WARN] {ticker} Pending-order fetch failed: {exc}")
                    pending = []
                open_ids = {str(o.get("id")) for o in pending if isinstance(o, dict) and o.get("id") is not None}
                if oid not in open_ids:
                    logs.append(
                        f"[WARN] {ticker} Tracked protective stop id={oid} not in broker pending list; "
                        "marking missing for re-place."
                    )
                    st.unit2_stop_order_id = None
                    st.missing_protective_stop = True

        if not self.params.protective_stop_broker_escape_enabled:
            return False

        try:
            row = await self.client.get_open_position_row(ticker)
        except T212APIError as exc:
            logs.append(f"[WARN] {ticker} Broker /positions fetch failed: {exc}")
            return False

        if not row:
            st.protective_stop_anomaly_streak = 0
            return False

        cp_raw = row.get("currentPrice")
        try:
            cp = float(cp_raw) if cp_raw is not None else 0.0
        except (TypeError, ValueError):
            return False
        if cp <= 0:
            return False

        stop_level = float(st.stop_loss)
        buf_pct = max(float(self.params.protective_stop_broker_price_buffer_pct), 0.0)
        buf_abs = max(float(self.params.protective_stop_broker_price_buffer_abs), 0.0)
        buffer = max(buf_abs, stop_level * buf_pct)
        if cp >= stop_level - buffer:
            st.protective_stop_anomaly_streak = 0
            return False

        st.protective_stop_anomaly_streak += 1
        logs.append(
            f"[WARN] {ticker} Broker currentPrice={cp:.4f} below local stop {stop_level:.4f} "
            f"(buffer={buffer:.4f}); streak={st.protective_stop_anomaly_streak}. "
            "T212 stops trigger on last traded price — UI can differ from LTP."
        )

        n_conf = max(int(self.params.protective_stop_broker_escape_confirmations), 1)
        if st.protective_stop_anomaly_streak < n_conf:
            return False

        logs.append(
            f"[CRITICAL] {ticker} Forcing market exit: broker currentPrice={cp:.4f} < stop={stop_level:.4f} "
            f"after {n_conf} consecutive cycles with an open position."
        )
        self._schedule_email_alert(
            subject=f"CRITICAL - Broker stop desync exit ({symbol})",
            body=(
                f"Symbol: {symbol}\n"
                f"Broker currentPrice: {cp:.4f}\n"
                f"Local stop: {stop_level:.4f}\n"
                "Cancelled pending STOP orders for this instrument and submitted a market sell."
            ),
        )
        await self._cancel_all_stop_orders_for_instrument(
            symbol=symbol,
            ticker=ticker,
            resolved_ticker=resolved,
            logs=logs,
        )
        st.unit2_stop_order_id = None
        st.status = "FORCED_EXIT_PENDING"
        st.forced_exit_attempts = int(st.forced_exit_attempts) + 1
        st.forced_exit_last_attempt_timestamp_utc = datetime.now(tz=ZoneInfo("UTC")).isoformat()
        try:
            q = await self._broker_open_quantity_stable(ticker)
            if q > 0:
                cq = self._signed_exit_qty(q, "long")
                resp = await self.client.close_position(ticker=ticker, qty=int(cq))
                if isinstance(resp, dict) and resp.get("id") is not None:
                    st.forced_exit_order_id = str(resp["id"])
        except T212APIError as exc:
            logs.append(f"[CRITICAL] [{symbol}] Forced exit failed: {exc}")

        if st.entry_price is not None and float(st.entry_price) > 0:
            pnl_pct = ((cp - float(st.entry_price)) / float(st.entry_price)) * 100.0
            self._record_trade_return(symbol, pnl_pct, logs, reason="broker_stop_desync_exit")
        # Do not reset immediately: broker may show the position for a few cycles (pending market order,
        # partial fill, or API lag). Keep state in FORCED_EXIT_PENDING and let the scanning guard reconcile.
        st.side = "long"
        return True

    @staticmethod
    def _signed_exit_qty(qty: float, side: str) -> int:
        """
        Trading 212 uses signed quantities: LONG exits must be SELL (negative qty).
        """
        whole_qty = int(math.floor(max(qty, 0.0)))
        if side == "long":
            return -abs(whole_qty)
        return abs(whole_qty)

    @staticmethod
    def _is_order_not_found_error(exc: Exception) -> bool:
        return "order not found" in str(exc).lower() and "(404)" in str(exc)

    @staticmethod
    def _is_inventory_settlement_race_error(exc: Exception) -> bool:
        err = str(exc).lower()
        return (
            "selling-equity-not-owned" in err
            or ("selling more equities than owned" in err and "owned: 0" in err)
            or "owned: 0" in err
        )

    async def _place_exit_order_with_retry(
        self,
        place_order: Callable[[], Awaitable[dict[str, Any]]],
        symbol: str,
        order_label: str,
        logs: list[str],
        max_attempts: int = 3,
        retry_delay_seconds: float = 2.0,
    ) -> dict[str, Any] | None:
        for attempt in range(1, max_attempts + 1):
            try:
                return await place_order()
            except T212APIError as exc:
                if not self._is_inventory_settlement_race_error(exc):
                    raise
                logs.append(
                    f"[WARN] [{symbol}] {order_label} attempt {attempt}/{max_attempts} "
                    f"hit inventory settlement race: {exc}"
                )
                if attempt == max_attempts:
                    logs.append(
                        f"[{symbol}] {order_label} placement failed after {max_attempts} attempts."
                    )
                    return None
                await asyncio.sleep(retry_delay_seconds)
        return None

    async def _cancel_order_if_exists(
        self,
        order_id: str | None,
        *,
        symbol: str,
        ticker: str,
        logs: list[str],
        context_label: str,
    ) -> bool:
        """
        Cancel a broker order and treat 404 as already-cancelled.
        """
        if not order_id:
            return True
        try:
            await self.client.cancel_order(order_id)
            return True
        except T212APIError as exc:
            if self._is_order_not_found_error(exc):
                logs.append(
                    f"[INFO] {ticker} {context_label} order already absent at broker (404)."
                )
                return True
            logs.append(f"[{symbol}] Failed to cancel {context_label} order: {exc}")
            return False

    async def _wait_for_inventory_quantity(
        self,
        *,
        symbol: str,
        ticker: str,
        required_qty: int,
        logs: list[str],
        poll_interval_seconds: float = 3.0,
        timeout_seconds: float = 45.0,
    ) -> int:
        """
        Poll portfolio quantity until required inventory is visible or timeout expires.
        """
        if required_qty <= 0:
            return 0

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        attempt = 0
        last_visible_qty = 0

        while True:
            attempt += 1
            try:
                live_qty = await self.client.get_position_quantity(ticker=ticker)
                last_visible_qty = self._to_whole_shares(live_qty)
            except T212APIError as exc:
                logs.append(f"[WARN] {ticker} Inventory poll attempt {attempt} failed: {exc}")

            if last_visible_qty >= required_qty:
                if attempt > 1:
                    logs.append(
                        f"[INFO] {ticker} Inventory settled: visible={last_visible_qty} required={required_qty}."
                    )
                return last_visible_qty

            remaining = deadline - loop.time()
            if remaining <= 0:
                logs.append(
                    f"[WARN] {ticker} Inventory settlement timeout: visible={last_visible_qty} required={required_qty}."
                )
                return last_visible_qty

            logs.append(
                f"[INFO] {ticker} Waiting for inventory sync ({last_visible_qty}/{required_qty}) "
                f"before placing protective SL."
            )
            await asyncio.sleep(min(poll_interval_seconds, max(remaining, 0.1)))

    async def _ensure_initial_protective_stop(
        self,
        *,
        symbol: str,
        ticker: str,
        st: SymbolState,
        logs: list[str],
        expected_qty: int,
    ) -> bool:
        """
        Ensure the initial full-position protective stop exists at broker level.
        """
        # If a protective stop already exists at broker (e.g. set manually / from previous run),
        # adopt it instead of attempting to place a new one (prevents owned=0 desync errors).
        existing_id, existing_price = await self._find_existing_protective_stop_order_id_and_price(ticker=ticker)
        if existing_id and existing_price and math.isfinite(float(existing_price)) and float(existing_price) > 0:
            st.unit2_stop_order_id = str(existing_id)
            st.stop_loss = float(existing_price)
            st.missing_protective_stop = False
            return True

        visible_qty = await self._wait_for_inventory_quantity(
            symbol=symbol,
            ticker=ticker,
            required_qty=expected_qty,
            logs=logs,
            poll_interval_seconds=3.0,
            timeout_seconds=45.0,
        )
        if visible_qty < expected_qty:
            st.unit2_stop_order_id = None
            st.missing_protective_stop = True
            logs.append(
                f"[WARN] {ticker} Protective SL deferred: inventory not settled yet "
                f"({visible_qty}/{expected_qty}). Will retry next cycle."
            )
            return False

        try:
            stop_qty = self._signed_exit_qty(expected_qty, st.side or "long")
            stop_resp = await self._place_exit_order_with_retry(
                place_order=lambda: self._place_stop_order(
                    ticker=ticker,
                    qty=int(stop_qty),
                    stop_price=float(st.stop_loss),
                ),
                symbol=symbol,
                order_label="Initial protective SL stop",
                logs=logs,
                max_attempts=5,
                retry_delay_seconds=2.0,
            )
            if not stop_resp:
                st.unit2_stop_order_id = None
                st.missing_protective_stop = True
                logs.append(
                    f"[WARN] {ticker} Protective SL placement failed after retries. Will retry next cycle."
                )
                return False
            st.unit2_stop_order_id = str(stop_resp.get("id", "unknown"))
            st.missing_protective_stop = False
            return True
        except T212APIError as exc:
            st.unit2_stop_order_id = None
            st.missing_protective_stop = True
            logs.append(
                f"[WARN] {ticker} Protective SL placement failed with API error: {exc}. "
                "Will retry next cycle."
            )
            return False

    @staticmethod
    def _compute_breakeven_plus_stop(entry_price: float, side: str, offset_pct: float) -> float:
        # Breakeven+ offset helps cover spread and hypothetical fees on Unit 2 stop.
        if side == "long":
            return entry_price * (1.0 + offset_pct)
        return entry_price * (1.0 - offset_pct)

    @staticmethod
    def _is_eu_open_buffer_active() -> bool:
        """
        Block new entries during the first 15 minutes after EU cash open (CET).
        Existing positions are still managed as usual.
        """
        now_cet = datetime.now(tz=ZoneInfo("Europe/Berlin"))
        open_start = dt_time(9, 0)
        open_end = dt_time(9, 15)
        return open_start <= now_cet.time() < open_end

    @staticmethod
    def _parse_utc_timestamp(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw)
        except Exception:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=ZoneInfo("UTC"))
        return parsed.astimezone(ZoneInfo("UTC"))

    def _is_overnight_position(self, st: SymbolState, bar_ts: datetime) -> bool:
        entry_ts = self._parse_utc_timestamp(st.entry_timestamp_utc)
        if entry_ts is None:
            return False
        return bar_ts.date() > entry_ts.date()

    def _profit_lock_params_for_symbol(self, symbol: str) -> tuple[float, float]:
        trigger = float(self.params.profit_lock_trigger_pct)
        stop = float(self.params.profit_lock_stop_pct)
        raw_map = getattr(self.params, "profit_lock_by_symbol", {})
        if isinstance(raw_map, dict):
            raw = raw_map.get(symbol)
            if isinstance(raw, (tuple, list)) and len(raw) >= 2:
                try:
                    trigger = float(raw[0])
                    stop = float(raw[1])
                except (TypeError, ValueError):
                    pass
        return max(trigger, 0.0), max(stop, 0.0)

    def _atr_dynamic_params_for_symbol(self, symbol: str) -> tuple[float, float, float]:
        stop_mult = float(self.params.atr_dynamic_stop_mult)
        tp_r = float(self.params.atr_dynamic_tp_r)
        be_r = float(self.params.atr_dynamic_be_r)
        raw_map = getattr(self.params, "atr_dynamic_params_by_symbol", {})
        if isinstance(raw_map, dict):
            raw = raw_map.get(symbol)
            if isinstance(raw, (tuple, list)) and len(raw) >= 3:
                try:
                    stop_mult = float(raw[0])
                    tp_r = float(raw[1])
                    be_r = float(raw[2])
                except (TypeError, ValueError):
                    pass
        return max(stop_mult, 0.1), max(tp_r, 0.1), max(be_r, 0.1)

    def _morning_real_profit_trigger_pct_for_symbol(self, symbol: str) -> float:
        value = float(self.params.morning_real_profit_trigger_pct)
        raw_map = getattr(self.params, "morning_real_profit_trigger_pct_by_symbol", {})
        if isinstance(raw_map, dict) and symbol in raw_map:
            try:
                value = float(raw_map[symbol])
            except (TypeError, ValueError):
                pass
        return max(value, 0.0)

    def _morning_profit_capture_pct_for_symbol(self, symbol: str) -> float:
        value = float(self.params.morning_profit_capture_pct)
        raw_map = getattr(self.params, "morning_profit_capture_pct_by_symbol", {})
        if isinstance(raw_map, dict) and symbol in raw_map:
            try:
                value = float(raw_map[symbol])
            except (TypeError, ValueError):
                pass
        return max(value, 0.0)

    def _morning_protect_window_minutes_for_symbol(self, symbol: str) -> int:
        value = int(self.params.morning_protect_window_minutes)
        raw_map = getattr(self.params, "morning_protect_window_minutes_by_symbol", {})
        if isinstance(raw_map, dict) and symbol in raw_map:
            try:
                value = int(raw_map[symbol])
            except (TypeError, ValueError):
                pass
        return max(value, 1)

    def _is_session_open_window(self, symbol: str, st: SymbolState, bar_ts: datetime) -> bool:
        open_ts = self._parse_utc_timestamp(st.session_open_bar_timestamp_utc)
        if open_ts is None:
            return False
        if bar_ts < open_ts:
            return False
        elapsed = bar_ts - open_ts
        return elapsed <= timedelta(minutes=self._morning_protect_window_minutes_for_symbol(symbol))

    def _is_morning_protect_enabled_for_symbol(self, symbol: str) -> bool:
        symbol_flags = getattr(self.params, "morning_protect_symbol_enabled", {})
        if isinstance(symbol_flags, dict) and symbol in symbol_flags:
            return bool(symbol_flags.get(symbol))
        return bool(self.params.morning_protect_enabled)

    def _compute_morning_protect_stop(
        self,
        *,
        symbol: str,
        st: SymbolState,
        bar_ts: datetime,
        high: float,
        close: float,
    ) -> float | None:
        """
        For overnight underperformers, lift stop to breakeven or slightly above it.
        """
        if not self.params.morning_protect_enabled:
            return None
        if not self._is_morning_protect_enabled_for_symbol(symbol):
            return None
        if st.side != "long" or st.entry_price is None or st.stop_loss is None:
            return None
        if not self._is_session_open_window(symbol=symbol, st=st, bar_ts=bar_ts):
            return None
        if not self._is_overnight_position(st=st, bar_ts=bar_ts):
            return None
        if close <= 0:
            return None

        entry = float(st.entry_price)
        current_stop = float(st.stop_loss)
        session_high = max(float(high), float(st.highest_high_since_entry or high))
        peak_profit_pct = (session_high - entry) / entry if entry > 0 else 0.0
        morning_real_profit_trigger_pct = self._morning_real_profit_trigger_pct_for_symbol(symbol)
        if peak_profit_pct >= morning_real_profit_trigger_pct:
            return None

        # Capture a fraction of current unrealized gains, but never below breakeven target.
        current_profit = max(close - entry, 0.0)
        morning_profit_capture_pct = self._morning_profit_capture_pct_for_symbol(symbol)
        candidate = max(
            entry,
            entry + (morning_profit_capture_pct * current_profit),
        )
        # For broker validity, keep long stop safely below current traded price proxy.
        max_valid_stop = close * 0.9995
        if candidate >= max_valid_stop:
            return None
        if candidate <= current_stop:
            return None
        return candidate

    async def _maybe_apply_morning_protect_stop(
        self,
        *,
        symbol: str,
        ticker: str,
        st: SymbolState,
        bar_ts: datetime,
        high: float,
        close: float,
        logs: list[str],
        context_label: str,
    ) -> bool:
        """
        Try replacing current protective stop with morning breakeven-or-better stop.
        Returns True when stop was updated.
        """
        candidate_stop = self._compute_morning_protect_stop(
            symbol=symbol,
            st=st,
            bar_ts=bar_ts,
            high=high,
            close=close,
        )
        if candidate_stop is None:
            return False

        try:
            live_qty = await self.client.get_position_quantity(ticker=ticker)
        except T212APIError as exc:
            logs.append(f"[WARN] {ticker} Morning-protect stop skipped (live qty sync failed): {exc}")
            return False

        runner_qty = self._to_whole_shares(live_qty)
        if runner_qty <= 0:
            logs.append(f"[INFO] {ticker} Morning-protect stop skipped because position is already flat.")
            self._reset_symbol(symbol)
            return False

        cancelled = await self._cancel_order_if_exists(
            st.unit2_stop_order_id,
            symbol=symbol,
            ticker=ticker,
            logs=logs,
            context_label=context_label,
        )
        if not cancelled:
            logs.append(f"[WARN] {ticker} Morning-protect stop update aborted; SL cancellation failed.")
            return False

        stop_qty = self._signed_exit_qty(runner_qty, st.side or "long")
        replacement = await self._place_exit_order_with_retry(
            place_order=lambda: self._place_stop_order(
                ticker=ticker,
                qty=int(stop_qty),
                stop_price=float(candidate_stop),
            ),
            symbol=symbol,
            order_label="Morning-protect SL stop",
            logs=logs,
            max_attempts=5,
            retry_delay_seconds=2.0,
        )
        if not replacement:
            logs.append(f"[WARN] {ticker} Morning-protect stop placement failed; previous stop retained.")
            return False

        st.unit2_stop_order_id = str(replacement.get("id", "unknown"))
        st.stop_loss = float(candidate_stop)
        st.morning_protect_applied = True
        logs.append(
            f"[UPDATE] {ticker} Morning-protect stop moved to {float(candidate_stop):.4f} "
            "(overnight underperformer protection)."
        )
        return True

    def _strategy_mode_for_symbol(self, symbol: str) -> str:
        raw = str(self.params.symbol_strategy_mode.get(symbol, "BASE")).strip().upper()
        return raw if raw in {"BASE", "ATR"} else "BASE"

    def _record_trade_return(self, symbol: str, pnl_pct: float, logs: list[str], reason: str) -> None:
        st = self.state.get(symbol)
        if st is None:
            return
        if not math.isfinite(pnl_pct):
            return
        bounded = max(min(float(pnl_pct), 100.0), -100.0)
        st.recent_trade_returns_pct.append(bounded)
        max_keep = 30
        if len(st.recent_trade_returns_pct) > max_keep:
            st.recent_trade_returns_pct = st.recent_trade_returns_pct[-max_keep:]
        logs.append(
            f"[INFO] {symbol} EWR memory updated ({reason}): pnl={bounded:.2f}% "
            f"samples={len(st.recent_trade_returns_pct)}"
        )

    def _portfolio_recent_returns_pct(self, lookback: int) -> list[float]:
        if lookback <= 0:
            return []
        series = {
            symbol: list(self.state.get(symbol, SymbolState()).recent_trade_returns_pct)
            for symbol in SYMBOLS_MAP.keys()
        }
        min_len = min((len(v) for v in series.values()), default=0)
        if min_len <= 0:
            return []
        usable = min(min_len, lookback)
        out: list[float] = []
        for i in range(-usable, 0):
            vals = [series[s][i] for s in SYMBOLS_MAP.keys()]
            out.append(sum(vals) / len(vals))
        return out

    def _average_pair_correlation(self, lookback: int) -> float:
        if lookback < 2:
            return 0.0
        windows = {
            symbol: list(self.state.get(symbol, SymbolState()).recent_trade_returns_pct)[-lookback:]
            for symbol in SYMBOLS_MAP.keys()
        }
        if any(len(vals) < 2 for vals in windows.values()):
            return 0.0
        correlations: list[float] = []
        symbols = list(SYMBOLS_MAP.keys())
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                a = windows[symbols[i]]
                b = windows[symbols[j]]
                if len(a) != len(b) or len(a) < 2:
                    continue
                try:
                    corr = statistics.correlation(a, b)
                except Exception:
                    continue
                if math.isfinite(corr):
                    correlations.append(float(corr))
        if not correlations:
            return 0.0
        return sum(correlations) / len(correlations)

    def _compute_edge_risk_profile(self) -> tuple[dict[str, float], float, str]:
        if not bool(getattr(self.params, "edge_weighted_risk_enabled", False)):
            return (
                {symbol: 1.0 for symbol in SYMBOLS_MAP.keys()},
                1.0,
                "EWR disabled",
            )

        lookback = max(int(getattr(self.params, "edge_risk_lookback_trades", 8)), 1)
        min_trades = max(int(getattr(self.params, "edge_risk_min_trades", 4)), 1)
        alpha = float(getattr(self.params, "edge_risk_z_alpha", 0.20))
        min_mult = max(float(getattr(self.params, "edge_risk_min_mult", 0.60)), 0.1)
        max_mult = max(float(getattr(self.params, "edge_risk_max_mult", 1.40)), min_mult)

        scores: dict[str, float] = {}
        for symbol in SYMBOLS_MAP.keys():
            hist = list(self.state.get(symbol, SymbolState()).recent_trade_returns_pct)[-lookback:]
            if len(hist) < min_trades:
                scores[symbol] = 0.0
                continue
            mean_r = sum(hist) / len(hist)
            std_r = statistics.pstdev(hist) if len(hist) > 1 else 0.0
            scores[symbol] = mean_r - (0.5 * std_r)

        vals = list(scores.values())
        mu = (sum(vals) / len(vals)) if vals else 0.0
        sigma = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        if sigma <= 1e-9:
            sigma = 1.0

        out: dict[str, float] = {}
        for symbol in SYMBOLS_MAP.keys():
            z = (scores[symbol] - mu) / sigma
            mult = 1.0 + (alpha * z)
            out[symbol] = min(max(mult, min_mult), max_mult)

        # Optional momentum tilt on top of EWR:
        # increase/decrease symbol risk by recent mean return, then renormalize to keep
        # average multiplier near 1.0, and clamp to configured guardrails.
        if bool(getattr(self.params, "edge_momentum_tilt_enabled", False)):
            mom_lb = max(int(getattr(self.params, "edge_momentum_lookback_trades", 4)), 1)
            mom_tilt = max(float(getattr(self.params, "edge_momentum_tilt", 0.0)), 0.0)
            if mom_tilt > 0:
                for symbol in SYMBOLS_MAP.keys():
                    hist = list(self.state.get(symbol, SymbolState()).recent_trade_returns_pct)[-mom_lb:]
                    mean_r = (sum(hist) / len(hist)) if hist else 0.0
                    # Scale by 10 so +/-10% recent mean maps close to full tilt effect.
                    scaled = max(min(mean_r / 10.0, 1.0), -1.0)
                    mom_mult = max(0.20, 1.0 + (mom_tilt * scaled))
                    out[symbol] *= mom_mult

                avg_mult = (sum(out.values()) / len(out)) if out else 1.0
                if avg_mult <= 1e-9:
                    avg_mult = 1.0
                for symbol in SYMBOLS_MAP.keys():
                    normalized = out[symbol] / avg_mult
                    out[symbol] = min(max(normalized, min_mult), max_mult)
        exposure = 1.0
        notes: list[str] = []
        if bool(getattr(self.params, "edge_multi_logic_enabled", False)):
            # Breadth gate: if too few symbols have positive recent edge, reduce gross exposure.
            breadth_floor = max(float(getattr(self.params, "edge_breadth_floor", 0.0)), 0.0)
            breadth_exposure = min(max(float(getattr(self.params, "edge_breadth_exposure", 1.0)), 0.1), 1.0)
            mom_lb = max(int(getattr(self.params, "edge_momentum_lookback_trades", 4)), 1)
            positive = 0
            for symbol in SYMBOLS_MAP.keys():
                hist = list(self.state.get(symbol, SymbolState()).recent_trade_returns_pct)[-mom_lb:]
                mean_r = (sum(hist) / len(hist)) if hist else 0.0
                if mean_r > 0.0:
                    positive += 1
            breadth = positive / max(len(SYMBOLS_MAP.keys()), 1)
            if breadth_floor > 0 and breadth < breadth_floor:
                exposure = min(exposure, breadth_exposure)
                notes.append(f"breadth={breadth:.2f}<{breadth_floor:.2f}")

            # Regime gate: portfolio-volatility and win-rate based exposure reduction.
            regime_lb = max(int(getattr(self.params, "edge_regime_lookback_trades", 3)), 1)
            regime_hist = self._portfolio_recent_returns_pct(regime_lb)
            if len(regime_hist) >= regime_lb:
                rvol = statistics.pstdev(regime_hist) if len(regime_hist) > 1 else 0.0
                rwin = sum(1 for x in regime_hist if x > 0.0) / len(regime_hist)
                vol_soft = float(getattr(self.params, "edge_regime_vol_soft", 99.0))
                vol_hard = float(getattr(self.params, "edge_regime_vol_hard", 99.0))
                win_soft = float(getattr(self.params, "edge_regime_win_soft", -1.0))
                win_hard = float(getattr(self.params, "edge_regime_win_hard", -1.0))
                exp_soft = min(max(float(getattr(self.params, "edge_regime_exposure_soft", 1.0)), 0.1), 1.0)
                exp_hard = min(max(float(getattr(self.params, "edge_regime_exposure_hard", 1.0)), 0.1), 1.0)
                if rvol >= vol_hard or rwin <= win_hard:
                    exposure = min(exposure, exp_hard)
                    notes.append(f"regime_hard(vol={rvol:.2f},win={rwin:.2f})")
                elif rvol >= vol_soft or rwin <= win_soft:
                    exposure = min(exposure, exp_soft)
                    notes.append(f"regime_soft(vol={rvol:.2f},win={rwin:.2f})")

            # Drawdown throttle from synthetic recent portfolio equity curve.
            dd_hist = self._portfolio_recent_returns_pct(30)
            if dd_hist:
                eq = 1.0
                peak = 1.0
                for r in dd_hist:
                    eq *= (1.0 + (float(r) / 100.0))
                    peak = max(peak, eq)
                dd = (peak - eq) / peak if peak > 0 else 0.0
                dd1 = max(float(getattr(self.params, "edge_dd_level1", 1.0)), 0.0)
                dd2 = max(float(getattr(self.params, "edge_dd_level2", 1.0)), dd1)
                dd_exp1 = min(max(float(getattr(self.params, "edge_dd_exposure1", 1.0)), 0.1), 1.0)
                dd_exp2 = min(max(float(getattr(self.params, "edge_dd_exposure2", 1.0)), 0.1), 1.0)
                if dd >= dd2:
                    exposure = min(exposure, dd_exp2)
                    notes.append(f"dd_hard={dd:.2%}")
                elif dd >= dd1:
                    exposure = min(exposure, dd_exp1)
                    notes.append(f"dd_soft={dd:.2%}")

            # Correlation cap: reduce gross exposure when symbols are highly correlated.
            corr_lb = max(int(getattr(self.params, "edge_corr_lookback_trades", 3)), 2)
            avg_corr = self._average_pair_correlation(corr_lb)
            corr_soft = float(getattr(self.params, "edge_corr_soft", 2.0))
            corr_hard = float(getattr(self.params, "edge_corr_hard", 2.0))
            corr_exp_soft = min(max(float(getattr(self.params, "edge_corr_exposure_soft", 1.0)), 0.1), 1.0)
            corr_exp_hard = min(max(float(getattr(self.params, "edge_corr_exposure_hard", 1.0)), 0.1), 1.0)
            if avg_corr >= corr_hard:
                exposure = min(exposure, corr_exp_hard)
                notes.append(f"corr_hard={avg_corr:.2f}")
            elif avg_corr >= corr_soft:
                exposure = min(exposure, corr_exp_soft)
                notes.append(f"corr_soft={avg_corr:.2f}")

        exposure = min(max(exposure, 0.10), 1.0)
        summary = f"exposure={exposure:.2f}"
        if notes:
            summary += " (" + ", ".join(notes) + ")"
        return out, exposure, summary

    async def process(
        self,
        signals: dict[str, dict[str, Any]],
        equity: float,
    ) -> list[str]:
        logs: list[str] = []
        self._risk_mult_by_symbol, self._portfolio_exposure_mult, self._risk_profile_summary = (
            self._compute_edge_risk_profile()
        )
        logs.append(f"[INFO] Edge risk profile: {self._risk_profile_summary}")
        for symbol, snapshot in signals.items():
            try:
                symbol_logs = await self._process_symbol(
                    symbol=symbol,
                    snapshot=snapshot,
                    equity=equity,
                )
            except Exception as exc:
                # Never let a single-symbol failure break the entire cycle.
                ticker = SYMBOLS_MAP.get(symbol, symbol)
                logs.append(f"[WARN] {ticker} Symbol processing error (skipped this cycle): {exc}")
                continue
            else:
                logs.extend(symbol_logs)
        if not BOT_SAFE_MODE:
            self._persist_state()
        return logs

    async def _process_symbol(
        self,
        symbol: str,
        snapshot: dict[str, Any],
        equity: float,
    ) -> list[str]:
        logs: list[str] = []
        st = self.state[symbol]
        ticker = SYMBOLS_MAP[symbol]
        strategy_mode = self._strategy_mode_for_symbol(symbol)
        atr_stop_mult, atr_tp_r, atr_be_r = self._atr_dynamic_params_for_symbol(symbol)
        profit_lock_trigger_pct, profit_lock_stop_pct = self._profit_lock_params_for_symbol(symbol)

        # When the market is closed we run in "manage-only" mode:
        # - never allow pending/new entries
        # - allow active position management to proceed based on last known bars and broker quotes
        market_open = bool(snapshot.get("market_open", True))
        if not market_open and st.status == "PENDING_ENTRY":
            try:
                if st.pending_order_id:
                    await self.client.cancel_order(st.pending_order_id)
            except T212APIError:
                pass
            self._reset_symbol(symbol)
            logs.append(f"[WARN] {ticker} Pending entry cancelled (market closed manage-only mode).")
            return logs

        # If entry is blocked (market closed / stale / paused), still allow ACTIVE management,
        # but do not allow new entries.
        entry_blocked = bool(snapshot.get("entry_blocked", False))
        if entry_blocked and st.status in {"SCANNING", "PENDING_ENTRY"}:
            logs.append(f"[{symbol}] Entry blocked: {snapshot.get('reason', 'blocked')}")
            return logs

        if not snapshot.get("ready"):
            logs.append(f"[{symbol}] Data not ready: {snapshot.get('reason', 'unknown')}")
            return logs

        bar_ts = self._parse_utc_timestamp(snapshot.get("timestamp"))
        if bar_ts is None:
            bar_ts = datetime.now(tz=ZoneInfo("UTC"))
        bar_day_key = bar_ts.date().isoformat()
        if st.last_bar_date_utc != bar_day_key:
            st.last_bar_date_utc = bar_day_key
            st.session_open_bar_timestamp_utc = bar_ts.isoformat()

        # Reconcile active local state with broker quantity to auto-heal stale states.
        if st.status in {"UNIT1_ACTIVE", "UNIT2_ACTIVE", "ATR_ACTIVE"}:
            try:
                live_qty_for_reconcile = await self.client.get_position_quantity(ticker=ticker)
            except T212APIError as exc:
                logs.append(f"[WARN] {ticker} Active-state reconciliation skipped due sync error: {exc}")
            else:
                if self._to_whole_shares(live_qty_for_reconcile) <= 0:
                    st.flat_sync_miss_count = int(st.flat_sync_miss_count) + 1
                    if st.flat_sync_miss_count >= 2:
                        stale_status = st.status
                        self._reset_symbol(symbol)
                        logs.append(
                            f"[WARN] {ticker} Reset stale local state ({stale_status}); "
                            "broker shows no open position for 2 consecutive cycles."
                        )
                        return logs
                else:
                    st.flat_sync_miss_count = 0

        if st.status in {"UNIT1_ACTIVE", "UNIT2_ACTIVE", "ATR_ACTIVE"}:
            if await self._maybe_reconcile_broker_protective_stop(
                symbol=symbol, ticker=ticker, st=st, logs=logs
            ):
                return logs

        side_signal = snapshot["signal_side"]
        high = float(snapshot["signal_high"])
        low = float(snapshot["signal_low"])
        close = float(snapshot.get("close", high))
        atr_5m = float(snapshot["atr_5m"])
        atr_15m = float(snapshot.get("atr_15m", 0.0) or 0.0)

        # Enforce long-only execution state for Trading 212 Invest/Cash accounts.
        if st.side not in (None, "long"):
            if st.status == "PENDING_ENTRY" and st.pending_order_id:
                try:
                    await self.client.cancel_order(st.pending_order_id)
                except T212APIError:
                    # State is reset regardless; failure to cancel should not block loop progression.
                    pass
            self._reset_symbol(symbol)
            logs.append(f"[WARN] {ticker} Non-long legacy state detected and reset (Long-Only mode).")
            return logs

        if st.status == "SCANNING":
            # Safety guard: if broker already reports inventory for this symbol while local
            # state is SCANNING, do not allow a fresh entry (prevents duplicate stacking
            # from multi-instance runs or stale local state).
            try:
                live_qty = await self.client.get_position_quantity(ticker=ticker)
            except T212APIError as exc:
                logs.append(f"[WARN] {ticker} Portfolio sync failed while scanning: {exc}")
                return logs
            if self._to_whole_shares(live_qty) >= 1:
                # If we previously attempted a forced exit, stay in a reconciliation loop until
                # the broker position is actually flat. This prevents confusing "SCANNING but still
                # holding" warnings and avoids accidental re-entry while an exit is pending.
                if st.forced_exit_order_id or st.forced_exit_attempts > 0:
                    await self._reconcile_forced_exit(
                        symbol=symbol,
                        ticker=ticker,
                        st=st,
                        bar_ts=bar_ts,
                        logs=logs,
                    )
                    return logs
                # Auto-detect "exit in progress" even if local state was reset (e.g., restart overnight):
                # if there is already a pending market SELL for this ticker, do not spam warnings—just
                # treat it as FORCED_EXIT_PENDING and wait for broker to flatten.
                if await self._has_pending_market_exit(ticker=ticker):
                    st.status = "FORCED_EXIT_PENDING"
                    logs.append(
                        f"[INFO] [{symbol}] Broker position exists and a market SELL is pending; "
                        "waiting for exit fill (no re-entry)."
                    )
                    return logs
                adopted = await self._adopt_broker_position_if_needed(
                    symbol=symbol,
                    ticker=ticker,
                    st=st,
                    bar_ts=bar_ts,
                    high=high,
                    atr_5m=atr_5m,
                    strategy_mode=strategy_mode,
                    atr_stop_mult=atr_stop_mult,
                    logs=logs,
                )
                if not adopted:
                    logs.append(
                        f"[WARN] {ticker} Existing broker position detected while local state is SCANNING. "
                        "Skipping new entry to avoid duplicate exposure."
                    )
                    return logs
                # If we adopted successfully, continue processing as an ACTIVE position immediately.

            if side_signal == "short":
                logs.append(
                    f"[INFO] {ticker} Short signal detected but ignored (Account is strictly Long-Only)."
                )
                return logs

            if side_signal == "long":
                # Spread protection: skip new order creation during EU open buffer.
                if self._is_eu_open_buffer_active():
                    logs.append(f"[WARN] {ticker} Open buffer active (09:00-09:15 CET), skipping new entry.")
                    return logs

                # Trend-strength filter: require 15m EMA rising (slope up) AND 15m DTosc bullish.
                # This avoids long entries in sideways/choppy regimes where most losses occur.
                if self.params.trend_strength_filter_enabled:
                    ema_15m = snapshot.get("ema_15m")
                    prev_ema_15m = snapshot.get("prev_ema_15m")
                    fast_15m = snapshot.get("fast_15m")
                    slow_15m = snapshot.get("slow_15m")
                    if (
                        ema_15m is None or prev_ema_15m is None
                        or fast_15m is None or slow_15m is None
                        or not (ema_15m > prev_ema_15m and fast_15m > slow_15m)
                    ):
                        logs.append(
                            f"[INFO] {ticker} Trend-strength filter: 15m EMA slope or DTosc not bullish; skipping entry."
                        )
                        return logs

                entry = high
                if strategy_mode == "ATR":
                    risk_distance = atr_stop_mult * atr_5m
                else:
                    risk_distance = self.params.atr_multiplier * atr_5m
                stop_loss = entry - risk_distance
                risk_distance_per_share = abs(entry - stop_loss)
                if risk_distance_per_share <= 0 or entry <= 0:
                    logs.append(f"[{symbol}] Invalid risk distance, skipping setup.")
                    return logs

                # Whipsaw protection: reject entries where initial stop distance is too tight.
                min_stop_distance_pct = risk_distance_per_share / entry
                if min_stop_distance_pct < 0.002:
                    logs.append(
                        f"[WARN] {ticker} Stop loss too tight (<0.2%), skipping to avoid spread execution."
                    )
                    return logs

                # Risk-based quantity from stop distance.
                risk_mult = float(self._risk_mult_by_symbol.get(symbol, 1.0))
                risk_budget = equity * RISK_PCT * risk_mult * float(self._portfolio_exposure_mult)
                risk_qty = risk_budget / risk_distance_per_share
                try:
                    free_funds = await self.client.get_free_funds()
                except T212APIError as exc:
                    logs.append(f"[WARN] {ticker} Free funds fetch failed, skipping entry: {exc}")
                    return logs

                # Sizing guardrail combines free cash availability and equity cap.
                max_allowed_cost = min(free_funds * 0.95, equity * MAX_ALLOCATION_PCT)
                if max_allowed_cost <= 0:
                    logs.append(f"[WARN] {ticker} No free trading funds available, skipping entry.")
                    return logs

                proposed_cost = risk_qty * entry
                max_qty = max_allowed_cost / entry
                final_qty = min(risk_qty, max_qty)
                qty_total = self._to_whole_shares(final_qty)
                if proposed_cost > max_allowed_cost:
                    logs.append(
                        f"[INFO] Position size for {symbol} capped by free funds/equity limits."
                    )
                if qty_total < 1:
                    logs.append(f"[WARN] {ticker} Calculated quantity is less than 1 share. Skipping entry.")
                    return logs
                logs.append(
                    f"[INFO] {ticker} EWR risk multiplier={risk_mult:.3f} "
                    f"global_exposure={float(self._portfolio_exposure_mult):.2f} "
                    f"(risk_budget={risk_budget:.2f})."
                )

                if BOT_SAFE_MODE:
                    logs.append(
                        f"[{symbol}] SAFE_MODE: skipping stop order placement "
                        f"{side_signal.upper()} stop={entry:.4f} qty={qty_total}"
                    )
                    return logs

                try:
                    resp = await self._place_stop_order(
                        ticker=ticker,
                        qty=int(qty_total),
                        stop_price=entry,
                    )
                    st.status = "PENDING_ENTRY"
                    st.side = side_signal
                    st.pending_order_id = str(resp.get("id", "unknown"))
                    st.pending_stop_price = entry
                    st.stop_loss = stop_loss
                    st.risk_distance = risk_distance
                    st.qty_total = qty_total
                    st.entry_price = None
                    logs.append(
                        f"[{symbol}] PENDING_ENTRY {side_signal.upper()} mode={strategy_mode} "
                        f"stop={entry:.4f} sl={stop_loss:.4f} qty={qty_total}"
                    )
                    self._schedule_email_alert(
                        subject=f"Pending Entry - {symbol}",
                        body=(
                            f"Symbol: {symbol}\n"
                            f"Type: {side_signal.upper()} STOP\n"
                            f"Price: {entry:.4f}"
                        ),
                    )
                except T212APIError as exc:
                    logs.append(f"[{symbol}] Failed to place stop order: {exc}")
                    self._schedule_email_alert(
                        subject=f"Critical Error - Order Placement ({symbol})",
                        body=(
                            f"Symbol: {symbol}\n"
                            "Action: Stop order placement failed\n"
                            f"Error: {exc}"
                        ),
                    )
            return logs

        if st.status == "PENDING_ENTRY":
            if not st.side or st.pending_stop_price is None:
                self._reset_symbol(symbol)
                logs.append(f"[{symbol}] Corrupt pending state reset.")
                return logs

            stop_crossed = (
                st.side == "long" and high >= st.pending_stop_price
            ) or (
                st.side == "short" and low <= st.pending_stop_price
            )
            try:
                portfolio_qty = await self.client.get_position_quantity(ticker=ticker)
            except T212APIError as exc:
                portfolio_qty = 0.0
                logs.append(f"[WARN] {ticker} Portfolio sync failed while pending: {exc}")

            # IMPORTANT: For broker stop-orders, price crossing the stop level does NOT guarantee fill.
            # Only treat entry as filled once broker portfolio reports inventory.
            filled_qty = self._to_whole_shares(portfolio_qty)
            if st.side == "long" and filled_qty >= 1:
                logs.append(
                    f"[INFO] {ticker} Pending entry confirmed filled from portfolio state (qty={filled_qty})."
                )
                filled = True
            else:
                filled = False

            if stop_crossed and not filled:
                st.pending_entry_cross_streak = int(st.pending_entry_cross_streak) + 1

                # If the stop level is crossed but there's still no inventory, the broker order might have been
                # cancelled/rejected/expired. Reconcile against broker pending orders and reset if the order is gone.
                # This prevents endless "crossed but no inventory" loops.
                order_missing = False
                if st.pending_order_id and st.pending_order_id != "unknown":
                    try:
                        pending = await self.client.get_pending_orders()
                    except T212APIError as exc:
                        pending = []
                        logs.append(f"[WARN] {ticker} Pending-order fetch failed while pending entry: {exc}")
                    broker_ids = {
                        str(o.get("id"))
                        for o in pending
                        if isinstance(o, dict) and o.get("id") is not None
                    }
                    if st.pending_order_id not in broker_ids:
                        order_missing = True

                if order_missing and st.pending_entry_cross_streak >= 2:
                    logs.append(
                        f"[WARN] {ticker} Entry stop crossed but broker pending order id={st.pending_order_id} "
                        "is not present; resetting pending state so a fresh order can be placed."
                    )
                    self._reset_symbol(symbol)
                    return logs

                logs.append(
                    f"[INFO] {ticker} Entry stop level crossed but no inventory yet; staying PENDING_ENTRY "
                    f"(streak={st.pending_entry_cross_streak})."
                )
                # If price has crossed the stop, avoid trailing/cancelling logic (order may be in broker trigger/fill path).
                return logs

            if filled:
                st.status = "ATR_ACTIVE" if strategy_mode == "ATR" else "UNIT1_ACTIVE"
                st.entry_price = st.pending_stop_price
                st.pending_order_id = None
                st.pending_entry_cross_streak = 0
                st.highest_high_since_entry = high
                st.lowest_low_since_entry = low
                st.missing_protective_stop = False
                st.break_even_moved = False
                st.profit_lock_moved = False
                st.entry_timestamp_utc = datetime.now(tz=ZoneInfo("UTC")).isoformat()
                st.morning_protect_applied = False
                st.flat_sync_miss_count = 0
                if st.risk_distance is None or st.entry_price is None:
                    self._reset_symbol(symbol)
                    logs.append(f"[{symbol}] Invalid fill state reset.")
                    return logs

                qty_total_shares = self._to_whole_shares(st.qty_total)
                unit1_qty = qty_total_shares // 2
                unit2_qty = qty_total_shares - unit1_qty
                if strategy_mode == "ATR":
                    st.unit1_qty = 0.0
                    st.unit2_qty = float(qty_total_shares)
                    st.unit1_tp_price = (
                        st.entry_price + (atr_tp_r * st.risk_distance)
                        if st.side == "long"
                        else st.entry_price - (atr_tp_r * st.risk_distance)
                    )
                else:
                    st.unit1_qty = unit1_qty
                    st.unit2_qty = unit2_qty
                    st.unit1_tp_price = (
                        st.entry_price + (self.params.unit1_tp_rr * st.risk_distance)
                        if st.side == "long"
                        else st.entry_price - (self.params.unit1_tp_rr * st.risk_distance)
                    )

                # Give broker inventory a moment to settle before placing sell-side exits.
                await asyncio.sleep(3)

                # Synchronized Exit (Variant B): no TP limit order at broker.
                st.unit1_order_id = None
                if qty_total_shares < 1:
                    st.unit2_stop_order_id = None
                    st.missing_protective_stop = True
                    logs.append(
                        f"[WARN] {ticker} Initial SL placement skipped because quantity is below 1 share."
                    )
                    return logs

                stop_ready = await self._ensure_initial_protective_stop(
                    symbol=symbol,
                    ticker=ticker,
                    st=st,
                    logs=logs,
                    expected_qty=qty_total_shares,
                )
                if not stop_ready:
                    self._schedule_email_alert(
                        subject=f"Warning - Initial SL Pending ({symbol})",
                        body=(
                            f"Symbol: {symbol}\n"
                            "Action: Initial stop-loss is still pending due inventory settlement race.\n"
                            "Recovery: Bot will retry SL placement in the next cycle automatically."
                        ),
                    )
                    return logs

                if strategy_mode == "ATR":
                    logs.append(
                        f"[{symbol}] ENTRY FILLED mode=ATR at {st.entry_price:.4f}; "
                        f"atrTP={float(st.unit1_tp_price):.4f}; "
                        f"broker SL={float(st.stop_loss):.4f} for 100% qty"
                    )
                    # Telegram notification: entry
                    self._schedule_telegram_alert(
                        f"🚀 [ENTRY] LONG on {symbol} | Entry: €{float(st.entry_price):.2f} | "
                        f"SL: €{float(st.stop_loss):.2f} | TP: €{float(st.unit1_tp_price):.2f}"
                    )
                else:
                    logs.append(
                        f"[{symbol}] ENTRY FILLED at {st.entry_price:.4f}; "
                        f"virtual TP={float(st.unit1_tp_price):.4f}; "
                        f"broker SL={float(st.stop_loss):.4f} for 100% qty"
                    )
                    # Telegram notification: entry
                    self._schedule_telegram_alert(
                        f"🚀 [ENTRY] LONG on {symbol} | Entry: €{float(st.entry_price):.2f} | "
                        f"SL: €{float(st.stop_loss):.2f} | TP: €{float(st.unit1_tp_price):.2f}"
                    )
                self._schedule_email_alert(
                    subject=f"Trade Filled - {symbol}",
                    body=(
                        f"Symbol: {symbol}\n"
                        f"Mode: {strategy_mode}\n"
                        f"Entry: {float(st.entry_price):.4f}\n"
                        f"Virtual TP: {float(st.unit1_tp_price):.4f}\n"
                        f"Initial SL: {float(st.stop_loss):.4f}\n"
                        "Status: Initial SL active for full position"
                    ),
                )
                return logs

            # Trailing or cancelling pending order based on Miner momentum behavior.
            if st.side == "long":
                if snapshot["fast_5m"] > snapshot["slow_5m"]:
                    new_stop = min(st.pending_stop_price, high)
                    if new_stop != st.pending_stop_price:
                        try:
                            if st.pending_order_id:
                                await self.client.cancel_order(st.pending_order_id)
                            resp = await self._place_stop_order(
                                ticker=ticker,
                                qty=int(self._to_whole_shares(st.qty_total)),
                                stop_price=new_stop,
                            )
                            st.pending_order_id = str(resp.get("id", "unknown"))
                            st.pending_stop_price = new_stop
                            logs.append(f"[{symbol}] Trailed LONG pending stop to {new_stop:.4f}")
                        except T212APIError as exc:
                            if self._is_order_not_found_error(exc):
                                logs.append(
                                    f"[INFO] {ticker} Pending order no longer exists; waiting for portfolio sync."
                                )
                            else:
                                logs.append(f"[{symbol}] Failed to trail LONG pending order: {exc}")
                else:
                    try:
                        if st.pending_order_id:
                            await self.client.cancel_order(st.pending_order_id)
                    except T212APIError as exc:
                        if self._is_order_not_found_error(exc):
                            logs.append(
                                f"[INFO] {ticker} Pending order already gone; waiting for portfolio sync."
                            )
                            return logs
                        logs.append(f"[{symbol}] Pending cancel failed: {exc}")
                    self._reset_symbol(symbol)
                    logs.append(f"[{symbol}] LONG momentum reversed, pending order cancelled.")
            else:
                # Hard long-only safeguard: short pending entries are not allowed.
                try:
                    if st.pending_order_id:
                        await self.client.cancel_order(st.pending_order_id)
                except T212APIError as exc:
                    logs.append(f"[{symbol}] Pending cancel failed: {exc}")
                self._reset_symbol(symbol)
                logs.append(f"[WARN] {ticker} Short pending entry blocked and cleared (Long-Only mode).")
            return logs

        # Broker price fallback for ACTIVE position management.
        # If the candle feed (yfinance 5m) lags/stalls, stops won't tighten even when Trading212 price
        # has moved significantly. For ACTIVE states only, blend broker currentPrice into high/low/close
        # so BE/profit-lock/trailing logic can react.
        if st.status in {"UNIT1_ACTIVE", "UNIT2_ACTIVE", "ATR_ACTIVE"}:
            broker_cp = await self._broker_current_price_safe(ticker=ticker)
            now_utc = datetime.now(tz=_UTC)
            is_stale = (now_utc - bar_ts).total_seconds() > _max_stale_age_seconds()
            if broker_cp is not None and broker_cp > 0:
                drift = abs(broker_cp - close) / max(close, 1e-9)
                if is_stale:
                    market_open = _is_market_open_now(symbol, now_utc=now_utc)
                    level = "WARN" if market_open else "INFO"
                    suffix = "" if market_open else " (outside expected session)"
                    logs.append(
                        f"[{level}] {ticker} Candle feed stale{suffix} (bar_ts={bar_ts.isoformat()}); "
                        f"using broker currentPrice={broker_cp:.4f} as management fallback."
                    )
                    # When stale, do NOT use old candle low/high for stop-hit decisions.
                    # Treat broker currentPrice as the effective bar OHLC proxy.
                    close = float(broker_cp)
                    high = float(broker_cp)
                    low = float(broker_cp)
                elif drift >= 0.005:
                    logs.append(
                        f"[INFO] {ticker} Candle/price drift detected (bar_ts={bar_ts.isoformat()}); "
                        f"candleClose={close:.4f} brokerCurrentPrice={broker_cp:.4f} "
                        f"(drift={drift * 100.0:.2f}%)."
                    )
                    # Minor drift: blend only to expand the range, but keep candle semantics.
                    high = max(float(high), float(broker_cp))
                    low = min(float(low), float(broker_cp))
                else:
                    # Minor drift: blend only to expand the range, but keep candle semantics.
                    high = max(float(high), float(broker_cp))
                    low = min(float(low), float(broker_cp))

        if st.status == "ATR_ACTIVE":
            if not st.side or st.entry_price is None or st.stop_loss is None or st.risk_distance is None:
                self._reset_symbol(symbol)
                logs.append(f"[{symbol}] Corrupt ATR state reset.")
                return logs

            expected_qty = self._to_whole_shares(st.qty_total)
            if expected_qty >= 1 and (st.missing_protective_stop or not st.unit2_stop_order_id):
                stop_ready = await self._ensure_initial_protective_stop(
                    symbol=symbol,
                    ticker=ticker,
                    st=st,
                    logs=logs,
                    expected_qty=expected_qty,
                )
                if not stop_ready:
                    logs.append(
                        f"[WARN] {ticker} ATR mode position remains without confirmed protective SL; retry scheduled."
                    )
                    return logs
                logs.append(f"[INFO] {ticker} ATR mode protective SL restored after settlement sync.")

            if st.highest_high_since_entry is None:
                st.highest_high_since_entry = high
            else:
                st.highest_high_since_entry = max(st.highest_high_since_entry, high)
            if st.lowest_low_since_entry is None:
                st.lowest_low_since_entry = low
            else:
                st.lowest_low_since_entry = min(st.lowest_low_since_entry, low)

            await self._maybe_apply_morning_protect_stop(
                symbol=symbol,
                ticker=ticker,
                st=st,
                bar_ts=bar_ts,
                high=high,
                close=close,
                logs=logs,
                context_label="atr protective SL",
            )

            # ATR mode break-even: move stop to entry after configured R-multiple.
            if (
                st.side == "long"
                and not st.break_even_moved
                and high >= float(st.entry_price) + (atr_be_r * float(st.risk_distance))
            ):
                break_even_stop = float(st.entry_price)
                current_stop = float(st.stop_loss)
                if break_even_stop > current_stop:
                    try:
                        live_qty = await self.client.get_position_quantity(ticker=ticker)
                    except T212APIError as exc:
                        logs.append(
                            f"[WARN] {ticker} ATR break-even update skipped because live quantity sync failed: {exc}"
                        )
                        return logs

                    runner_qty = self._to_whole_shares(live_qty)
                    if runner_qty <= 0:
                        logs.append(f"[INFO] {ticker} ATR break-even skipped because position is already flat.")
                        self._reset_symbol(symbol)
                        return logs

                    cancelled = await self._cancel_order_if_exists(
                        st.unit2_stop_order_id,
                        symbol=symbol,
                        ticker=ticker,
                        logs=logs,
                        context_label="atr protective SL",
                    )
                    if not cancelled:
                        logs.append(
                            f"[WARN] {ticker} ATR break-even update aborted because SL cancellation failed."
                        )
                        return logs

                    stop_qty = self._signed_exit_qty(runner_qty, st.side)
                    replacement = await self._place_exit_order_with_retry(
                        place_order=lambda: self._place_stop_order(
                            ticker=ticker,
                            qty=int(stop_qty),
                            stop_price=break_even_stop,
                        ),
                        symbol=symbol,
                        order_label="ATR break-even SL stop",
                        logs=logs,
                        max_attempts=5,
                        retry_delay_seconds=2.0,
                    )
                    if not replacement:
                        logs.append(
                            f"[WARN] {ticker} ATR break-even SL placement failed; keeping previous stop."
                        )
                        return logs
                    st.unit2_stop_order_id = str(replacement.get("id", "unknown"))
                    st.stop_loss = break_even_stop
                st.break_even_moved = True
                logs.append(
                    f"[UPDATE] ATR mode reached +{atr_be_r:.2f}R. "
                    "Stop Loss moved to break-even (Entry Price)."
                )
                # Telegram notification: break-even (ATR)
                self._schedule_telegram_alert(
                    f"🛡️ [UPDATE] {symbol} reached +{atr_be_r:.2f}R. "
                    f"Stop Loss moved to Break-Even (€{float(st.entry_price):.2f})."
                )

            # Profit-lock upgrade: at higher unrealized gain, lift stop above entry.
            if (
                st.side == "long"
                and st.entry_price is not None
                and profit_lock_trigger_pct > 0
                and profit_lock_stop_pct > 0
                and high >= float(st.entry_price) * (1.0 + profit_lock_trigger_pct)
            ):
                lock_stop = float(st.entry_price) * (1.0 + profit_lock_stop_pct)
                current_stop = float(st.stop_loss)
                if lock_stop > current_stop:
                    try:
                        live_qty = await self.client.get_position_quantity(ticker=ticker)
                    except T212APIError as exc:
                        logs.append(f"[WARN] {ticker} ATR profit-lock update skipped: {exc}")
                        return logs

                    runner_qty = self._to_whole_shares(live_qty)
                    if runner_qty <= 0:
                        logs.append(f"[INFO] {ticker} ATR profit-lock skipped because position is already flat.")
                        self._reset_symbol(symbol)
                        return logs

                    cancelled = await self._cancel_order_if_exists(
                        st.unit2_stop_order_id,
                        symbol=symbol,
                        ticker=ticker,
                        logs=logs,
                        context_label="atr protective SL",
                    )
                    if not cancelled:
                        logs.append(f"[WARN] {ticker} ATR profit-lock update aborted; SL cancellation failed.")
                        return logs

                    stop_qty = self._signed_exit_qty(runner_qty, st.side)
                    replacement = await self._place_exit_order_with_retry(
                        place_order=lambda: self._place_stop_order(
                            ticker=ticker,
                            qty=int(stop_qty),
                            stop_price=lock_stop,
                        ),
                        symbol=symbol,
                        order_label="ATR profit-lock SL stop",
                        logs=logs,
                        max_attempts=5,
                        retry_delay_seconds=2.0,
                    )
                    if not replacement:
                        logs.append(f"[WARN] {ticker} ATR profit-lock SL placement failed.")
                        return logs
                    st.unit2_stop_order_id = str(replacement.get("id", "unknown"))
                    st.stop_loss = lock_stop
                    st.profit_lock_moved = True
                    logs.append(
                        f"[UPDATE] ATR profit reached +{profit_lock_trigger_pct * 100.0:.2f}%. "
                        f"Stop Loss lifted to +{profit_lock_stop_pct * 100.0:.2f}%."
                    )

            atr_stop_hit = (st.side == "long" and low <= st.stop_loss) or (
                st.side == "short" and high >= st.stop_loss
            )
            if atr_stop_hit:
                try:
                    live_qty = await self._broker_open_quantity_stable(ticker)
                    if live_qty <= 0:
                        logs.append(
                            f"[INFO] {ticker} ATR stop condition hit but position is already flat; resetting state."
                        )
                    else:
                        close_qty = self._signed_exit_qty(live_qty, st.side)
                        await self.client.close_position(ticker=ticker, qty=int(close_qty))
                        logs.append(f"[{symbol}] ATR stop-loss hit, closed full position.")
                except T212APIError as exc:
                    if self._is_inventory_settlement_race_error(exc):
                        logs.append(
                            f"[INFO] {ticker} ATR stop close skipped because broker reports no owned shares."
                        )
                    else:
                        logs.append(f"[{symbol}] ATR stop close failed: {exc}")
                if st.entry_price is not None and st.stop_loss is not None and float(st.entry_price) > 0:
                    pnl_pct = ((float(st.stop_loss) - float(st.entry_price)) / float(st.entry_price)) * 100.0
                    self._record_trade_return(symbol, pnl_pct, logs, reason="atr_stop")
                # Telegram notification: exit (stop)
                if st.stop_loss is not None:
                    self._schedule_telegram_alert(
                        f"❌ [EXIT] {symbol} closed at Stop Loss (€{float(st.stop_loss):.2f})."
                    )
                self._reset_symbol(symbol)
                return logs

            atr_tp_hit = (
                st.side == "long" and close >= float(st.unit1_tp_price)
            ) or (
                st.side == "short" and low <= float(st.unit1_tp_price)
            )
            if atr_tp_hit:
                try:
                    live_qty = await self.client.get_position_quantity(ticker=ticker)
                    if live_qty <= 0:
                        logs.append(
                            f"[INFO] {ticker} ATR target hit but position is already flat; resetting state."
                        )
                    else:
                        close_qty = self._signed_exit_qty(live_qty, st.side)
                        await self.client.close_position(ticker=ticker, qty=int(close_qty))
                        logs.append(
                            f"[{symbol}] ATR target hit at {float(st.unit1_tp_price):.4f}, closed full position."
                        )
                except T212APIError as exc:
                    if self._is_inventory_settlement_race_error(exc):
                        logs.append(
                            f"[INFO] {ticker} ATR target close skipped because broker reports no owned shares."
                        )
                    else:
                        logs.append(f"[{symbol}] ATR target close failed: {exc}")
                if st.entry_price is not None and st.unit1_tp_price is not None and float(st.entry_price) > 0:
                    pnl_pct = (
                        (float(st.unit1_tp_price) - float(st.entry_price)) / float(st.entry_price)
                    ) * 100.0
                    self._record_trade_return(symbol, pnl_pct, logs, reason="atr_target")
                # Telegram notification: exit (take profit)
                if st.unit1_tp_price is not None:
                    self._schedule_telegram_alert(
                        f"✅ [EXIT] {symbol} closed at Take Profit (€{float(st.unit1_tp_price):.2f})."
                    )
                self._reset_symbol(symbol)
                return logs
            return logs

        if st.status == "UNIT1_ACTIVE":
            if not st.side or st.entry_price is None or st.stop_loss is None:
                self._reset_symbol(symbol)
                logs.append(f"[{symbol}] Corrupt UNIT1 state reset.")
                return logs

            # Recovery path: keep retrying initial protective SL until broker confirms it.
            expected_qty = self._to_whole_shares(st.qty_total)
            if expected_qty >= 1 and (st.missing_protective_stop or not st.unit2_stop_order_id):
                stop_ready = await self._ensure_initial_protective_stop(
                    symbol=symbol,
                    ticker=ticker,
                    st=st,
                    logs=logs,
                    expected_qty=expected_qty,
                )
                if not stop_ready:
                    logs.append(
                        f"[WARN] {ticker} Position remains without confirmed protective SL; retry scheduled next cycle."
                    )
                    return logs
                logs.append(
                    f"[INFO] {ticker} Initial protective SL successfully restored after settlement sync."
                )

            if st.highest_high_since_entry is None:
                st.highest_high_since_entry = high
            else:
                st.highest_high_since_entry = max(st.highest_high_since_entry, high)
            if st.lowest_low_since_entry is None:
                st.lowest_low_since_entry = low
            else:
                st.lowest_low_since_entry = min(st.lowest_low_since_entry, low)

            await self._maybe_apply_morning_protect_stop(
                symbol=symbol,
                ticker=ticker,
                st=st,
                bar_ts=bar_ts,
                high=high,
                close=close,
                logs=logs,
                context_label="initial SL",
            )

            # Free-trade upgrade: once price reaches configured trigger, move SL to entry.
            if (
                st.side == "long"
                and not st.break_even_moved
                and st.entry_price is not None
                and high >= float(st.entry_price) * (1.0 + self.params.break_even_trigger_pct)
            ):
                break_even_stop = float(st.entry_price)
                current_stop = float(st.stop_loss)
                if break_even_stop > current_stop:
                    try:
                        live_qty = await self.client.get_position_quantity(ticker=ticker)
                    except T212APIError as exc:
                        logs.append(
                            f"[WARN] {ticker} Break-even update skipped because live quantity sync failed: {exc}"
                        )
                        return logs

                    runner_qty = self._to_whole_shares(live_qty)
                    if runner_qty <= 0:
                        logs.append(
                            f"[INFO] {ticker} Break-even update skipped because position is already flat."
                        )
                        self._reset_symbol(symbol)
                        return logs

                    cancelled = await self._cancel_order_if_exists(
                        st.unit2_stop_order_id,
                        symbol=symbol,
                        ticker=ticker,
                        logs=logs,
                        context_label="initial SL",
                    )
                    if not cancelled:
                        logs.append(
                            f"[WARN] {ticker} Break-even update aborted because initial SL cancellation failed."
                        )
                        return logs

                    stop_qty = self._signed_exit_qty(runner_qty, st.side)
                    replacement = await self._place_exit_order_with_retry(
                        place_order=lambda: self._place_stop_order(
                            ticker=ticker,
                            qty=int(stop_qty),
                            stop_price=break_even_stop,
                        ),
                        symbol=symbol,
                        order_label="Break-even SL stop",
                        logs=logs,
                        max_attempts=5,
                        retry_delay_seconds=2.0,
                    )
                    if not replacement:
                        logs.append(
                            f"[WARN] {ticker} Break-even SL placement failed; keeping previous protective stop."
                        )
                        return logs

                    st.unit2_stop_order_id = str(replacement.get("id", "unknown"))
                    st.stop_loss = break_even_stop
                st.break_even_moved = True
                trigger_pct = self.params.break_even_trigger_pct * 100.0
                logs.append(
                    f"[UPDATE] Price reached +{trigger_pct:.2f}% profit. "
                    "Stop Loss moved to break-even (Entry Price)."
                )
                # Telegram notification: break-even
                self._schedule_telegram_alert(
                    f"🛡️ [UPDATE] {symbol} moved +{trigger_pct:.2f}% in profit. "
                    f"Stop Loss moved to Break-Even (€{float(st.entry_price):.2f})."
                )

            # Profit-lock upgrade: once price reaches configured higher gain, lock profits.
            if (
                st.side == "long"
                and st.entry_price is not None
                and profit_lock_trigger_pct > 0
                and profit_lock_stop_pct > 0
                and high >= float(st.entry_price) * (1.0 + profit_lock_trigger_pct)
            ):
                lock_stop = float(st.entry_price) * (1.0 + profit_lock_stop_pct)
                current_stop = float(st.stop_loss)
                if lock_stop > current_stop:
                    try:
                        live_qty = await self.client.get_position_quantity(ticker=ticker)
                    except T212APIError as exc:
                        logs.append(f"[WARN] {ticker} Profit-lock update skipped: {exc}")
                        return logs

                    runner_qty = self._to_whole_shares(live_qty)
                    if runner_qty <= 0:
                        logs.append(
                            f"[INFO] {ticker} Profit-lock update skipped because position is already flat."
                        )
                        self._reset_symbol(symbol)
                        return logs

                    cancelled = await self._cancel_order_if_exists(
                        st.unit2_stop_order_id,
                        symbol=symbol,
                        ticker=ticker,
                        logs=logs,
                        context_label="protective SL",
                    )
                    if not cancelled:
                        logs.append(f"[WARN] {ticker} Profit-lock update aborted; SL cancellation failed.")
                        return logs

                    stop_qty = self._signed_exit_qty(runner_qty, st.side)
                    replacement = await self._place_exit_order_with_retry(
                        place_order=lambda: self._place_stop_order(
                            ticker=ticker,
                            qty=int(stop_qty),
                            stop_price=lock_stop,
                        ),
                        symbol=symbol,
                        order_label="Profit-lock SL stop",
                        logs=logs,
                        max_attempts=5,
                        retry_delay_seconds=2.0,
                    )
                    if not replacement:
                        logs.append(f"[WARN] {ticker} Profit-lock SL placement failed.")
                        return logs

                    st.unit2_stop_order_id = str(replacement.get("id", "unknown"))
                    st.stop_loss = lock_stop
                    st.profit_lock_moved = True
                    logs.append(
                        f"[UPDATE] Profit reached +{profit_lock_trigger_pct * 100.0:.2f}%. "
                        f"Stop Loss lifted to +{profit_lock_stop_pct * 100.0:.2f}%."
                    )

            # Optional: start ATR trailing already during UNIT1_ACTIVE (BASE mode),
            # but only after BE/profit-lock has moved the stop at least once.
            if (
                st.side == "long"
                and bool(self.params.unit1_trail_in_unit1_by_symbol.get(symbol, False))
                and (st.break_even_moved or st.profit_lock_moved)
                and st.highest_high_since_entry is not None
                and math.isfinite(atr_15m)
                and atr_15m > 0
            ):
                trail_stop = float(st.highest_high_since_entry) - (float(self.params.atr_trail_mult) * float(atr_15m))
                current_stop = float(st.stop_loss)
                if trail_stop > current_stop:
                    try:
                        live_qty = await self.client.get_position_quantity(ticker=ticker)
                    except T212APIError as exc:
                        logs.append(f"[WARN] {ticker} UNIT1 trailing update skipped: {exc}")
                        return logs

                    runner_qty = self._to_whole_shares(live_qty)
                    if runner_qty <= 0:
                        logs.append(
                            f"[INFO] {ticker} UNIT1 trailing update skipped because position is already flat."
                        )
                        self._reset_symbol(symbol)
                        return logs

                    cancelled = await self._cancel_order_if_exists(
                        st.unit2_stop_order_id,
                        symbol=symbol,
                        ticker=ticker,
                        logs=logs,
                        context_label="protective SL",
                    )
                    if not cancelled:
                        logs.append(f"[WARN] {ticker} UNIT1 trailing update aborted; SL cancellation failed.")
                        return logs

                    stop_qty = self._signed_exit_qty(runner_qty, st.side)
                    replacement = await self._place_exit_order_with_retry(
                        place_order=lambda: self._place_stop_order(
                            ticker=ticker,
                            qty=int(stop_qty),
                            stop_price=float(trail_stop),
                        ),
                        symbol=symbol,
                        order_label="UNIT1 trailing SL stop",
                        logs=logs,
                        max_attempts=5,
                        retry_delay_seconds=2.0,
                    )
                    if not replacement:
                        logs.append(f"[WARN] {ticker} UNIT1 trailing SL placement failed.")
                        return logs

                    st.unit2_stop_order_id = str(replacement.get("id", "unknown"))
                    st.stop_loss = float(trail_stop)
                    logs.append(
                        f"[UPDATE] UNIT1 trailing active. Stop Loss trailed to {float(trail_stop):.4f}."
                    )

            stop_hit = (st.side == "long" and low <= st.stop_loss) or (
                st.side == "short" and high >= st.stop_loss
            )
            if stop_hit:
                try:
                    # Broker-side stop orders can fill before this loop observes the state change.
                    # Sync live quantity first to avoid duplicate sell requests.
                    live_qty = await self._broker_open_quantity_stable(ticker)
                    if live_qty <= 0:
                        logs.append(
                            f"[INFO] {ticker} Stop-loss condition hit but position is already flat; resetting local state."
                        )
                    else:
                        close_qty = self._signed_exit_qty(live_qty, st.side)
                        await self.client.close_position(ticker=ticker, qty=int(close_qty))
                        logs.append(f"[{symbol}] Stop-loss hit, closed full position.")
                except T212APIError as exc:
                    if self._is_inventory_settlement_race_error(exc):
                        logs.append(
                            f"[INFO] {ticker} Stop-loss close skipped because broker reports no owned shares; treating as already closed."
                        )
                    else:
                        logs.append(f"[{symbol}] Failed stop close: {exc}")
                if st.entry_price is not None and st.stop_loss is not None and float(st.entry_price) > 0:
                    pnl_pct = ((float(st.stop_loss) - float(st.entry_price)) / float(st.entry_price)) * 100.0
                    self._record_trade_return(symbol, pnl_pct, logs, reason="unit1_stop")
                # Telegram notification: exit (stop)
                if st.stop_loss is not None:
                    self._schedule_telegram_alert(
                        f"❌ [EXIT] {symbol} closed at Stop Loss (€{float(st.stop_loss):.2f})."
                    )
                self._reset_symbol(symbol)
                return logs

            # Use closed-candle price as deterministic current market proxy for virtual TP.
            tp_hit = (
                st.side == "long" and close >= float(st.unit1_tp_price)
            ) or (
                st.side == "short" and low <= float(st.unit1_tp_price)
            )
            if tp_hit:
                # Sequence for synchronized exit:
                # 1) Cancel full-position broker SL.
                cancelled = await self._cancel_order_if_exists(
                    st.unit2_stop_order_id,
                    symbol=symbol,
                    ticker=ticker,
                    logs=logs,
                    context_label="initial SL",
                )
                if not cancelled:
                    logs.append(
                        f"[WARN] {ticker} Virtual TP trigger skipped because initial SL cancellation failed."
                    )
                    return logs
                st.unit2_stop_order_id = None

                # 2) Execute market sell for Unit1 quantity (50%).
                try:
                    live_qty = await self.client.get_position_quantity(ticker=ticker)
                except T212APIError as exc:
                    logs.append(f"[{symbol}] Failed to sync live quantity at virtual TP trigger: {exc}")
                    return logs

                live_whole_qty = self._to_whole_shares(live_qty)
                target_unit1_qty = self._to_whole_shares(st.unit1_qty)
                if live_whole_qty <= 0:
                    logs.append(
                        f"[INFO] {ticker} Virtual TP hit but position is already flat; resetting local state."
                    )
                    self._reset_symbol(symbol)
                    return logs

                if target_unit1_qty >= 1:
                    market_exit_qty = min(target_unit1_qty, live_whole_qty)
                    try:
                        close_qty = self._signed_exit_qty(market_exit_qty, st.side)
                        await self.client.close_position(ticker=ticker, qty=int(close_qty))
                    except T212APIError as exc:
                        logs.append(f"[{symbol}] Virtual TP market sell failed: {exc}")
                        return logs
                else:
                    market_exit_qty = 0
                    logs.append(
                        f"[INFO] {ticker} Virtual TP reached with 1-share position; no partial TP market sell."
                    )

                # 3) Place fresh SL for remaining runners and transition to Unit2.
                st.status = "UNIT2_ACTIVE"
                st.stop_loss = self._compute_breakeven_plus_stop(
                    entry_price=st.entry_price,
                    side=st.side,
                    offset_pct=self.params.breakeven_offset_pct,
                )
                if (
                    st.side == "long"
                    and close >= float(st.entry_price) * (1.0 + profit_lock_trigger_pct)
                ):
                    lock_stop = float(st.entry_price) * (1.0 + profit_lock_stop_pct)
                    st.stop_loss = max(float(st.stop_loss), lock_stop)
                remaining_qty = max(live_whole_qty - market_exit_qty, 0)
                st.unit2_qty = float(remaining_qty)
                if remaining_qty <= 0:
                    logs.append(
                        f"[INFO] {ticker} Virtual TP closed entire position; no runners remain."
                    )
                    if st.entry_price is not None and float(st.entry_price) > 0:
                        pnl_pct = ((float(close) - float(st.entry_price)) / float(st.entry_price)) * 100.0
                        self._record_trade_return(symbol, pnl_pct, logs, reason="virtual_tp_full_close")
                    self._schedule_email_alert(
                        subject=f"Exit Event - Virtual TP Full Close ({symbol})",
                        body=(
                            f"Symbol: {symbol}\n"
                            "Event: Virtual TP triggered and full position was closed."
                        ),
                    )
                    self._reset_symbol(symbol)
                    return logs

                try:
                    runner_stop_qty = self._signed_exit_qty(remaining_qty, st.side)
                    runner_stop_resp = await self._place_exit_order_with_retry(
                        place_order=lambda: self._place_stop_order(
                            ticker=ticker,
                            qty=int(runner_stop_qty),
                            stop_price=float(st.stop_loss),
                        ),
                        symbol=symbol,
                        order_label="Runner SL stop",
                        logs=logs,
                        max_attempts=5,
                        retry_delay_seconds=2.0,
                    )
                    st.unit2_stop_order_id = (
                        str(runner_stop_resp.get("id", "unknown")) if runner_stop_resp else None
                    )
                except T212APIError as exc:
                    logs.append(f"[{symbol}] Runner SL stop placement failed: {exc}")
                    st.unit2_stop_order_id = None

                # Keep runner capital protected; if SL cannot be restored, flatten remainder.
                if not st.unit2_stop_order_id:
                    try:
                        refreshed_live_qty = await self.client.get_position_quantity(ticker=ticker)
                        if refreshed_live_qty > 0:
                            force_close_qty = self._signed_exit_qty(refreshed_live_qty, st.side)
                            await self.client.close_position(ticker=ticker, qty=int(force_close_qty))
                            logs.append(
                                f"[WARN] {ticker} Runner SL missing after virtual TP; closed remainder for safety."
                            )
                    except T212APIError as exc:
                        logs.append(
                            f"[{symbol}] CRITICAL: runner SL missing and safety close failed: {exc}"
                        )
                    self._schedule_email_alert(
                        subject=f"Critical Error - Missing Runner SL ({symbol})",
                        body=(
                            f"Symbol: {symbol}\n"
                            "Action: Virtual TP triggered, but runner stop-loss placement failed.\n"
                            "Safety fallback: attempted immediate close of remaining shares."
                        ),
                    )
                    self._reset_symbol(symbol)
                    return logs

                logs.append(
                    f"[{symbol}] Virtual TP triggered at close={close:.4f}; "
                    f"sold {market_exit_qty} share(s), runners={remaining_qty}, "
                    f"runner SL={float(st.stop_loss):.4f}."
                )
                self._schedule_email_alert(
                    subject=f"Exit Event - Virtual TP ({symbol})",
                    body=(
                        f"Symbol: {symbol}\n"
                        f"Event: Virtual TP reached at close {close:.4f}\n"
                        f"Sold qty: {market_exit_qty}\n"
                        f"Runner qty: {remaining_qty}\n"
                        f"Runner Stop: {float(st.stop_loss):.4f}"
                    ),
                )
            return logs

        if st.status == "UNIT2_ACTIVE":
            if not st.side or st.stop_loss is None:
                self._reset_symbol(symbol)
                logs.append(f"[{symbol}] Corrupt UNIT2 state reset.")
                return logs

            if st.highest_high_since_entry is None:
                st.highest_high_since_entry = high
            else:
                st.highest_high_since_entry = max(st.highest_high_since_entry, high)
            if st.lowest_low_since_entry is None:
                st.lowest_low_since_entry = low
            else:
                st.lowest_low_since_entry = min(st.lowest_low_since_entry, low)

            await self._maybe_apply_morning_protect_stop(
                symbol=symbol,
                ticker=ticker,
                st=st,
                bar_ts=bar_ts,
                high=high,
                close=close,
                logs=logs,
                context_label="runner SL",
            )

            if (
                st.side == "long"
                and st.entry_price is not None
                and profit_lock_trigger_pct > 0
                and profit_lock_stop_pct > 0
                and high >= float(st.entry_price) * (1.0 + profit_lock_trigger_pct)
            ):
                lock_stop = float(st.entry_price) * (1.0 + profit_lock_stop_pct)
                st.stop_loss = max(float(st.stop_loss), lock_stop)

            be_stop_hit = (st.side == "long" and low <= st.stop_loss) or (
                st.side == "short" and high >= st.stop_loss
            )
            if be_stop_hit:
                try:
                    # Unit2 may already be closed by broker-side stop order.
                    live_qty = await self._broker_open_quantity_stable(ticker)
                    if live_qty <= 0:
                        logs.append(
                            f"[INFO] {ticker} Unit2 stop condition hit but position is already flat; resetting local state."
                        )
                    else:
                        close_qty = self._signed_exit_qty(live_qty, st.side)
                        await self.client.close_position(ticker=ticker, qty=int(close_qty))
                        logs.append(
                            f"[{symbol}] Unit2 Breakeven+ stop hit at {float(st.stop_loss):.4f}, closed remainder."
                        )
                        self._schedule_email_alert(
                            subject=f"Exit Event - Unit2 Stop ({symbol})",
                            body=(
                                f"Symbol: {symbol}\n"
                                "Event: Unit 2 closed at Breakeven+ stop"
                            ),
                        )
                except T212APIError as exc:
                    if self._is_inventory_settlement_race_error(exc):
                        logs.append(
                            f"[INFO] {ticker} Unit2 close skipped because broker reports no owned shares; treating as already closed."
                        )
                    else:
                        logs.append(f"[{symbol}] Unit2 BE close failed: {exc}")
                if st.entry_price is not None and st.stop_loss is not None and float(st.entry_price) > 0:
                    pnl_pct = ((float(st.stop_loss) - float(st.entry_price)) / float(st.entry_price)) * 100.0
                    self._record_trade_return(symbol, pnl_pct, logs, reason="unit2_stop")
                # Telegram notification: exit (runner stop)
                if st.stop_loss is not None:
                    self._schedule_telegram_alert(
                        f"❌ [EXIT] {symbol} closed at Stop Loss (€{float(st.stop_loss):.2f})."
                    )
                self._reset_symbol(symbol)
                return logs

            atr_15m = snapshot.get("atr_15m")
            if atr_15m is not None:
                atr_15m = float(atr_15m)
                if atr_15m > 0:
                    old_stop = float(st.stop_loss)
                    if st.side == "long":
                        trail_stop = float(st.highest_high_since_entry) - (
                            self.params.atr_trail_mult * atr_15m
                        )
                        st.stop_loss = max(st.stop_loss, trail_stop)
                    else:
                        trail_stop = float(st.lowest_low_since_entry) + (
                            self.params.atr_trail_mult * atr_15m
                        )
                        st.stop_loss = min(st.stop_loss, trail_stop)
                    if float(st.stop_loss) != old_stop:
                        # Keep logs concise: only emit when the stop actually improves.
                        try:
                            live_qty = await self.client.get_position_quantity(ticker=ticker)
                        except T212APIError as exc:
                            logs.append(
                                f"[WARN] {ticker} Trailing update skipped because live quantity sync failed: {exc}"
                            )
                            return logs

                        runner_qty = self._to_whole_shares(live_qty)
                        if runner_qty <= 0:
                            logs.append(
                                f"[INFO] {ticker} Trailing update skipped because runner position is already flat."
                            )
                            self._reset_symbol(symbol)
                            return logs

                        cancelled = await self._cancel_order_if_exists(
                            st.unit2_stop_order_id,
                            symbol=symbol,
                            ticker=ticker,
                            logs=logs,
                            context_label="runner SL",
                        )
                        if not cancelled:
                            # Preserve old stop in local state because broker stop replacement did not complete.
                            st.stop_loss = old_stop
                            logs.append(
                                f"[WARN] {ticker} Runner SL trailing update aborted; keeping previous stop {old_stop:.4f}."
                            )
                            return logs

                        stop_qty = self._signed_exit_qty(runner_qty, st.side)
                        try:
                            updated_stop_resp = await self._place_exit_order_with_retry(
                                place_order=lambda: self._place_stop_order(
                                    ticker=ticker,
                                    qty=int(stop_qty),
                                    stop_price=float(st.stop_loss),
                                ),
                                symbol=symbol,
                                order_label="Runner trailing SL stop",
                                logs=logs,
                                max_attempts=5,
                                retry_delay_seconds=2.0,
                            )
                            st.unit2_stop_order_id = (
                                str(updated_stop_resp.get("id", "unknown"))
                                if updated_stop_resp
                                else None
                            )
                        except T212APIError as exc:
                            logs.append(f"[{symbol}] Runner trailing SL placement failed: {exc}")
                            st.unit2_stop_order_id = None

                        if not st.unit2_stop_order_id:
                            # If replacement fails, restore previous stop locally and flatten for safety.
                            st.stop_loss = old_stop
                            try:
                                live_qty_after = await self.client.get_position_quantity(ticker=ticker)
                                if live_qty_after > 0:
                                    emergency_qty = self._signed_exit_qty(live_qty_after, st.side)
                                    await self.client.close_position(ticker=ticker, qty=int(emergency_qty))
                                    logs.append(
                                        f"[WARN] {ticker} Runner trailing stop replacement failed; closed remainder for safety."
                                    )
                            except T212APIError as exc:
                                logs.append(
                                    f"[{symbol}] CRITICAL: runner trailing stop replacement failed and emergency close failed: {exc}"
                                )
                            self._schedule_email_alert(
                                subject=f"Critical Error - Runner Trailing SL ({symbol})",
                                body=(
                                    f"Symbol: {symbol}\n"
                                    "Action: Failed to replace runner trailing stop-loss at broker.\n"
                                    "Safety fallback: attempted immediate close."
                                ),
                            )
                            self._reset_symbol(symbol)
                            return logs

                        logs.append(
                            f"[{symbol}] Unit2 trailing stop adjusted to {float(st.stop_loss):.4f}"
                        )
            return logs

        logs.append(f"[{symbol}] Unknown state {st.status}, resetting.")
        self._reset_symbol(symbol)
        return logs

    async def _has_pending_market_exit(self, *, ticker: str) -> bool:
        """
        Best-effort detection of a pending market order that would close a LONG position.
        This is used to reduce noisy warnings when a market sell is queued (overnight) but
        the broker still reports inventory.
        """
        try:
            pending = await self.client.get_pending_orders()
        except T212APIError:
            return False

        for row in pending:
            if not isinstance(row, dict):
                continue
            row_ticker = row.get("ticker")
            if row_ticker is None and isinstance(row.get("instrument"), dict):
                row_ticker = row["instrument"].get("ticker")
            if str(row_ticker or "").strip() != str(ticker).strip():
                continue

            qty_raw = row.get("quantity")
            if qty_raw is None:
                qty_raw = row.get("qty")
            try:
                qty = float(qty_raw) if qty_raw is not None else 0.0
            except (TypeError, ValueError):
                qty = 0.0

            typ = str(row.get("type") or row.get("orderType") or row.get("order_type") or "").upper()
            if "MARKET" in typ and qty < 0:
                return True

        return False

    async def _reconcile_forced_exit(
        self,
        *,
        symbol: str,
        ticker: str,
        st: SymbolState,
        bar_ts: datetime,
        logs: list[str],
    ) -> None:
        """
        After a broker-stop desync forced exit, the broker can still show an open position for a few
        cycles (pending market order, partial fill, API lag, or closed-market queuing).

        This method keeps local state in a safe "exit reconciliation" loop until the broker position
        is flat, and retries closing if the exit order is missing.
        """
        # Mark state explicitly for operator clarity.
        if st.status != "FORCED_EXIT_PENDING":
            st.status = "FORCED_EXIT_PENDING"

        try:
            live_qty = await self.client.get_position_quantity(ticker=ticker)
        except T212APIError as exc:
            logs.append(f"[WARN] {ticker} Forced-exit reconcile qty fetch failed: {exc}")
            return

        whole = self._to_whole_shares(live_qty)
        if whole <= 0:
            logs.append(f"[OK] [{symbol}] Forced-exit reconcile: broker position is flat; resuming normal scanning.")
            st.forced_exit_order_id = None
            st.forced_exit_attempts = 0
            st.forced_exit_last_attempt_timestamp_utc = None
            st.protective_stop_anomaly_streak = 0
            self._reset_symbol(symbol)
            return

        # Check whether we already have a pending exit order at the broker.
        pending_ids: set[str] = set()
        try:
            pending = await self.client.get_pending_orders()
            for row in pending:
                if isinstance(row, dict) and row.get("id") is not None:
                    pending_ids.add(str(row["id"]))
        except T212APIError as exc:
            logs.append(f"[WARN] {ticker} Forced-exit reconcile pending-orders fetch failed: {exc}")

        if st.forced_exit_order_id and st.forced_exit_order_id in pending_ids:
            logs.append(
                f"[INFO] [{symbol}] Forced-exit reconcile: exit order still pending at broker "
                f"(order_id={st.forced_exit_order_id}). Holding until filled."
            )
            return

        # No tracked pending exit order; submit another market close. Keep attempts bounded by time
        # to avoid spamming the broker in illiquid/out-of-hours conditions.
        last_ts = self._parse_utc_timestamp(st.forced_exit_last_attempt_timestamp_utc) if st.forced_exit_last_attempt_timestamp_utc else None
        if last_ts is not None and (bar_ts - last_ts) < timedelta(minutes=5):
            logs.append(
                f"[INFO] [{symbol}] Forced-exit reconcile: broker still shows qty={whole}, "
                "but last close attempt was <5m ago; waiting."
            )
            return

        st.forced_exit_attempts = int(st.forced_exit_attempts) + 1
        st.forced_exit_last_attempt_timestamp_utc = bar_ts.isoformat()
        try:
            cq = self._signed_exit_qty(whole, "long")
            resp = await self.client.close_position(ticker=ticker, qty=int(cq))
            oid = resp.get("id") if isinstance(resp, dict) else None
            if oid is not None:
                st.forced_exit_order_id = str(oid)
            logs.append(
                f"[CRITICAL] [{symbol}] Forced-exit reconcile: submitted market close retry "
                f"(attempt={st.forced_exit_attempts}, order_id={st.forced_exit_order_id or 'unknown'})."
            )
        except T212APIError as exc:
            logs.append(f"[CRITICAL] [{symbol}] Forced-exit reconcile close retry failed: {exc}")
