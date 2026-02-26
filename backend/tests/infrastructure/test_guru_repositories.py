"""Tests for Smart Money repository functions in repositories.py.

Focus: Season Highlights cold-start exclusion (>= 2 filings guard).
"""

import pytest
from sqlmodel import Session

from domain.entities import Guru, GuruFiling, GuruHolding
from domain.enums import HoldingAction
from infrastructure.persistence.repositories import _compute_trend
from infrastructure.repositories import (
    find_activity_feed,
    find_all_guru_summaries,
    find_consensus_stocks,
    find_grand_portfolio,
    find_holding_history_by_guru,
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

    def test_no_filing_returns_none_for_metrics(self, test_session: Session):
        """Guru with no filings should have None for concentration and turnover."""
        _make_guru(
            test_session, cik="1000000050", display_name="No Filing Metrics Guru"
        )

        summaries = find_all_guru_summaries(test_session)

        match = next(
            (s for s in summaries if s["display_name"] == "No Filing Metrics Guru"),
            None,
        )
        assert match is not None
        assert match["top5_concentration_pct"] is None
        assert match["turnover_pct"] is None

    def test_top5_concentration_pct_sums_top_five_weights(self, test_session: Session):
        """top5_concentration_pct should be the sum of the top-5 weight_pct values."""
        guru = _make_guru(
            test_session, cik="1000000051", display_name="Concentration Guru"
        )
        # holdings_count must reflect the actual holdings we add (7 here)
        filing = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="CONC-001",
                report_date="2025-12-31",
                filing_date="2026-02-14",
                total_value=1_000_000.0,
                holdings_count=7,
            ),
        )
        # Add 7 holdings with distinct weight_pct values
        weights = [30.0, 20.0, 15.0, 10.0, 8.0, 5.0, 2.0]
        for i, w in enumerate(weights):
            holding = GuruHolding(
                filing_id=filing.id,
                guru_id=guru.id,
                cusip=f"CONC-C{i:03d}",
                ticker=f"TICK{i}",
                company_name=f"Company {i}",
                value=100_000.0,
                shares=1000.0,
                action=HoldingAction.UNCHANGED.value,
                weight_pct=w,
            )
            save_holdings_batch(test_session, [holding])

        summaries = find_all_guru_summaries(test_session)

        match = next(
            (s for s in summaries if s["display_name"] == "Concentration Guru"), None
        )
        assert match is not None
        # Top-5: 30+20+15+10+8 = 83.0
        assert match["top5_concentration_pct"] == pytest.approx(83.0)

    def test_turnover_pct_counts_new_and_sold(self, test_session: Session):
        """turnover_pct = (new_positions + sold_out) / holdings_count * 100."""
        guru = _make_guru(test_session, cik="1000000052", display_name="Turnover Guru")
        # 4 holdings: 1 NEW_POSITION, 1 SOLD_OUT, 2 UNCHANGED → turnover = 50%
        filing = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="TURN-001",
                report_date="2025-12-31",
                filing_date="2026-02-14",
                total_value=1_000_000.0,
                holdings_count=4,
            ),
        )
        actions = [
            HoldingAction.NEW_POSITION,
            HoldingAction.SOLD_OUT,
            HoldingAction.UNCHANGED,
            HoldingAction.UNCHANGED,
        ]
        for i, action in enumerate(actions):
            holding = GuruHolding(
                filing_id=filing.id,
                guru_id=guru.id,
                cusip=f"TURN-C{i:03d}",
                ticker=f"TTICK{i}",
                company_name=f"Company {i}",
                value=100_000.0,
                shares=1000.0,
                action=action.value,
                weight_pct=10.0,
            )
            save_holdings_batch(test_session, [holding])

        summaries = find_all_guru_summaries(test_session)

        match = next(
            (s for s in summaries if s["display_name"] == "Turnover Guru"), None
        )
        assert match is not None
        # (1 + 1) / 4 * 100 = 50.0
        assert match["turnover_pct"] == pytest.approx(50.0)

    def test_concentration_fewer_than_5_holdings_sums_all(self, test_session: Session):
        """When a filing has fewer than 5 holdings, concentration is the sum of all."""
        guru = _make_guru(
            test_session, cik="1000000053", display_name="Few Holdings Guru"
        )
        filing = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="FEW-001",
                report_date="2025-12-31",
                filing_date="2026-02-14",
                total_value=1_000_000.0,
                holdings_count=3,
            ),
        )
        weights = [40.0, 35.0, 25.0]
        for i, w in enumerate(weights):
            holding = GuruHolding(
                filing_id=filing.id,
                guru_id=guru.id,
                cusip=f"FEW-C{i:03d}",
                ticker=f"FTICK{i}",
                company_name=f"Company {i}",
                value=100_000.0,
                shares=1000.0,
                action=HoldingAction.UNCHANGED.value,
                weight_pct=w,
            )
            save_holdings_batch(test_session, [holding])

        summaries = find_all_guru_summaries(test_session)

        match = next(
            (s for s in summaries if s["display_name"] == "Few Holdings Guru"), None
        )
        assert match is not None
        # All 3 holdings: 40+35+25 = 100.0
        assert match["top5_concentration_pct"] == pytest.approx(100.0)

    def test_turnover_pct_is_none_when_holdings_count_is_zero(
        self, test_session: Session
    ):
        """Filing with holdings_count=0 should yield turnover_pct=None (division guard)."""
        guru = _make_guru(
            test_session, cik="1000000054", display_name="Empty Filing Guru"
        )
        save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="EMPTY-001",
                report_date="2025-12-31",
                filing_date="2026-02-14",
                total_value=0.0,
                holdings_count=0,
            ),
        )

        summaries = find_all_guru_summaries(test_session)

        match = next(
            (s for s in summaries if s["display_name"] == "Empty Filing Guru"), None
        )
        assert match is not None
        assert match["turnover_pct"] is None


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
        # gurus is now list[dict] with display_name, action, weight_pct
        guru_names = {g["display_name"] for g in meta_entry["gurus"]}
        assert "Consensus Guru A" in guru_names
        assert "Consensus Guru B" in guru_names

    def test_enriched_fields_present(self, test_session: Session):
        """Each consensus item should include company_name, avg_weight_pct, sector."""
        guru_a = _make_guru(
            test_session, cik="2000000006", display_name="Enrich Guru A"
        )
        guru_b = _make_guru(
            test_session, cik="2000000007", display_name="Enrich Guru B"
        )
        filing_a = _make_filing(test_session, guru_a.id, "CON-006", "2025-12-31")
        filing_b = _make_filing(test_session, guru_b.id, "CON-007", "2025-12-31")
        self._make_holding_with_ticker(
            test_session, filing_a.id, guru_a.id, "CUSIP-EA1", "GOOGL"
        )
        self._make_holding_with_ticker(
            test_session, filing_b.id, guru_b.id, "CUSIP-EB1", "GOOGL"
        )

        result = find_consensus_stocks(test_session)

        entry = next((r for r in result if r["ticker"] == "GOOGL"), None)
        assert entry is not None
        assert entry["company_name"] == "Company GOOGL"
        assert entry["avg_weight_pct"] == pytest.approx(5.0)
        assert entry["sector"] is None  # helper doesn't set sector
        # Each guru detail has the expected keys and values
        for g in entry["gurus"]:
            assert "display_name" in g
            assert "action" in g
            assert g["weight_pct"] == pytest.approx(5.0)

    def test_sold_out_excluded(self, test_session: Session):
        """SOLD_OUT positions must not appear in consensus."""
        guru_a = _make_guru(
            test_session, cik="2000000008", display_name="SoldOut Guru A"
        )
        guru_b = _make_guru(
            test_session, cik="2000000009", display_name="SoldOut Guru B"
        )
        filing_a = _make_filing(test_session, guru_a.id, "CON-008", "2025-12-31")
        filing_b = _make_filing(test_session, guru_b.id, "CON-009", "2025-12-31")

        for filing_id, guru_id, cusip in [
            (filing_a.id, guru_a.id, "CUSIP-SO1"),
            (filing_b.id, guru_b.id, "CUSIP-SO2"),
        ]:
            holding = GuruHolding(
                filing_id=filing_id,
                guru_id=guru_id,
                cusip=cusip,
                ticker="SOLD_TICKER",
                company_name="Sold Co",
                value=100_000.0,
                shares=500.0,
                action=HoldingAction.SOLD_OUT.value,
                weight_pct=2.0,
            )
            save_holdings_batch(test_session, [holding])

        result = find_consensus_stocks(test_session)

        assert not any(r["ticker"] == "SOLD_TICKER" for r in result)

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


