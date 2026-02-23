# Folio — Investment Analysis System

**Folio** is a self-hosted, thesis-driven stock tracking system for disciplined investors. Track watchlist stocks, monitor market signals, and analyze currency exposure.

## Quick Start

```bash
docker-compose up -d
make test          # Run backend tests
make lint          # Run ruff linter
make format        # Format code
```

## Frontend Development

```bash
cd frontend-react && npm run dev    # Start dev server (http://localhost:3000)
cd frontend-react && npm run build  # Production build
cd frontend-react && npm run lint   # ESLint
```

See `.cursor/rules/` for project conventions and coding standards.
