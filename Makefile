# ---------------------------------------------------------------------------
# Folio — Development Shortcuts
# ---------------------------------------------------------------------------
# Usage:
#   make install   # 首次安裝依賴（建立 venv + pip install）
#   make test      # 執行所有後端測試
#   make lint      # Ruff 靜態分析（自動修正）
#   make format    # Ruff 程式碼格式化
#   make help      # 列出所有可用目標
# ---------------------------------------------------------------------------

PYTHON   ?= backend/.venv/bin/python
PIP      ?= backend/.venv/bin/pip
RUFF     ?= backend/.venv/bin/ruff

# 測試環境變數（與 CI 一致）
export LOG_DIR       ?= /tmp/folio_test_logs
export DATABASE_URL  ?= sqlite://

.DEFAULT_GOAL := help

.PHONY: help install test lint format

help: ## 列出所有可用的 Make 目標
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## 建立 venv 並安裝依賴（首次設定用）
	cd backend && python3 -m venv .venv
	$(PIP) install -r backend/requirements.txt

test: ## 執行所有後端測試（in-memory SQLite，與 CI 一致）
	$(PYTHON) -m pytest backend/tests/ -v --tb=short

lint: ## 執行 ruff check --fix（靜態分析 + 自動修正）
	$(RUFF) check --fix backend/

format: ## 執行 ruff format（程式碼格式化）
	$(RUFF) format backend/
