"""Tests for RemovalLog, ThesisLog, and ScanLog repository functions in repositories.py."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from domain.entities import RemovalLog, ScanLog, Stock, ThesisLog
from domain.enums import StockCategory
from infrastructure.repositories import (
    create_removal_log,
    create_scan_log,
    create_thesis_log,
    find_latest_removal,
    find_latest_removals_batch,
    find_removal_history,
    find_scan_history,
    find_thesis_history,
    get_max_thesis_version,
    save_stock,
)


@pytest.fixture
def test_session() -> Iterator[Session]:
    from tests.conftest import test_engine

    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def seed_stock(test_session: Session):
    """Ensure a Stock row exists for FK constraints before each test."""
    for ticker in ("AAPL", "MSFT"):
        existing = test_session.get(Stock, ticker)
        if existing is None:
            save_stock(
                test_session,
                Stock(ticker=ticker, category=StockCategory.MOAT),
            )


# ===========================================================================
# ThesisLog Repository
# ===========================================================================


class TestThesisLogRepository:
    def test_create_thesis_log_and_get_max_version(self, test_session: Session):
        thesis = ThesisLog(stock_ticker="AAPL", content="Initial thesis", version=1)
        create_thesis_log(test_session, thesis)
        test_session.commit()

        max_v = get_max_thesis_version(test_session, "AAPL")
        assert max_v >= 1

    def test_find_thesis_history_returns_ordered_desc(self, test_session: Session):
        for v in range(1, 4):
            log = ThesisLog(stock_ticker="MSFT", content=f"Thesis v{v}", version=v)
            create_thesis_log(test_session, log)
        test_session.commit()

        history = find_thesis_history(test_session, "MSFT")
        assert len(history) >= 3
        # Versions should be descending
        versions = [h.version for h in history]
        assert versions == sorted(versions, reverse=True)

    def test_find_thesis_history_empty_for_unknown_ticker(self, test_session: Session):
        history = find_thesis_history(test_session, "UNKNOWN_XYZ")
        assert history == []

    def test_get_max_thesis_version_returns_zero_when_no_entries(
        self, test_session: Session
    ):
        max_v = get_max_thesis_version(test_session, "TOTALLY_NEW_TICKER_ABC")
        assert max_v == 0


# ===========================================================================
# RemovalLog Repository
# ===========================================================================


class TestRemovalLogRepository:
    def test_create_and_find_latest_removal(self, test_session: Session):
        log = RemovalLog(stock_ticker="AAPL", reason="Thesis invalidated")
        create_removal_log(test_session, log)
        test_session.commit()

        latest = find_latest_removal(test_session, "AAPL")
        assert latest is not None
        assert latest.reason == "Thesis invalidated"

    def test_find_latest_removal_returns_none_for_unknown(self, test_session: Session):
        result = find_latest_removal(test_session, "NO_SUCH_TICKER")
        assert result is None

    def test_find_removal_history_returns_all_entries(self, test_session: Session):
        now = datetime.now(UTC)
        for i, reason in enumerate(["First removal", "Second removal"]):
            log = RemovalLog(
                stock_ticker="MSFT",
                reason=reason,
                created_at=now + timedelta(hours=i),
            )
            create_removal_log(test_session, log)
        test_session.commit()

        history = find_removal_history(test_session, "MSFT")
        assert len(history) >= 2
        # Should be descending by created_at
        dates = [h.created_at for h in history]
        assert dates == sorted(dates, reverse=True)

    def test_find_removal_history_empty_for_unknown_ticker(self, test_session: Session):
        history = find_removal_history(test_session, "NO_REMOVAL_TICKER")
        assert history == []

    def test_find_latest_removals_batch_returns_latest_per_ticker(
        self, test_session: Session
    ):
        now = datetime.now(UTC)
        for i, reason in enumerate(["Old AAPL removal", "New AAPL removal"]):
            log = RemovalLog(
                stock_ticker="AAPL",
                reason=reason,
                created_at=now + timedelta(hours=i),
            )
            create_removal_log(test_session, log)
        create_removal_log(
            test_session,
            RemovalLog(
                stock_ticker="MSFT",
                reason="MSFT removal",
                created_at=now,
            ),
        )
        test_session.commit()

        result = find_latest_removals_batch(test_session, ["AAPL", "MSFT"])
        assert "AAPL" in result
        assert "MSFT" in result
        # Should be the latest AAPL removal
        assert result["AAPL"].reason == "New AAPL removal"

    def test_find_latest_removals_batch_empty_list_returns_empty_dict(
        self, test_session: Session
    ):
        result = find_latest_removals_batch(test_session, [])
        assert result == {}


# ===========================================================================
# ScanLog Repository
# ===========================================================================


class TestScanLogRepository:
    def test_create_and_find_scan_history(self, test_session: Session):
        log = ScanLog(
            stock_ticker="AAPL",
            signal="NORMAL",
            market_status="NEUTRAL",
            market_status_details="",
        )
        create_scan_log(test_session, log)
        test_session.commit()

        history = find_scan_history(test_session, "AAPL")
        assert len(history) >= 1
        assert any(h.signal == "NORMAL" for h in history)

    def test_find_scan_history_respects_limit(self, test_session: Session):
        for i in range(5):
            log = ScanLog(
                stock_ticker="MSFT",
                signal="NORMAL",
                market_status="NEUTRAL",
                scanned_at=datetime.now(UTC) + timedelta(minutes=i),
            )
            create_scan_log(test_session, log)
        test_session.commit()

        history = find_scan_history(test_session, "MSFT", limit=2)
        assert len(history) <= 2

    def test_find_scan_history_ordered_desc(self, test_session: Session):
        now = datetime.now(UTC)
        for i in range(3):
            log = ScanLog(
                stock_ticker="AAPL",
                signal="CAUTION_HIGH",
                market_status="GREED",
                scanned_at=now + timedelta(minutes=i),
            )
            create_scan_log(test_session, log)
        test_session.commit()

        history = find_scan_history(test_session, "AAPL")
        times = [h.scanned_at for h in history]
        assert times == sorted(times, reverse=True)

    def test_find_scan_history_empty_for_unknown_ticker(self, test_session: Session):
        history = find_scan_history(test_session, "NO_SCAN_TICKER")
        assert history == []
