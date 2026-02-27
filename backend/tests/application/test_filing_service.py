"""
Tests for filing_service and guru_service (Phase 3 application layer).
All EDGAR network calls are mocked — no I/O in this test suite.
"""

from datetime import date
from unittest.mock import patch

import pytest
from sqlmodel import Session

from domain.constants import DEFAULT_GURUS, GURU_TOP_HOLDINGS_COUNT
from domain.entities import Guru, GuruFiling, GuruHolding
from domain.enums import HoldingAction
from infrastructure.repositories import (
    find_all_active_gurus,
    find_filing_by_accession,
    find_holdings_by_filing,
    find_latest_filing_by_guru,
    save_filing,
    save_guru,
    save_holdings_batch,
)

GURU_MODULE = "application.guru.guru_service"
FILING_MODULE = "application.stock.filing_service"

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_SAMPLE_EDGAR_FILINGS = [
    {
        "accession_number": "0001067983-25-000006",
        "accession_path": "000106798325000006",
        "filing_date": "2025-02-14",
        "report_date": "2024-12-31",
        "primary_doc": "0001067983-25-000006-index.htm",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/1067983/000106798325000006/0001067983-25-000006-index.htm",
    },
    {
        "accession_number": "0001067983-24-000006",
        "accession_path": "000106798324000006",
        "filing_date": "2024-08-14",
        "report_date": "2024-06-30",
        "primary_doc": "0001067983-24-000006-index.htm",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/1067983/000106798324000006/0001067983-24-000006-index.htm",
    },
]

_SAMPLE_RAW_HOLDINGS = [
    {
        "cusip": "037833100",
        "company_name": "APPLE INC",
        "value": 174530.0,
        "shares": 905560000.0,
    },
    {
        "cusip": "025816109",
        "company_name": "AMERICAN EXPRESS CO",
        "value": 41100.0,
        "shares": 151610700.0,
    },
    {
        "cusip": "808513105",
        "company_name": "BANK OF AMERICA CORP",
        "value": 37200.0,
        "shares": 1032852006.0,
    },
]


def _make_guru(session: Session, cik: str = "0001067983") -> Guru:
    return save_guru(
        session,
        Guru(name="Berkshire Hathaway Inc", cik=cik, display_name="Warren Buffett"),
    )


# ===========================================================================
# guru_service tests
# ===========================================================================


class TestSeedDefaultGurus:
    """Tests for seed_default_gurus()."""

    def test_seed_default_gurus_should_insert_all_defaults(self, db_session: Session):
        from application.guru.guru_service import seed_default_gurus

        count = seed_default_gurus(db_session)

        assert count == len(DEFAULT_GURUS)
        active = find_all_active_gurus(db_session)
        assert len(active) == len(DEFAULT_GURUS)

    def test_seed_default_gurus_should_be_idempotent(self, db_session: Session):
        from application.guru.guru_service import seed_default_gurus

        seed_default_gurus(db_session)
        count_second = seed_default_gurus(db_session)

        assert count_second == 0
        active = find_all_active_gurus(db_session)
        assert len(active) == len(DEFAULT_GURUS)

    def test_seed_default_gurus_should_mark_as_is_default(self, db_session: Session):
        from application.guru.guru_service import seed_default_gurus

        seed_default_gurus(db_session)
        active = find_all_active_gurus(db_session)

        assert all(g.is_default for g in active)

    def test_seed_default_gurus_should_set_style_and_tier(self, db_session: Session):
        from application.guru.guru_service import seed_default_gurus
        from domain.core.constants import DEFAULT_GURUS

        seed_default_gurus(db_session)
        active = find_all_active_gurus(db_session)

        assert len(active) == len(DEFAULT_GURUS)
        assert all(g.style is not None for g in active)
        assert all(g.tier is not None for g in active)

    def test_seed_default_gurus_should_backfill_style_tier_on_second_call(
        self, db_session: Session
    ):
        from application.guru.guru_service import seed_default_gurus
        from infrastructure.repositories import find_guru_by_cik, update_guru

        seed_default_gurus(db_session)

        # Wipe style/tier for one guru to simulate pre-existing data
        buffett = find_guru_by_cik(db_session, "0001067983")
        assert buffett is not None
        buffett.style = None
        buffett.tier = None
        update_guru(db_session, buffett)

        # Second seed should backfill
        seed_default_gurus(db_session)

        refreshed = find_guru_by_cik(db_session, "0001067983")
        assert refreshed is not None
        assert refreshed.style == "VALUE"
        assert refreshed.tier == "TIER_1"


