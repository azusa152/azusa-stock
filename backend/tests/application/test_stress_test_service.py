"""Tests for stress test application service (orchestration logic)."""

from unittest.mock import patch

import pytest
from sqlmodel import Session

from application.portfolio.stress_test_service import calculate_stress_test
from application.stock.stock_service import StockNotFoundError
from domain.entities import Holding
from domain.enums import StockCategory

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------


def _make_fx_rates_mock(base_currency: str = "USD") -> dict[str, float]:
    """Mock FX rates with USD as base."""
    return {
        "USD": 1.0,
        "TWD": 32.0,
        "JPY": 150.0,
    }


def _mock_compute_holding_market_values(holdings, fx_rates):
    """Mock _compute_holding_market_values to return simplified data.

    FX rates are quotations: fx_rates["TWD"] = 32.0 means 1 USD = 32 TWD.
    To convert TWD to USD, divide by the FX rate.

    Note: This mock uses inverted FX convention (divide by rate) for test simplicity.
    The real get_exchange_rates from infrastructure.market_data returns rates where
    you multiply by the rate to convert to display currency. This divergence is
    intentional to keep test setup simple and isolated from infrastructure changes.
    """
    currency_values = {}
    cash_currency_values = {}
    ticker_agg = {}

    for h in holdings:
        cat = h.category.value if hasattr(h.category, "value") else str(h.category)
        # FX rate: how many units of h.currency equals 1 USD
        # To convert to USD, divide by FX rate
        fx = fx_rates.get(h.currency, 1.0)

        if h.is_cash:
            # Cash: quantity is already in the currency
            market_value = h.quantity / fx  # Convert to USD
            price = 1.0
        else:
            # Use cost_basis as fallback price
            price = h.cost_basis if h.cost_basis else 100.0
            # price is in h.currency, need to convert to USD
            market_value = h.quantity * price / fx

        currency_values[h.currency] = (
            currency_values.get(h.currency, 0.0) + market_value
        )

        if h.is_cash:
            cash_currency_values[h.currency] = (
                cash_currency_values.get(h.currency, 0.0) + market_value
            )

        key = h.ticker
        if key not in ticker_agg:
            ticker_agg[key] = {
                "category": cat,
                "currency": h.currency,
                "qty": 0.0,
                "mv": 0.0,
                "prev_mv": 0.0,
                "cost_sum": 0.0,
                "cost_qty": 0.0,
                "price": price,
                "fx": fx,
                "has_prev_close": False,
            }
        ticker_agg[key]["qty"] += h.quantity
        ticker_agg[key]["mv"] += market_value
        ticker_agg[key]["prev_mv"] += market_value

    return currency_values, cash_currency_values, ticker_agg


# ---------------------------------------------------------------------------
# Happy Path
# ---------------------------------------------------------------------------


