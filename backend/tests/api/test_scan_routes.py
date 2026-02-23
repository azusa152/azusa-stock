"""Tests for scan routes (GET /scan/last, GET /scan/status)."""

from datetime import datetime, timezone

from sqlmodel import Session

from tests.conftest import test_engine


class TestGetLastScan:
    """Tests for GET /scan/last — including market_status field."""

    def test_scan_last_should_return_nulls_when_no_scans(self, client):
        # Act
        resp = client.get("/scan/last")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["last_scanned_at"] is None
        assert data["epoch"] is None
        assert data["market_status"] is None
        assert data["market_status_details"] is None

    def test_scan_last_should_include_market_status_after_scan(self, client):
        # Arrange — create a stock, then insert a ScanLog directly
        client.post(
            "/ticker",
            json={
                "ticker": "AAPL",
                "category": "Trend_Setter",
                "thesis": "Big tech leader",
            },
        )

        from domain.entities import ScanLog

        scan_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        scan_log = ScanLog(
            stock_ticker="AAPL",
            signal="NORMAL",
            market_status="BULLISH",
            market_status_details="風向球整體穩健（0/4 跌破 60MA）",
            details="",
            scanned_at=scan_time,
        )
        with Session(test_engine) as session:
            session.add(scan_log)
            session.commit()

        # Act
        resp = client.get("/scan/last")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["last_scanned_at"] is not None
        assert data["market_status"] == "BULLISH"
        assert data["market_status_details"] == "風向球整體穩健（0/4 跌破 60MA）"
        assert data["epoch"] is not None

    def test_scan_last_should_return_latest_scan_market_status(self, client):
        # Arrange — create stock and two scan logs with different market_status
        client.post(
            "/ticker",
            json={
                "ticker": "MSFT",
                "category": "Trend_Setter",
                "thesis": "Cloud leader",
            },
        )

        from domain.entities import ScanLog

        older_scan = ScanLog(
            stock_ticker="MSFT",
            signal="NORMAL",
            market_status="BULLISH",
            market_status_details="風向球整體穩健（0/4 跌破 60MA）",
            details="",
            scanned_at=datetime(2025, 6, 14, 10, 0, 0, tzinfo=timezone.utc),
        )
        newer_scan = ScanLog(
            stock_ticker="MSFT",
            signal="THESIS_BROKEN",
            market_status="BEARISH",
            market_status_details="風向球偏空（3/4 跌破 60MA）",
            details="",
            scanned_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        with Session(test_engine) as session:
            session.add(older_scan)
            session.add(newer_scan)
            session.commit()

        # Act
        resp = client.get("/scan/last")

        # Assert — should return the newest scan's market_status and details
        assert resp.status_code == 200
        data = resp.json()
        assert data["market_status"] == "BEARISH"
        assert data["market_status_details"] == "風向球偏空（3/4 跌破 60MA）"


class TestGetScanStatus:
    """Tests for GET /scan/status — returns whether a scan is running."""

    def test_scan_status_should_return_not_running_by_default(self, client):
        # Act
        resp = client.get("/scan/status")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_running"] is False

    def test_scan_status_should_return_running_when_lock_is_held(self, client):
        from api.scan_routes import _scan_lock

        # Arrange — acquire the lock to simulate an in-progress scan
        _scan_lock.acquire()
        try:
            # Act
            resp = client.get("/scan/status")

            # Assert
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_running"] is True
        finally:
            _scan_lock.release()
