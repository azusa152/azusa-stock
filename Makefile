# ===========================================================================
#  Folio — Development Shortcuts
# ===========================================================================
#
#  Quick reference (run `make help` for the full list):
#
#  Fullstack (composite):
#    make ci               Full CI check — mirrors ALL GitHub CI pipeline jobs
#    make lint             Lint backend + frontend
#    make test             Test backend + frontend (pytest + Vitest)
#    make format           Format backend code
#
#  Backend (granular):
#    make backend-lint     Ruff check + format check
#    make backend-test     pytest (in-memory SQLite)
#    make backend-format   Ruff format
#    make backend-security pip-audit vulnerability scan
#
#  Frontend (granular):
#    make frontend-lint    ESLint
#    make frontend-dev     Start Vite dev server
#    make frontend-build   Production build (run generate-api first if types are stale)
#    make frontend-security npm audit (high severity)
#
#  CI Integrity:
#    make check-api-spec   Verify OpenAPI spec matches backend (mirrors CI api-spec job)
#    make check-constants  Verify backend/frontend constant sync
#    make check-ci         Verify make ci covers all GitHub CI pipeline jobs
#
#  Setup:
#    make setup            First-time: venv + npm + codegen + pre-commit hooks
#    make install          Create backend venv and install deps (incl. pip-audit)
#    make frontend-install Install frontend deps (npm ci)
#    make generate-api     Export OpenAPI spec + regenerate TS types
#    make setup-hooks      Install pre-commit hooks (architecture boundary + ruff)
#    make lock             Resolve deps: requirements.in → requirements.txt
#    make upgrade           Re-lock all deps to latest compatible versions
#
#  Docker:
#    make up               Start all services (background)
#    make down             Stop and remove all containers
#    make restart          Rebuild and restart all services (down + up)
#
#  Utilities:
#    make generate-key     Generate a secure FOLIO_API_KEY
#    make security         Security audit (.env, secrets)
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
.PHONY: setup install frontend-install setup-hooks

setup: install frontend-install generate-api setup-hooks ## Full first-time setup (backend + frontend + codegen + hooks)
	@echo "Setup complete. Run 'make ci' to verify everything passes."

install: ## Create backend venv and install dependencies
	cd $(BACKEND_DIR) && python3 -m venv .venv
	$(PIP) install pip-tools
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt

frontend-install: ## Install frontend dependencies (npm ci)
	cd $(FRONTEND_DIR) && npm ci

setup-hooks: .venv-check ## Install pre-commit hooks (auto-runs architecture boundary + ruff on every commit)
	$(PIP) install pre-commit
	$(BACKEND_DIR)/.venv/bin/pre-commit install

lock: .venv-check ## Resolve deps: requirements.in → requirements.txt (run after editing .in)
	$(BACKEND_DIR)/.venv/bin/pip-compile $(BACKEND_DIR)/requirements.in \
		--output-file=$(BACKEND_DIR)/requirements.txt --strip-extras

upgrade: .venv-check ## Re-lock all deps to latest compatible versions
	$(BACKEND_DIR)/.venv/bin/pip-compile $(BACKEND_DIR)/requirements.in \
		--output-file=$(BACKEND_DIR)/requirements.txt --strip-extras --upgrade

# ---------------------------------------------------------------------------
#  Backend (granular)
# ---------------------------------------------------------------------------
.PHONY: backend-lint backend-test backend-test-quick backend-format

backend-lint: .venv-check ## Ruff check + format --check (backend only)
	$(RUFF) check --fix $(BACKEND_DIR)/
	$(RUFF) format --check $(BACKEND_DIR)/

backend-test: .venv-check ## Run pytest with coverage (in-memory SQLite, backend only)
	LOG_DIR=/tmp/folio_test_logs DATABASE_URL=sqlite:// \
		$(PYTHON) -m pytest $(BACKEND_DIR)/tests/ -v --tb=short \
		-n auto --durations=20 \
		--cov --cov-config=$(BACKEND_DIR)/pyproject.toml --cov-report=term-missing

backend-test-quick: .venv-check ## Fast test run — no coverage, for local iteration
	LOG_DIR=/tmp/folio_test_logs DATABASE_URL=sqlite:// \
		$(PYTHON) -m pytest $(BACKEND_DIR)/tests/ -q --tb=short \
		-n auto

backend-format: .venv-check ## Ruff format — rewrite files in place (backend only)
	$(RUFF) format $(BACKEND_DIR)/

# ---------------------------------------------------------------------------
#  Frontend (granular)
# ---------------------------------------------------------------------------
.PHONY: frontend-lint frontend-dev frontend-build frontend-security

frontend-lint: .node-check ## ESLint (frontend only)
	cd $(FRONTEND_DIR) && npm run lint

frontend-dev: .node-check generate-api ## Start Vite dev server (requires backend venv; or cd frontend-react && npm run dev)
	cd $(FRONTEND_DIR) && npm run dev

frontend-build: .node-check ## Build frontend for production (run generate-api first if types are stale)
	cd $(FRONTEND_DIR) && npm run build

frontend-security: .node-check ## npm audit — frontend high-severity vulnerabilities (mirrors CI frontend-security job)
	cd $(FRONTEND_DIR) && npm audit --audit-level=high

# ---------------------------------------------------------------------------
#  Fullstack / Composite
# ---------------------------------------------------------------------------
.PHONY: lint test format ci clean frontend-test

lint: backend-lint frontend-lint ## Lint entire project (backend + frontend)

frontend-test: .node-check ## Run frontend tests with coverage (Vitest)
	cd $(FRONTEND_DIR) && npm run test:coverage

test: backend-test frontend-test ## Test entire project (backend + frontend)

format: backend-format ## Format entire project (backend code)

ci: lint test check-constants check-api-spec check-i18n frontend-build frontend-security backend-security ## Full CI check — mirrors all GitHub CI pipeline jobs

clean: ## Remove build caches (.pytest_cache, .ruff_cache, dist, node_modules/.cache)
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.ruff_cache
	rm -rf .pytest_cache .ruff_cache
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
.PHONY: generate-key security help check-constants check-api-spec check-i18n backend-security check-ci

check-constants: .venv-check ## Check backend/frontend constant sync
	$(PYTHON) scripts/check_constant_sync.py

check-i18n: ## Check locale key parity (backend + frontend locale files)
	python3 scripts/check_locale_parity.py

check-api-spec: .venv-check ## Check OpenAPI spec is up to date (mirrors CI api-spec job)
	LOG_DIR=/tmp/folio_logs DATABASE_URL=sqlite:// \
		$(PYTHON) scripts/export_openapi.py
	git diff --exit-code $(FRONTEND_DIR)/src/api/openapi.json

backend-security: .venv-check ## pip-audit — backend vulnerabilities (mirrors CI security job)
	$(BACKEND_DIR)/.venv/bin/pip-audit --desc --ignore-vuln CVE-2025-69872

check-ci: .venv-check ## Verify make ci covers all GitHub CI pipeline jobs
	$(PYTHON) scripts/check_ci_completeness.py

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
