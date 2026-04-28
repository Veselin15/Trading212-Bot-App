from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Defaults are provided so tooling like Alembic can run even before a local `.env` exists.
    database_url: str = "postgresql+asyncpg://t212_bot:t212_bot@localhost:5432/t212_bot"

    jwt_secret: str = "change-me"
    jwt_issuer: str = "t212-bot-backend"
    jwt_audience: str = "t212-bot-portal"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    app_base_url: str = "http://localhost:8000"

    # Supabase (used for portal-driven licenses/subscriptions)
    supabase_url: str = ""
    supabase_service_role_key: str = ""


settings = Settings()  # type: ignore[call-arg]

