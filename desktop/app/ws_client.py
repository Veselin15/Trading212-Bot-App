from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

import websockets
from websockets.exceptions import ConnectionClosed


def _smoke_health_url(ws_url: str) -> str:
    """Map ``ws://host:port/...`` to ``http://host:port/health/supabase-smoke`` for diagnostics."""
    try:
        p = urlparse(ws_url.strip())
        if p.scheme in ("ws", "wss") and p.hostname:
            http_scheme = "https" if p.scheme == "wss" else "http"
            if p.port:
                netloc = f"{p.hostname}:{p.port}"
            else:
                netloc = p.hostname
            return f"{http_scheme}://{netloc}/health/supabase-smoke"
    except Exception:
        pass
    return "http://127.0.0.1:8010/health/supabase-smoke"


@dataclass(frozen=True)
class WsConfig:
    url: str
    license_key: str
    reconnect_interval_s: int = 5
    max_reconnect_attempts: int = 0  # 0 = unlimited


class ExecWsClient:
    def __init__(
        self,
        *,
        cfg: WsConfig,
        on_status: Callable[[str], None],
        on_event: Callable[[str], None],
        on_signal: Callable[[dict[str, Any]], Awaitable[None]],
        on_bot_snapshot: Callable[[dict[str, Any]], None],
    ) -> None:
        self._cfg = cfg
        self._on_status = on_status
        self._on_event = on_event
        self._on_signal = on_signal
        self._on_bot_snapshot = on_bot_snapshot
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            self._on_status("CONNECTING")
            try:
                async with websockets.connect(
                    self._cfg.url,
                    ping_interval=25,
                    ping_timeout=20,
                    close_timeout=10,
                ) as ws:
                    self._on_status("ONLINE")
                    attempt = 0
                    self._on_event(f"Connected to {self._cfg.url}")
                    await ws.send(json.dumps({"type": "HELLO", "license_key": self._cfg.license_key}))

                    while not self._stop.is_set():
                        raw = await ws.recv()
                        msg = json.loads(raw)
                        mtype = msg.get("type")
                        if mtype == "WELCOME":
                            self._on_event("Handshake OK (WELCOME).")
                            continue
                        if mtype == "PING":
                            await ws.send(json.dumps({"type": "PONG"}))
                            continue
                        if mtype == "SIGNAL":
                            payload = msg.get("payload") or {}
                            if isinstance(payload, dict):
                                self._on_event(f"SIGNAL received (id={payload.get('id')})")
                                await self._on_signal(payload)
                            continue
                        if mtype == "BOT_SNAPSHOT":
                            payload = msg.get("payload") or {}
                            if isinstance(payload, dict):
                                self._on_bot_snapshot(payload)
                            continue
            except ConnectionClosed as exc:
                self._on_status("OFFLINE")
                code = getattr(exc, "code", None)
                reason = getattr(exc, "reason", "") or ""
                if code == 4401:
                    self._on_event("Disconnected: invalid license key format.")
                elif code == 4404:
                    self._on_event("Disconnected: license not found or revoked.")
                elif code == 4403:
                    self._on_event("Disconnected: subscription/license not active.")
                elif code == 4409:
                    self._on_event("Disconnected: license already locked to a different IP.")
                elif code == 4400:
                    self._on_event("Disconnected: bad handshake.")
                elif code == 4420:
                    smoke = _smoke_health_url(self._cfg.url)
                    self._on_event(
                        "Disconnected: backend could not load Supabase URL + service role key. "
                        f"Open {smoke} in a browser (lengths only, no secrets). "
                        "If the WS URL uses 'localhost', try '127.0.0.1' to match uvicorn --host 127.0.0.1."
                    )
                    if reason.strip():
                        self._on_event(f"Server close reason: {reason.strip()}")
                else:
                    self._on_event(f"Disconnected (code={code}): {reason}".strip())
                attempt += 1
                if self._cfg.max_reconnect_attempts > 0 and attempt >= self._cfg.max_reconnect_attempts:
                    self._on_event(f"Max reconnect attempts ({self._cfg.max_reconnect_attempts}) reached. Stopped.")
                    return
                interval = self._cfg.reconnect_interval_s
                self._on_event(f"Reconnecting in {interval}s…")
                await asyncio.sleep(float(interval))
            except Exception:
                self._on_status("OFFLINE")
                attempt += 1
                if self._cfg.max_reconnect_attempts > 0 and attempt >= self._cfg.max_reconnect_attempts:
                    self._on_event(f"Max reconnect attempts ({self._cfg.max_reconnect_attempts}) reached. Stopped.")
                    return
                interval = self._cfg.reconnect_interval_s
                self._on_event(f"Disconnected. Reconnecting in {interval}s…")
                await asyncio.sleep(float(interval))

