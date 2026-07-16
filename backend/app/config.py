"""Application settings.

Config comes from env vars (and a local `.env`) — never hardcoded secrets. In AWS the
same vars are supplied by the platform + Secrets Manager. See `.env.example` at the repo root.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Origins allowed to call the API (the local Vite dev server by default).
    cors_origins: str = "http://localhost:5173"

    # EU data residency (golden rule). No AWS calls happen in phase 1 — kept for later phases.
    aws_region: str = "eu-central-1"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
