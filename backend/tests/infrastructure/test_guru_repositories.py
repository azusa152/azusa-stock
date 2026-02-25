"""Tests for Smart Money repository functions in repositories.py.

Focus: Season Highlights cold-start exclusion (>= 2 filings guard).
"""

import pytest
from sqlmodel import Session

from domain.entities import Guru, GuruFiling, GuruHolding
from domain.enums import HoldingAction
from infrastructure.repositories import (
    find_all_guru_summaries,
    find_consensus_stocks,
    find_notable_changes_all_gurus,
    find_sector_breakdown,
    save_filing,
    save_guru,
    save_holdings_batch,
)


@pytest.fixture
def test_session() -> Session:
    """Provide a test session (uses conftest's test_engine)."""
    from tests.conftest import test_engine

    with Session(test_engine) as session:
        yield session


def _make_guru(session: Session, cik: str, display_name: str) -> Guru:
    """Helper: Create and save a guru."""
    return save_guru(
        session,
        Guru(
            name=f"Institution {cik}",
            cik=cik,
            display_name=display_name,
            is_active=True,
        ),
    )


def _make_filing(
    session: Session,
    guru_id: int,
    accession_number: str,
    report_date: str,
) -> GuruFiling:
    """Helper: Create and save a filing."""
    return save_filing(
        session,
        GuruFiling(
            guru_id=guru_id,
            accession_number=accession_number,
            report_date=report_date,
            filing_date="2025-02-14",
            total_value=1_000_000.0,
            holdings_count=2,
        ),
    )


def _make_holding(
    session: Session,
    filing_id: int,
    guru_id: int,
    cusip: str,
    ticker: str,
    action: HoldingAction,
) -> GuruHolding:
    """Helper: Create a single holding with specified action."""
    holding = GuruHolding(
        filing_id=filing_id,
        guru_id=guru_id,
        cusip=cusip,
        ticker=ticker,
        company_name=f"Company {ticker}",
        value=100_000.0,
        shares=1000.0,
        action=action.value,
        weight_pct=10.0,
    )
    save_holdings_batch(session, [holding])
    return holding


