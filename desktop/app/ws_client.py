from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

import websockets


@dataclass(frozen=True)
class WsConfig:
    url: str
    license_key: str


class ExecWsClient:
    def __init__(
        self,
        *,
        cfg: WsConfig,
        on_status: Callable[[str], None],
        on_signal: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        self._cfg = cfg
        self._on_status = on_status
        self._on_signal = on_signal
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self) -> None:
        while not self._stop.is_set():
            self._on_status("CONNECTING")
            try:
                async with websockets.connect(self._cfg.url, ping_interval=None) as ws:
                    self._on_status("ONLINE")
                    await ws.send(json.dumps({"type": "HELLO", "license_key": self._cfg.license_key}))

                    while not self._stop.is_set():
                        raw = await ws.recv()
                        msg = json.loads(raw)
                        mtype = msg.get("type")
                        if mtype == "PING":
                            await ws.send(json.dumps({"type": "PONG"}))
                            continue
                        if mtype == "SIGNAL":
                            payload = msg.get("payload") or {}
                            if isinstance(payload, dict):
                                await self._on_signal(payload)
                            continue
            except Exception:
                self._on_status("OFFLINE")
                await asyncio.sleep(5.0)