class TestListGurus:
    """Tests for list_gurus()."""

    def test_list_gurus_should_return_active_only(self, db_session: Session):
        from application.guru.guru_service import (
            list_gurus,
            remove_guru,
            seed_default_gurus,
        )

        seed_default_gurus(db_session)
        all_active = find_all_active_gurus(db_session)
        first_id = all_active[0].id

        remove_guru(db_session, first_id)

        result = list_gurus(db_session)
        assert len(result) == len(DEFAULT_GURUS) - 1
        assert all(g.is_active for g in result)

    def test_list_gurus_should_return_empty_when_none(self, db_session: Session):
        from application.guru.guru_service import list_gurus

        result = list_gurus(db_session)
        assert result == []


class TestAddGuru:
    """Tests for add_guru()."""

    def test_add_guru_should_persist_and_return(self, db_session: Session):
        from application.guru.guru_service import add_guru

        guru = add_guru(
            db_session, name="Test Corp", cik="0000000099", display_name="Test"
        )

        assert guru.id is not None
        assert guru.cik == "0000000099"
        assert guru.display_name == "Test"
        assert guru.is_active is True
        assert guru.is_default is False

    def test_add_guru_should_reactivate_deactivated_guru(self, db_session: Session):
        from application.guru.guru_service import add_guru, remove_guru

        original = add_guru(
            db_session, name="Corp", cik="0000000098", display_name="Old"
        )
        remove_guru(db_session, original.id)

        reactivated = add_guru(
            db_session, name="Corp Updated", cik="0000000098", display_name="New"
        )

        assert reactivated.id == original.id
        assert reactivated.is_active is True
        assert reactivated.display_name == "New"

    def test_add_guru_should_not_create_duplicate_cik(self, db_session: Session):
        from application.guru.guru_service import add_guru

        add_guru(db_session, name="Corp A", cik="0000000097", display_name="A")
        add_guru(db_session, name="Corp A v2", cik="0000000097", display_name="A v2")

        active = find_all_active_gurus(db_session)
        cik_97 = [g for g in active if g.cik == "0000000097"]
        assert len(cik_97) == 1
        assert cik_97[0].display_name == "A v2"


class TestRemoveGuru:
    """Tests for remove_guru()."""

    def test_remove_guru_should_return_true_and_deactivate(self, db_session: Session):
        from application.guru.guru_service import add_guru, remove_guru

        guru = add_guru(db_session, name="Corp", cik="0000000096", display_name="Mgr")
        result = remove_guru(db_session, guru.id)

        assert result is True
        active = find_all_active_gurus(db_session)
        assert not any(g.id == guru.id for g in active)

    def test_remove_guru_should_return_false_when_not_found(self, db_session: Session):
        from application.guru.guru_service import remove_guru

        result = remove_guru(db_session, 9999)

        assert result is False


# ===========================================================================
# filing_service — sync_guru_filing tests (mocked EDGAR)
# ===========================================================================


class TestSyncGuruFiling:
    """Tests for sync_guru_filing() with mocked EDGAR calls."""

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_sync_should_return_synced_status(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session)
        result = sync_guru_filing(db_session, guru.id)

        assert result["status"] == "synced"
        assert result["guru_id"] == guru.id
        assert result["guru_display_name"] == "Warren Buffett"
        assert (
            result["accession_number"] == _SAMPLE_EDGAR_FILINGS[0]["accession_number"]
        )
        assert result["report_date"] == "2024-12-31"
        assert result["holdings_count"] == len(_SAMPLE_RAW_HOLDINGS)

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_sync_should_persist_filing_to_db(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session)
        sync_guru_filing(db_session, guru.id)

        filing = find_filing_by_accession(
            db_session, _SAMPLE_EDGAR_FILINGS[0]["accession_number"]
        )
        assert filing is not None
        assert filing.guru_id == guru.id
        assert filing.total_value == sum(h["value"] for h in _SAMPLE_RAW_HOLDINGS)

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_sync_should_persist_holdings_to_db(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session)
        sync_guru_filing(db_session, guru.id)

        filing = find_filing_by_accession(
            db_session, _SAMPLE_EDGAR_FILINGS[0]["accession_number"]
        )
        assert filing is not None
        holdings = find_holdings_by_filing(db_session, filing.id)
        assert len(holdings) == len(_SAMPLE_RAW_HOLDINGS)

    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_sync_should_return_skipped_when_already_synced(
        self, _mock_cusip, _mock_get, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session)
        # Pre-insert the filing to simulate already synced
        save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number=_SAMPLE_EDGAR_FILINGS[0]["accession_number"],
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )

        result = sync_guru_filing(db_session, guru.id)

        assert result["status"] == "skipped"

    @patch(f"{FILING_MODULE}.get_latest_13f_filings", return_value=[])
    def test_sync_should_return_error_when_no_edgar_filings(
        self, _mock_get, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session)
        result = sync_guru_filing(db_session, guru.id)

        assert result["status"] == "error"
        assert "no 13F filings" in result["error"]

    def test_sync_should_return_error_when_guru_not_found(self, db_session: Session):
        from application.stock.filing_service import sync_guru_filing

        result = sync_guru_filing(db_session, 9999)

        assert result["status"] == "error"
        assert "guru not found" in result["error"]

    @patch(f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=[])
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_sync_should_return_error_when_infotable_empty(
        self, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session)
        result = sync_guru_filing(db_session, guru.id)

        assert result["status"] == "error"
        assert "failed to fetch or parse" in result["error"]

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_sync_should_be_idempotent(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session)
        result1 = sync_guru_filing(db_session, guru.id)
        result2 = sync_guru_filing(db_session, guru.id)

        assert result1["status"] == "synced"
        assert result2["status"] == "skipped"


