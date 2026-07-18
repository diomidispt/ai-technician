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
    # Keep models resident between requests so there's no multi-second reload lag on the next
    # question. Sent on every Ollama call. "30m" = stay loaded 30 min after last use.
    ollama_keep_alive: str = "30m"
    # --- Vision (photo input, $0/local) ---
    # A technician photographs the control panel / error display; this model reads the code + text
    # off it, which then flows into the normal manual RAG. Needs `ollama pull <vision_model>`.
    # minicpm-v: strong OCR, fits by aya on 16GB. Alts: moondream (lighter), llama3.2-vision.
    vision_enabled: bool = True
    vision_model: str = "minicpm-v"
    # Cap the answer length so generation doesn't run on unnecessarily (speed). Plenty for a
    # thorough grounded answer; -1 would be unlimited.
    answer_num_predict: int = 800

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
    # so retrieval isn't blind to context. Falls back to the raw question. Runs in the same LLM
    # call as the intent router (see below) — one round trip does both jobs.
    query_rewrite_enabled: bool = True
    history_max_turns: int = 6  # most recent messages passed to the model for coherence

    # Intent router: decides whether a message needs the manuals (technical) or is small talk
    # (greeting/thanks/"who are you"). Chit-chat gets a natural reply with no retrieval — so
    # greetings aren't answered from random chunks. Uses the answer model (kept off the small
    # rewrite model — it was found to misroute Greek technical questions as chitchat), and shares
    # one call with the query rewrite above (see `_route_and_rewrite` in pipeline.py).
    intent_router_enabled: bool = True

    # --- Conversation history (persisted per-user threads behind the sidebar) ---
    # Keep only the N most-recently-used threads per user; starting an N+1th prunes the oldest.
    history_max_conversations: int = 30
    # Sufficiency gate (internal-first): if the BEST match's cosine distance exceeds this, treat
    # the library as not covering the question -> web fallback / refuse. Measured on this corpus:
    # real in-scope questions top out ~0.44 (Greek pushes highest), while "related-but-unanswerable"
    # traps like a nonexistent error code "E4" start ~0.47. So 0.45 sits in that narrow gap — it
    # stops the model being handed loosely-related chunks and fabricating an answer with citations.
    # The gap is tight (an 8B-model limitation); reliable grounding is the main win from Claude.
    sufficiency_max_distance: float = 0.45
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
    # Prepended to web-fallback queries so results stay on-domain (a bare "E4" would otherwise pull
    # unrelated "HP printer E4" hits). Set empty to search the raw question.
    web_search_scope: str = "Jensen industrial laundry equipment"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
