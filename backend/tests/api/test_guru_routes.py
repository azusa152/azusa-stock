"""
Tests for Smart Money API routes (guru_routes.py + resonance_router).

Covers the key areas called out in the Phase 5 review:
  - 404 responses when guru / filing not found
  - _sync_lock mutex returning 429 on concurrent calls
  - GuruCreate validation (min/max field lengths)
  - get_top_holdings n clamping (up to 50, not capped at GURU_TOP_HOLDINGS_COUNT)
  - Webhook dispatch for guru_sync and guru_summary actions
"""

from unittest.mock import patch

from sqlmodel import Session

from domain.entities import Guru, GuruFiling, GuruHolding
from infrastructure.repositories import save_filing, save_guru, save_holdings_batch
from tests.conftest import test_engine

SYNC_ALL_TARGET = "api.routes.guru_routes.sync_all_gurus"
SYNC_ONE_TARGET = "api.routes.guru_routes.sync_guru_filing"
SEND_DIGEST_TARGET = "api.routes.guru_routes.send_filing_season_digest"
WEBHOOK_SYNC_TARGET = "application.messaging.webhook_service.sync_all_gurus"
WEBHOOK_DIGEST_TARGET = (
    "application.messaging.webhook_service.send_filing_season_digest"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guru(
    session: Session, cik: str = "0001067983", display_name: str = "Buffett"
) -> Guru:
    return save_guru(
        session,
        Guru(name="Berkshire Hathaway", cik=cik, display_name=display_name),
    )


def _make_filing(
    session: Session,
    guru_id: int,
    report_date: str = "2024-12-31",
) -> GuruFiling:
    return save_filing(
        session,
        GuruFiling(
            guru_id=guru_id,
            accession_number=f"ACC-{guru_id}-001",
            report_date=report_date,
            filing_date="2025-02-14",
            total_value=1_000_000.0,
            holdings_count=3,
        ),
    )


def _make_filing_with_acc(
    session: Session,
    guru_id: int,
    accession_number: str,
    report_date: str,
) -> GuruFiling:
    return save_filing(
        session,
        GuruFiling(
            guru_id=guru_id,
            accession_number=accession_number,
            report_date=report_date,
            filing_date="2024-11-14",
            total_value=900_000.0,
            holdings_count=2,
        ),
    )


def _make_holdings(session: Session, filing_id: int, guru_id: int, count: int) -> None:
    holdings = [
        GuruHolding(
            filing_id=filing_id,
            guru_id=guru_id,
            cusip=f"CUSIP{i:05d}",
            ticker=f"TICK{i}",
            company_name=f"Company {i}",
            value=float(count - i) * 10_000,
            shares=float(count - i) * 100,
            action="UNCHANGED",
            weight_pct=float(count - i) / count * 100,
        )
        for i in range(count)
    ]
    save_holdings_batch(session, holdings)


# ===========================================================================
# GET /gurus
# ===========================================================================


class TestGetGurus:
    def test_should_return_empty_list_when_no_gurus(self, client):
        resp = client.get("/gurus")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_should_return_guru_list(self, client):
        with Session(test_engine) as session:
            _make_guru(session)

        resp = client.get("/gurus")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Buffett"
        assert "id" in data[0]
        assert "cik" in data[0]
        assert "is_default" in data[0]


# ===========================================================================
# POST /gurus — GuruCreate validation
# ===========================================================================


class TestCreateGuru:
    def test_should_create_guru_with_valid_data(self, client):
        resp = client.post(
            "/gurus",
            json={
                "name": "Berkshire Hathaway",
                "cik": "0001067983",
                "display_name": "Buffett",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["display_name"] == "Buffett"
        assert body["cik"] == "0001067983"

    def test_should_reject_empty_name(self, client):
        resp = client.post(
            "/gurus",
            json={"name": "", "cik": "0001067983", "display_name": "Buffett"},
        )
        assert resp.status_code == 422

    def test_should_reject_name_too_long(self, client):
        resp = client.post(
            "/gurus",
            json={"name": "X" * 201, "cik": "0001067983", "display_name": "Buffett"},
        )
        assert resp.status_code == 422

    def test_should_reject_empty_cik(self, client):
        resp = client.post(
            "/gurus",
            json={"name": "Berkshire Hathaway", "cik": "", "display_name": "Buffett"},
        )
        assert resp.status_code == 422

    def test_should_reject_cik_too_long(self, client):
        resp = client.post(
            "/gurus",
            json={
                "name": "Berkshire Hathaway",
                "cik": "X" * 21,
                "display_name": "Buffett",
            },
        )
        assert resp.status_code == 422

    def test_should_reject_empty_display_name(self, client):
        resp = client.post(
            "/gurus",
            json={
                "name": "Berkshire Hathaway",
                "cik": "0001067983",
                "display_name": "",
            },
        )
        assert resp.status_code == 422

    def test_should_reject_display_name_too_long(self, client):
        resp = client.post(
            "/gurus",
            json={
                "name": "Berkshire Hathaway",
                "cik": "0001067983",
                "display_name": "X" * 101,
            },
        )
        assert resp.status_code == 422


# ===========================================================================
# DELETE /gurus/{guru_id}
# ===========================================================================


class TestDeleteGuru:
    def test_should_return_404_when_guru_not_found(self, client):
        resp = client.delete("/gurus/9999")
        assert resp.status_code == 404

    def test_should_deactivate_existing_guru(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session)
            guru_id = guru.id

        resp = client.delete(f"/gurus/{guru_id}")
        assert resp.status_code == 200
        assert str(guru_id) in resp.json()["message"]


# ===========================================================================
# POST /gurus/sync — mutex 429
# ===========================================================================


class TestSyncAll:
    def test_should_return_429_when_sync_lock_held(self, client):
        from api.routes.guru_routes import _sync_lock

        # Acquire the lock before the request to simulate a concurrent sync
        _sync_lock.acquire()
        try:
            resp = client.post("/gurus/sync")
            assert resp.status_code == 429
            assert "in progress" in resp.json()["detail"].lower()
        finally:
            _sync_lock.release()

    def test_should_return_sync_summary(self, client):
        mock_results = [
            {
                "status": "synced",
                "guru_id": 1,
                "new_positions": 2,
                "sold_out": 1,
                "increased": 0,
                "decreased": 0,
            },
            {"status": "skipped", "guru_id": 2},
        ]
        with patch(SYNC_ALL_TARGET, return_value=mock_results):
            resp = client.post("/gurus/sync")

        assert resp.status_code == 200
        body = resp.json()
        assert body["synced"] == 1
        assert body["skipped"] == 1
        assert body["errors"] == 0


# ===========================================================================
# POST /gurus/{guru_id}/sync
# ===========================================================================


class TestSyncOne:
    def test_should_return_404_when_guru_not_found(self, client):
        mock_result = {"status": "error", "error": "guru not found", "guru_id": 9999}
        with patch(SYNC_ONE_TARGET, return_value=mock_result):
            resp = client.post("/gurus/9999/sync")
        assert resp.status_code == 404

    def test_should_return_sync_result(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session)
            guru_id = guru.id

        mock_result = {
            "status": "synced",
            "guru_id": guru_id,
            "new_positions": 1,
            "sold_out": 0,
            "increased": 2,
            "decreased": 0,
        }
        with patch(SYNC_ONE_TARGET, return_value=mock_result):
            resp = client.post(f"/gurus/{guru_id}/sync")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "synced"
        assert body["new_positions"] == 1


# ===========================================================================
# GET /gurus/{guru_id}/filing — 404
# ===========================================================================


class TestGetFiling:
    def test_should_return_404_when_no_filing(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session)
            guru_id = guru.id

        resp = client.get(f"/gurus/{guru_id}/filing")
        assert resp.status_code == 404

    def test_should_return_filing_summary(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session)
            filing = _make_filing(session, guru.id)
            _make_holdings(session, filing.id, guru.id, count=3)
            guru_id = guru.id

        resp = client.get(f"/gurus/{guru_id}/filing")
        assert resp.status_code == 200
        body = resp.json()
        assert body["guru_id"] == guru_id
        assert body["report_date"] == "2024-12-31"
        assert body["holdings_count"] == 3
        assert body["total_value"] == 1_000_000.0
        assert "top_holdings" in body


# ===========================================================================
# GET /gurus/{guru_id}/holdings
# ===========================================================================


class TestGetHoldings:
    def test_should_return_empty_when_no_filing(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session)
            guru_id = guru.id

        resp = client.get(f"/gurus/{guru_id}/holdings")
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# GET /gurus/{guru_id}/top — n clamping
# ===========================================================================


class TestGetTopHoldings:
    def test_should_return_404_when_no_filing(self, client):
        resp = client.get("/gurus/9999/top")
        assert resp.status_code == 404

    def test_should_return_top_n_holdings(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session)
            filing = _make_filing(session, guru.id)
            _make_holdings(session, filing.id, guru.id, count=20)
            guru_id = guru.id

        resp = client.get(f"/gurus/{guru_id}/top?n=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        # Verify descending weight order
        weights = [h["weight_pct"] for h in data if h["weight_pct"] is not None]
        assert weights == sorted(weights, reverse=True)

    def test_should_support_n_beyond_default_top_count(self, client):
        """n=25 must return 25 items, not be silently capped at GURU_TOP_HOLDINGS_COUNT (10)."""
        with Session(test_engine) as session:
            guru = _make_guru(session)
            filing = _make_filing(session, guru.id)
            _make_holdings(session, filing.id, guru.id, count=30)
            guru_id = guru.id

        resp = client.get(f"/gurus/{guru_id}/top?n=25")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 25

    def test_should_reject_n_above_maximum(self, client):
        resp = client.get("/gurus/1/top?n=51")
        assert resp.status_code == 422

    def test_should_reject_n_below_minimum(self, client):
        resp = client.get("/gurus/1/top?n=0")
        assert resp.status_code == 422

    def test_should_include_filing_dates_in_response(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session)
            filing = _make_filing(session, guru.id)
            _make_holdings(session, filing.id, guru.id, count=3)
            guru_id = guru.id

        resp = client.get(f"/gurus/{guru_id}/top")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        for h in data:
            assert h["report_date"] == "2024-12-31"
            assert h["filing_date"] == "2025-02-14"


# ===========================================================================
# GET /resonance
# ===========================================================================


class TestGetResonance:
    def test_should_return_empty_when_no_gurus(self, client):
        resp = client.get("/resonance")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_gurus"] == 0
        assert body["gurus_with_overlap"] == 0
        assert body["results"] == []


# ===========================================================================
# GET /resonance/great-minds
# ===========================================================================


class TestGetGreatMinds:
    def test_should_return_empty_when_no_gurus(self, client):
        resp = client.get("/resonance/great-minds")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 0
        assert body["stocks"] == []


# ===========================================================================
# GET /resonance/{ticker}
# ===========================================================================


class TestGetResonanceTicker:
    def test_should_return_empty_when_no_gurus_hold_ticker(self, client):
        resp = client.get("/resonance/AAPL")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "AAPL"
        assert body["guru_count"] == 0
        assert body["gurus"] == []

    def test_should_uppercase_ticker(self, client):
        resp = client.get("/resonance/aapl")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"


# ===========================================================================
# Webhook dispatch — guru_sync and guru_summary
# ===========================================================================


class TestWebhookGuruSync:
    def test_guru_sync_should_dispatch_and_return_success(self, client):
        mock_results = [
            {
                "status": "synced",
                "guru_id": 1,
                "new_positions": 1,
                "sold_out": 0,
                "increased": 0,
                "decreased": 0,
            },
        ]
        with patch(WEBHOOK_SYNC_TARGET, return_value=mock_results):
            resp = client.post("/webhook", json={"action": "guru_sync"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["synced"] == 1
        assert body["data"]["total"] == 1

    def test_guru_sync_should_return_failure_on_exception(self, client):
        with patch(WEBHOOK_SYNC_TARGET, side_effect=Exception("EDGAR down")):
            resp = client.post("/webhook", json={"action": "guru_sync"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "EDGAR down" in body["message"]


class TestWebhookGuruSummary:
    def test_guru_summary_should_dispatch_and_return_success(self, client):
        mock_digest = {"status": "sent", "guru_count": 3, "message": "ok"}
        with patch(WEBHOOK_DIGEST_TARGET, return_value=mock_digest):
            resp = client.post("/webhook", json={"action": "guru_summary"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["guru_count"] == 3

    def test_guru_summary_should_return_failure_on_exception(self, client):
        with patch(
            WEBHOOK_DIGEST_TARGET, side_effect=Exception("Telegram unreachable")
        ):
            resp = client.post("/webhook", json={"action": "guru_summary"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "Telegram unreachable" in body["message"]

    def test_help_should_include_guru_actions(self, client):
        resp = client.post("/webhook", json={"action": "help"})
        assert resp.status_code == 200
        actions = resp.json()["data"]["actions"]
        assert "guru_sync" in actions
        assert "guru_summary" in actions


# ===========================================================================
# GET /gurus/dashboard
# ===========================================================================

DASHBOARD_TARGET = "api.routes.guru_routes.get_dashboard_summary"

_DASHBOARD_DATA = {
    "gurus": [
        {
            "id": 1,
            "display_name": "Warren Buffett",
            "latest_report_date": "2024-12-31",
            "latest_filing_date": "2025-02-14",
            "total_value": 267_530_000.0,
            "holdings_count": 45,
            "filing_count": 18,
        }
    ],
    "season_highlights": {
        "new_positions": [
            {
                "ticker": "NVDA",
                "company_name": "NVIDIA Corp",
                "guru_id": 1,
                "guru_display_name": "Warren Buffett",
                "value": 5_000_000.0,
                "weight_pct": 1.8,
                "change_pct": None,
            }
        ],
        "sold_outs": [
            {
                "ticker": "PARA",
                "company_name": "Paramount Global",
                "guru_id": 1,
                "guru_display_name": "Warren Buffett",
                "value": 0.0,
                "weight_pct": 0.0,
                "change_pct": -100.0,
            }
        ],
    },
    "consensus": [
        {
            "ticker": "AAPL",
            "guru_count": 2,
            "gurus": ["Warren Buffett", "Ray Dalio"],
            "total_value": 200_000_000.0,
        }
    ],
    "sector_breakdown": [
        {
            "sector": "Technology",
            "total_value": 500_000_000.0,
            "holding_count": 10,
            "weight_pct": 45.0,
        }
    ],
}


class TestGetDashboard:
    def test_should_return_200_with_correct_shape(self, client):
        with patch(DASHBOARD_TARGET, return_value=_DASHBOARD_DATA):
            resp = client.get("/gurus/dashboard")

        assert resp.status_code == 200
        body = resp.json()
        assert "gurus" in body
        assert "season_highlights" in body
        assert "consensus" in body
        assert "sector_breakdown" in body

    def test_should_map_guru_summary_fields(self, client):
        with patch(DASHBOARD_TARGET, return_value=_DASHBOARD_DATA):
            resp = client.get("/gurus/dashboard")

        guru = resp.json()["gurus"][0]
        assert guru["id"] == 1
        assert guru["display_name"] == "Warren Buffett"
        assert guru["latest_report_date"] == "2024-12-31"
        assert guru["filing_count"] == 18

    def test_should_map_season_highlights(self, client):
        with patch(DASHBOARD_TARGET, return_value=_DASHBOARD_DATA):
            resp = client.get("/gurus/dashboard")

        highlights = resp.json()["season_highlights"]
        assert len(highlights["new_positions"]) == 1
        assert highlights["new_positions"][0]["ticker"] == "NVDA"
        assert len(highlights["sold_outs"]) == 1
        assert highlights["sold_outs"][0]["ticker"] == "PARA"

    def test_should_map_consensus_stocks(self, client):
        with patch(DASHBOARD_TARGET, return_value=_DASHBOARD_DATA):
            resp = client.get("/gurus/dashboard")

        consensus = resp.json()["consensus"]
        assert len(consensus) == 1
        assert consensus[0]["ticker"] == "AAPL"
        assert consensus[0]["guru_count"] == 2

    def test_should_map_sector_breakdown(self, client):
        with patch(DASHBOARD_TARGET, return_value=_DASHBOARD_DATA):
            resp = client.get("/gurus/dashboard")

        breakdown = resp.json()["sector_breakdown"]
        assert len(breakdown) == 1
        assert breakdown[0]["sector"] == "Technology"
        assert breakdown[0]["weight_pct"] == 45.0

    def test_should_return_empty_collections_when_no_data(self, client):
        empty_data = {
            "gurus": [],
            "season_highlights": {"new_positions": [], "sold_outs": []},
            "consensus": [],
            "sector_breakdown": [],
        }
        with patch(DASHBOARD_TARGET, return_value=empty_data):
            resp = client.get("/gurus/dashboard")

        assert resp.status_code == 200
        body = resp.json()
        assert body["gurus"] == []
        assert body["consensus"] == []
        assert body["sector_breakdown"] == []
        assert body["season_highlights"]["new_positions"] == []
        assert body["season_highlights"]["sold_outs"] == []


# ===========================================================================
# GET /gurus/{guru_id}/filings
# ===========================================================================


class TestGetFilingHistory:
    def test_should_return_filings_list(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session, cik="0009000001")
            guru_id = guru.id
            _make_filing(session, guru_id, report_date="2024-12-31")
            _make_filing_with_acc(session, guru_id, "ACC-Q3", "2024-09-30")

        resp = client.get(f"/gurus/{guru_id}/filings")
        assert resp.status_code == 200
        body = resp.json()
        assert "filings" in body
        assert len(body["filings"]) == 2
        # Should be descending by report_date
        assert body["filings"][0]["report_date"] >= body["filings"][1]["report_date"]

    def test_should_return_empty_list_when_no_filings(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session, cik="0009000002")
            guru_id = guru.id

        resp = client.get(f"/gurus/{guru_id}/filings")
        assert resp.status_code == 200
        assert resp.json()["filings"] == []

    def test_should_include_required_fields(self, client):
        with Session(test_engine) as session:
            guru = _make_guru(session, cik="0009000003")
            guru_id = guru.id
            _make_filing(session, guru_id)

        resp = client.get(f"/gurus/{guru_id}/filings")
        filing = resp.json()["filings"][0]
        assert "id" in filing
        assert "report_date" in filing
        assert "filing_date" in filing
        assert "total_value" in filing
        assert "holdings_count" in filing