# ===========================================================================
# filing_service — diff logic (classify_holding_change integration)
# ===========================================================================


class TestSyncHoldingDiff:
    """Tests for quarter-over-quarter holding diff logic."""

    def _setup_previous_holding(
        self, session: Session, guru: Guru, cusip: str, shares: float
    ):
        """Pre-populate a previous quarter's filing + holding in the DB."""
        prev_filing = save_filing(
            session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="PREV-ACC-001",
                report_date="2024-09-30",
                filing_date="2024-11-14",
            ),
        )
        save_holdings_batch(
            session,
            [
                GuruHolding(
                    filing_id=prev_filing.id,
                    guru_id=guru.id,
                    cusip=cusip,
                    company_name="Test Co",
                    value=100.0,
                    shares=shares,
                )
            ],
        )
        return prev_filing

    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_new_position_should_be_classified_when_no_previous(
        self, _mock_get, _mock_cusip, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        new_holdings = [
            {
                "cusip": "NEWCUSIP1",
                "company_name": "New Co",
                "value": 50.0,
                "shares": 1000.0,
            }
        ]
        with patch(
            f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=new_holdings
        ):
            guru = _make_guru(db_session, cik="0001111111")
            sync_guru_filing(db_session, guru.id)

        filing = find_filing_by_accession(
            db_session, _SAMPLE_EDGAR_FILINGS[0]["accession_number"]
        )
        assert filing is not None
        holdings = find_holdings_by_filing(db_session, filing.id)
        assert len(holdings) == 1
        assert holdings[0].action == HoldingAction.NEW_POSITION.value
        assert holdings[0].change_pct is None

    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_sold_out_should_be_classified_when_current_shares_zero(
        self, _mock_get, _mock_cusip, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session, cik="0001111112")
        self._setup_previous_holding(db_session, guru, cusip="OLDCUSIP1", shares=1000.0)

        # Current filing has that CUSIP with 0 shares
        sold_holdings = [
            {
                "cusip": "OLDCUSIP1",
                "company_name": "Old Co",
                "value": 0.0,
                "shares": 0.0,
            }
        ]
        with patch(
            f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=sold_holdings
        ):
            sync_guru_filing(db_session, guru.id)

        latest = find_latest_filing_by_guru(db_session, guru.id)
        assert latest is not None
        holdings = find_holdings_by_filing(db_session, latest.id)
        assert holdings[0].action == HoldingAction.SOLD_OUT.value

    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_increased_should_be_classified_when_shares_up_by_threshold(
        self, _mock_get, _mock_cusip, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session, cik="0001111113")
        self._setup_previous_holding(db_session, guru, cusip="INCR001", shares=1000.0)

        # +50% increase
        incr_holdings = [
            {
                "cusip": "INCR001",
                "company_name": "Inc Co",
                "value": 150.0,
                "shares": 1500.0,
            }
        ]
        with patch(
            f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=incr_holdings
        ):
            sync_guru_filing(db_session, guru.id)

        latest = find_latest_filing_by_guru(db_session, guru.id)
        assert latest is not None
        holdings = find_holdings_by_filing(db_session, latest.id)
        assert holdings[0].action == HoldingAction.INCREASED.value
        assert holdings[0].change_pct == pytest.approx(50.0)

    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_decreased_should_be_classified_when_shares_down_by_threshold(
        self, _mock_get, _mock_cusip, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session, cik="0001111114")
        self._setup_previous_holding(db_session, guru, cusip="DECR001", shares=1000.0)

        # -50% decrease
        decr_holdings = [
            {
                "cusip": "DECR001",
                "company_name": "Dec Co",
                "value": 50.0,
                "shares": 500.0,
            }
        ]
        with patch(
            f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=decr_holdings
        ):
            sync_guru_filing(db_session, guru.id)

        latest = find_latest_filing_by_guru(db_session, guru.id)
        assert latest is not None
        holdings = find_holdings_by_filing(db_session, latest.id)
        assert holdings[0].action == HoldingAction.DECREASED.value
        assert holdings[0].change_pct == pytest.approx(-50.0)

    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_sold_out_should_be_created_when_cusip_absent_from_current_filing(
        self, _mock_get, _mock_cusip, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session, cik="0001111116")
        self._setup_previous_holding(db_session, guru, cusip="GONE001", shares=5000.0)

        # Current filing doesn't contain GONE001 at all
        current_holdings = [
            {
                "cusip": "NEWCUSIP2",
                "company_name": "Other Co",
                "value": 100.0,
                "shares": 1000.0,
            }
        ]
        with patch(
            f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=current_holdings
        ):
            result = sync_guru_filing(db_session, guru.id)

        assert result["sold_out"] == 1

        latest = find_latest_filing_by_guru(db_session, guru.id)
        assert latest is not None
        holdings = find_holdings_by_filing(db_session, latest.id)
        sold = [h for h in holdings if h.action == HoldingAction.SOLD_OUT.value]
        assert len(sold) == 1
        assert sold[0].cusip == "GONE001"
        assert sold[0].shares == 0.0
        assert sold[0].change_pct == pytest.approx(-100.0)

    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_unchanged_should_be_classified_when_change_below_threshold(
        self, _mock_get, _mock_cusip, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session, cik="0001111115")
        self._setup_previous_holding(db_session, guru, cusip="SAME001", shares=1000.0)

        # +5% — below 20% threshold
        same_holdings = [
            {
                "cusip": "SAME001",
                "company_name": "Same Co",
                "value": 105.0,
                "shares": 1050.0,
            }
        ]
        with patch(
            f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=same_holdings
        ):
            sync_guru_filing(db_session, guru.id)

        latest = find_latest_filing_by_guru(db_session, guru.id)
        assert latest is not None
        holdings = find_holdings_by_filing(db_session, latest.id)
        assert holdings[0].action == HoldingAction.UNCHANGED.value


# ===========================================================================
# filing_service — weight_pct and top_holdings tests
# ===========================================================================


class TestSyncWeightAndTopHoldings:
    """Tests for weight_pct computation and top_holdings in summary."""

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_weight_pct_should_sum_to_100(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        guru = _make_guru(db_session, cik="0001222221")
        sync_guru_filing(db_session, guru.id)

        filing = find_filing_by_accession(
            db_session, _SAMPLE_EDGAR_FILINGS[0]["accession_number"]
        )
        assert filing is not None
        holdings = find_holdings_by_filing(db_session, filing.id)
        total_weight = sum(h.weight_pct or 0 for h in holdings)
        assert abs(total_weight - 100.0) < 0.1

    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_top_holdings_should_be_limited_to_top_n(
        self, _mock_get, _mock_cusip, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        # Generate more holdings than GURU_TOP_HOLDINGS_COUNT
        many_holdings = [
            {
                "cusip": f"CUSIPAAA{i:02d}",
                "company_name": f"Co {i}",
                "value": float(100 - i),
                "shares": float(1000 - i * 10),
            }
            for i in range(GURU_TOP_HOLDINGS_COUNT + 5)
        ]
        with patch(
            f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=many_holdings
        ):
            guru = _make_guru(db_session, cik="0001222222")
            result = sync_guru_filing(db_session, guru.id)

        assert len(result["top_holdings"]) == GURU_TOP_HOLDINGS_COUNT

    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    def test_top_holdings_should_be_ordered_by_weight_desc(
        self, _mock_get, _mock_cusip, db_session: Session
    ):
        from application.stock.filing_service import sync_guru_filing

        many_holdings = [
            {
                "cusip": f"CUSIPAAB{i:02d}",
                "company_name": f"Co {i}",
                "value": float(i + 1),
                "shares": float((i + 1) * 10),
            }
            for i in range(5)
        ]
        with patch(
            f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=many_holdings
        ):
            guru = _make_guru(db_session, cik="0001222223")
            result = sync_guru_filing(db_session, guru.id)

        weights = [
            h["weight_pct"]
            for h in result["top_holdings"]
            if h["weight_pct"] is not None
        ]
        assert weights == sorted(weights, reverse=True)


# ===========================================================================
# filing_service — sync_all_gurus tests
# ===========================================================================


class TestSyncAllGurus:
    """Tests for sync_all_gurus()."""

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings", return_value=_SAMPLE_EDGAR_FILINGS
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_sync_all_should_return_result_for_each_active_guru(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import sync_all_gurus

        save_guru(db_session, Guru(name="G1", cik="0002000001", display_name="G1"))
        save_guru(db_session, Guru(name="G2", cik="0002000002", display_name="G2"))

        results = sync_all_gurus(db_session)

        assert len(results) == 2

    @patch(f"{FILING_MODULE}.get_latest_13f_filings", return_value=[])
    def test_sync_all_should_handle_individual_errors_without_crashing(
        self, _mock_get, db_session: Session
    ):
        from application.stock.filing_service import sync_all_gurus

        save_guru(db_session, Guru(name="G1", cik="0002000003", display_name="G1"))

        results = sync_all_gurus(db_session)

        assert len(results) == 1
        assert results[0]["status"] == "error"

    def test_sync_all_should_return_empty_when_no_active_gurus(
        self, db_session: Session
    ):
        from application.stock.filing_service import sync_all_gurus

        results = sync_all_gurus(db_session)

        assert results == []


# ===========================================================================
# filing_service — get_filing_summary and get_holding_changes
# ===========================================================================


class TestGetFilingSummaryAndChanges:
    """Tests for get_filing_summary() and get_holding_changes()."""

    def _seed_guru_and_holding(
        self, session: Session, action: str, cik: str = "0003000001"
    ):
        guru = save_guru(
            session,
            Guru(name="Corp", cik=cik, display_name="Manager"),
        )
        filing = save_filing(
            session,
            GuruFiling(
                guru_id=guru.id,
                accession_number=f"ACC-{cik}",
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )
        save_holdings_batch(
            session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="TEST001",
                    company_name="Test Co",
                    value=100.0,
                    shares=1000.0,
                    action=action,
                    weight_pct=100.0,
                )
            ],
        )
        return guru, filing

    def test_get_filing_summary_should_return_none_when_guru_not_found(
        self, db_session: Session
    ):
        from application.stock.filing_service import get_filing_summary

        result = get_filing_summary(db_session, 9999)
        assert result is None

    def test_get_filing_summary_should_return_none_when_no_filing(
        self, db_session: Session
    ):
        from application.stock.filing_service import get_filing_summary

        guru = save_guru(
            db_session, Guru(name="Corp", cik="0003000099", display_name="Mgr")
        )
        result = get_filing_summary(db_session, guru.id)
        assert result is None

    def test_get_filing_summary_should_include_action_counts(self, db_session: Session):
        from application.stock.filing_service import get_filing_summary

        guru, _ = self._seed_guru_and_holding(
            db_session, HoldingAction.NEW_POSITION.value
        )
        result = get_filing_summary(db_session, guru.id)

        assert result is not None
        assert result["new_positions"] == 1
        assert result["sold_out"] == 0
        assert result["holdings_count"] == 1

    def test_get_holding_changes_should_exclude_unchanged(self, db_session: Session):
        from application.stock.filing_service import get_holding_changes

        guru = save_guru(
            db_session, Guru(name="Corp", cik="0003000002", display_name="Mgr")
        )
        filing = save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="ACC-CHANGE",
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )
        save_holdings_batch(
            db_session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="UNC001",
                    company_name="Unchanged Co",
                    value=100.0,
                    shares=1000.0,
                    action=HoldingAction.UNCHANGED.value,
                ),
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="NEW001",
                    company_name="New Co",
                    value=200.0,
                    shares=2000.0,
                    action=HoldingAction.NEW_POSITION.value,
                ),
            ],
        )

        changes = get_holding_changes(db_session, guru.id)

        assert len(changes) == 1
        assert changes[0]["cusip"] == "NEW001"
        assert changes[0]["action"] == HoldingAction.NEW_POSITION.value

    def test_get_holding_changes_should_include_filing_metadata(
        self, db_session: Session
    ):
        from application.stock.filing_service import get_holding_changes

        guru, _ = self._seed_guru_and_holding(
            db_session, HoldingAction.NEW_POSITION.value, cik="0003000004"
        )
        changes = get_holding_changes(db_session, guru.id)

        assert len(changes) == 1
        assert changes[0]["report_date"] == "2024-12-31"
        assert changes[0]["filing_date"] == "2025-02-14"
        assert changes[0]["guru_id"] == guru.id

    def test_get_holding_changes_should_return_empty_when_no_filing(
        self, db_session: Session
    ):
        from application.stock.filing_service import get_holding_changes

        guru = save_guru(
            db_session, Guru(name="Corp", cik="0003000003", display_name="Mgr")
        )
        changes = get_holding_changes(db_session, guru.id)
        assert changes == []


