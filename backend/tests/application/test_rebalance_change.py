"""Tests for portfolio-level daily change calculation in rebalance_service."""

import json
from unittest.mock import patch

import pytest
from sqlmodel import Session

from application.rebalance_service import calculate_rebalance
from domain.entities import Holding, UserInvestmentProfile, UserPreferences
from domain.enums import StockCategory


class TestRebalancePortfolioChange:
    """Tests for portfolio-level daily change calculation."""

    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.prewarm_signals_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.get_etf_top_holdings", return_value=None)
    @patch("application.rebalance_service.get_etf_sector_weights", return_value=None)
    def test_calculate_rebalance_should_include_total_change(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)

        holding = Holding(
            user_id="default",
            ticker="NVDA",
            category=StockCategory.GROWTH,
            quantity=10.0,
            cost_basis=100.0,
            currency="USD",
            is_cash=False,
        )
        db_session.add(holding)
        db_session.commit()

        # Mock signals with current and previous price
        mock_signals.return_value = {
            "price": 120.0,
            "previous_close": 110.0,
            "change_pct": 9.09,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        assert "total_value" in result
        assert "previous_total_value" in result
        assert "total_value_change" in result
        assert "total_value_change_pct" in result

        # Current: 10 * 120 = 1200
        # Previous: 10 * 110 = 1100
        # Change: 1200 - 1100 = 100
        # Change %: (100 / 1100) * 100 = 9.09%
        assert result["total_value"] == pytest.approx(1200.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(1100.0, rel=0.01)
        assert result["total_value_change"] == pytest.approx(100.0, rel=0.01)
        assert result["total_value_change_pct"] == pytest.approx(9.09, rel=0.01)

    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.prewarm_signals_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.get_etf_top_holdings", return_value=None)
    @patch("application.rebalance_service.get_etf_sector_weights", return_value=None)
    def test_calculate_rebalance_should_include_holding_change_pct(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)

        holding = Holding(
            user_id="default",
            ticker="AAPL",
            category=StockCategory.GROWTH,
            quantity=5.0,
            cost_basis=150.0,
            currency="USD",
            is_cash=False,
        )
        db_session.add(holding)
        db_session.commit()

        # Mock signals
        mock_signals.return_value = {
            "price": 180.0,
            "previous_close": 175.0,
            "change_pct": 2.86,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        assert "holdings_detail" in result
        assert len(result["holdings_detail"]) == 1

        holding_detail = result["holdings_detail"][0]
        assert "change_pct" in holding_detail

        # Current MV: 5 * 180 = 900
        # Previous MV: 5 * 175 = 875
        # Change %: (900 - 875) / 875 * 100 = 2.86%
        assert holding_detail["change_pct"] == pytest.approx(2.86, rel=0.01)

    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.prewarm_signals_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.get_etf_top_holdings", return_value=None)
    @patch("application.rebalance_service.get_etf_sector_weights", return_value=None)
    def test_calculate_rebalance_should_handle_missing_previous_close(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange: New stock with no previous_close
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)

        holding = Holding(
            user_id="default",
            ticker="NEW",
            category=StockCategory.GROWTH,
            quantity=10.0,
            cost_basis=50.0,
            currency="USD",
            is_cash=False,
        )
        db_session.add(holding)
        db_session.commit()

        # Mock signals with no previous_close (newly added stock)
        mock_signals.return_value = {
            "price": 55.0,
            "previous_close": None,
            "change_pct": None,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert — no previous_close: holding change_pct is None (N/A in UI)
        # Portfolio-level totals still balance (prev_mv falls back to mv)
        holding_detail = result["holdings_detail"][0]
        assert result["total_value"] == pytest.approx(550.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(550.0, rel=0.01)
        assert holding_detail["change_pct"] is None

    @patch("application.rebalance_service.get_exchange_rates")
    def test_calculate_rebalance_should_handle_zero_previous_total_value(
        self, mock_fx, db_session: Session
    ):
        # Arrange: Portfolio with cash only (no price change)
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Cash": 100}),
            is_active=True,
        )
        db_session.add(profile)

        holding = Holding(
            user_id="default",
            ticker="USD",
            category=StockCategory.CASH,
            quantity=1000.0,
            currency="USD",
            is_cash=True,
        )
        db_session.add(holding)
        db_session.commit()

        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        # Cash has no change (same current and previous)
        assert result["total_value"] == pytest.approx(1000.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(1000.0, rel=0.01)
        assert result["total_value_change"] == pytest.approx(0.0, rel=0.01)
        assert result["total_value_change_pct"] == pytest.approx(0.0, rel=0.01)

    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.prewarm_signals_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.get_etf_top_holdings", return_value=None)
    @patch("application.rebalance_service.get_etf_sector_weights", return_value=None)
    def test_calculate_rebalance_should_aggregate_multiple_holdings_change(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange: Multiple holdings with different changes
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)

        holding1 = Holding(
            user_id="default",
            ticker="NVDA",
            category=StockCategory.GROWTH,
            quantity=10.0,
            cost_basis=100.0,
            currency="USD",
            is_cash=False,
        )
        db_session.add(holding1)

        holding2 = Holding(
            user_id="default",
            ticker="AAPL",
            category=StockCategory.GROWTH,
            quantity=5.0,
            cost_basis=150.0,
            currency="USD",
            is_cash=False,
        )
        db_session.add(holding2)
        db_session.commit()

        # Mock signals for both holdings
        def mock_signals_side_effect(ticker):
            if ticker == "NVDA":
                return {
                    "price": 120.0,
                    "previous_close": 110.0,
                    "change_pct": 9.09,
                }
            elif ticker == "AAPL":
                return {
                    "price": 170.0,
                    "previous_close": 180.0,
                    "change_pct": -5.56,
                }
            return None

        mock_signals.side_effect = mock_signals_side_effect
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        # NVDA: current = 10 * 120 = 1200, previous = 10 * 110 = 1100
        # AAPL: current = 5 * 170 = 850, previous = 5 * 180 = 900
        # Total: current = 2050, previous = 2000
        # Change: (2050 - 2000) / 2000 * 100 = 2.5%
        assert result["total_value"] == pytest.approx(2050.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(2000.0, rel=0.01)
        assert result["total_value_change"] == pytest.approx(50.0, rel=0.01)
        assert result["total_value_change_pct"] == pytest.approx(2.5, rel=0.01)

        # Check individual holdings
        holdings = result["holdings_detail"]
        nvda_holding = next(h for h in holdings if h["ticker"] == "NVDA")
        aapl_holding = next(h for h in holdings if h["ticker"] == "AAPL")

        assert nvda_holding["change_pct"] == pytest.approx(9.09, rel=0.01)
        assert aapl_holding["change_pct"] == pytest.approx(-5.56, rel=0.01)


class TestRebalanceAdviceTranslation:
    """Application-layer step 5.5: advice must be list[str], not list[dict]."""

    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.prewarm_signals_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.get_etf_top_holdings", return_value=None)
    @patch("application.rebalance_service.get_etf_sector_weights", return_value=None)
    def test_advice_is_list_of_strings_when_balanced(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange — perfectly balanced portfolio: Growth 50% / Bond 50%
        db_session.add(UserPreferences(user_id="default", language="en"))
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 50, "Bond": 50}),
            is_active=True,
        )
        db_session.add(profile)
        for ticker, category in [
            ("NVDA", StockCategory.GROWTH),
            ("BND", StockCategory.BOND),
        ]:
            db_session.add(
                Holding(
                    user_id="default",
                    ticker=ticker,
                    category=category,
                    quantity=10.0,
                    cost_basis=100.0,
                    currency="USD",
                    is_cash=False,
                )
            )
        db_session.commit()

        mock_signals.return_value = {
            "price": 100.0,
            "previous_close": 100.0,
            "change_pct": 0.0,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert — translated strings, not raw dicts
        advice = result["advice"]
        assert isinstance(advice, list)
        assert len(advice) >= 1
        assert all(
            isinstance(a, str) for a in advice
        ), f"Expected list[str], got: {advice}"
        assert any("No rebalancing needed" in a for a in advice)

    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.prewarm_signals_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.get_etf_top_holdings", return_value=None)
    @patch("application.rebalance_service.get_etf_sector_weights", return_value=None)
    def test_advice_is_list_of_strings_when_overweight(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange — Growth 80% vs target 50%: clear overweight drift
        db_session.add(UserPreferences(user_id="default", language="en"))
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 50, "Bond": 50}),
            is_active=True,
        )
        db_session.add(profile)
        db_session.add(
            Holding(
                user_id="default",
                ticker="NVDA",
                category=StockCategory.GROWTH,
                quantity=80.0,
                cost_basis=1.0,
                currency="USD",
                is_cash=False,
            )
        )
        db_session.add(
            Holding(
                user_id="default",
                ticker="BND",
                category=StockCategory.BOND,
                quantity=20.0,
                cost_basis=1.0,
                currency="USD",
                is_cash=False,
            )
        )
        db_session.commit()

        mock_signals.return_value = {
            "price": 1.0,
            "previous_close": 1.0,
            "change_pct": 0.0,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert — translated strings, not raw dicts
        advice = result["advice"]
        assert isinstance(advice, list)
        assert len(advice) >= 1
        assert all(
            isinstance(a, str) for a in advice
        ), f"Expected list[str], got: {advice}"
        assert any("overweight" in a.lower() for a in advice)
