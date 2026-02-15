# Folio — Investment Analysis System

**Folio** is a self-hosted, thesis-driven stock tracking system for disciplined investors. Track watchlist stocks, monitor market signals, and analyze currency exposure across your portfolio.

## Tech Stack
- **Backend:** FastAPI (Python 3.12+)
- **Frontend:** Streamlit
- **Database:** SQLite (via SQLModel)
- **Infrastructure:** Docker Compose
- **Data Source:** yfinance
- **Notifications:** Telegram Bot API

## Critical Rules
- **Language:** All UI text and log messages MUST be in **Traditional Chinese (繁體中文)**
- **Clean Architecture:** Backend follows strict layering (domain → application → infrastructure → api)
- **AI Agent-First:** Every API endpoint must be machine-readable and self-documenting

---

# Project Rules

Always read and follow the cursor rules at the start of every task:

- `.cursor/rules/project-core.mdc` — Project role, investment philosophy, tech stack
- `.cursor/rules/coding-standards.mdc` — Clean Architecture, Clean Code principles
- `.cursor/rules/python-tooling.mdc` — Python, ruff, logging (auto-attached for backend)
- `.cursor/rules/testing.mdc` — pytest standards (auto-attached for tests)
- `.cursor/rules/docker.mdc` — Container best practices (auto-attached for Docker files)
- `.cursor/rules/security.mdc` — Secrets management (agent-requested)
- `.cursor/rules/frontend-standards.mdc` — Streamlit caching, session state, privacy mode
- `.cursor/rules/git-conventions.mdc` — Commit format, branch naming, branch workflow
- `.cursor/rules/ai-agent-friendly.mdc` — AI agent API design, OpenAPI, webhook discoverability
