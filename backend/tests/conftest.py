"""
Shared test fixtures — TestClient, in-memory SQLite, mock external services.
"""

import os
import tempfile

# Set environment variables BEFORE any app imports to avoid /app filesystem access
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

# Patch disk cache dir before infrastructure.market_data imports it
import domain.constants  # noqa: E402

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache"
)

from collections.abc import Generator  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from infrastructure.database import get_session  # noqa: E402
from main import app  # noqa: E402

# ---------------------------------------------------------------------------
# In-memory SQLite engine with StaticPool (shared single connection)
# ---------------------------------------------------------------------------

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def _override_get_session() -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Mock external services — yfinance & Telegram
# ---------------------------------------------------------------------------

MOCK_SIGNALS = {
    "ticker": "NVDA",
    "price": 120.0,
    "previous_close": 118.0,
    "change_pct": 1.69,  # (120-118)/118*100 = 1.69%
    "rsi": 55.0,
    "ma200": 100.0,
    "ma60": 110.0,
    "bias": 9.1,
    "volume_ratio": 1.2,
    "status": ["價格在 MA200 之上", "RSI 正常"],
}

MOCK_MOAT = {
    "ticker": "NVDA",
    "moat": "護城河穩固",
    "details": "毛利率 YoY +2.1%",
    "margins": [{"quarter": "Q1", "margin": 65.0}],
    "yoy_change": 2.1,
}

MOCK_FEAR_GREED = {
    "composite_score": 38,  # CNN-primary: equals CNN mock score directly
    "composite_level": "FEAR",
    "vix": {
        "value": 22.5,
        "change_1d": 1.2,
        "level": "FEAR",
        "fetched_at": "2025-06-15T10:00:00+00:00",
    },
    "cnn": {
        "score": 38,
        "label": "Fear",
        "level": "FEAR",
        "fetched_at": "2025-06-15T10:00:00+00:00",
    },
    "fetched_at": "2025-06-15T10:00:00+00:00",
}


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create all tables once for the test session."""
    import domain.entities  # noqa: F401 — register models with SQLModel

    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate all tables between tests for isolation."""
    yield
    with Session(test_engine) as session:
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.exec(table.delete())  # type: ignore[arg-type]
        session.commit()


# All external service patches — collected as a list to avoid Python's
# "too many statically nested blocks" limit with the `with` statement.
_MOCK_EARNINGS = {"ticker": "NVDA", "next_earnings_date": None}
_MOCK_DIVIDEND = {"ticker": "NVDA", "dividend_yield": None}
_MOCK_FX_RATES = {"USD": 1.0, "TWD": 0.032}

_PATCHES: list[tuple[str, object]] = [
    # Infrastructure layer
    ("infrastructure.market_data.get_technical_signals", MOCK_SIGNALS),
    ("infrastructure.market_data.get_price_history", []),
    ("infrastructure.market_data.get_earnings_date", _MOCK_EARNINGS),
    ("infrastructure.market_data.get_dividend_info", _MOCK_DIVIDEND),
    ("infrastructure.market_data.get_fear_greed_index", MOCK_FEAR_GREED),
    ("infrastructure.notification.send_telegram_message", None),
    ("infrastructure.notification.send_telegram_message_dual", None),
    # scan_service
    ("application.scan_service.get_technical_signals", MOCK_SIGNALS),
    ("application.scan_service.analyze_moat_trend", MOCK_MOAT),
    ("application.scan_service.get_fear_greed_index", MOCK_FEAR_GREED),
    # rebalance_service
    ("application.rebalance_service.get_technical_signals", MOCK_SIGNALS),
    ("application.rebalance_service.get_exchange_rates", _MOCK_FX_RATES),
    ("application.rebalance_service.get_etf_top_holdings", []),
    ("application.rebalance_service.get_forex_history", []),
    ("application.rebalance_service.get_forex_history_long", []),
    ("application.rebalance_service.prewarm_signals_batch", {}),
    ("application.rebalance_service.prewarm_etf_holdings_batch", {}),
    # webhook_service
    ("application.webhook_service.get_technical_signals", MOCK_SIGNALS),
    ("application.webhook_service.analyze_moat_trend", MOCK_MOAT),
    ("application.webhook_service.get_fear_greed_index", MOCK_FEAR_GREED),
    # notification_service
    ("application.notification_service.get_fear_greed_index", MOCK_FEAR_GREED),
    # stock_service
    ("application.stock_service.analyze_moat_trend", MOCK_MOAT),
    ("application.stock_service.get_technical_signals", MOCK_SIGNALS),
    ("application.stock_service.get_earnings_date", _MOCK_EARNINGS),
    ("application.stock_service.get_dividend_info", _MOCK_DIVIDEND),
    ("application.stock_service.detect_is_etf", False),
    # API routes
    ("api.scan_routes.get_fear_greed_index", MOCK_FEAR_GREED),
    # prewarm_service (prevent background prewarm during tests)
    ("application.prewarm_service.prewarm_all_caches", None),
]


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """TestClient with overridden DB session and mocked external services."""
    app.dependency_overrides[get_session] = _override_get_session

    patchers = [patch(target, return_value=rv) for target, rv in _PATCHES]
    for p in patchers:
        p.start()

    with TestClient(app) as c:
        yield c

    for p in patchers:
        p.stop()

    app.dependency_overrides.clear()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Standalone DB session fixture for service layer unit tests."""
    with Session(test_engine) as session:
        yield session
        session.rollback()
