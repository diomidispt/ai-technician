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
    # Hybrid retrieval: vector search (meaning) fused with Postgres full-text (exact tokens like
    # error codes / part numbers / model names) via Reciprocal Rank Fusion. Set HYBRID_ENABLED=false
    # to fall back to vector-only.
    hybrid_enabled: bool = True
    retrieval_candidate_k: int = 20  # candidates pulled from EACH retriever before fusion
    rrf_k: int = 60  # RRF constant; larger = flatter weighting of rank positions

    # --- Conversation memory (history-aware retrieval) ---
    # Rewrite a follow-up ("and for the WE110?") into a standalone search query using recent turns,
    # so retrieval isn't blind to context. One fast LLM call; falls back to the raw question.
    query_rewrite_enabled: bool = True
    history_max_turns: int = 6  # most recent messages passed to the model for coherence
    # Sufficiency gate (internal-first): if the BEST match's cosine distance exceeds this, treat
    # the library as not covering the question -> web fallback. Tuned for bge-m3 on the
    # section-prefixed corpus (measured: in-scope best ~0.26-0.37, out-of-scope best ~0.57-0.63),
    # so 0.50 separates them with margin. Verified via `make eval` (routing accuracy).
    sufficiency_max_distance: float = 0.50
    # Citations/context: keep only chunks within this distance of the best match, so we don't
    # cite loosely-related pages. Absolute thresholds don't separate them (distances cluster);
    # a margin off the best match does.
    relevance_margin: float = 0.1

    # --- Auth (local simulation of Cognito; JWT signed with a local secret) ---
    # Override JWT_SECRET in production. In real AWS this becomes Cognito, not a local secret.
    jwt_secret: str = "dev-only-change-me-please-32byte-minimum-secret"
    jwt_expire_minutes: int = 480  # 8h working day
    # Seeded on startup if the users table is empty (so you can log in immediately).
    seed_admin_email: str = "admin"
    seed_admin_password: str = "admin"
    seed_tech_email: str = "technician"
    seed_tech_password: str = "technician"

    # --- Ingestion / document library ---
    # Where admin-uploaded PDFs are stored + ingested from. In the container this is /docs
    # (a mounted volume); locally it's the sample_docs folder.
    docs_dir: str = "/docs"

    # OCR fallback (local stand-in for AWS Textract): when a page has little/no extractable text
    # (a scan or a drawing), render it and run Tesseract so its labels/notes become searchable.
    # Needs the system `tesseract` binary (+ language packs); degrades gracefully if absent.
    ocr_enabled: bool = True
    ocr_min_text_chars: int = 20  # below this, treat the page as scanned and try OCR
    ocr_langs: str = "ell+eng"  # Tesseract language packs (Greek + English)

    # --- Web-search fallback (DuckDuckGo, no API key) ---
    # Runs ONLY when the internal library is insufficient (internal-first rule). Sends the
    # query out, so it's not fully offline. Set WEB_FALLBACK_ENABLED=false to keep it offline.
    web_fallback_enabled: bool = True
    web_results: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