class TestSeasonHighlightsColdStartExclusion:
    """Test that gurus with only 1 filing are excluded from season highlights."""

    def test_guru_with_1_filing_excluded_from_season_highlights(
        self, test_session: Session
    ):
        """
        Guru with only 1 filing should NOT appear in season highlights,
        even if holdings have NEW_POSITION action (cold-start artifact).
        """
        # Arrange: 1 guru, 1 filing, 1 NEW_POSITION holding
        guru = _make_guru(
            test_session, cik="0000000001", display_name="Single Filing Guru"
        )
        filing = _make_filing(
            test_session,
            guru.id,
            accession_number="ACC-001",
            report_date="2025-12-31",
        )
        _make_holding(
            test_session,
            filing.id,
            guru.id,
            cusip="CUSIP001",
            ticker="AAPL",
            action=HoldingAction.NEW_POSITION,
        )

        # Act
        result = find_notable_changes_all_gurus(test_session)

        # Assert: should be empty (guru excluded due to only 1 filing)
        assert result["new_positions"] == []
        assert result["sold_outs"] == []

    def test_guru_with_2_filings_included_in_season_highlights(
        self, test_session: Session
    ):
        """
        Guru with >= 2 filings should appear in season highlights
        with correct NEW_POSITION/SOLD_OUT entries from latest filing.
        """
        # Arrange: 1 guru, 2 filings
        guru = _make_guru(
            test_session, cik="0000000002", display_name="Multi Filing Guru"
        )
        filing1 = _make_filing(
            test_session,
            guru.id,
            accession_number="ACC-002-F1",
            report_date="2025-09-30",
        )
        filing2 = _make_filing(
            test_session,
            guru.id,
            accession_number="ACC-002-F2",
            report_date="2025-12-31",
        )

        # Filing 1 (older): baseline holdings
        _make_holding(
            test_session,
            filing1.id,
            guru.id,
            cusip="CUSIP001",
            ticker="AAPL",
            action=HoldingAction.UNCHANGED,
        )

        # Filing 2 (latest): NEW_POSITION + SOLD_OUT
        _make_holding(
            test_session,
            filing2.id,
            guru.id,
            cusip="CUSIP002",
            ticker="NVDA",
            action=HoldingAction.NEW_POSITION,
        )
        _make_holding(
            test_session,
            filing2.id,
            guru.id,
            cusip="CUSIP003",
            ticker="TSLA",
            action=HoldingAction.SOLD_OUT,
        )

        # Act
        result = find_notable_changes_all_gurus(test_session)

        # Assert: should include NEW_POSITION and SOLD_OUT from latest filing
        assert len(result["new_positions"]) == 1
        assert result["new_positions"][0]["ticker"] == "NVDA"
        assert result["new_positions"][0]["guru_display_name"] == "Multi Filing Guru"

        assert len(result["sold_outs"]) == 1
        assert result["sold_outs"][0]["ticker"] == "TSLA"
        assert result["sold_outs"][0]["guru_display_name"] == "Multi Filing Guru"

    def test_mixed_gurus_only_multi_filing_included(self, test_session: Session):
        """
        When multiple gurus exist (some with 1 filing, some with 2+),
        only gurus with >= 2 filings should appear in season highlights.
        """
        # Arrange: guru A (1 filing), guru B (2 filings)
        guru_a = _make_guru(test_session, cik="0000000003", display_name="Guru A")
        filing_a1 = _make_filing(
            test_session,
            guru_a.id,
            accession_number="ACC-003-F1",
            report_date="2025-12-31",
        )
        _make_holding(
            test_session,
            filing_a1.id,
            guru_a.id,
            cusip="CUSIPA1",
            ticker="AAPL",
            action=HoldingAction.NEW_POSITION,
        )

        guru_b = _make_guru(test_session, cik="0000000004", display_name="Guru B")
        filing_b1 = _make_filing(
            test_session,
            guru_b.id,
            accession_number="ACC-004-F1",
            report_date="2025-09-30",
        )
        filing_b2 = _make_filing(
            test_session,
            guru_b.id,
            accession_number="ACC-004-F2",
            report_date="2025-12-31",
        )
        _make_holding(
            test_session,
            filing_b1.id,
            guru_b.id,
            cusip="CUSIPB1",
            ticker="MSFT",
            action=HoldingAction.UNCHANGED,
        )
        _make_holding(
            test_session,
            filing_b2.id,
            guru_b.id,
            cusip="CUSIPB2",
            ticker="GOOGL",
            action=HoldingAction.NEW_POSITION,
        )

        # Act
        result = find_notable_changes_all_gurus(test_session)

        # Assert: only guru B (2 filings) should appear
        assert len(result["new_positions"]) == 1
        assert result["new_positions"][0]["guru_display_name"] == "Guru B"
        assert result["new_positions"][0]["ticker"] == "GOOGL"

    def test_guru_with_3_filings_included(self, test_session: Session):
        """
        Guru with 3+ filings should be included (sanity check for >= 2 logic).
        """
        # Arrange: 1 guru, 3 filings
        guru = _make_guru(
            test_session, cik="0000000005", display_name="Three Filing Guru"
        )
        _filing1 = _make_filing(
            test_session,
            guru.id,
            accession_number="ACC-005-F1",
            report_date="2025-06-30",
        )
        _filing2 = _make_filing(
            test_session,
            guru.id,
            accession_number="ACC-005-F2",
            report_date="2025-09-30",
        )
        filing3 = _make_filing(
            test_session,
            guru.id,
            accession_number="ACC-005-F3",
            report_date="2025-12-31",
        )

        _make_holding(
            test_session,
            filing3.id,
            guru.id,
            cusip="CUSIP005",
            ticker="AMD",
            action=HoldingAction.NEW_POSITION,
        )

        # Act
        result = find_notable_changes_all_gurus(test_session)

        # Assert: should include guru with 3 filings
        assert len(result["new_positions"]) == 1
        assert result["new_positions"][0]["ticker"] == "AMD"
        assert result["new_positions"][0]["guru_display_name"] == "Three Filing Guru"

    def test_no_active_gurus_returns_empty(self, test_session: Session):
        """
        When no active gurus exist, season highlights should be empty.
        """
        # Act (no data setup)
        result = find_notable_changes_all_gurus(test_session)

        # Assert
        assert result["new_positions"] == []
        assert result["sold_outs"] == []


