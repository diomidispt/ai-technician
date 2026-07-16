.PHONY: demo dev down ingest backend-dev frontend-dev test lint help

help:
	@echo "Jensen AI Technical Support Assistant — make targets"
	@echo "  make demo          Full local stack via docker compose (frontend :5173, api :8000, db :5432)"
	@echo "  make dev           Alias for demo"
	@echo "  make down          Stop the local stack"
	@echo "  make ingest        Ingest PDFs from ingestion/sample_docs into pgvector (stack must be up)"
	@echo "  make backend-dev   Run backend only (uvicorn --reload) without Docker"
	@echo "  make frontend-dev  Run frontend only (Vite) without Docker"
	@echo "  make test          Run backend tests"
	@echo "  make lint          ruff check + format the backend"

demo dev:
	docker compose up --build

down:
	docker compose down

# Ingest PDFs (dropped in ingestion/sample_docs/) using the running backend container,
# which already has the deps + DB + Ollama config wired.
ingest:
	docker compose exec backend python -m app.ingestion.run /docs

backend-dev:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm install && npm run dev

test:
	cd backend && pytest

lint:
	ruff check backend && ruff format backend
