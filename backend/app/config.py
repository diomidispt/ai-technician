"""Application settings.

Config comes from env vars (and a local `.env`) — never hardcoded secrets. Defaults target
a **local venv** run (localhost). `docker-compose.yml` overrides the DB + Ollama hosts for the
containerized backend. See `.env.example` at the repo root.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Origins allowed to call the API (the local Vite dev server by default).
    cors_origins: str = "http://localhost:5173"

    # EU data residency (golden rule). No AWS calls locally — kept for later phases.
    aws_region: str = "eu-central-1"

    # --- Data (Postgres + pgvector) ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/jensen"

    # --- Ollama (local LLM + embeddings; $0, on-device) ---
    ollama_base_url: str = "http://localhost:11434"
    # Multilingual (answers in the user's language, incl. Greek). Set ANSWER_MODEL to override.
    answer_model: str = "aya-expanse:8b"  # multilingual; good Greek (llama3.2:3b = faster English)
    embed_model: str = "bge-m3"  # multilingual embeddings -> cross-lingual retrieval
    embed_dim: int = 1024  # bge-m3 output dimension (must match the embedding model)

    # --- Retrieval ---
    retrieval_top_k: int = 5
    # Max cosine DISTANCE (0=identical, 2=opposite) to still count a chunk as relevant.
    # Above this for every chunk => treat the library as insufficient (internal-first rule).
    similarity_max_distance: float = 0.75

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