# ===========================================================================
# find_all_guru_summaries
# ===========================================================================


class TestFindAllGuruSummaries:
    def test_returns_active_guru_with_filing_info(self, test_session: Session):
        """Active guru with a filing should appear in summaries with correct counts."""
        guru = _make_guru(test_session, cik="1000000001", display_name="Summary Guru")
        _make_filing(
            test_session,
            guru.id,
            accession_number="SUM-001",
            report_date="2025-12-31",
        )

        summaries = find_all_guru_summaries(test_session)

        match = next(
            (s for s in summaries if s["display_name"] == "Summary Guru"), None
        )
        assert match is not None
        assert match["filing_count"] == 1
        assert match["latest_report_date"] == "2025-12-31"

    def test_guru_with_multiple_filings_shows_latest(self, test_session: Session):
        """Guru with 2 filings: latest_report_date should be the most recent one."""
        guru = _make_guru(
            test_session, cik="1000000002", display_name="Multi Summary Guru"
        )
        _make_filing(test_session, guru.id, "SUM-002-F1", "2025-09-30")
        _make_filing(test_session, guru.id, "SUM-002-F2", "2025-12-31")

        summaries = find_all_guru_summaries(test_session)

        match = next(
            (s for s in summaries if s["display_name"] == "Multi Summary Guru"), None
        )
        assert match is not None
        assert match["latest_report_date"] == "2025-12-31"
        assert match["filing_count"] == 2

    def test_returns_list_of_dicts(self, test_session: Session):
        result = find_all_guru_summaries(test_session)
        assert isinstance(result, list)

    def test_guru_without_filings_shows_zeros(self, test_session: Session):
        """Guru with no filings should still appear with filing_count=0 and None dates."""
        guru = _make_guru(test_session, cik="1000000003", display_name="No Filing Guru")
        # Explicitly set is_active=True (already the default)
        assert guru.is_active is True

        summaries = find_all_guru_summaries(test_session)

        match = next(
            (s for s in summaries if s["display_name"] == "No Filing Guru"), None
        )
        assert match is not None
        assert match["filing_count"] == 0
        assert match["latest_report_date"] is None


# ===========================================================================
# find_consensus_stocks
# ===========================================================================