# ===========================================================================
# filing_service — backfill_guru_filings tests
# ===========================================================================

# Fixed reference date used for all backfill window tests.
# All three sample report_dates (2024-06-30, 2024-09-30, 2024-12-31) fall within
# a 5-year window anchored to this date, so tests won't silently break as the
# real wall clock advances past 2029.
_BACKFILL_TODAY = date(2026, 2, 18)

# Multiple EDGAR filings spanning different quarters (sorted newest-first as EDGAR returns)
_BACKFILL_EDGAR_FILINGS = [
    {
        "accession_number": "0001067983-25-000006",
        "accession_path": "000106798325000006",
        "filing_date": "2025-02-14",
        "report_date": "2024-12-31",
        "primary_doc": "0001067983-25-000006-index.htm",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/1067983/000106798325000006/0001067983-25-000006-index.htm",
    },
    {
        "accession_number": "0001067983-24-000099",
        "accession_path": "000106798324000099",
        "filing_date": "2024-11-14",
        "report_date": "2024-09-30",
        "primary_doc": "0001067983-24-000099-index.htm",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/1067983/000106798324000099/0001067983-24-000099-index.htm",
    },
    {
        "accession_number": "0001067983-24-000006",
        "accession_path": "000106798324000006",
        "filing_date": "2024-08-14",
        "report_date": "2024-06-30",
        "primary_doc": "0001067983-24-000006-index.htm",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/1067983/000106798324000006/0001067983-24-000006-index.htm",
    },
]


