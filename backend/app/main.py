from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Trading212 Bot Backend")
    return app


app = create_app()

