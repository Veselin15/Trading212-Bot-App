from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import License, LicenseStatus
from app.db.session import db_session
from app.ws.manager import Connection, WsManager


router = APIRouter(prefix="/ws", tags=["ws"])

ws_manager = WsManager()


def _client_ip(ws: WebSocket) -> str:
    if ws.client is None:
        return ""
    return ws.client.host or ""


@router.websocket("/exec")
async def ws_exec(ws: WebSocket, session: AsyncSession = Depends(db_session)) -> None:
    await ws.accept()

    hello = await ws.receive_json()
    if not isinstance(hello, dict) or hello.get("type") != "HELLO":
        await ws.close(code=4400)
        return
    license_key_raw = hello.get("license_key")
    try:
        license_key = uuid.UUID(str(license_key_raw))
    except Exception:
        await ws.close(code=4401)
        return

    lic = (
        await session.execute(select(License).where(License.license_key == license_key).limit(1))
    ).scalar_one_or_none()
    if lic is None or lic.revoked_at is not None:
        await ws.close(code=4404)
        return

    now = datetime.now(tz=UTC)
    if lic.status != LicenseStatus.active or lic.expires_at <= now:
        await ws.close(code=4403)
        return

    ip = _client_ip(ws)
    if lic.last_ip_address and str(lic.last_ip_address) != ip:
        await ws.close(code=4409)
        return

    # Persist IP lock + last seen
    lic.last_ip_address = ip or None
    lic.last_seen_at = now
    await session.commit()

    conn = Connection(
        license_id=lic.id,
        license_key=lic.license_key,
        ip=ip,
        websocket=ws,
        last_pong_at=now,
    )
    await ws_manager.upsert(conn)

    try:
        await ws.send_json({"type": "WELCOME"})
        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict):
                continue
            mtype = msg.get("type")
            if mtype == "PONG":
                await ws_manager.touch_pong(lic.id)
                continue
            if mtype == "ACK":
                continue
            if mtype == "ECHO":
                await ws.send_json({"type": "ECHO", "payload": msg.get("payload")})
                continue
    except WebSocketDisconnect:
        await ws_manager.remove(lic.id)
    except Exception:
        await ws_manager.remove(lic.id)
        try:
            await ws.close(code=1011)
        except Exception:
            pass


async def heartbeat_loop() -> None:
    # Runs inside the backend process; safe to start once.
    while True:
        await asyncio.sleep(30.0)
        await ws_manager.ping_sweep(ping_payload={"type": "PING"}, pong_timeout_s=40.0)

