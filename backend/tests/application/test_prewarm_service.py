"""Tests for startup cache prewarm service."""

from unittest.mock import patch

from sqlmodel import Session

from application.prewarm_service import _collect_tickers, prewarm_all_caches
from domain.entities import Holding, Stock
from domain.enums import StockCategory


# ---------------------------------------------------------------------------
# _collect_tickers
# ---------------------------------------------------------------------------


class TestCollectTickers:
    """Tests for the ticker collection logic."""

    def test_should_return_empty_when_no_stocks_or_holdings(self, db_session: Session):
        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            result = _collect_tickers()

        # Assert
        assert result["all"] == []
        assert result["signals"] == []
        assert result["moat"] == []
        assert result["etf"] == []
        assert result["beta"] == []

    def test_should_collect_active_stocks(self, db_session: Session):
        # Arrange
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI leader",
            )
        )
        db_session.add(
            Stock(
                ticker="MSFT",
                category=StockCategory.GROWTH,
                current_thesis="Cloud",
            )
        )
        db_session.commit()

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            result = _collect_tickers()

        # Assert
        assert sorted(result["all"]) == ["MSFT", "NVDA"]
        assert sorted(result["signals"]) == ["MSFT", "NVDA"]
        assert sorted(result["moat"]) == ["MSFT", "NVDA"]
        assert sorted(result["beta"]) == ["MSFT", "NVDA"]

    def test_should_exclude_cash_from_signals(self, db_session: Session):
        # Arrange
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI",
            )
        )
        db_session.add(
            Stock(
                ticker="USD",
                category=StockCategory.CASH,
                current_thesis="Cash",
            )
        )
        db_session.commit()

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            result = _collect_tickers()

        # Assert
        assert "USD" in result["all"]
        assert "USD" not in result["signals"]
        assert "NVDA" in result["signals"]
        assert "USD" not in result["beta"]
        assert "NVDA" in result["beta"]

    def test_should_exclude_bond_and_cash_from_moat(self, db_session: Session):
        # Arrange
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI",
            )
        )
        db_session.add(
            Stock(
                ticker="TLT",
                category=StockCategory.BOND,
                current_thesis="Treasury",
            )
        )
        db_session.add(
            Stock(
                ticker="USD",
                category=StockCategory.CASH,
                current_thesis="Cash",
            )
        )
        db_session.commit()

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            result = _collect_tickers()

        # Assert
        assert "TLT" not in result["moat"]
        assert "USD" not in result["moat"]
        assert "NVDA" in result["moat"]

    def test_should_identify_etf_tickers(self, db_session: Session):
        # Arrange
        db_session.add(
            Stock(
                ticker="VTI",
                category=StockCategory.TREND_SETTER,
                current_thesis="US Market",
                is_etf=True,
            )
        )
        db_session.add(
            Stock(
                ticker="MSFT",
                category=StockCategory.TREND_SETTER,
                current_thesis="Cloud",
                is_etf=False,
            )
        )
        db_session.commit()

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            result = _collect_tickers()

        # Assert
        assert result["etf"] == ["VTI"]
        assert "MSFT" not in result["etf"]

    def test_should_union_watchlist_and_holdings(self, db_session: Session):
        # Arrange — NVDA in watchlist, AAPL only in holdings
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI",
            )
        )
        db_session.add(
            Holding(
                ticker="NVDA",
                category=StockCategory.MOAT,
                quantity=10,
                cost_basis=120.0,
            )
        )
        db_session.add(
            Holding(
                ticker="AAPL",
                category=StockCategory.GROWTH,
                quantity=5,
                cost_basis=180.0,
            )
        )
        db_session.commit()

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            result = _collect_tickers()

        # Assert — both should appear
        assert "NVDA" in result["all"]
        assert "AAPL" in result["all"]
        assert "NVDA" in result["beta"]
        assert "AAPL" in result["beta"]

    def test_should_exclude_cash_holdings(self, db_session: Session):
        # Arrange — cash holding should be excluded
        db_session.add(
            Holding(
                ticker="USD",
                category=StockCategory.CASH,
                quantity=50000,
                is_cash=True,
            )
        )
        db_session.add(
            Holding(
                ticker="NVDA",
                category=StockCategory.MOAT,
                quantity=10,
                cost_basis=120.0,
            )
        )
        db_session.commit()

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            result = _collect_tickers()

        # Assert — USD cash holding excluded, NVDA included
        assert "USD" not in result["all"]
        assert "NVDA" in result["all"]
        assert "USD" not in result["beta"]
        assert "NVDA" in result["beta"]

    def test_should_skip_inactive_stocks(self, db_session: Session):
        # Arrange
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI",
                is_active=True,
            )
        )
        db_session.add(
            Stock(
                ticker="INTC",
                category=StockCategory.MOAT,
                current_thesis="Old chip",
                is_active=False,
            )
        )
        db_session.commit()

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            result = _collect_tickers()

        # Assert
        assert "NVDA" in result["all"]
        assert "INTC" not in result["all"]