# ===========================================================================
# find_activity_feed
# ===========================================================================


class TestFindActivityFeed:
    """Tests for the find_activity_feed repository function."""

    def _make_holding_with_action(
        self,
        session: Session,
        filing_id: int,
        guru_id: int,
        cusip: str,
        ticker: str,
        action: HoldingAction,
        value: float = 100_000.0,
    ) -> None:
        holding = GuruHolding(
            filing_id=filing_id,
            guru_id=guru_id,
            cusip=cusip,
            ticker=ticker,
            company_name=f"Company {ticker}",
            value=value,
            shares=1000.0,
            action=action.value,
            weight_pct=10.0,
        )
        save_holdings_batch(session, [holding])

    def test_most_bought_contains_new_position_and_increased(
        self, test_session: Session
    ):
        """most_bought should aggregate NEW_POSITION and INCREASED actions."""
        guru = _make_guru(test_session, cik="4000000001", display_name="Buy Guru A")
        filing = _make_filing(test_session, guru.id, "ACT-001", "2025-12-31")

        self._make_holding_with_action(
            test_session,
            filing.id,
            guru.id,
            "ACT-C001",
            "AAPL",
            HoldingAction.NEW_POSITION,
        )
        self._make_holding_with_action(
            test_session,
            filing.id,
            guru.id,
            "ACT-C002",
            "MSFT",
            HoldingAction.INCREASED,
        )

        result = find_activity_feed(test_session)

        tickers_bought = [item["ticker"] for item in result["most_bought"]]
        assert "AAPL" in tickers_bought
        assert "MSFT" in tickers_bought

    def test_most_sold_contains_sold_out_and_decreased(self, test_session: Session):
        """most_sold should aggregate SOLD_OUT and DECREASED actions."""
        guru = _make_guru(test_session, cik="4000000002", display_name="Sell Guru B")
        filing = _make_filing(test_session, guru.id, "ACT-002", "2025-12-31")

        self._make_holding_with_action(
            test_session, filing.id, guru.id, "ACT-C003", "TSLA", HoldingAction.SOLD_OUT
        )
        self._make_holding_with_action(
            test_session,
            filing.id,
            guru.id,
            "ACT-C004",
            "NFLX",
            HoldingAction.DECREASED,
        )

        result = find_activity_feed(test_session)

        tickers_sold = [item["ticker"] for item in result["most_sold"]]
        assert "TSLA" in tickers_sold
        assert "NFLX" in tickers_sold

    def test_buy_and_sell_are_mutually_exclusive(self, test_session: Session):
        """A ticker in most_bought must not appear in most_sold and vice versa."""
        guru = _make_guru(test_session, cik="4000000003", display_name="Mixed Guru C")
        filing = _make_filing(test_session, guru.id, "ACT-003", "2025-12-31")

        self._make_holding_with_action(
            test_session,
            filing.id,
            guru.id,
            "ACT-C005",
            "BUYONLY",
            HoldingAction.NEW_POSITION,
        )
        self._make_holding_with_action(
            test_session,
            filing.id,
            guru.id,
            "ACT-C006",
            "SELLONLY",
            HoldingAction.SOLD_OUT,
        )

        result = find_activity_feed(test_session)

        bought_tickers = {item["ticker"] for item in result["most_bought"]}
        sold_tickers = {item["ticker"] for item in result["most_sold"]}
        assert "BUYONLY" in bought_tickers
        assert "SELLONLY" not in bought_tickers
        assert "SELLONLY" in sold_tickers
        assert "BUYONLY" not in sold_tickers

    def test_returns_dict_with_both_keys(self, test_session: Session):
        """find_activity_feed should always return a dict with most_bought and most_sold."""
        result = find_activity_feed(test_session)
        assert isinstance(result, dict)
        assert "most_bought" in result
        assert "most_sold" in result
        assert isinstance(result["most_bought"], list)
        assert isinstance(result["most_sold"], list)

    def test_multi_guru_increases_guru_count(self, test_session: Session):
        """When two gurus both buy the same ticker, guru_count should be 2."""
        guru_a = _make_guru(test_session, cik="4000000004", display_name="Count Guru D")
        guru_b = _make_guru(test_session, cik="4000000005", display_name="Count Guru E")
        filing_a = _make_filing(test_session, guru_a.id, "ACT-004", "2025-12-31")
        filing_b = _make_filing(test_session, guru_b.id, "ACT-005", "2025-12-31")

        self._make_holding_with_action(
            test_session,
            filing_a.id,
            guru_a.id,
            "ACT-C007",
            "SHARED",
            HoldingAction.NEW_POSITION,
        )
        self._make_holding_with_action(
            test_session,
            filing_b.id,
            guru_b.id,
            "ACT-C008",
            "SHARED",
            HoldingAction.NEW_POSITION,
        )

        result = find_activity_feed(test_session)

        shared = next(
            (item for item in result["most_bought"] if item["ticker"] == "SHARED"), None
        )
        assert shared is not None
        assert shared["guru_count"] == 2
        assert set(shared["gurus"]) == {"Count Guru D", "Count Guru E"}

    def test_limit_truncates_results(self, test_session: Session):
        """Passing limit=1 should return at most 1 item per list."""
        guru = _make_guru(test_session, cik="4000000006", display_name="Limit Guru F")
        filing = _make_filing(test_session, guru.id, "ACT-006", "2025-12-31")

        # Seed 3 distinct buy tickers
        for i, ticker in enumerate(["TICK1", "TICK2", "TICK3"]):
            self._make_holding_with_action(
                test_session,
                filing.id,
                guru.id,
                f"ACT-C00{9 + i}",
                ticker,
                HoldingAction.NEW_POSITION,
            )

        result = find_activity_feed(test_session, limit=1)

        assert len(result["most_bought"]) <= 1