class TestFindConsensusStocks:
    def _make_holding_with_ticker(
        self,
        session: Session,
        filing_id: int,
        guru_id: int,
        cusip: str,
        ticker: str,
    ) -> None:
        holding = GuruHolding(
            filing_id=filing_id,
            guru_id=guru_id,
            cusip=cusip,
            ticker=ticker,
            company_name=f"Company {ticker}",
            value=500_000.0,
            shares=1000.0,
            action=HoldingAction.UNCHANGED.value,
            weight_pct=5.0,
        )
        save_holdings_batch(session, [holding])

    def test_ticker_held_by_multiple_gurus_appears_in_consensus(
        self, test_session: Session
    ):
        """A ticker held in both gurus' latest filings should appear in consensus."""
        guru_a = _make_guru(
            test_session, cik="2000000001", display_name="Consensus Guru A"
        )
        guru_b = _make_guru(
            test_session, cik="2000000002", display_name="Consensus Guru B"
        )

        filing_a = _make_filing(test_session, guru_a.id, "CON-001", "2025-12-31")
        filing_b = _make_filing(test_session, guru_b.id, "CON-002", "2025-12-31")

        self._make_holding_with_ticker(
            test_session, filing_a.id, guru_a.id, "CUSIP-CA1", "META"
        )
        self._make_holding_with_ticker(
            test_session, filing_b.id, guru_b.id, "CUSIP-CB1", "META"
        )

        result = find_consensus_stocks(test_session)

        meta_entry = next((r for r in result if r["ticker"] == "META"), None)
        assert meta_entry is not None
        assert meta_entry["guru_count"] == 2
        assert len(meta_entry["gurus"]) == 2

    def test_ticker_held_by_single_guru_not_in_consensus(self, test_session: Session):
        """A ticker held by only one guru should NOT appear (consensus requires 2+)."""
        guru = _make_guru(test_session, cik="2000000003", display_name="Solo Guru")
        filing = _make_filing(test_session, guru.id, "CON-003", "2025-12-31")
        self._make_holding_with_ticker(
            test_session, filing.id, guru.id, "CUSIP-SG1", "SOLO_TICKER"
        )

        result = find_consensus_stocks(test_session)

        assert not any(r["ticker"] == "SOLO_TICKER" for r in result)

    def test_returns_list(self, test_session: Session):
        assert isinstance(find_consensus_stocks(test_session), list)


# ===========================================================================
# find_sector_breakdown
# ===========================================================================


class TestFindSectorBreakdown:
    def _make_sector_holding(
        self,
        session: Session,
        filing_id: int,
        guru_id: int,
        cusip: str,
        ticker: str,
        sector: str,
        value: float,
    ) -> None:
        holding = GuruHolding(
            filing_id=filing_id,
            guru_id=guru_id,
            cusip=cusip,
            ticker=ticker,
            company_name=f"Company {ticker}",
            value=value,
            shares=100.0,
            action=HoldingAction.UNCHANGED.value,
            weight_pct=10.0,
            sector=sector,
        )
        save_holdings_batch(session, [holding])

    def test_sector_breakdown_aggregates_by_sector(self, test_session: Session):
        """Holdings with the same sector should be summed under one entry."""
        guru = _make_guru(test_session, cik="3000000001", display_name="Sector Guru")
        filing = _make_filing(test_session, guru.id, "SEC-001", "2025-12-31")

        self._make_sector_holding(
            test_session, filing.id, guru.id, "CUSIP-SE1", "AAPL", "Technology", 800_000
        )
        self._make_sector_holding(
            test_session, filing.id, guru.id, "CUSIP-SE2", "MSFT", "Technology", 200_000
        )
        self._make_sector_holding(
            test_session, filing.id, guru.id, "CUSIP-SE3", "JPM", "Financials", 500_000
        )

        result = find_sector_breakdown(test_session)

        sectors = {r["sector"]: r for r in result}
        assert "Technology" in sectors
        assert "Financials" in sectors
        assert sectors["Technology"]["holding_count"] == 2
        assert sectors["Technology"]["total_value"] == pytest.approx(1_000_000)

    def test_weight_pct_sums_to_100(self, test_session: Session):
        """weight_pct across all sectors should sum to ~100%."""
        guru = _make_guru(test_session, cik="3000000002", display_name="Weight Guru")
        filing = _make_filing(test_session, guru.id, "SEC-002", "2025-12-31")

        for i, sector in enumerate(["Tech", "Health", "Energy"]):
            self._make_sector_holding(
                test_session,
                filing.id,
                guru.id,
                f"CUSIP-W{i}",
                f"TICKER{i}",
                sector,
                1_000_000,
            )

        result = find_sector_breakdown(test_session)
        total_weight = sum(r["weight_pct"] for r in result)
        assert total_weight == pytest.approx(100.0, rel=0.01)

    def test_returns_list(self, test_session: Session):
        assert isinstance(find_sector_breakdown(test_session), list)
