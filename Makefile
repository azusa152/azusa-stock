# ===========================================================================
#  Folio — Development Shortcuts
# ===========================================================================
#
#  Quick reference (run `make help` for the full list):
#
#  Fullstack (composite):
#    make ci               Run all linting + all tests (mirrors CI)
#    make lint             Lint backend + frontend
#    make test             Test backend (+ frontend when Phase 4 adds Vitest)
#    make format           Format backend code
#
#  Backend (granular):
#    make backend-lint     Ruff check + format check
#    make backend-test     pytest (in-memory SQLite)
#    make backend-format   Ruff format
#
#  Frontend (granular):
#    make frontend-lint    ESLint
#    make frontend-dev     Start Vite dev server
#    make frontend-build   Production build
#
#  Setup:
#    make setup            First-time: venv + npm + codegen
#    make install          Create backend venv and install deps
#    make frontend-install Install frontend deps (npm ci)
#    make generate-api     Export OpenAPI spec + regenerate TS types
#
#  Docker:
#    make up               Start all services (background)
#    make down             Stop and remove all containers
#    make restart          Rebuild and restart all services (down + up)
#
#  Utilities:
#    make generate-key     Generate a secure FOLIO_API_KEY
#    make security         Security audit (.env, secrets, pip-audit)
#    make clean            Remove build caches
#    make backup           Backup database to ./backups/
#    make restore          Restore database from latest backup
#    make help             List all available targets
#
# ===========================================================================

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------
BACKEND_DIR  := backend
FRONTEND_DIR := frontend-react

PYTHON ?= $(BACKEND_DIR)/.venv/bin/python
PIP    ?= $(BACKEND_DIR)/.venv/bin/pip
RUFF   ?= $(BACKEND_DIR)/.venv/bin/ruff

# Lazy-evaluated: only runs `docker volume ls` when backup/restore targets execute
VOLUME_NAME = $(shell docker volume ls --format '{{.Name}}' | grep radar-data | head -1)

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
#  Guards (hidden prerequisite targets — fail early with actionable messages)
# ---------------------------------------------------------------------------
.PHONY: .venv-check .node-check

.venv-check:
	@test -x $(PYTHON) || \
		{ echo "Error: backend venv not found. Run 'make install' first."; exit 1; }

.node-check:
	@test -d $(FRONTEND_DIR)/node_modules || \
		{ echo "Error: node_modules not found. Run 'make frontend-install' first."; exit 1; }

# ---------------------------------------------------------------------------
#  Setup & Install
# ---------------------------------------------------------------------------
.PHONY: setup install frontend-install

setup: install frontend-install generate-api ## Full first-time setup (backend + frontend + codegen)
	@echo "Setup complete. Run 'make ci' to verify everything passes."

install: ## Create backend venv and install dependencies
	cd $(BACKEND_DIR) && python3 -m venv .venv
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt

frontend-install: ## Install frontend dependencies (npm ci)
	cd $(FRONTEND_DIR) && npm ci

# ---------------------------------------------------------------------------
#  Backend (granular)
# ---------------------------------------------------------------------------
.PHONY: backend-lint backend-test backend-format

backend-lint: .venv-check ## Ruff check + format --check (backend only)
	$(RUFF) check --fix $(BACKEND_DIR)/
	$(RUFF) format --check $(BACKEND_DIR)/

backend-test: .venv-check ## Run pytest with in-memory SQLite (backend only)
	LOG_DIR=/tmp/folio_test_logs DATABASE_URL=sqlite:// \
		$(PYTHON) -m pytest $(BACKEND_DIR)/tests/ -v --tb=short

backend-format: .venv-check ## Ruff format — rewrite files in place (backend only)
	$(RUFF) format $(BACKEND_DIR)/

# ---------------------------------------------------------------------------
#  Frontend (granular)
# ---------------------------------------------------------------------------
.PHONY: frontend-lint frontend-dev frontend-build

frontend-lint: .node-check ## ESLint (frontend only)
	cd $(FRONTEND_DIR) && npm run lint

frontend-dev: .node-check generate-api ## Start Vite dev server (requires backend venv; or cd frontend-react && npm run dev)
	cd $(FRONTEND_DIR) && npm run dev

