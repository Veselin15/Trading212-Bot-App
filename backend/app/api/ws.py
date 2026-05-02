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
from app.ws.manager import Connection, WsManager


router = APIRouter(prefix="/ws", tags=["ws"])

ws_manager = WsManager()
_log = logging.getLogger("uvicorn.error")


def _client_ip(ws: WebSocket) -> str:
    if ws.client is None:
        return ""
    return ws.client.host or ""


@router.websocket("/exec")
async def ws_exec(ws: WebSocket) -> None:
    await ws.accept()
    _log.info("WS /ws/exec accepted (pid=%s)", os.getpid())

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

    root = ws.app
    sb = getattr(root.state, "supabase_rest", None)
    if sb is None:
        sb = SupabaseRest.from_settings()
    if sb is None:
        # 4420: missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (not a generic internal error).
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

    now = datetime.now(tz=UTC)
    ip = _client_ip(ws)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1) Validate license row.
            lic_rows = await sb.get(
                client,
                f"licenses?select=id,user_id,license_key,status,revoked_at,expires_at,last_ip_address&license_key=eq.{license_key}",
            )
            lic = lic_rows[0] if lic_rows else None
            if not lic or lic.get("revoked_at") is not None:
                await ws.close(code=4404)
                return
            if str(lic.get("status") or "inactive") != "active":
                await ws.close(code=4403)
                return

            expires_at = lic.get("expires_at")
            if expires_at:
                try:
                    exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                    if exp <= now:
                        await ws.close(code=4403)
                        return
                except Exception:
                    # If unparsable, treat as invalid.
                    await ws.close(code=4403)
                    return

            user_id = str(lic.get("user_id") or "").strip()
            if not user_id:
                await ws.close(code=4404)
                return

            # 2) Validate subscription row (latest).
            sub_rows = await sb.get(
                client,
                "subscriptions?select=status,current_period_end&"
                f"user_id=eq.{user_id}&order=created_at.desc&limit=1",
            )
            sub = sub_rows[0] if sub_rows else None
            if not sub or str(sub.get("status") or "") != "active":
                await ws.close(code=4403)
                return

            cpe = sub.get("current_period_end")
            if cpe:
                try:
                    end = datetime.fromisoformat(str(cpe).replace("Z", "+00:00"))
                    if end <= now:
                        await ws.close(code=4403)
                        return
                except Exception:
                    await ws.close(code=4403)
                    return

            # 3) Enforce one-license-per-IP (best-effort).
            locked_ip = str(lic.get("last_ip_address") or "").strip()
            if locked_ip and ip and locked_ip != ip:
                await ws.close(code=4409)
                return

            # Persist IP lock + last seen (service role bypasses RLS).
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
        license_id=uuid.UUID(str(lic["id"])),
        license_key=license_key,
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
                await ws_manager.touch_pong(conn.license_id)
                continue
            if mtype == "ACK":
                continue
            if mtype == "ECHO":
                await ws.send_json({"type": "ECHO", "payload": msg.get("payload")})
                continue
    except WebSocketDisconnect:
        await ws_manager.remove(conn.license_id)
    except Exception:
        await ws_manager.remove(conn.license_id)
        try:
            await ws.close(code=1011)
        except Exception:
            pass


async def heartbeat_loop() -> None:
    # Runs inside the backend process; safe to start once.
    while True:
        await asyncio.sleep(30.0)
        await ws_manager.ping_sweep(ping_payload={"type": "PING"}, pong_timeout_s=40.0)

