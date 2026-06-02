from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.integrations.supabase_rest import SupabaseRest, supabase_config_smoke_dict
from app.services.license_tier import resolve_license_tier
from app.services.tiers import capabilities_for
from app.ws.manager import Connection, WsManager


router = APIRouter(prefix="/ws", tags=["ws"])

ws_manager = WsManager()
_log = logging.getLogger("uvicorn.error")


def _client_ip(ws: WebSocket) -> str:
    if ws.client is None:
        return ""
    return ws.client.host or ""


def _parse_license_key(raw: object) -> uuid.UUID | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    try:
        return uuid.UUID(text)
    except Exception:
        return None


@router.websocket("/exec")
async def ws_exec(ws: WebSocket) -> None:
    await ws.accept()
    _log.info("WS /ws/exec accepted (pid=%s)", os.getpid())

    hello = await ws.receive_json()
    if not isinstance(hello, dict) or hello.get("type") != "HELLO":
        await ws.close(code=4400)
        return

    license_key = _parse_license_key(hello.get("license_key"))
    now = datetime.now(tz=UTC)
    ip = _client_ip(ws)
    tier = "expired"
    lic: dict | None = None
    connection_id: uuid.UUID

    # A valid license key (trial or paid) is required — paper trading is part of
    # the 14-day trial, so there is no anonymous/guest session.
    if license_key is None:
        _log.info("WS /ws/exec rejected: no license key (ip=%s)", ip or "?")
        await ws.close(code=4401, reason="License key required. Start your free trial at swifttrade.app")
        return

    root = ws.app
    sb = getattr(root.state, "supabase_rest", None)
    if sb is None:
        sb = SupabaseRest.from_settings()
    if sb is None:
        info = supabase_config_smoke_dict()
        diag = json.dumps(info, indent=2)
        _log.error("WS /ws/exec closing 4420 (no Supabase credentials). Diagnostics (no secrets):\n%s", diag)
        print(f"WS4420 pid={os.getpid()} see uvicorn.error log for JSON diagnostics", file=sys.stderr, flush=True)
        any_file = any(c.get("exists") for c in info.get("candidates", []) if isinstance(c, dict))
        reason = (
            f"file_url_len={info.get('file_url_len')} file_key_len={info.get('file_key_len')} "
            f"any_dotenv={any_file}"
        )
        if len(reason) > 118:
            reason = reason[:115] + "..."
        await ws.close(code=4420, reason=reason)
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tier, lic, _message = await resolve_license_tier(sb, client, license_key, now=now)
            if tier == "invalid":
                await ws.close(code=4404, reason="License key not recognized.")
                return
            if tier == "expired":
                await ws.close(code=4403, reason="Trial expired. Upgrade at swifttrade.app to resume.")
                return

            connection_id = uuid.UUID(str(lic["id"])) if lic else uuid.uuid4()

            if lic:
                await sb.patch(
                    client,
                    f"licenses?id=eq.{lic['id']}",
                    {"last_ip_address": ip or None, "last_seen_at": now.isoformat()},
                )
    except httpx.HTTPError:
        await ws.close(code=1011)
        return
    except Exception:
        await ws.close(code=1011)
        return

    conn = Connection(
        connection_id=connection_id,
        license_key=license_key,
        tier=tier,
        ip=ip,
        websocket=ws,
        last_pong_at=now,
    )
    await ws_manager.upsert(conn)

    try:
        caps = capabilities_for(tier)
        await ws.send_json({
            "type": "WELCOME",
            "tier": tier,
            "capabilities": {
                "live_trading": caps.live_trading,
                "full_signal_feed": caps.signal_level >= 2,
                "max_open_positions": caps.max_open_positions,
            },
        })
        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict):
                continue
            mtype = msg.get("type")
            if mtype == "PONG":
                await ws_manager.touch_pong(conn.connection_id)
                continue
            if mtype == "ACK":
                continue
            if mtype == "ECHO":
                await ws.send_json({"type": "ECHO", "payload": msg.get("payload")})
                continue
    except WebSocketDisconnect:
        await ws_manager.remove(conn.connection_id)
    except Exception:
        await ws_manager.remove(conn.connection_id)
        try:
            await ws.close(code=1011)
        except Exception:
            pass


async def heartbeat_loop() -> None:
    while True:
        await asyncio.sleep(30.0)
        await ws_manager.ping_sweep(ping_payload={"type": "PING"}, pong_timeout_s=40.0)
