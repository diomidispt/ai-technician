.PHONY: demo dev down backend-dev frontend-dev test lint help

help:
	@echo "Jensen AI Technical Support Assistant — make targets"
	@echo "  make demo          Full local stack via docker compose (frontend :5173, api :8000)"
	@echo "  make dev           Alias for demo"
	@echo "  make down          Stop the local stack"
	@echo "  make backend-dev   Run backend only (uvicorn --reload) without Docker"
	@echo "  make frontend-dev  Run frontend only (Vite) without Docker"
	@echo "  make test          Run backend tests"
	@echo "  make lint          ruff check + format the backend"

demo dev:
	docker compose up --build

down:
	docker compose down

backend-dev:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm install && npm run dev

test:
	cd backend && pytest

lint:
	ruff check backend && ruff format backend