class TestBackfillGuruFilings:
    """Tests for backfill_guru_filings()."""

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings",
        return_value=_BACKFILL_EDGAR_FILINGS,
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_backfill_should_sync_all_in_window_filings(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import backfill_guru_filings

        guru = _make_guru(db_session, cik="0004000001")
        result = backfill_guru_filings(
            db_session, guru.id, years=5, _today=_BACKFILL_TODAY
        )

        assert result["total_filings"] == len(_BACKFILL_EDGAR_FILINGS)
        assert result["synced"] == len(_BACKFILL_EDGAR_FILINGS)
        assert result["skipped"] == 0
        assert result["errors"] == 0
        assert result["guru_id"] == guru.id
        assert result["guru_display_name"] == "Warren Buffett"

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings",
        return_value=_BACKFILL_EDGAR_FILINGS,
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_backfill_should_be_idempotent(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import backfill_guru_filings

        guru = _make_guru(db_session, cik="0004000002")
        result1 = backfill_guru_filings(
            db_session, guru.id, years=5, _today=_BACKFILL_TODAY
        )
        result2 = backfill_guru_filings(
            db_session, guru.id, years=5, _today=_BACKFILL_TODAY
        )

        assert result1["synced"] == len(_BACKFILL_EDGAR_FILINGS)
        assert result2["synced"] == 0
        assert result2["skipped"] == len(_BACKFILL_EDGAR_FILINGS)

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings",
        return_value=_BACKFILL_EDGAR_FILINGS,
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_backfill_should_persist_all_filings_to_db(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import backfill_guru_filings

        guru = _make_guru(db_session, cik="0004000003")
        backfill_guru_filings(db_session, guru.id, years=5, _today=_BACKFILL_TODAY)

        for edgar in _BACKFILL_EDGAR_FILINGS:
            filing = find_filing_by_accession(db_session, edgar["accession_number"])
            assert filing is not None, (
                f"Filing {edgar['accession_number']} not found in DB"
            )

    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings",
        return_value=_BACKFILL_EDGAR_FILINGS,
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_backfill_should_filter_out_filings_outside_window(
        self, _mock_cusip, _mock_get, db_session: Session
    ):
        from application.stock.filing_service import backfill_guru_filings

        # years=0 → cutoff == _BACKFILL_TODAY; all sample report_dates are before that
        guru = _make_guru(db_session, cik="0004000004")
        result = backfill_guru_filings(
            db_session, guru.id, years=0, _today=_BACKFILL_TODAY
        )

        assert result["total_filings"] == 0
        assert result["synced"] == 0

    @patch(f"{FILING_MODULE}.get_latest_13f_filings", return_value=[])
    def test_backfill_should_return_zeros_when_no_edgar_filings(
        self, _mock_get, db_session: Session
    ):
        from application.stock.filing_service import backfill_guru_filings

        guru = _make_guru(db_session, cik="0004000005")
        result = backfill_guru_filings(db_session, guru.id)

        assert result["total_filings"] == 0
        assert result["synced"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0

    def test_backfill_should_return_error_when_guru_not_found(
        self, db_session: Session
    ):
        from application.stock.filing_service import backfill_guru_filings

        result = backfill_guru_filings(db_session, 9999)

        assert result["status"] == "error"
        assert "guru not found" in result["error"]

    @patch(
        f"{FILING_MODULE}.fetch_13f_filing_detail", return_value=_SAMPLE_RAW_HOLDINGS
    )
    @patch(
        f"{FILING_MODULE}.get_latest_13f_filings",
        return_value=_BACKFILL_EDGAR_FILINGS,
    )
    @patch(f"{FILING_MODULE}.map_cusip_to_ticker", side_effect=lambda c, n: None)
    def test_backfill_should_continue_after_single_filing_error(
        self, _mock_cusip, _mock_get, _mock_detail, db_session: Session
    ):
        from application.stock.filing_service import backfill_guru_filings

        call_count = 0

        def detail_side_effect(accession, cik):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return []  # Simulate parse failure for the 2nd filing
            return _SAMPLE_RAW_HOLDINGS

        _mock_detail.side_effect = detail_side_effect

        guru = _make_guru(db_session, cik="0004000006")
        result = backfill_guru_filings(
            db_session, guru.id, years=5, _today=_BACKFILL_TODAY
        )

        # 3 filings: 1st synced, 2nd error (empty holdings = error), 3rd synced
        assert result["synced"] == 2
        assert result["errors"] == 1
        assert result["total_filings"] == 3


# ===========================================================================
# filing_service — get_top_holdings tests
# ===========================================================================


class TestGetTopHoldings:
    """Tests for get_top_holdings()."""

    def _seed_filing_with_holdings(
        self, session: Session, cik: str, holdings_data: list[dict]
    ):
        guru = save_guru(session, Guru(name="Corp", cik=cik, display_name="Mgr"))
        filing = save_filing(
            session,
            GuruFiling(
                guru_id=guru.id,
                accession_number=f"ACC-TOP-{cik}",
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )
        save_holdings_batch(
            session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip=f"CUSIP{i:03d}",
                    company_name=h["company_name"],
                    value=h["value"],
                    shares=h["shares"],
                    weight_pct=h["weight_pct"],
                )
                for i, h in enumerate(holdings_data)
            ],
        )
        return guru

    def test_returns_empty_list_when_no_filing(self, db_session: Session) -> None:
        from application.stock.filing_service import get_top_holdings

        guru = save_guru(
            db_session, Guru(name="Corp", cik="0005000001", display_name="Mgr")
        )
        result = get_top_holdings(db_session, guru.id)
        assert result == []

    def test_returns_holdings_sorted_by_weight_desc(self, db_session: Session) -> None:
        from application.stock.filing_service import get_top_holdings

        holdings_data = [
            {
                "company_name": "Low Co",
                "value": 10.0,
                "shares": 100.0,
                "weight_pct": 10.0,
            },
            {
                "company_name": "High Co",
                "value": 70.0,
                "shares": 700.0,
                "weight_pct": 70.0,
            },
            {
                "company_name": "Mid Co",
                "value": 20.0,
                "shares": 200.0,
                "weight_pct": 20.0,
            },
        ]
        guru = self._seed_filing_with_holdings(db_session, "0005000002", holdings_data)

        result = get_top_holdings(db_session, guru.id)

        weights = [h["weight_pct"] for h in result if h["weight_pct"] is not None]
        assert weights == sorted(weights, reverse=True)

    def test_limits_to_n_holdings(self, db_session: Session) -> None:
        from application.stock.filing_service import get_top_holdings

        holdings_data = [
            {
                "company_name": f"Co {i}",
                "value": float(i + 1),
                "shares": float((i + 1) * 10),
                "weight_pct": float(i + 1),
            }
            for i in range(15)
        ]
        guru = self._seed_filing_with_holdings(db_session, "0005000003", holdings_data)

        result = get_top_holdings(db_session, guru.id, n=5)

        assert len(result) == 5

    def test_default_n_is_10(self, db_session: Session) -> None:
        from application.stock.filing_service import get_top_holdings

        holdings_data = [
            {
                "company_name": f"Co {i}",
                "value": float(i + 1),
                "shares": float((i + 1) * 10),
                "weight_pct": float(i + 1),
            }
            for i in range(15)
        ]
        guru = self._seed_filing_with_holdings(db_session, "0005000004", holdings_data)

        result = get_top_holdings(db_session, guru.id)

        assert len(result) == 10


# ===========================================================================
# TestGetDashboardSummary
# ===========================================================================


class TestGetDashboardSummary:
    """Test that get_dashboard_summary includes activity_feed key."""

    def test_dashboard_summary_includes_activity_feed_key(
        self, db_session: Session
    ) -> None:
        from application.stock.filing_service import get_dashboard_summary

        result = get_dashboard_summary(db_session)

        assert "activity_feed" in result
        assert "most_bought" in result["activity_feed"]
        assert "most_sold" in result["activity_feed"]

    def test_activity_feed_most_bought_contains_buy_actions(
        self, db_session: Session
    ) -> None:
        from application.stock.filing_service import get_dashboard_summary
        from domain.entities import Guru, GuruFiling, GuruHolding

        guru = save_guru(
            db_session,
            Guru(
                name="Dashboard Test Guru",
                cik="5555555555",
                display_name="Dashboard Guru",
                is_active=True,
            ),
        )
        filing = save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="DASH-001",
                report_date="2025-12-31",
                filing_date="2026-02-14",
                total_value=500_000.0,
                holdings_count=1,
            ),
        )
        save_holdings_batch(
            db_session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="DASHHCUSIP1",
                    ticker="DASH_TICKER",
                    company_name="Dashboard Co",
                    value=500_000.0,
                    shares=1000.0,
                    action=HoldingAction.NEW_POSITION.value,
                    weight_pct=100.0,
                )
            ],
        )

        result = get_dashboard_summary(db_session)

        bought_tickers = [
            item["ticker"] for item in result["activity_feed"]["most_bought"]
        ]
        assert "DASH_TICKER" in bought_tickers