# ===========================================================================
# _compute_trend
# ===========================================================================


class TestComputeTrend:
    def test_single_value_returns_stable(self):
        assert _compute_trend([100.0]) == "stable"

    def test_empty_returns_stable(self):
        assert _compute_trend([]) == "stable"

    def test_increasing_when_change_gte_10pct(self):
        assert _compute_trend([100.0, 115.0]) == "increasing"

    def test_decreasing_when_change_lte_minus10pct(self):
        assert _compute_trend([100.0, 85.0]) == "decreasing"

    def test_stable_when_change_between_minus10_and_10(self):
        assert _compute_trend([100.0, 105.0]) == "stable"

    def test_exited_when_last_is_zero(self):
        assert _compute_trend([100.0, 0.0]) == "exited"

    def test_new_when_first_is_zero(self):
        assert _compute_trend([0.0, 100.0]) == "new"


# ===========================================================================
# find_holding_history_by_guru
# ===========================================================================


class TestFindHoldingHistoryByGuru:
    def test_returns_empty_for_guru_with_no_filings(self, test_session: Session):
        guru = _make_guru(
            test_session,
            cik="5000000001",
            display_name="No Filings QoQ Guru",
        )
        result = find_holding_history_by_guru(test_session, guru.id)
        assert result == []

    def test_single_filing_returns_single_quarter_per_ticker(
        self, test_session: Session
    ):
        guru = _make_guru(
            test_session, cik="5000000002", display_name="Single Filing QoQ Guru"
        )
        filing = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="QOQ-001",
                report_date="2025-09-30",
                filing_date="2025-11-14",
                total_value=500_000.0,
                holdings_count=2,
            ),
        )
        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="QOQ0001",
                    ticker="AAPL",
                    company_name="Apple Inc",
                    value=300_000.0,
                    shares=2000.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=60.0,
                ),
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="QOQ0002",
                    ticker="MSFT",
                    company_name="Microsoft Corp",
                    value=200_000.0,
                    shares=500.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=40.0,
                ),
            ],
        )

        result = find_holding_history_by_guru(test_session, guru.id, quarters=3)

        assert len(result) == 2
        tickers = [item["ticker"] for item in result]
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        for item in result:
            assert len(item["quarters"]) == 1
            assert "trend" in item
            assert item["quarters"][0]["report_date"] == "2025-09-30"

    def test_multi_quarter_groups_by_ticker(self, test_session: Session):
        guru = _make_guru(
            test_session, cik="5000000003", display_name="Multi Quarter QoQ Guru"
        )
        filing1 = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="QOQ-003-F1",
                report_date="2025-03-31",
                filing_date="2025-05-14",
                total_value=400_000.0,
                holdings_count=1,
            ),
        )
        filing2 = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="QOQ-003-F2",
                report_date="2025-06-30",
                filing_date="2025-08-14",
                total_value=500_000.0,
                holdings_count=1,
            ),
        )
        # Same ticker in both filings
        for filing, shares in [(filing1, 1000.0), (filing2, 1200.0)]:
            save_holdings_batch(
                test_session,
                [
                    GuruHolding(
                        filing_id=filing.id,
                        guru_id=guru.id,
                        cusip="QOQ0003",
                        ticker="GOOG",
                        company_name="Alphabet Inc",
                        value=400_000.0,
                        shares=shares,
                        action=HoldingAction.INCREASED.value,
                        weight_pct=80.0,
                    )
                ],
            )

        result = find_holding_history_by_guru(test_session, guru.id, quarters=3)

        assert len(result) == 1
        item = result[0]
        assert item["ticker"] == "GOOG"
        assert len(item["quarters"]) == 2
        # Newest first
        assert item["quarters"][0]["report_date"] == "2025-06-30"
        assert item["quarters"][1]["report_date"] == "2025-03-31"
        # Shares increased by 20% → trend = increasing
        assert item["trend"] == "increasing"

    def test_sorted_by_latest_weight_desc(self, test_session: Session):
        guru = _make_guru(test_session, cik="5000000004", display_name="Sort QoQ Guru")
        filing = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="QOQ-004",
                report_date="2025-09-30",
                filing_date="2025-11-14",
                total_value=600_000.0,
                holdings_count=3,
            ),
        )
        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="QOQ0041",
                    ticker="LOW_WT",
                    company_name="Low Weight Co",
                    value=60_000.0,
                    shares=100.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=10.0,
                ),
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="QOQ0042",
                    ticker="HIGH_WT",
                    company_name="High Weight Co",
                    value=540_000.0,
                    shares=900.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=90.0,
                ),
            ],
        )

        result = find_holding_history_by_guru(test_session, guru.id)

        assert result[0]["ticker"] == "HIGH_WT"
        assert result[1]["ticker"] == "LOW_WT"

    def test_varying_quarter_counts_per_ticker(self, test_session: Session):
        """Ticker held across all 3 filings has 3 quarters; one held in only 2 has 2.

        Confirms the backend returns varying-length quarters lists — the frontend
        is responsible for padding empty cells when rendering the aligned table.
        """
        guru = _make_guru(
            test_session, cik="5000000005", display_name="Varying QoQ Guru"
        )
        filing1 = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="QOQ-005-F1",
                report_date="2024-03-31",
                filing_date="2024-05-14",
                total_value=400_000.0,
                holdings_count=1,
            ),
        )
        filing2 = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="QOQ-005-F2",
                report_date="2024-06-30",
                filing_date="2024-08-14",
                total_value=500_000.0,
                holdings_count=2,
            ),
        )
        filing3 = save_filing(
            test_session,
            GuruFiling(
                guru_id=guru.id,
                accession_number="QOQ-005-F3",
                report_date="2024-09-30",
                filing_date="2024-11-14",
                total_value=600_000.0,
                holdings_count=2,
            ),
        )
        # AAPL held in all 3 filings
        for filing, shares in [(filing1, 1000.0), (filing2, 1100.0), (filing3, 1200.0)]:
            save_holdings_batch(
                test_session,
                [
                    GuruHolding(
                        filing_id=filing.id,
                        guru_id=guru.id,
                        cusip="QOQ0051",
                        ticker="AAPL",
                        company_name="Apple Inc",
                        value=300_000.0,
                        shares=shares,
                        action=HoldingAction.UNCHANGED.value,
                        weight_pct=50.0,
                    )
                ],
            )
        # NVDA only in filing2 and filing3 (not filing1)
        for filing, shares in [(filing2, 500.0), (filing3, 600.0)]:
            save_holdings_batch(
                test_session,
                [
                    GuruHolding(
                        filing_id=filing.id,
                        guru_id=guru.id,
                        cusip="QOQ0052",
                        ticker="NVDA",
                        company_name="Nvidia Corp",
                        value=200_000.0,
                        shares=shares,
                        action=HoldingAction.NEW_POSITION.value,
                        weight_pct=40.0,
                    )
                ],
            )

        result = find_holding_history_by_guru(test_session, guru.id, quarters=3)

        aapl = next(item for item in result if item["ticker"] == "AAPL")
        nvda = next(item for item in result if item["ticker"] == "NVDA")

        # AAPL has data in all 3 filings
        assert len(aapl["quarters"]) == 3
        # NVDA only has data from 2 filings
        assert len(nvda["quarters"]) == 2
        # NVDA quarters should be from filing2 and filing3
        nvda_dates = {q["report_date"] for q in nvda["quarters"]}
        assert nvda_dates == {"2024-06-30", "2024-09-30"}