class TestCalculateStressTestHappyPath:
    """Tests for stress test service happy path."""

    @patch("application.portfolio.stress_test_service.prewarm_beta_batch")
    @patch("application.portfolio.stress_test_service.get_stock_beta")
    @patch("application.portfolio.stress_test_service._compute_holding_market_values")
    @patch("application.portfolio.stress_test_service.get_exchange_rates")
    def test_simple_portfolio_should_calculate_stress_test(
        self,
        mock_fx,
        mock_compute_mv,
        mock_beta,
        mock_prewarm,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Holding(
                ticker="NVDA",
                category=StockCategory.GROWTH,
                quantity=100,
                cost_basis=150.0,  # Will be used as price
                currency="USD",
            )
        )
        db_session.commit()

        mock_fx.return_value = _make_fx_rates_mock("USD")
        mock_compute_mv.side_effect = _mock_compute_holding_market_values
        mock_beta.return_value = 1.8

        # Act
        result = calculate_stress_test(db_session, -20.0, "USD")

        # Assert
        assert result["portfolio_beta"] == 1.8
        assert result["scenario_drop_pct"] == -20.0
        assert result["total_value"] == 15000.0  # 100 * 150
        assert result["total_loss"] == -5400.0  # 15000 * (-20%) * 1.8
        assert result["total_loss_pct"] == -36.0
        assert result["pain_level"]["level"] == "panic"
        assert result["display_currency"] == "USD"
        assert len(result["holdings_breakdown"]) == 1
        assert result["holdings_breakdown"][0]["ticker"] == "NVDA"

        # Verify prewarm was called
        mock_prewarm.assert_called_once()

    @patch("application.portfolio.stress_test_service.prewarm_beta_batch")
    @patch("application.portfolio.stress_test_service.get_stock_beta")
    @patch("application.portfolio.stress_test_service._compute_holding_market_values")
    @patch("application.portfolio.stress_test_service.get_exchange_rates")
    def test_mixed_portfolio_with_currency_conversion(
        self,
        mock_fx,
        mock_compute_mv,
        mock_beta,
        mock_prewarm,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Holding(
                ticker="NVDA",
                category=StockCategory.GROWTH,
                quantity=100,
                cost_basis=150.0,
                currency="USD",
            )
        )
        db_session.add(
            Holding(
                ticker="2330.TW",
                category=StockCategory.MOAT,
                quantity=1000,
                cost_basis=600.0,
                currency="TWD",
            )
        )
        db_session.commit()

        mock_fx.return_value = {"USD": 1.0, "TWD": 32.0}  # 32 TWD = 1 USD
        mock_compute_mv.side_effect = _mock_compute_holding_market_values

        def beta_side_effect(ticker):
            if ticker == "NVDA":
                return 1.8
            elif ticker == "2330.TW":
                return 1.2
            return None

        mock_beta.side_effect = beta_side_effect

        # Act
        result = calculate_stress_test(db_session, -10.0, "USD")

        # Assert
        # NVDA: 100 * 150 * 1.0 = 15000 USD
        # 2330.TW: 1000 * 600 / 32 = 18750 USD
        # Total: 33750 USD
        assert result["total_value"] == 33750.0

        # Portfolio beta:
        # NVDA weight = 15000/33750 = 44.44%, beta 1.8 → 0.8
        # 2330 weight = 18750/33750 = 55.56%, beta 1.2 → 0.67
        # Portfolio beta ≈ 1.47
        assert 1.45 <= result["portfolio_beta"] <= 1.49

        # Total loss: 33750 * (-10%) * 1.47 ≈ -4963
        assert -5000 <= result["total_loss"] <= -4900

    @patch("application.portfolio.stress_test_service.prewarm_beta_batch")
    @patch("application.portfolio.stress_test_service.get_stock_beta")
    @patch("application.portfolio.stress_test_service._compute_holding_market_values")
    @patch("application.portfolio.stress_test_service.get_exchange_rates")
    def test_cash_holdings_should_have_zero_beta(
        self,
        mock_fx,
        mock_compute_mv,
        mock_beta,
        mock_prewarm,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Holding(
                ticker="USD",
                category=StockCategory.CASH,
                quantity=50000,
                currency="USD",
                is_cash=True,
            )
        )
        db_session.add(
            Holding(
                ticker="NVDA",
                category=StockCategory.GROWTH,
                quantity=100,
                cost_basis=150.0,
                currency="USD",
            )
        )
        db_session.commit()

        mock_fx.return_value = _make_fx_rates_mock("USD")
        mock_compute_mv.side_effect = _mock_compute_holding_market_values
        mock_beta.return_value = 1.8

        # Act
        result = calculate_stress_test(db_session, -20.0, "USD")

        # Assert
        # Total value: 50000 (cash) + 15000 (NVDA) = 65000
        assert result["total_value"] == 65000.0

        # Portfolio beta: 50000/65000 * 0.0 + 15000/65000 * 1.8 ≈ 0.42
        assert 0.4 <= result["portfolio_beta"] <= 0.45

        # Cash should be in breakdown with beta 0
        cash_breakdown = next(
            h for h in result["holdings_breakdown"] if h["ticker"] == "USD"
        )
        assert cash_breakdown["beta"] == 0.0
        assert cash_breakdown["expected_loss"] == 0.0


# ---------------------------------------------------------------------------
# Beta Fallback
# ---------------------------------------------------------------------------


class TestBetaFallback:
    """Tests for beta fallback when yfinance returns None."""

    @patch("application.portfolio.stress_test_service.prewarm_beta_batch")
    @patch("application.portfolio.stress_test_service.get_stock_beta")
    @patch("application.portfolio.stress_test_service._compute_holding_market_values")
    @patch("application.portfolio.stress_test_service.get_exchange_rates")
    def test_should_use_category_fallback_when_beta_is_none(
        self,
        mock_fx,
        mock_compute_mv,
        mock_beta,
        mock_prewarm,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Holding(
                ticker="BTC-USD",  # Crypto may not have beta
                category=StockCategory.GROWTH,
                quantity=1,
                cost_basis=60000.0,
                currency="USD",
            )
        )
        db_session.commit()

        mock_fx.return_value = _make_fx_rates_mock("USD")
        mock_compute_mv.side_effect = _mock_compute_holding_market_values
        mock_beta.return_value = None  # yfinance returns None

        # Act
        result = calculate_stress_test(db_session, -20.0, "USD")

        # Assert — should use Growth fallback beta = 1.5
        assert result["portfolio_beta"] == 1.5

        breakdown = result["holdings_breakdown"][0]
        assert breakdown["beta"] == 1.5
        assert breakdown["expected_drop_pct"] == -30.0  # -20 * 1.5
        assert breakdown["expected_loss"] == -18000.0  # 60000 * -30%


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------