# ---------------------------------------------------------------------------
# prewarm_all_caches
# ---------------------------------------------------------------------------


class TestPrewarmAllCaches:
    """Tests for the orchestration function."""

    @patch("application.prewarm_service.get_ticker_sector")
    @patch("application.prewarm_service.prewarm_beta_batch")
    @patch("application.prewarm_service.prewarm_etf_holdings_batch")
    @patch("application.prewarm_service.prewarm_moat_batch")
    @patch("application.prewarm_service.get_fear_greed_index")
    @patch("application.prewarm_service.prewarm_signals_batch")
    def test_happy_path_should_call_all_phases(
        self,
        mock_signals,
        mock_fg,
        mock_moat,
        mock_etf,
        mock_beta,
        mock_sector,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI",
                is_etf=False,
            )
        )
        db_session.add(
            Stock(
                ticker="VTI",
                category=StockCategory.TREND_SETTER,
                current_thesis="ETF",
                is_etf=True,
            )
        )
        db_session.commit()

        mock_signals.return_value = {}
        mock_fg.return_value = {}
        mock_moat.return_value = {}
        mock_etf.return_value = {}
        mock_beta.return_value = {}
        mock_sector.return_value = "Technology"

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            prewarm_all_caches()

        # Assert
        mock_signals.assert_called_once()
        mock_fg.assert_called_once()
        mock_moat.assert_called_once()
        mock_etf.assert_called_once()
        mock_beta.assert_called_once()

        # Phase 7: sector prewarm called for moat tickers (NVDA + VTI)
        sector_tickers = sorted(c.args[0] for c in mock_sector.call_args_list)
        assert "NVDA" in sector_tickers
        assert "VTI" in sector_tickers

        # Verify correct tickers passed
        signals_tickers = sorted(mock_signals.call_args[0][0])
        assert "NVDA" in signals_tickers
        assert "VTI" in signals_tickers

        moat_tickers = sorted(mock_moat.call_args[0][0])
        assert "NVDA" in moat_tickers
        assert "VTI" in moat_tickers  # Trend_Setter is not in SKIP_MOAT_CATEGORIES

        etf_tickers = sorted(mock_etf.call_args[0][0])
        assert etf_tickers == ["VTI"]

        beta_tickers = sorted(mock_beta.call_args[0][0])
        assert "NVDA" in beta_tickers
        assert "VTI" in beta_tickers

    @patch("application.prewarm_service.get_ticker_sector")
    @patch("application.prewarm_service.prewarm_beta_batch")
    @patch("application.prewarm_service.prewarm_etf_holdings_batch")
    @patch("application.prewarm_service.prewarm_moat_batch")
    @patch("application.prewarm_service.get_fear_greed_index")
    @patch("application.prewarm_service.prewarm_signals_batch")
    def test_empty_db_should_skip_all_phases(
        self,
        mock_signals,
        mock_fg,
        mock_moat,
        mock_etf,
        mock_beta,
        mock_sector,
        db_session: Session,
    ):
        # Act — empty DB
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            prewarm_all_caches()

        # Assert — no prewarm functions called
        mock_signals.assert_not_called()
        mock_fg.assert_not_called()
        mock_moat.assert_not_called()
        mock_etf.assert_not_called()
        mock_beta.assert_not_called()
        mock_sector.assert_not_called()

    @patch("application.prewarm_service.get_ticker_sector")
    @patch("application.prewarm_service.prewarm_beta_batch")
    @patch("application.prewarm_service.prewarm_etf_holdings_batch")
    @patch("application.prewarm_service.prewarm_moat_batch")
    @patch("application.prewarm_service.get_fear_greed_index")
    @patch("application.prewarm_service.prewarm_signals_batch")
    def test_partial_failure_should_not_block_other_phases(
        self,
        mock_signals,
        mock_fg,
        mock_moat,
        mock_etf,
        mock_beta,
        mock_sector,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI",
            )
        )
        db_session.commit()

        # Signals phase fails
        mock_signals.side_effect = RuntimeError("yfinance 爆炸")
        mock_fg.return_value = {}
        mock_moat.return_value = {}
        mock_beta.return_value = {}
        mock_sector.return_value = "Technology"

        # Act — should NOT raise
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            prewarm_all_caches()

        # Assert — subsequent phases still called
        mock_signals.assert_called_once()
        mock_fg.assert_called_once()
        mock_moat.assert_called_once()
        mock_beta.assert_called_once()
        mock_sector.assert_called_once()  # sector prewarm still runs

    @patch("application.prewarm_service.get_ticker_sector")
    @patch("application.prewarm_service.prewarm_beta_batch")
    @patch("application.prewarm_service.prewarm_etf_holdings_batch")
    @patch("application.prewarm_service.prewarm_moat_batch")
    @patch("application.prewarm_service.get_fear_greed_index")
    @patch("application.prewarm_service.prewarm_signals_batch")
    def test_no_etf_should_skip_etf_phase(
        self,
        mock_signals,
        mock_fg,
        mock_moat,
        mock_etf,
        mock_beta,
        mock_sector,
        db_session: Session,
    ):
        # Arrange — no ETFs
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI",
                is_etf=False,
            )
        )
        db_session.commit()

        mock_signals.return_value = {}
        mock_fg.return_value = {}
        mock_moat.return_value = {}
        mock_beta.return_value = {}
        mock_sector.return_value = "Technology"

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            prewarm_all_caches()

        # Assert — ETF phase skipped, beta still called
        mock_etf.assert_not_called()
        mock_beta.assert_called_once()

    @patch("application.prewarm_service.get_ticker_sector")
    @patch("application.prewarm_service.prewarm_beta_batch")
    @patch("application.prewarm_service.prewarm_etf_holdings_batch")
    @patch("application.prewarm_service.prewarm_moat_batch")
    @patch("application.prewarm_service.get_fear_greed_index")
    @patch("application.prewarm_service.prewarm_signals_batch")
    def test_cash_stocks_should_be_excluded_from_signals_and_moat(
        self,
        mock_signals,
        mock_fg,
        mock_moat,
        mock_etf,
        mock_beta,
        mock_sector,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Stock(
                ticker="USD",
                category=StockCategory.CASH,
                current_thesis="Cash",
            )
        )
        db_session.add(
            Stock(
                ticker="NVDA",
                category=StockCategory.MOAT,
                current_thesis="AI",
            )
        )
        db_session.commit()

        mock_signals.return_value = {}
        mock_fg.return_value = {}
        mock_moat.return_value = {}
        mock_beta.return_value = {}
        mock_sector.return_value = "Technology"

        # Act
        with patch("application.prewarm_service.engine", db_session.get_bind()):
            prewarm_all_caches()

        # Assert
        signals_tickers = mock_signals.call_args[0][0]
        moat_tickers = mock_moat.call_args[0][0]
        beta_tickers = mock_beta.call_args[0][0]

        assert "USD" not in signals_tickers
        assert "USD" not in moat_tickers
        assert "USD" not in beta_tickers
        assert "NVDA" in signals_tickers
        assert "NVDA" in moat_tickers
        assert "NVDA" in beta_tickers

        # Sector prewarm uses moat tickers (excludes Cash)
        sector_tickers = [c.args[0] for c in mock_sector.call_args_list]
        assert "USD" not in sector_tickers
        assert "NVDA" in sector_tickers
