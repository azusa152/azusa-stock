import datetime

import pandas as pd
import pytest
from unittest.mock import patch

from infrastructure.market_data import _safe_loc, _fetch_moat_from_yf
from domain.enums import MoatStatus

NOT_AVAILABLE = MoatStatus.NOT_AVAILABLE.value


class TestSafeLoc:
    def test_first_label_found(self):
        df = pd.DataFrame({"Q1": [100]}, index=["Gross Profit"])
        assert _safe_loc(df, ["Gross Profit", "Other"], "Q1") == 100.0

    def test_fallback_label(self):
        df = pd.DataFrame({"Q1": [200]}, index=["Operating Revenue"])
        assert _safe_loc(df, ["Total Revenue", "Operating Revenue"], "Q1") == 200.0

    def test_all_labels_missing(self):
        df = pd.DataFrame({"Q1": [100]}, index=["Something Else"])
        assert _safe_loc(df, ["Gross Profit"], "Q1") is None

    def test_nan_skipped(self):
        df = pd.DataFrame({"Q1": [float("nan")]}, index=["Gross Profit"])
        assert _safe_loc(df, ["Gross Profit"], "Q1") is None

    def test_nan_skipped_falls_back_to_next_label(self):
        df = pd.DataFrame(
            {"Q1": [float("nan"), 500.0]}, index=["Total Revenue", "Operating Revenue"]
        )
        assert _safe_loc(df, ["Total Revenue", "Operating Revenue"], "Q1") == 500.0

    def test_returns_float(self):
        df = pd.DataFrame({"Q1": [42]}, index=["Revenue"])
        result = _safe_loc(df, ["Revenue"], "Q1")
        assert isinstance(result, float)
        assert result == 42.0


class TestFetchMoatFromYf:
    def _make_df(self, rows: dict, cols: list) -> pd.DataFrame:
        return pd.DataFrame(
            rows,
            index=list(rows.keys())
            if not isinstance(list(rows.keys())[0], str)
            else list(rows.keys()),
        )

    @patch("infrastructure.market_data._yf_quarterly_financials")
    def test_standard_labels_returns_correct_margin(self, mock_financials):
        cols = [datetime.date(2025, 12, 31), datetime.date(2024, 12, 31)]
        df = pd.DataFrame(
            {cols[0]: [30, 100], cols[1]: [28, 95]},
            index=["Gross Profit", "Total Revenue"],
        )
        mock_financials.return_value = df

        result = _fetch_moat_from_yf("AAPL")
        assert result["moat"] != NOT_AVAILABLE
        assert result["current_margin"] == pytest.approx(30.0)

    @patch("infrastructure.market_data._yf_quarterly_financials")
    def test_jp_company_with_operating_revenue(self, mock_financials):
        """J-GAAP companies may use 'Operating Revenue' instead of 'Total Revenue'."""
        cols = [datetime.date(2025, 12, 31), datetime.date(2024, 12, 31)]
        df = pd.DataFrame(
            {cols[0]: [30, 100], cols[1]: [28, 95]},
            index=["Gross Profit", "Operating Revenue"],
        )
        mock_financials.return_value = df

        result = _fetch_moat_from_yf("7203.T")
        assert result["moat"] != NOT_AVAILABLE
        assert result["current_margin"] is not None

    @patch("infrastructure.market_data._yf_quarterly_financials")
    def test_missing_gross_profit_returns_not_available(self, mock_financials):
        cols = [datetime.date(2025, 12, 31), datetime.date(2024, 12, 31)]
        df = pd.DataFrame(
            {cols[0]: [100], cols[1]: [95]},
            index=["Total Revenue"],
        )
        mock_financials.return_value = df

        result = _fetch_moat_from_yf("7203.T")
        assert result["moat"] == NOT_AVAILABLE

    @patch("infrastructure.market_data._yf_quarterly_financials")
    def test_nan_gross_profit_returns_not_available(self, mock_financials):
        cols = [datetime.date(2025, 12, 31), datetime.date(2024, 12, 31)]
        df = pd.DataFrame(
            {cols[0]: [float("nan"), 100], cols[1]: [float("nan"), 95]},
            index=["Gross Profit", "Total Revenue"],
        )
        mock_financials.return_value = df

        result = _fetch_moat_from_yf("7203.T")
        assert result["moat"] == NOT_AVAILABLE

    @patch("infrastructure.market_data._yf_quarterly_financials")
    def test_empty_dataframe_returns_not_available(self, mock_financials):
        mock_financials.return_value = pd.DataFrame()

        result = _fetch_moat_from_yf("7203.T")
        assert result["moat"] == NOT_AVAILABLE
