from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi import FastAPI

# Bump when you ship a new release.  Desktop app reads this from /version.
APP_VERSION = "2.0.0"

from app.api.license import router as license_router
from app.api.ws import heartbeat_loop, router as ws_router
from app.core.config import settings

_log = logging.getLogger("uvicorn.error")


def create_app() -> FastAPI:
    app = FastAPI(title="Trading212 Bot Backend")

    @app.get("/")
    async def root() -> dict[str, str]:
        # FastAPI returns 404 for ``/`` by default; browsers hitting the backend root look "broken".
        return {
            "service": "t212-bot-backend",
            "health": "/health",
            "supabase_smoke": "/health/supabase-smoke",
            "docs": "/docs",
            "ws_exec": "/ws/exec",
        }

    @app.get("/version")
    async def version() -> dict[str, str]:
        """Returns the backend version.  Desktop app displays this after connecting."""
        return {"version": APP_VERSION}

    @app.get("/health")
    async def health() -> dict[str, str | int]:
        return {"status": "ok", "process_pid": os.getpid()}

    @app.get("/health/supabase-smoke")
    async def health_supabase_smoke() -> dict:
        from app.integrations.supabase_rest import supabase_config_smoke_dict

        return supabase_config_smoke_dict()

    if settings.debug_routes_enabled:
        from app.api.debug import router as debug_router

        app.include_router(debug_router)
        _log.warning("Debug routes are ENABLED — disable in production unless behind a secret key.")
    app.include_router(license_router)
    app.include_router(ws_router)

    @app.on_event("startup")
    async def _startup() -> None:
        from app.integrations.supabase_rest import supabase_config_smoke_dict

        info = supabase_config_smoke_dict()
        ru = int(info.get("resolved_url_len") or 0)
        rk = int(info.get("resolved_key_len") or 0)
        if ru <= 0 or rk <= 0:
            _log.warning(
                "Supabase credentials missing for WS licensing (resolved_url_len=%s resolved_key_len=%s). "
                "Diagnostics (no secrets):\n%s",
                ru,
                rk,
                json.dumps(info, indent=2),
            )
        else:
            _log.info(
                "Supabase credentials resolved for WS (url_len=%s key_len=%s, primary .env exists=%s).",
                ru,
                rk,
                info.get("primary_exists"),
            )
        from app.integrations.supabase_rest import SupabaseRest

        # Resolve once at startup so WS uses the same client as the smoke check (Windows
        # reload / multi-listener quirks can otherwise see empty env in the handler).
        app.state.supabase_rest = SupabaseRest.from_settings()
        asyncio.create_task(heartbeat_loop())
        if settings.run_strategy:
            _log.warning(
                "Strategy runner ENABLED (RUN_STRATEGY=true) — new_trading212bot v2 ML engine."
            )
            from app.strategy.t212_miner_runner import run_t212_miner_strategy_forever

            asyncio.create_task(run_t212_miner_strategy_forever())
        else:
            _log.info("Strategy runner disabled (RUN_STRATEGY=false).")

    return app


app = create_app()

