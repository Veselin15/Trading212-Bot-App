from __future__ import annotations

import asyncio

from fastapi import FastAPI

from app.api.webhooks import router as webhooks_router
from app.api.ws import heartbeat_loop, router as ws_router
from app.strategy.t212_miner_runner import run_t212_miner_strategy_forever


def create_app() -> FastAPI:
    app = FastAPI(title="Trading212 Bot Backend")
    app.include_router(webhooks_router)
    app.include_router(ws_router)

    @app.on_event("startup")
    async def _startup() -> None:
        asyncio.create_task(heartbeat_loop())
        asyncio.create_task(run_t212_miner_strategy_forever())

    return app


app = create_app()

