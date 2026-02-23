# ---------------------------------------------------------------------------
# Folio — Development Shortcuts
# ---------------------------------------------------------------------------
# Usage:
#   make setup            # 首次完整設定（後端 venv + 前端 npm + 型別產生）
#   make install          # 安裝後端依賴（建立 venv + pip install）
#   make generate-api     # 匯出 OpenAPI 規格並產生前端 TypeScript 型別
#   make test             # 執行所有後端測試
#   make lint             # Ruff 靜態分析（自動修正）
#   make format           # Ruff 程式碼格式化
#   make frontend-install # 安裝前端依賴（npm ci）
#   make frontend-dev     # 啟動前端開發伺服器（需後端 venv；純前端請用 npm run dev）
#   make frontend-build   # 建構前端生產版本（需後端 venv；純前端請用 npm run build）
#   make frontend-lint    # 執行前端 ESLint
#   make up               # 啟動所有服務（背景執行）
#   make down             # 停止並移除所有容器
#   make restart          # 重新建構並重啟所有服務（保留資料）
#   make security         # 安全性檢查（.env 檔案、API Key、敏感資料）
#   make help             # 列出所有可用目標
# ---------------------------------------------------------------------------

PYTHON   ?= backend/.venv/bin/python
PIP      ?= backend/.venv/bin/pip
RUFF     ?= backend/.venv/bin/ruff

# 測試環境變數（與 CI 一致）
export LOG_DIR       ?= /tmp/folio_test_logs
export DATABASE_URL  ?= sqlite://

.DEFAULT_GOAL := help

.PHONY: help install test lint format generate-key backup restore up down restart security frontend-install frontend-dev frontend-build frontend-lint generate-api setup

# Dynamic volume name detection (project directory name may vary)
VOLUME_NAME := $(shell docker volume ls --format '{{.Name}}' | grep radar-data | head -1)

help: ## 列出所有可用的 Make 目標
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## 建立 venv 並安裝依賴（首次設定用）
	cd backend && python3 -m venv .venv
	$(PIP) install -r backend/requirements.txt

test: ## 執行所有後端測試（in-memory SQLite，與 CI 一致）
	$(PYTHON) -m pytest backend/tests/ -v --tb=short

lint: ## 執行 ruff check --fix + format --check（靜態分析 + 格式檢查）
	$(RUFF) check --fix backend/
	$(RUFF) format --check backend/

format: ## 執行 ruff format（程式碼格式化）
	$(RUFF) format backend/

generate-key: ## 生成安全的 API Key（用於 FOLIO_API_KEY）
	@echo "Generated API Key (add to .env as FOLIO_API_KEY):"
	@python3 -c "import secrets; print(f'sk-folio-{secrets.token_urlsafe(32)}')"

backup: ## 備份資料庫到 ./backups/
	@mkdir -p backups
	@vol=$(VOLUME_NAME); \
	if [ -z "$$vol" ]; then echo "❌ Error: radar-data volume not found"; exit 1; fi; \
	docker run --rm -v $$vol:/data -v $$(pwd)/backups:/backup alpine \
		cp /data/radar.db /backup/radar-$$(date +%Y%m%d_%H%M%S).db
	@echo "✅ Backup saved to ./backups/"
	@ls -lh backups/radar-*.db | tail -1

restore: ## 還原資料庫（用法：make restore 或 make restore FILE=backups/radar-xxx.db）
	@vol=$(VOLUME_NAME); \
	if [ -z "$$vol" ]; then echo "❌ Error: radar-data volume not found"; exit 1; fi; \
	file=$${FILE:-$$(ls -t backups/radar-*.db 2>/dev/null | head -1)}; \
	if [ -z "$$file" ]; then echo "❌ Error: No backup found in ./backups/"; exit 1; fi; \
	docker run --rm -v $$vol:/data -v $$(pwd)/backups:/backup alpine \
		cp /backup/$$(basename $$file) /data/radar.db; \
	echo "✅ Restored from $$file"

up: ## 啟動所有服務（背景執行）
	docker compose up -d --build

down: ## 停止並移除所有容器
	docker compose down

restart: ## 重新建構並重啟所有服務（保留資料）
	docker compose up --build -d

frontend-install: ## 安裝前端依賴（npm ci）
	cd frontend-react && npm ci

generate-api: ## 匯出 OpenAPI 規格並產生 TypeScript 型別
	$(PYTHON) scripts/export_openapi.py
	cd frontend-react && npx openapi-typescript src/api/openapi.json -o src/api/types/generated.d.ts

setup: install frontend-install generate-api ## 首次完整設定（後端 + 前端 + 型別產生）
	@echo "Setup complete."

frontend-dev: generate-api ## 啟動前端開發伺服器（需後端 venv — 純前端請用 npm run dev）
	cd frontend-react && npm run dev

frontend-build: generate-api ## 建構前端生產版本（需後端 venv — 純前端請用 npm run build）
	cd frontend-react && npm run build

frontend-lint: ## 執行前端 ESLint
	cd frontend-react && npm run lint

security: ## 安全性檢查（.env 檔案、API Key、敏感資料）
	@echo "=== Security Audit ==="
	@echo ""
	@echo "--- .env file ---"
	@if [ -f .env ]; then echo "✅ .env exists"; else echo "⚠️  .env not found (copy from .env.example)"; fi
	@echo ""
	@echo "--- FOLIO_API_KEY ---"
	@if grep -q 'FOLIO_API_KEY=.' .env 2>/dev/null; then echo "✅ FOLIO_API_KEY is set"; else echo "⚠️  FOLIO_API_KEY is empty or missing (run: make generate-key)"; fi
	@echo ""
	@echo "--- Secrets in source ---"
	@if rg -l 'sk-folio-|TELEGRAM.*=[0-9]' --glob '!.env*' --glob '!*.example' --glob '!Makefile' . 2>/dev/null; then echo "❌ Potential secrets found in source!"; else echo "✅ No hardcoded secrets detected"; fi
	@echo ""
	@echo "--- .env in .gitignore ---"
	@if grep -q '^\.env$$' .gitignore 2>/dev/null; then echo "✅ .env is in .gitignore"; else echo "⚠️  .env is NOT in .gitignore"; fi
