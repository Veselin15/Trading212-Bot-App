from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import WebSocket

from app.services.tiers import signal_level_for_tier


@dataclass
class Connection:
    connection_id: uuid.UUID
    license_key: uuid.UUID | None
    tier: str
    ip: str
    websocket: WebSocket
    last_pong_at: datetime

    @property
    def signal_level(self) -> int:
        """Highest signal level this connection is entitled to receive."""
        return signal_level_for_tier(self.tier)


class WsManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: dict[uuid.UUID, Connection] = {}

    async def upsert(self, conn: Connection) -> None:
        async with self._lock:
            old = self._connections.get(conn.connection_id)
            self._connections[conn.connection_id] = conn
        if old is not None and old.websocket is not conn.websocket:
            try:
                await old.websocket.close(code=4000)
            except Exception:
                pass

    async def remove(self, connection_id: uuid.UUID) -> None:
        async with self._lock:
            self._connections.pop(connection_id, None)

    async def touch_pong(self, connection_id: uuid.UUID) -> None:
        async with self._lock:
            conn = self._connections.get(connection_id)
            if conn:
                conn.last_pong_at = datetime.now(tz=UTC)

    async def broadcast(self, message: dict, *, min_signal_level: int = 0) -> int:
        """Send ``message`` to connections whose ``signal_level`` >= ``min_signal_level``.

        ``min_signal_level=0`` (the default) reaches everyone — used for snapshots and
        control frames. Tier-gated signals pass a higher level so that lower tiers
        (e.g. Starter) never receive Pro-only signals.
        """
        async with self._lock:
            conns = list(self._connections.values())
        sent = 0
        for conn in conns:
            if min_signal_level and conn.signal_level < min_signal_level:
                continue
            try:
                await conn.websocket.send_json(message)
                sent += 1
            except Exception:
                await self.remove(conn.connection_id)
        return sent

    async def ping_sweep(self, *, ping_payload: dict, pong_timeout_s: float) -> None:
        async with self._lock:
            conns = list(self._connections.values())
        now = datetime.now(tz=UTC)

        for conn in conns:
            try:
                await conn.websocket.send_json(ping_payload)
            except Exception:
                await self.remove(conn.connection_id)
                continue

            age_s = (now - conn.last_pong_at).total_seconds()
            if age_s > pong_timeout_s:
                try:
                    await conn.websocket.close(code=4001)
                except Exception:
                    pass
                await self.remove(conn.connection_id)
