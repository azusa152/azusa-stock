"""Tests for GET /snapshots and GET /snapshots/twr endpoints."""

import json
from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from domain.entities import PortfolioSnapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_snapshot(
    session: Session,
    snapshot_date: date,
    total_value: float,
    benchmark_value: float | None = None,
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
# GET /snapshots
# ---------------------------------------------------------------------------


class TestListSnapshots:
    def test_should_return_empty_list_when_no_snapshots(self, client: TestClient):
        resp = client.get("/snapshots")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_should_return_snapshots_ordered_by_date(
        self, client: TestClient, db_session: Session
    ):
        today = datetime.now(UTC).date()
        _insert_snapshot(db_session, today - timedelta(days=2), 100_000)
        _insert_snapshot(db_session, today - timedelta(days=1), 105_000)
        _insert_snapshot(db_session, today, 110_000)

        resp = client.get("/snapshots", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Ascending order — oldest first
        assert data[0]["total_value"] == 100_000
        assert data[-1]["total_value"] == 110_000

    def test_should_reject_invalid_days_range(self, client: TestClient):
        resp = client.get("/snapshots", params={"days": 0})
        assert resp.status_code == 422

        resp = client.get("/snapshots", params={"days": 731})
        assert resp.status_code == 422

    def test_should_accept_max_days(self, client: TestClient):
        resp = client.get("/snapshots", params={"days": 730})
        assert resp.status_code == 200

    def test_should_reject_start_without_end(self, client: TestClient):
        resp = client.get("/snapshots", params={"start": "2025-01-01"})
        assert resp.status_code == 422

    def test_should_reject_start_after_end(self, client: TestClient):
        resp = client.get(
            "/snapshots", params={"start": "2025-06-01", "end": "2025-01-01"}
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /snapshots/twr
# ---------------------------------------------------------------------------


class TestGetTwr:
    def test_should_return_none_when_no_snapshots(self, client: TestClient):
        resp = client.get("/snapshots/twr")
        assert resp.status_code == 200
        data = resp.json()
        assert data["twr_pct"] is None
        assert data["snapshot_count"] == 0

    def test_should_return_none_for_single_snapshot(
        self, client: TestClient, db_session: Session
    ):
        today = datetime.now(UTC).date()
        _insert_snapshot(db_session, today, 100_000)
        resp = client.get("/snapshots/twr")
        assert resp.status_code == 200
        data = resp.json()
        assert data["twr_pct"] is None
        assert data["snapshot_count"] == 1

    def test_should_compute_positive_twr(self, client: TestClient, db_session: Session):
        today = datetime.now(UTC).date()
        start = date(today.year, 1, 1)
        _insert_snapshot(db_session, start, 100_000)
        _insert_snapshot(db_session, start + timedelta(days=30), 110_000)

        resp = client.get(
            "/snapshots/twr",
            params={
                "start": start.isoformat(),
                "end": (start + timedelta(days=30)).isoformat(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["twr_pct"] == 10.0
        assert data["snapshot_count"] == 2
        assert data["start_date"] is not None
        assert data["end_date"] is not None

    def test_should_compute_negative_twr(self, client: TestClient, db_session: Session):
        today = datetime.now(UTC).date()
        start = date(today.year, 1, 1)
        _insert_snapshot(db_session, start, 100_000)
        _insert_snapshot(db_session, start + timedelta(days=30), 90_000)

        resp = client.get(
            "/snapshots/twr",
            params={
                "start": start.isoformat(),
                "end": (start + timedelta(days=30)).isoformat(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["twr_pct"] == -10.0

    def test_should_reject_start_after_end(self, client: TestClient):
        resp = client.get(
            "/snapshots/twr",
            params={"start": "2025-06-01", "end": "2025-01-01"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /snapshots/backfill-benchmarks
# ---------------------------------------------------------------------------


class TestBackfillBenchmarks:
    def test_should_return_accepted_when_triggered(self, client: TestClient):
        resp = client.post("/snapshots/backfill-benchmarks")
        assert resp.status_code == 200
        assert resp.json()["message"]  # localized message, non-empty