class TestStressTestErrorHandling:
    """Tests for error scenarios."""

    def test_should_raise_when_no_holdings(self, db_session: Session):
        # Arrange — empty DB
        # Act & Assert
        with pytest.raises(StockNotFoundError, match="尚未輸入任何持倉"):
            calculate_stress_test(db_session, -20.0, "USD")

    @patch("application.portfolio.stress_test_service.prewarm_beta_batch")
    @patch("application.portfolio.stress_test_service.get_stock_beta")
    @patch("application.portfolio.stress_test_service._compute_holding_market_values")
    @patch("application.portfolio.stress_test_service.get_exchange_rates")
    def test_should_handle_missing_price_with_cost_basis_fallback(
        self,
        mock_fx,
        mock_compute_mv,
        mock_beta,
        mock_prewarm,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Holding(
                ticker="UNLISTED",
                category=StockCategory.GROWTH,
                quantity=100,
                cost_basis=50.0,
                currency="USD",
            )
        )
        db_session.commit()

        mock_fx.return_value = _make_fx_rates_mock("USD")
        mock_compute_mv.side_effect = _mock_compute_holding_market_values
        mock_beta.return_value = 1.5

        # Act
        result = calculate_stress_test(db_session, -20.0, "USD")

        # Assert — should use cost_basis as fallback
        assert result["total_value"] == 5000.0  # 100 * 50
        assert result["portfolio_beta"] == 1.5
        assert result["total_loss"] == -1500.0  # 5000 * (-20%) * 1.5


# ---------------------------------------------------------------------------
# Privacy
# ---------------------------------------------------------------------------


class TestStressTestPrivacy:
    """Tests for privacy compliance (no absolute dollar logging)."""

    @patch("application.portfolio.stress_test_service.logger")
    @patch("application.portfolio.stress_test_service.prewarm_beta_batch")
    @patch("application.portfolio.stress_test_service.get_stock_beta")
    @patch("application.portfolio.stress_test_service._compute_holding_market_values")
    @patch("application.portfolio.stress_test_service.get_exchange_rates")
    def test_should_not_log_absolute_dollar_amounts(
        self,
        mock_fx,
        mock_compute_mv,
        mock_beta,
        mock_prewarm,
        mock_logger,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Holding(
                ticker="NVDA",
                category=StockCategory.GROWTH,
                quantity=100,
                cost_basis=150.0,
                currency="USD",
            )
        )
        db_session.commit()

        mock_fx.return_value = _make_fx_rates_mock("USD")
        mock_compute_mv.side_effect = _mock_compute_holding_market_values
        mock_beta.return_value = 1.8

        # Act
        calculate_stress_test(db_session, -20.0, "USD")

        # Assert — Check logger.info calls do NOT contain dollar amounts
        info_calls = [str(call) for call in mock_logger.info.call_args_list]

        for call in info_calls:
            # Should NOT log total_value, total_loss, or any absolute dollar amount
            assert "15000" not in call  # total_value
            assert "5400" not in call  # total_loss
            # Should only log beta and scenario %
            if "壓力測試完成" in call:
                assert "Beta=" in call or "beta=" in call.lower()
                assert "情境=" in call


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestStressTestEdgeCases:
    """Tests for edge cases."""

    @patch("application.portfolio.stress_test_service.prewarm_beta_batch")
    @patch("application.portfolio.stress_test_service.get_stock_beta")
    @patch("application.portfolio.stress_test_service._compute_holding_market_values")
    @patch("application.portfolio.stress_test_service.get_exchange_rates")
    def test_all_cash_portfolio_should_return_zero_loss(
        self,
        mock_fx,
        mock_compute_mv,
        mock_beta,
        mock_prewarm,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Holding(
                ticker="USD",
                category=StockCategory.CASH,
                quantity=100000,
                currency="USD",
                is_cash=True,
            )
        )
        db_session.commit()

        mock_fx.return_value = _make_fx_rates_mock("USD")
        mock_compute_mv.side_effect = _mock_compute_holding_market_values

        # Act
        result = calculate_stress_test(db_session, -50.0, "USD")

        # Assert
        assert result["portfolio_beta"] == 0.0
        assert result["total_loss"] == 0.0
        assert result["pain_level"]["level"] == "low"
        # prewarm_beta_batch should NOT be called (no non-cash tickers)
        mock_prewarm.assert_not_called()

    @patch("application.portfolio.stress_test_service.prewarm_beta_batch")
    @patch("application.portfolio.stress_test_service.get_stock_beta")
    @patch("application.portfolio.stress_test_service._compute_holding_market_values")
    @patch("application.portfolio.stress_test_service.get_exchange_rates")
    def test_extreme_scenario_should_trigger_panic_zone(
        self,
        mock_fx,
        mock_compute_mv,
        mock_beta,
        mock_prewarm,
        db_session: Session,
    ):
        # Arrange
        db_session.add(
            Holding(
                ticker="TQQQ",  # 3x leveraged
                category=StockCategory.GROWTH,
                quantity=100,
                cost_basis=60.0,
                currency="USD",
            )
        )
        db_session.commit()

        mock_fx.return_value = _make_fx_rates_mock("USD")
        mock_compute_mv.side_effect = _mock_compute_holding_market_values
        mock_beta.return_value = 3.0  # 3x leveraged

        # Act
        result = calculate_stress_test(db_session, -20.0, "USD")

        # Assert
        # Loss: 6000 * (-20%) * 3.0 = -3600 (60% loss)
        assert result["total_loss"] == -3600.0
        assert result["total_loss_pct"] == -60.0
        assert result["pain_level"]["level"] == "panic"
        assert len(result["advice"]) > 0  # panic zone should have advice
