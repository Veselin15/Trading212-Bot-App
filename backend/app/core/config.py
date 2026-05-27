from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env_paths import backend_dotenv_candidate_paths

# Always load backend/.env regardless of cwd (uvicorn is often started from repo root).
_BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"


def _backend_dotenv_path_candidates() -> list[Path]:
    return backend_dotenv_candidate_paths(_BACKEND_ENV)


def _primary_env_file_for_pydantic() -> Path:
    for p in _backend_dotenv_path_candidates():
        if p.is_file():
            return p
    return _BACKEND_ENV


_ENV_FILE_FOR_SETTINGS = _primary_env_file_for_pydantic()


def _hydrate_supabase_env_from_backend_dotenv() -> None:
    """Copy SUPABASE_* from ``.env`` into os.environ when unset or whitespace-only.

    pydantic-settings merges env before dotenv; blank ``SUPABASE_URL`` /
    ``SUPABASE_SERVICE_ROLE_KEY`` in the process environment would otherwise
    mask values from disk. Tries package-adjacent ``backend/.env`` then cwd fallbacks.
    """
    try:
        from dotenv import dotenv_values
    except ImportError:
        return
    merged: dict[str, str] = {}
    for path in _backend_dotenv_path_candidates():
        if not path.is_file():
            continue
        vals = dotenv_values(path, encoding="utf-8-sig")
        for k, v in vals.items():
            if k is None:
                continue
            nk = str(k).strip().lstrip("\ufeff")
            if nk not in merged:
                merged[nk] = "" if v is None else str(v)
    for key in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        text = (merged.get(key) or "").strip()
        if not text:
            continue
        current = os.environ.get(key)
        if current is None or not str(current).strip():
            os.environ[key] = text


_hydrate_supabase_env_from_backend_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE_FOR_SETTINGS),
        # utf-8-sig: tolerate UTF-8 BOM in .env (common on Windows).
        env_file_encoding="utf-8-sig",
        # Env vars override .env; empty strings in the shell/IDE would otherwise mask backend/.env.
        env_ignore_empty=True,
        extra="ignore",
    )

    # Defaults are provided so tooling like Alembic can run even before a local `.env` exists.
    database_url: str = "postgresql+asyncpg://t212_bot:t212_bot@localhost:5432/t212_bot"

    jwt_secret: str = "change-me"
    jwt_issuer: str = "t212-bot-backend"
    jwt_audience: str = "t212-bot-portal"

    app_base_url: str = "http://127.0.0.1:8010"

    # Supabase (used for portal-driven licenses/subscriptions)
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Local dev: true. Production deploy sets DEBUG_ROUTES_ENABLED=false.
    debug_routes_enabled: bool = True
    debug_api_key: str = ""

    # Legacy SQLAlchemy Postgres (unused for licensing). Set false in production deploy.
    run_db_migrations: bool = True

    # Strategy runner (Server-App/t212_miner_bot). Disable on low-spec prod boxes by default.
    # When enabled, requires additional deps and data feed reliability.
    run_strategy: bool = False


settings = Settings()  # type: ignore[call-arg]

