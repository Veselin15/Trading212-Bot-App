from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

from .default_executor_url import DEFAULT_EXECUTOR_WS_URL
from .license_key_util import normalize_license_key


def _http_base(ws_url: str) -> str:
    """Map ``wss://host/...`` → ``https://host``.  Used to derive REST endpoints."""
    try:
        p = urlparse(ws_url.strip())
        if p.scheme in ("ws", "wss") and p.hostname:
            scheme = "https" if p.scheme == "wss" else "http"
            netloc = f"{p.hostname}:{p.port}" if p.port else str(p.hostname)
            return f"{scheme}://{netloc}"
    except Exception:
        pass
    fb = urlparse(DEFAULT_EXECUTOR_WS_URL.strip())
    scheme = "https" if fb.scheme == "wss" else "http"
    netloc = f"{fb.hostname}:{fb.port}" if fb.port else str(fb.hostname)
    return f"{scheme}://{netloc}"


def _smoke_health_url(ws_url: str) -> str:
    return f"{_http_base(ws_url)}/health/supabase-smoke"


async def _fetch_backend_version(base: str) -> str | None:
    """GET /version from the backend; returns the version string or None on any error."""
    try:
        timeout = aiohttp.ClientTimeout(total=5.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{base}/version") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return str(data.get("version") or "").strip() or None
    except Exception:
        pass
    return None


@dataclass(frozen=True)
class WsConfig:
    url: str
    license_key: str | None = None
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
        on_tier: Callable[[str], None] | None = None,
    ) -> None:
        self._cfg = cfg
        self._on_status = on_status
        self._on_event = on_event
        self._on_signal = on_signal
        self._on_bot_snapshot = on_bot_snapshot
        self._on_tier = on_tier
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    def _hello_payload(self) -> dict[str, Any]:
        key = normalize_license_key(self._cfg.license_key)
        payload: dict[str, Any] = {"type": "HELLO", "mode": "paper" if key is None else "licensed"}
        if key is not None:
            payload["license_key"] = key
        return payload

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
                    base = _http_base(self._cfg.url)
                    server_ver = await _fetch_backend_version(base)
                    if server_ver:
                        self._on_event(f"Connected — server v{server_ver}")
                    else:
                        self._on_event(f"Connected to {self._cfg.url}")
                    await ws.send(json.dumps(self._hello_payload()))

                    while not self._stop.is_set():
                        raw = await ws.recv()
                        msg = json.loads(raw)
                        mtype = msg.get("type")
                        if mtype == "WELCOME":
                            tier = str(msg.get("tier") or "trial")
                            if self._on_tier:
                                self._on_tier(tier)
                            if tier == "pro":
                                self._on_event("Handshake OK — Pro tier (live trading, full signal feed).")
                            elif tier == "starter":
                                self._on_event("Handshake OK — Starter tier (live trading, core signals).")
                            elif tier == "trial":
                                self._on_event("Handshake OK — Free trial (paper trading only).")
                            else:
                                self._on_event("Handshake OK — paper trading only.")
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
                if code == 4000:
                    self._on_event(
                        "Session ended: your license key connected from another device or session. "
                        "Reconnect here to take the session back."
                    )
                elif code == 4400:
                    self._on_event("Disconnected: bad handshake (unexpected message type sent).")
                elif code == 4401:
                    self._on_event(
                        "Disconnected: a license key is required. Paste your key from swifttrade.app "
                        "(start a free 14-day trial to get one), then reconnect."
                    )
                elif code == 4403:
                    self._on_event(
                        "Disconnected: your free trial has ended (or the subscription lapsed). "
                        "Upgrade at swifttrade.app to resume, then reconnect."
                    )
                elif code == 4404:
                    self._on_event(
                        "Disconnected: license key not found or has been revoked. "
                        "Check your key in the Setup tab."
                    )
                elif code == 4409:
                    self._on_event("Disconnected: session conflict — reconnecting will resolve this.")
                elif code == 4420:
                    smoke = _smoke_health_url(self._cfg.url)
                    self._on_event(
                        "Disconnected: server could not load its credentials. "
                        f"Server health: {smoke}"
                    )
                    if reason.strip():
                        self._on_event(f"Server reason: {reason.strip()}")
                elif code == 1011:
                    self._on_event("Disconnected: internal server error — will retry.")
                else:
                    msg = f"Disconnected (code={code})"
                    if reason.strip():
                        msg += f": {reason.strip()}"
                    self._on_event(msg)
                attempt += 1
                if self._cfg.max_reconnect_attempts > 0 and attempt >= self._cfg.max_reconnect_attempts:
                    self._on_event(f"Max reconnect attempts ({self._cfg.max_reconnect_attempts}) reached. Stopped.")
                    return
                interval = self._cfg.reconnect_interval_s
                self._on_event(f"Reconnecting in {interval}s…")
                await asyncio.sleep(float(interval))
            except Exception:
                self._on_status("OFFLINE")
                # Show the actual error so users can diagnose TLS / DNS / proxy issues.
                # (Common in production: blocked WebSocket, bad clock, TLS interception, etc.)
                try:
                    import ssl

                    if isinstance(sys.exc_info()[1], ssl.SSLCertVerificationError):
                        self._on_event(
                            "TLS error: certificate verification failed. "
                            "Check your system clock, antivirus HTTPS scanning, or corporate proxy."
                        )
                except Exception:
                    pass
                exc = sys.exc_info()[1]
                if exc is not None:
                    self._on_event(f"Connection error: {type(exc).__name__}: {exc}")
                attempt += 1
                if self._cfg.max_reconnect_attempts > 0 and attempt >= self._cfg.max_reconnect_attempts:
                    self._on_event(f"Max reconnect attempts ({self._cfg.max_reconnect_attempts}) reached. Stopped.")
                    return
                interval = self._cfg.reconnect_interval_s
                self._on_event(f"Disconnected. Reconnecting in {interval}s…")
                await asyncio.sleep(float(interval))
