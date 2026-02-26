"""
Unit tests for snapshot_service: take_daily_snapshot, get_snapshots, get_snapshot_range,
_needs_backfill, backfill_benchmark_values.

All external I/O is mocked — no yfinance requests, no Telegram calls.
DB uses the in-memory SQLite engine from conftest.
"""

import json
from datetime import date, timedelta
from unittest.mock import patch

from sqlmodel import Session, select

from application.portfolio.snapshot_service import (
    _needs_backfill,
    backfill_benchmark_values,
    get_snapshot_range,
    get_snapshots,
    take_daily_snapshot,
)
from domain.entities import PortfolioSnapshot

# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

_REBALANCE_PATCH = "application.portfolio.rebalance_service.calculate_rebalance"
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


# ---------------------------------------------------------------------------
# _needs_backfill
# ---------------------------------------------------------------------------


class TestNeedsBackfill:
    """White-box tests for the private _needs_backfill helper."""

    def test_should_return_true_for_invalid_json(self):
        assert _needs_backfill("not-valid-json") is True

    def test_should_return_true_for_empty_dict(self):
        assert _needs_backfill("{}") is True

    def test_should_return_true_when_any_value_is_null(self):
        assert _needs_backfill('{"^GSPC": null, "VT": 120.0}') is True

    def test_should_return_true_when_none_is_stored(self):
        # None (Python) is serialized to null in JSON
        assert _needs_backfill("null") is True

    def test_should_return_false_when_all_values_are_present(self):
        assert _needs_backfill('{"^GSPC": 5000.0, "VT": 120.0}') is False


# ---------------------------------------------------------------------------
# backfill_benchmark_values
# ---------------------------------------------------------------------------

_BENCHMARK_HISTORY_PATCH = "infrastructure.market_data.get_benchmark_close_history"


class TestBackfillBenchmarkValues:
    def test_should_return_zero_when_no_snapshots_need_backfill(
        self, db_session: Session
    ):
        """If every snapshot already has all benchmark values, nothing is updated."""
        today = date.today()
        snap = PortfolioSnapshot(
            snapshot_date=today,
            total_value=100_000.0,
            category_values=json.dumps({"Growth": 100_000.0}),
            display_currency="USD",
            benchmark_values=json.dumps({"^GSPC": 5000.0, "VT": 120.0}),
        )
        db_session.add(snap)
        db_session.commit()

        result = backfill_benchmark_values(db_session)

        assert result == 0

    def test_should_return_zero_when_there_are_no_snapshots_at_all(
        self, db_session: Session
    ):
        """Empty table → early-exit path, returns 0."""
        result = backfill_benchmark_values(db_session)
        assert result == 0

    def test_should_update_snapshots_with_missing_benchmark_values(
        self, db_session: Session
    ):
        """Snapshots with empty benchmark_values dict should be filled in."""
        import pandas as pd

        today = date.today()
        snap = PortfolioSnapshot(
            snapshot_date=today,
            total_value=100_000.0,
            category_values=json.dumps({"Growth": 100_000.0}),
            display_currency="USD",
            benchmark_values="{}",  # needs backfill
        )
        db_session.add(snap)
        db_session.commit()

        # Return a one-row Series with a price on `today`
        mock_series = pd.Series(
            [5000.0],
            index=pd.DatetimeIndex([pd.Timestamp(today, tz="UTC")]),
        )

        with patch(_BENCHMARK_HISTORY_PATCH, return_value=mock_series):
            result = backfill_benchmark_values(db_session)

        assert result > 0
        db_session.refresh(snap)
        bv = json.loads(snap.benchmark_values)
        assert any(v is not None for v in bv.values())
