"""Tests for ETF exclusion from market sentiment calculation."""

from unittest.mock import patch

from sqlmodel import Session

from application.scan.scan_service import run_scan
from domain.entities import Stock
from domain.enums import StockCategory


@patch("application.scan.scan_service.batch_download_history", new=lambda *a, **kw: {})
class TestETFExclusionFromSentiment:
    """ETFs flagged with is_etf=True should be excluded from Layer 1 sentiment."""

    @patch("application.scan.scan_service.send_telegram_message_dual")
    @patch("application.scan.scan_service.get_fear_greed_index")
    @patch("application.scan.scan_service.analyze_moat_trend")
    @patch("application.scan.scan_service.get_technical_signals")
    @patch("application.scan.scan_service.analyze_market_sentiment")
    def test_run_scan_should_exclude_etf_from_sentiment_tickers(
        self,
        mock_sentiment,
        mock_signals,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ):
        """ETF Trend_Setter stocks should NOT be passed to analyze_market_sentiment."""
        # Arrange — create individual stock + ETF
        db_session.add(
            Stock(
                ticker="MSFT",
                category=StockCategory.TREND_SETTER,
                current_thesis="Cloud",
                is_etf=False,
            )
        )
        db_session.add(
            Stock(
                ticker="VTI",
                category=StockCategory.TREND_SETTER,
                current_thesis="US Market ETF",
                is_etf=True,
            )
        )
        db_session.commit()

        mock_sentiment.return_value = {
            "status": "BULLISH",
            "details": "test",
            "below_60ma_pct": 0.0,
        }
        mock_fg.return_value = {
            "composite_score": 50,
            "composite_level": "NEUTRAL",
            "fetched_at": "2025-01-01T00:00:00+00:00",
        }
        mock_signals.return_value = {
            "ticker": "MSFT",
            "price": 400.0,
            "previous_close": 395.0,
            "change_pct": 1.27,
            "rsi": 55.0,
            "ma200": 350.0,
            "ma60": 380.0,
            "bias": 5.0,
            "volume_ratio": 1.0,
            "status": [],
        }
        mock_moat.return_value = {"moat": "護城河穩固", "details": "ok"}

        # Act
        run_scan(db_session)

        # Assert — VTI should NOT be in the ticker list passed to sentiment
        mock_sentiment.assert_called_once()
        ticker_list = mock_sentiment.call_args[0][0]
        assert "MSFT" in ticker_list
        assert "VTI" not in ticker_list

    @patch("application.scan.scan_service.send_telegram_message_dual")
    @patch("application.scan.scan_service.get_fear_greed_index")
    @patch("application.scan.scan_service.analyze_moat_trend")
    @patch("application.scan.scan_service.get_technical_signals")
    @patch("application.scan.scan_service.analyze_market_sentiment")
    def test_run_scan_should_include_non_etf_trend_setters(
        self,
        mock_sentiment,
        mock_signals,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ):
        """Non-ETF Trend_Setter stocks should still be passed to sentiment."""
        # Arrange — two non-ETF trend setters
        db_session.add(
            Stock(
                ticker="MSFT",
                category=StockCategory.TREND_SETTER,
                current_thesis="Cloud",
                is_etf=False,
            )
        )
        db_session.add(
            Stock(
                ticker="GOOGL",
                category=StockCategory.TREND_SETTER,
                current_thesis="Search",
                is_etf=False,
            )
        )
        db_session.commit()

        mock_sentiment.return_value = {
            "status": "BULLISH",
            "details": "test",
            "below_60ma_pct": 0.0,
        }
        mock_fg.return_value = {
            "composite_score": 50,
            "composite_level": "NEUTRAL",
            "fetched_at": "2025-01-01T00:00:00+00:00",
        }
        mock_signals.return_value = {
            "ticker": "MSFT",
            "price": 400.0,
            "previous_close": 395.0,
            "change_pct": 1.27,
            "rsi": 55.0,
            "ma200": 350.0,
            "ma60": 380.0,
            "bias": 5.0,
            "volume_ratio": 1.0,
            "status": [],
        }
        mock_moat.return_value = {"moat": "護城河穩固", "details": "ok"}

        # Act
        run_scan(db_session)

        # Assert — both non-ETF stocks should be in sentiment ticker list
        mock_sentiment.assert_called_once()
        ticker_list = mock_sentiment.call_args[0][0]
        assert "MSFT" in ticker_list
        assert "GOOGL" in ticker_list