# ===========================================================================
# find_grand_portfolio tests
# ===========================================================================


class TestFindGrandPortfolio:
    """Tests for find_grand_portfolio repository function."""

    def test_aggregates_values_across_gurus(self, test_session: Session):
        """combined_weight_pct should sum values across all gurus."""
        guru1 = _make_guru(test_session, cik="GP0001", display_name="Grand Guru1")
        guru2 = _make_guru(test_session, cik="GP0002", display_name="Grand Guru2")

        filing1 = _make_filing(test_session, guru1.id, "GP-ACC-001", "2024-12-31")
        filing2 = _make_filing(test_session, guru2.id, "GP-ACC-002", "2024-12-31")

        # Both gurus hold AAPL
        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=filing1.id,
                    guru_id=guru1.id,
                    cusip="GP-C001",
                    ticker="AAPL",
                    company_name="Apple Inc",
                    sector="Technology",
                    value=200_000.0,
                    shares=1000.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=50.0,
                ),
                GuruHolding(
                    filing_id=filing2.id,
                    guru_id=guru2.id,
                    cusip="GP-C002",
                    ticker="AAPL",
                    company_name="Apple Inc",
                    sector="Technology",
                    value=100_000.0,
                    shares=500.0,
                    action=HoldingAction.INCREASED.value,
                    weight_pct=40.0,
                ),
            ],
        )

        result = find_grand_portfolio(test_session)
        items = result["items"]
        assert len(items) >= 1
        aapl = next(i for i in items if i["ticker"] == "AAPL")

        # total_value for AAPL: 200000 + 100000 = 300000
        assert aapl["total_value"] == pytest.approx(300_000.0)
        assert aapl["guru_count"] == 2
        assert aapl["combined_weight_pct"] == pytest.approx(100.0)

    def test_combined_weight_pct_sums_to_100(self, test_session: Session):
        """combined_weight_pct for all items should sum to ~100%."""
        guru = _make_guru(test_session, cik="GP0003", display_name="Grand Guru3")
        filing = _make_filing(test_session, guru.id, "GP-ACC-003", "2024-12-31")

        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="GP-C010",
                    ticker="MSFT",
                    company_name="Microsoft",
                    sector="Technology",
                    value=600_000.0,
                    shares=2000.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=60.0,
                ),
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="GP-C011",
                    ticker="GOOGL",
                    company_name="Alphabet",
                    sector="Technology",
                    value=400_000.0,
                    shares=1500.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=40.0,
                ),
            ],
        )

        result = find_grand_portfolio(test_session)
        items = [i for i in result["items"] if i["ticker"] in ("MSFT", "GOOGL")]
        total_weight = sum(i["combined_weight_pct"] for i in items)
        assert total_weight == pytest.approx(100.0, abs=0.01)

    def test_excludes_sold_out_positions(self, test_session: Session):
        """SOLD_OUT holdings must not appear in grand portfolio results."""
        guru = _make_guru(test_session, cik="GP0004", display_name="Grand Guru4")
        filing = _make_filing(test_session, guru.id, "GP-ACC-004", "2024-12-31")

        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="GP-C020",
                    ticker="SOLD_STOCK",
                    company_name="Sold Corp",
                    sector="Finance",
                    value=0.0,
                    shares=0.0,
                    action=HoldingAction.SOLD_OUT.value,
                    weight_pct=0.0,
                ),
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="GP-C021",
                    ticker="KEPT_STOCK",
                    company_name="Kept Corp",
                    sector="Finance",
                    value=500_000.0,
                    shares=1000.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=50.0,
                ),
            ],
        )

        result = find_grand_portfolio(test_session)
        tickers = {i["ticker"] for i in result["items"]}
        assert "SOLD_STOCK" not in tickers
        assert "KEPT_STOCK" in tickers

    def test_sector_breakdown_is_correct(self, test_session: Session):
        """sector_breakdown should aggregate total_value by sector."""
        guru = _make_guru(test_session, cik="GP0005", display_name="Grand Guru5")
        filing = _make_filing(test_session, guru.id, "GP-ACC-005", "2024-12-31")

        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="GP-C030",
                    ticker="TECH1",
                    company_name="Tech One",
                    sector="Technology",
                    value=700_000.0,
                    shares=1000.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=70.0,
                ),
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip="GP-C031",
                    ticker="FIN1",
                    company_name="Finance One",
                    sector="Finance",
                    value=300_000.0,
                    shares=500.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=30.0,
                ),
            ],
        )

        result = find_grand_portfolio(test_session)
        breakdown = {b["sector"]: b for b in result["sector_breakdown"]}
        assert breakdown["Technology"]["total_value"] == pytest.approx(700_000.0)
        assert breakdown["Technology"]["weight_pct"] == pytest.approx(70.0)
        assert breakdown["Finance"]["total_value"] == pytest.approx(300_000.0)
        assert breakdown["Finance"]["holding_count"] == 1

    def test_returns_empty_when_no_active_filings(self, test_session: Session):
        """With no filings in the database, grand portfolio should return empty results."""
        result = find_grand_portfolio(test_session)
        assert result["items"] == []
        assert result["total_value"] == 0.0
        assert result["unique_tickers"] == 0
        assert result["sector_breakdown"] == []


