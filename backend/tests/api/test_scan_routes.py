"""Tests for scan routes (GET /scan/last, GET /scan/status)."""

from datetime import UTC, datetime

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

        scan_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)
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
            scanned_at=datetime(2025, 6, 14, 10, 0, 0, tzinfo=UTC),
        )
        newer_scan = ScanLog(
            stock_ticker="MSFT",
            signal="THESIS_BROKEN",
            market_status="BEARISH",
            market_status_details="風向球偏空（3/4 跌破 60MA）",
            details="",
            scanned_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
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


class TestGetSignalActivity:
    """Tests for GET /signals/activity — returns signal activity for non-NORMAL stocks."""

    def test_signal_activity_should_return_empty_when_no_stocks(self, client):
        # Act
        resp = client.get("/signals/activity")

        # Assert
        assert resp.status_code == 200
        assert resp.json() == []

    def test_signal_activity_should_return_only_non_normal_stocks(self, client):
        # Arrange — create two stocks: one NORMAL, one OVERSOLD
        client.post(
            "/ticker",
            json={
                "ticker": "AAPL",
                "category": "Trend_Setter",
                "thesis": "Normal stock",
            },
        )
        client.post(
            "/ticker",
            json={"ticker": "TSLA", "category": "Growth", "thesis": "Oversold stock"},
        )

        from domain.entities import Stock

        with Session(test_engine) as session:
            tsla = session.get(Stock, "TSLA")
            assert tsla is not None
            tsla.last_scan_signal = "OVERSOLD"
            tsla.signal_since = datetime(2025, 6, 10, 8, 0, 0, tzinfo=UTC)
            session.commit()

        # Act
        resp = client.get("/signals/activity")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["ticker"] == "TSLA"
        assert item["signal"] == "OVERSOLD"
        assert item["signal_since"] is not None
        assert item["duration_days"] is not None
        assert item["consecutive_scans"] >= 1
        assert isinstance(item["is_new"], bool)

    def test_signal_activity_response_schema_has_required_fields(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "Overheated"},
        )

        from domain.entities import Stock

        with Session(test_engine) as session:
            nvda = session.get(Stock, "NVDA")
            assert nvda is not None
            nvda.last_scan_signal = "OVERHEATED"
            session.commit()

        # Act
        resp = client.get("/signals/activity")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert any(item["ticker"] == "NVDA" for item in data)
        for item in data:
            assert "ticker" in item
            assert "signal" in item
            assert "consecutive_scans" in item
            assert "is_new" in item


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
        from api.routes.scan_routes import _scan_lock

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
