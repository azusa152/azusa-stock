"""
Unit tests for snapshot_service: take_daily_snapshot, get_snapshots, get_snapshot_range.

All external I/O is mocked — no yfinance requests, no Telegram calls.
DB uses the in-memory SQLite engine from conftest.
"""

import json
from datetime import date, timedelta
from unittest.mock import patch

from sqlmodel import Session, select

from application.snapshot_service import (
    get_snapshot_range,
    get_snapshots,
    take_daily_snapshot,
)
from domain.entities import PortfolioSnapshot

# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

_REBALANCE_PATCH = "application.rebalance_service.calculate_rebalance"
_SP500_PATCH = "infrastructure.market_data.get_technical_signals"

MOCK_REBALANCE = {
    "total_value": 100_000.0,
    "display_currency": "USD",
    "categories": {
        "Growth": {"market_value": 60_000.0, "drift_pct": 5.0},
        "Bond": {"market_value": 40_000.0, "drift_pct": -5.0},
    },
}

MOCK_SP500 = {"ticker": "^GSPC", "price": 5_100.0, "change_pct": 0.5}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_snapshot(
    session: Session,
    snapshot_date: date,
    total_value: float = 90_000.0,
    benchmark_value: float | None = 5_000.0,
) -> PortfolioSnapshot:
    snap = PortfolioSnapshot(
        snapshot_date=snapshot_date,
        total_value=total_value,
        category_values=json.dumps({"Growth": total_value}),
        display_currency="USD",
        benchmark_value=benchmark_value,
    )
    session.add(snap)
    session.commit()
    session.refresh(snap)
    return snap


# ---------------------------------------------------------------------------
# take_daily_snapshot
# ---------------------------------------------------------------------------


class TestTakeDailySnapshot:
    def test_should_store_total_value(self, db_session: Session):
        """Snapshot row must record total_value from rebalance result."""
        with (
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_SP500_PATCH, return_value=MOCK_SP500),
        ):
            snap = take_daily_snapshot(db_session)

        assert snap.id is not None
        assert snap.total_value == 100_000.0
        assert snap.display_currency == "USD"

    def test_should_store_category_values_as_json(self, db_session: Session):
        """category_values field must be valid JSON with category keys."""
        with (
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_SP500_PATCH, return_value=MOCK_SP500),
        ):
            snap = take_daily_snapshot(db_session)

        parsed = json.loads(snap.category_values)
        assert "Growth" in parsed
        assert parsed["Growth"] == 60_000.0
        assert parsed["Bond"] == 40_000.0

    def test_should_store_benchmark_value(self, db_session: Session):
        """benchmark_value must be populated from S&P 500 price."""
        with (
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_SP500_PATCH, return_value=MOCK_SP500),
        ):
            snap = take_daily_snapshot(db_session)

        assert snap.benchmark_value == 5_100.0

    def test_should_upsert_on_same_date(self, db_session: Session):
        """Calling take_daily_snapshot twice on the same date must update, not insert."""
        today = date.today()
        _insert_snapshot(db_session, today, total_value=80_000.0)

        with (
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_SP500_PATCH, return_value=MOCK_SP500),
        ):
            snap = take_daily_snapshot(db_session)

        # Must still be only one row for today
        all_today = list(
            db_session.exec(
                select(PortfolioSnapshot).where(
                    PortfolioSnapshot.snapshot_date == today
                )
            ).all()
        )
        assert len(all_today) == 1
        assert snap.total_value == 100_000.0  # updated, not the old 80k

    def test_should_tolerate_sp500_failure(self, db_session: Session):
        """benchmark_value should be None when S&P 500 fetch raises."""
        with (
            patch(_REBALANCE_PATCH, return_value=MOCK_REBALANCE),
            patch(_SP500_PATCH, side_effect=RuntimeError("yfinance down")),
        ):
            snap = take_daily_snapshot(db_session)

        assert snap.benchmark_value is None
        assert snap.total_value == 100_000.0  # rest of snapshot still saved


# ---------------------------------------------------------------------------
# get_snapshots
# ---------------------------------------------------------------------------


class TestGetSnapshots:
    def test_should_return_ordered_by_date(self, db_session: Session):
        """Results must be sorted ascending by snapshot_date."""
        today = date.today()
        _insert_snapshot(db_session, today - timedelta(days=2), total_value=88_000.0)
        _insert_snapshot(db_session, today - timedelta(days=1), total_value=92_000.0)
        _insert_snapshot(db_session, today, total_value=100_000.0)

        snaps = get_snapshots(db_session, days=7)

        assert len(snaps) == 3
        assert snaps[0].total_value == 88_000.0
        assert snaps[1].total_value == 92_000.0
        assert snaps[2].total_value == 100_000.0

    def test_should_respect_days_window(self, db_session: Session):
        """Snapshots older than the requested window must be excluded."""
        today = date.today()
        _insert_snapshot(db_session, today - timedelta(days=40), total_value=70_000.0)
        _insert_snapshot(db_session, today - timedelta(days=5), total_value=95_000.0)

        snaps = get_snapshots(db_session, days=30)

        assert len(snaps) == 1
        assert snaps[0].total_value == 95_000.0

    def test_should_return_empty_when_no_snapshots(self, db_session: Session):
        """Empty portfolio → empty list, no error."""
        snaps = get_snapshots(db_session, days=30)
        assert snaps == []


# ---------------------------------------------------------------------------
# get_snapshot_range
# ---------------------------------------------------------------------------


class TestGetSnapshotRange:
    def test_should_return_snapshots_within_range(self, db_session: Session):
        """Only snapshots within [start, end] (inclusive) must be returned."""
        today = date.today()
        _insert_snapshot(db_session, today - timedelta(days=10), total_value=80_000.0)
        _insert_snapshot(db_session, today - timedelta(days=5), total_value=90_000.0)
        _insert_snapshot(db_session, today, total_value=100_000.0)

        start = today - timedelta(days=6)
        end = today - timedelta(days=1)
        snaps = get_snapshot_range(db_session, start, end)

        assert len(snaps) == 1
        assert snaps[0].total_value == 90_000.0

    def test_should_be_inclusive_on_both_bounds(self, db_session: Session):
        """start and end dates must be included in the result."""
        today = date.today()
        start = today - timedelta(days=5)
        end = today - timedelta(days=1)

        _insert_snapshot(db_session, start, total_value=85_000.0)
        _insert_snapshot(db_session, end, total_value=95_000.0)

        snaps = get_snapshot_range(db_session, start, end)

        assert len(snaps) == 2
        assert snaps[0].snapshot_date == start
        assert snaps[1].snapshot_date == end

    def test_should_return_empty_for_out_of_range(self, db_session: Session):
        """No snapshots in range → empty list, no error."""
        today = date.today()
        _insert_snapshot(db_session, today - timedelta(days=10))

        snaps = get_snapshot_range(
            db_session,
            today - timedelta(days=3),
            today - timedelta(days=1),
        )
        assert snaps == []