# ---------------------------------------------------------------------------
# Style filter tests
# ---------------------------------------------------------------------------


def _make_guru_with_style(
    session: Session, cik: str, display_name: str, style: str
) -> Guru:
    """Helper: Create and save a guru with a specific style."""
    return save_guru(
        session,
        Guru(
            name=f"Institution {cik}",
            cik=cik,
            display_name=display_name,
            is_active=True,
            style=style,
        ),
    )


class TestStyleFilter:
    """Style filter parameter propagates correctly through all aggregation functions."""

    def test_find_all_guru_summaries_filters_by_style(self, test_session: Session):
        """Only active gurus with the matching style are returned."""
        value_guru = _make_guru_with_style(
            test_session, "SF0001", "Value Guru", "VALUE"
        )
        _make_filing(test_session, value_guru.id, "SF-ACC-001", "2024-12-31")

        growth_guru = _make_guru_with_style(
            test_session, "SF0002", "Growth Guru", "GROWTH"
        )
        _make_filing(test_session, growth_guru.id, "SF-ACC-002", "2024-12-31")

        results = find_all_guru_summaries(test_session, style="VALUE")
        names = [r["display_name"] for r in results]
        assert "Value Guru" in names
        assert "Growth Guru" not in names

    def test_find_grand_portfolio_filters_by_style(self, test_session: Session):
        """Grand portfolio only aggregates holdings from gurus of the given style."""
        value_guru = _make_guru_with_style(
            test_session, "SF0003", "Value Guru 2", "VALUE"
        )
        value_filing = _make_filing(
            test_session, value_guru.id, "SF-ACC-003", "2024-12-31"
        )
        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=value_filing.id,
                    guru_id=value_guru.id,
                    cusip="SF-C001",
                    ticker="AAPL",
                    company_name="Apple",
                    value=200_000.0,
                    shares=1000.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=20.0,
                )
            ],
        )

        growth_guru = _make_guru_with_style(
            test_session, "SF0004", "Growth Guru 2", "GROWTH"
        )
        growth_filing = _make_filing(
            test_session, growth_guru.id, "SF-ACC-004", "2024-12-31"
        )
        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=growth_filing.id,
                    guru_id=growth_guru.id,
                    cusip="SF-C002",
                    ticker="NVDA",
                    company_name="NVIDIA",
                    value=300_000.0,
                    shares=500.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=30.0,
                )
            ],
        )

        result = find_grand_portfolio(test_session, style="VALUE")
        tickers = [i["ticker"] for i in result["items"]]
        assert "AAPL" in tickers
        assert "NVDA" not in tickers

    def test_find_grand_portfolio_excludes_inactive_gurus_when_style_set(
        self, test_session: Session
    ):
        """Inactive gurus are excluded from grand portfolio even when their style matches."""
        active_guru = _make_guru_with_style(
            test_session, "SF0005", "Active Value Guru", "VALUE"
        )
        active_filing = _make_filing(
            test_session, active_guru.id, "SF-ACC-005", "2024-12-31"
        )
        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=active_filing.id,
                    guru_id=active_guru.id,
                    cusip="SF-C003",
                    ticker="MSFT",
                    company_name="Microsoft",
                    value=100_000.0,
                    shares=400.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=10.0,
                )
            ],
        )

        inactive_guru = save_guru(
            test_session,
            Guru(
                name="Inactive Institution",
                cik="SF0006",
                display_name="Inactive Value Guru",
                is_active=False,
                style="VALUE",
            ),
        )
        inactive_filing = _make_filing(
            test_session, inactive_guru.id, "SF-ACC-006", "2024-12-31"
        )
        save_holdings_batch(
            test_session,
            [
                GuruHolding(
                    filing_id=inactive_filing.id,
                    guru_id=inactive_guru.id,
                    cusip="SF-C004",
                    ticker="AMZN",
                    company_name="Amazon",
                    value=150_000.0,
                    shares=600.0,
                    action=HoldingAction.UNCHANGED.value,
                    weight_pct=15.0,
                )
            ],
        )

        result = find_grand_portfolio(test_session, style="VALUE")
        tickers = [i["ticker"] for i in result["items"]]
        assert "MSFT" in tickers
        assert "AMZN" not in tickers

    def test_find_consensus_stocks_filters_by_style(self, test_session: Session):
        """Consensus only counts gurus of the given style; single-style holding is excluded."""
        # Two VALUE gurus both hold AAPL → consensus
        v1 = _make_guru_with_style(test_session, "SF0007", "Value A", "VALUE")
        v1_f = _make_filing(test_session, v1.id, "SF-ACC-007", "2024-12-31")
        v2 = _make_guru_with_style(test_session, "SF0008", "Value B", "VALUE")
        v2_f = _make_filing(test_session, v2.id, "SF-ACC-008", "2024-12-31")

        # GROWTH guru also holds AAPL, but should not count when filtering VALUE
        g1 = _make_guru_with_style(test_session, "SF0009", "Growth A", "GROWTH")
        g1_f = _make_filing(test_session, g1.id, "SF-ACC-009", "2024-12-31")

        for fid, gid, cusip in [
            (v1_f.id, v1.id, "SF-C005"),
            (v2_f.id, v2.id, "SF-C006"),
            (g1_f.id, g1.id, "SF-C007"),
        ]:
            save_holdings_batch(
                test_session,
                [
                    GuruHolding(
                        filing_id=fid,
                        guru_id=gid,
                        cusip=cusip,
                        ticker="AAPL",
                        company_name="Apple",
                        value=100_000.0,
                        shares=500.0,
                        action=HoldingAction.UNCHANGED.value,
                        weight_pct=10.0,
                    )
                ],
            )

        result = find_consensus_stocks(test_session, style="VALUE")
        aapl = next((r for r in result if r["ticker"] == "AAPL"), None)
        assert aapl is not None
        assert aapl["guru_count"] == 2

    def test_style_none_returns_all_gurus(self, test_session: Session):
        """Passing style=None (default) returns data across all styles."""
        v = _make_guru_with_style(test_session, "SF0010", "Nil Value Guru", "VALUE")
        _make_filing(test_session, v.id, "SF-ACC-010", "2024-12-31")
        g = _make_guru_with_style(test_session, "SF0011", "Nil Growth Guru", "GROWTH")
        _make_filing(test_session, g.id, "SF-ACC-011", "2024-12-31")

        results = find_all_guru_summaries(test_session, style=None)
        names = [r["display_name"] for r in results]
        assert "Nil Value Guru" in names
        assert "Nil Growth Guru" in names
