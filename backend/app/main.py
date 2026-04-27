from __future__ import annotations

from fastapi import FastAPI

from app.api.webhooks import router as webhooks_router


def create_app() -> FastAPI:
    app = FastAPI(title="Trading212 Bot Backend")
    app.include_router(webhooks_router)
    return app


app = create_app()