frontend-build: .node-check generate-api ## Build frontend for production (requires backend venv; or cd frontend-react && npm run build)
	cd $(FRONTEND_DIR) && npm run build

# ---------------------------------------------------------------------------
#  Fullstack / Composite
# ---------------------------------------------------------------------------
.PHONY: lint test format ci clean

lint: backend-lint frontend-lint ## Lint entire project (backend + frontend)

test: backend-test ## Test entire project (backend now; frontend-test added in Phase 4)

format: backend-format ## Format entire project (backend code)

ci: lint test ## Full CI check — runs all linting + all tests

clean: ## Remove build caches (.pytest_cache, .ruff_cache, dist, node_modules/.cache)
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.ruff_cache
	rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/node_modules/.cache

# ---------------------------------------------------------------------------
#  API Codegen
# ---------------------------------------------------------------------------
.PHONY: generate-api

generate-api: .venv-check ## Export OpenAPI spec and regenerate TypeScript types
	$(PYTHON) scripts/export_openapi.py
	cd $(FRONTEND_DIR) && npx openapi-typescript src/api/openapi.json -o src/api/types/generated.d.ts

# ---------------------------------------------------------------------------
#  Docker
# ---------------------------------------------------------------------------
.PHONY: up down restart

up: ## Start all services (background, rebuild images)
	docker compose up -d --build

down: ## Stop and remove all containers
	docker compose down

restart: down up ## Rebuild and restart all services (preserves data volumes)

# ---------------------------------------------------------------------------
#  Database
# ---------------------------------------------------------------------------
.PHONY: backup restore

backup: ## Backup database to ./backups/
	@mkdir -p backups
	@vol=$(VOLUME_NAME); \
	if [ -z "$$vol" ]; then echo "Error: radar-data volume not found"; exit 1; fi; \
	docker run --rm -v $$vol:/data -v $$(pwd)/backups:/backup alpine \
		cp /data/radar.db /backup/radar-$$(date +%Y%m%d_%H%M%S).db
	@echo "Backup saved to ./backups/"
	@ls -lh backups/radar-*.db | tail -1

restore: ## Restore database (use FILE=backups/radar-xxx.db or defaults to latest)
	@vol=$(VOLUME_NAME); \
	if [ -z "$$vol" ]; then echo "Error: radar-data volume not found"; exit 1; fi; \
	file=$${FILE:-$$(ls -t backups/radar-*.db 2>/dev/null | head -1)}; \
	if [ -z "$$file" ]; then echo "Error: No backup found in ./backups/"; exit 1; fi; \
	docker run --rm -v $$vol:/data -v $$(pwd)/backups:/backup alpine \
		cp /backup/$$(basename $$file) /data/radar.db; \
	echo "Restored from $$file"

# ---------------------------------------------------------------------------
#  Utilities
# ---------------------------------------------------------------------------
.PHONY: generate-key security help

generate-key: ## Generate a secure API key (add to .env as FOLIO_API_KEY)
	@echo "Generated API Key (add to .env as FOLIO_API_KEY):"
	@python3 -c "import secrets; print(f'sk-folio-{secrets.token_urlsafe(32)}')"

security: ## Security audit (.env file, hardcoded secrets, pip-audit)
	@echo "=== Security Audit ==="
	@echo ""
	@echo "--- .env file ---"
	@if [ -f .env ]; then echo ".env exists"; else echo "WARNING: .env not found (copy from .env.example)"; fi
	@echo ""
	@echo "--- FOLIO_API_KEY ---"
	@if grep -q 'FOLIO_API_KEY=.' .env 2>/dev/null; then echo "FOLIO_API_KEY is set"; else echo "WARNING: FOLIO_API_KEY is empty or missing (run: make generate-key)"; fi
	@echo ""
	@echo "--- Secrets in source ---"
	@if rg -l 'sk-folio-|TELEGRAM.*=[0-9]' --glob '!.env*' --glob '!*.example' --glob '!Makefile' . 2>/dev/null; then echo "ERROR: Potential secrets found in source!"; else echo "No hardcoded secrets detected"; fi
	@echo ""
	@echo "--- .env in .gitignore ---"
	@if grep -q '^\.env$$' .gitignore 2>/dev/null; then echo ".env is in .gitignore"; else echo "WARNING: .env is NOT in .gitignore"; fi

help: ## List all available Make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
