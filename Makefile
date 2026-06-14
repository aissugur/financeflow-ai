# Convenience shortcuts. On Windows, run the underlying commands directly if you
# don't have `make` (see README "Local setup").

.PHONY: install backend frontend test eval docker-up docker-down

install:        ## Install backend (dev) + frontend dependencies
	cd backend && pip install -r requirements-dev.txt
	cd frontend && npm install

backend:        ## Run the FastAPI backend with auto-reload on :8000
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:       ## Run the Vite dev server on :5173
	cd frontend && npm run dev

test:           ## Run the backend test suite
	cd backend && pytest

eval:           ## Run the anti-hallucination evaluation from the CLI
	cd backend && python -m app.eval_cli

docker-up:      ## Build and run backend + frontend with Docker Compose
	docker compose up --build

docker-down:    ## Stop and remove the Docker Compose stack
	docker compose down
