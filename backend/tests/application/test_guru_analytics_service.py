from unittest.mock import patch

import pandas as pd
import pytest

from application.guru.backtest_service import (
    get_guru_backtest,
    invalidate_guru_backtest_cache,
)
from application.guru.heatmap_service import get_heatmap, invalidate_heatmap_cache
from domain.entities import Guru, GuruFiling, GuruHolding
from infrastructure.repositories import save_filing, save_guru, save_holdings_batch


def _seed_guru_with_two_filings(db_session):
    guru = save_guru(
        db_session,
        Guru(name="Berkshire Hathaway", cik="0001067983", display_name="Buffett"),
    )
    filing_q4 = save_filing(
        db_session,
        GuruFiling(
            guru_id=guru.id,
            accession_number="ACC-Q4",
            report_date="2024-12-31",
            filing_date="2025-02-14",
            total_value=1_000_000.0,
            holdings_count=1,
        ),
    )
    filing_q1 = save_filing(
        db_session,
        GuruFiling(
            guru_id=guru.id,
            accession_number="ACC-Q1",
            report_date="2025-03-31",
            filing_date="2025-05-15",
            total_value=1_100_000.0,
            holdings_count=1,
        ),
    )
    save_holdings_batch(
        db_session,
        [
            GuruHolding(
                filing_id=filing_q4.id,
                guru_id=guru.id,
                cusip="CUSIP-AAPL",
                ticker="AAPL",
                company_name="Apple Inc",
                value=1_000_000.0,
                shares=10_000.0,
                action="INCREASED",
                change_pct=25.0,
                weight_pct=100.0,
                sector="Technology",
            ),
            GuruHolding(
                filing_id=filing_q1.id,
                guru_id=guru.id,
                cusip="CUSIP-AAPL",
                ticker="AAPL",
                company_name="Apple Inc",
                value=1_100_000.0,
                shares=11_000.0,
                action="INCREASED",
                change_pct=10.0,
                weight_pct=100.0,
                sector="Technology",
            ),
        ],
    )
    return guru


def _mock_download_frame():
    idx = pd.to_datetime(["2025-02-14", "2025-03-14", "2025-05-15", "2025-06-16"])
    aapl = pd.DataFrame({"Close": [100.0, 104.0, 110.0, 113.0]}, index=idx)
    spy = pd.DataFrame({"Close": [200.0, 203.0, 210.0, 211.0]}, index=idx)
    return pd.concat({"AAPL": aapl, "SPY": spy}, axis=1)


def _mock_download_frame_without_benchmark():
    idx = pd.to_datetime(["2025-02-14", "2025-03-14", "2025-05-15", "2025-06-16"])
    aapl = pd.DataFrame({"Close": [100.0, 104.0, 110.0, 113.0]}, index=idx)
    return pd.concat({"AAPL": aapl}, axis=1)


def test_get_heatmap_should_return_items_with_action_breakdown_and_guru_details(
    db_session,
):
    _seed_guru_with_two_filings(db_session)

    invalidate_heatmap_cache()
    payload = get_heatmap(db_session, style=None, lang="en")

    assert payload["report_date"] == "2025-03-31"
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["ticker"] == "AAPL"
    assert item["action_breakdown"]["INCREASED"] >= 1
    assert item["gurus"][0]["guru_display_name"] == "Buffett"


def test_get_guru_backtest_should_return_quarters_and_cumulative_series(db_session):
    guru = _seed_guru_with_two_filings(db_session)

    invalidate_guru_backtest_cache()
    with patch(
        "application.guru.backtest_service.yf.download",
        return_value=_mock_download_frame(),
    ):
        payload = get_guru_backtest(
            session=db_session,
            guru_id=guru.id,
            quarters=2,
            benchmark="SPY",
            lang="en",
        )

    assert payload is not None
    assert payload["guru_id"] == guru.id
    assert payload["benchmark"] == "SPY"
    assert len(payload["quarters"]) == 2
    assert payload["quarters"][0]["top5_holdings"][0] == "AAPL"
    assert len(payload["cumulative_series"]["dates"]) > 0


def test_get_guru_backtest_should_raise_when_not_enough_filings(db_session):
    guru = save_guru(
        db_session,
        Guru(name="Bridgewater", cik="0001350694", display_name="Ray Dalio"),
    )
    save_filing(
        db_session,
        GuruFiling(
            guru_id=guru.id,
            accession_number="ACC-ONLY",
            report_date="2024-12-31",
            filing_date="2025-02-14",
            total_value=100.0,
            holdings_count=1,
        ),
    )

    with (
        patch(
            "application.guru.backtest_service.yf.download",
            return_value=_mock_download_frame(),
        ),
        pytest.raises(ValueError, match="not_enough_filings"),
    ):
        get_guru_backtest(
            session=db_session,
            guru_id=guru.id,
            quarters=2,
            benchmark="SPY",
            lang="en",
        )


def test_get_guru_backtest_should_raise_when_benchmark_data_missing(db_session):
    guru = _seed_guru_with_two_filings(db_session)

    invalidate_guru_backtest_cache()
    with (
        patch(
            "application.guru.backtest_service.yf.download",
            return_value=_mock_download_frame_without_benchmark(),
        ),
        pytest.raises(ValueError, match="benchmark_data_missing"),
    ):
        get_guru_backtest(
            session=db_session,
            guru_id=guru.id,
            quarters=2,
            benchmark="SPY",
            lang="en",
        )