# ===========================================================================
# Phase 7 — enrich_holdings_with_performance tests
# ===========================================================================


class TestEnrichHoldingsWithPerformance:
    """Unit tests for enrich_holdings_with_performance."""

    ENRICH_TARGET = "infrastructure.market_data.fetch_price_pair"

    def test_computes_positive_price_change_correctly(self):
        from application.stock.filing_service import enrich_holdings_with_performance

        holdings = [{"ticker": "AAPL", "company_name": "Apple"}]
        with patch(
            self.ENRICH_TARGET,
            return_value={"AAPL": {"report_price": 100.0, "current_price": 110.0}},
        ):
            result = enrich_holdings_with_performance(holdings, "2024-12-31")

        assert result[0]["price_change_pct"] == pytest.approx(10.0)

    def test_computes_negative_price_change_correctly(self):
        from application.stock.filing_service import enrich_holdings_with_performance

        holdings = [{"ticker": "TSLA", "company_name": "Tesla"}]
        with patch(
            self.ENRICH_TARGET,
            return_value={"TSLA": {"report_price": 200.0, "current_price": 190.0}},
        ):
            result = enrich_holdings_with_performance(holdings, "2024-12-31")

        assert result[0]["price_change_pct"] == pytest.approx(-5.0)

    def test_sets_none_when_ticker_is_missing(self):
        from application.stock.filing_service import enrich_holdings_with_performance

        holdings = [{"ticker": None, "company_name": "Unknown Co"}]
        with patch(self.ENRICH_TARGET, return_value={}):
            result = enrich_holdings_with_performance(holdings, "2024-12-31")

        assert result[0]["price_change_pct"] is None

    def test_sets_none_when_price_map_has_none_prices(self):
        from application.stock.filing_service import enrich_holdings_with_performance

        holdings = [{"ticker": "NVDA", "company_name": "Nvidia"}]
        with patch(
            self.ENRICH_TARGET,
            return_value={"NVDA": {"report_price": None, "current_price": 500.0}},
        ):
            result = enrich_holdings_with_performance(holdings, "2024-12-31")

        assert result[0]["price_change_pct"] is None

    def test_never_raises_when_fetch_price_pair_throws(self):
        """enrich_holdings_with_performance must not propagate exceptions."""
        from application.stock.filing_service import enrich_holdings_with_performance

        holdings = [{"ticker": "BAD", "company_name": "Bad Co"}]
        with patch(self.ENRICH_TARGET, side_effect=RuntimeError("network error")):
            # Should not raise; price_change_pct remains None
            result = enrich_holdings_with_performance(holdings, "2024-12-31")

        assert result[0]["price_change_pct"] is None

    def test_include_performance_false_does_not_call_enrich(self, db_session: Session):
        """get_holding_changes with include_performance=False must skip enrichment."""
        from application.stock.filing_service import (
            get_holding_changes,
        )

        guru = save_guru(
            db_session,
            Guru(name="PerfTestGuru", cik="0009900001", display_name="Perf Test"),
        )
        filing = save_filing(
            db_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="PERF-ACC-001",
                report_date="2024-12-31",
                filing_date="2025-02-14",
            ),
        )
        save_holdings_batch(
            db_session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="PERFCUSIP1",
                    ticker="PERF",
                    company_name="Perf Co",
                    value=100_000.0,
                    shares=1000.0,
                    action=HoldingAction.NEW_POSITION.value,
                    weight_pct=100.0,
                )
            ],
        )

        enrich_path = (
            "application.stock.filing_service.enrich_holdings_with_performance"
        )
        with patch(enrich_path) as mock_enrich:
            get_holding_changes(db_session, guru.id, include_performance=False)
            mock_enrich.assert_not_called()
