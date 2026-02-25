"""
Tests for calculate_currency_exposure and send_xray_warnings in rebalance_service.py.
All external calls (exchange rates, forex history, Telegram) are mocked.
"""

from unittest.mock import patch

import pytest
from sqlmodel import Session

from application.portfolio.rebalance_service import (
    calculate_currency_exposure,
    send_xray_warnings,
)
from domain.entities import Holding
from domain.enums import StockCategory

REBALANCE_MODULE = "application.portfolio.rebalance_service"


def _make_holding(
    session: Session,
    ticker: str = "AAPL",
    currency: str = "USD",
    quantity: float = 10.0,
    cost_basis: float = 100.0,
    is_cash: bool = False,
) -> Holding:
    holding = Holding(
        user_id="default",
        ticker=ticker,
        category=StockCategory.MOAT,
        quantity=quantity,
        cost_basis=cost_basis,
        currency=currency,
        is_cash=is_cash,
    )
    session.add(holding)
    session.commit()
    return holding


# ===========================================================================
# calculate_currency_exposure
# ===========================================================================


class TestCalculateCurrencyExposure:
    def test_returns_empty_result_when_no_holdings(self, db_session: Session) -> None:
        result = calculate_currency_exposure(db_session, home_currency="TWD")

        assert result["home_currency"] == "TWD"
        assert result["total_value_home"] == 0.0
        assert result["breakdown"] == []
        assert result["non_home_pct"] == 0.0

    def test_single_usd_holding_with_twd_home(self, db_session: Session) -> None:
        _make_holding(
            db_session, ticker="AAPL", currency="USD", quantity=10.0, cost_basis=150.0
        )

        with (
            patch(f"{REBALANCE_MODULE}.get_exchange_rates", return_value={"USD": 32.0}),
            patch(
                f"{REBALANCE_MODULE}.get_technical_signals",
                return_value={"price": 150.0},
            ),
            patch(f"{REBALANCE_MODULE}.prewarm_signals_batch"),
            patch(f"{REBALANCE_MODULE}.get_forex_history", return_value=[]),
            patch(f"{REBALANCE_MODULE}.get_forex_history_long", return_value=[]),
        ):
            result = calculate_currency_exposure(db_session, home_currency="TWD")

        assert result["home_currency"] == "TWD"
        # USD holdings converted to TWD: 10 * 150 * 32 = 48,000
        assert result["total_value_home"] == pytest.approx(48_000, rel=0.01)
        assert len(result["breakdown"]) == 1
        assert result["breakdown"][0]["currency"] == "USD"
        # All in USD → non-home should be ~100%
        assert result["non_home_pct"] > 0

    def test_home_currency_from_profile_fallback(self, db_session: Session) -> None:
        """When home_currency is None and no profile exists, defaults to TWD."""
        _make_holding(
            db_session, ticker="NVDA", currency="USD", quantity=5.0, cost_basis=200.0
        )

        with (
            patch(f"{REBALANCE_MODULE}.get_exchange_rates", return_value={"USD": 32.0}),
            patch(
                f"{REBALANCE_MODULE}.get_technical_signals",
                return_value={"price": 200.0},
            ),
            patch(f"{REBALANCE_MODULE}.prewarm_signals_batch"),
            patch(f"{REBALANCE_MODULE}.get_forex_history", return_value=[]),
            patch(f"{REBALANCE_MODULE}.get_forex_history_long", return_value=[]),
        ):
            result = calculate_currency_exposure(db_session)  # home_currency=None

        assert result["home_currency"] == "TWD"

    def test_fx_movement_computed_from_history(self, db_session: Session) -> None:
        """When forex history has >= 2 entries, fx_movements should be populated."""
        _make_holding(
            db_session, ticker="AAPL", currency="USD", quantity=10.0, cost_basis=100.0
        )

        short_history = [{"close": 30.0}, {"close": 31.5}]

        with (
            patch(f"{REBALANCE_MODULE}.get_exchange_rates", return_value={"USD": 31.5}),
            patch(
                f"{REBALANCE_MODULE}.get_technical_signals",
                return_value={"price": 100.0},
            ),
            patch(f"{REBALANCE_MODULE}.prewarm_signals_batch"),
            patch(f"{REBALANCE_MODULE}.get_forex_history", return_value=short_history),
            patch(f"{REBALANCE_MODULE}.get_forex_history_long", return_value=[]),
        ):
            result = calculate_currency_exposure(db_session, home_currency="TWD")

        movements = result.get("fx_movements", [])
        assert len(movements) == 1
        assert movements[0]["pair"] == "USD/TWD"
        assert movements[0]["change_pct"] == pytest.approx(5.0, rel=0.01)

    def test_cash_holding_tracked_separately(self, db_session: Session) -> None:
        """Cash holdings should appear in cash_breakdown, not distort non_home_pct."""
        _make_holding(
            db_session,
            ticker="USD_CASH",
            currency="USD",
            quantity=5000.0,
            cost_basis=1.0,
            is_cash=True,
        )

        with (
            patch(f"{REBALANCE_MODULE}.get_exchange_rates", return_value={"USD": 32.0}),
            patch(f"{REBALANCE_MODULE}.get_technical_signals", return_value=None),
            patch(f"{REBALANCE_MODULE}.prewarm_signals_batch"),
            patch(f"{REBALANCE_MODULE}.get_forex_history", return_value=[]),
            patch(f"{REBALANCE_MODULE}.get_forex_history_long", return_value=[]),
        ):
            result = calculate_currency_exposure(db_session, home_currency="TWD")

        assert "cash_breakdown" in result
        assert result["total_cash_home"] > 0

    def test_result_contains_required_keys(self, db_session: Session) -> None:
        """Ensure the output schema has all expected fields even with no holdings."""
        result = calculate_currency_exposure(db_session, home_currency="USD")

        required_keys = {
            "home_currency",
            "total_value_home",
            "breakdown",
            "non_home_pct",
            "cash_breakdown",
            "cash_non_home_pct",
            "total_cash_home",
            "fx_movements",
            "risk_level",
            "advice",
            "calculated_at",
        }
        assert required_keys.issubset(result.keys())


# ===========================================================================
# send_xray_warnings
# ===========================================================================


class TestSendXrayWarnings:
    def test_no_warnings_when_all_below_threshold(self, db_session: Session) -> None:
        xray_entries = [
            {
                "symbol": "AAPL",
                "total_weight_pct": 5.0,
                "direct_weight_pct": 5.0,
                "indirect_value": 0.0,
                "indirect_sources": [],
            }
        ]

        result = send_xray_warnings(xray_entries, "USD", db_session)

        assert result == []

    def test_warning_sent_when_above_threshold_with_indirect(
        self, db_session: Session
    ) -> None:
        """Entry with total_weight_pct > threshold AND indirect_value > 0 → warning generated."""
        from domain.constants import XRAY_SINGLE_STOCK_WARN_PCT

        xray_entries = [
            {
                "symbol": "NVDA",
                "total_weight_pct": XRAY_SINGLE_STOCK_WARN_PCT + 5.0,
                "direct_weight_pct": 8.0,
                "indirect_value": 1_000.0,
                "indirect_sources": ["VTI"],
            }
        ]

        with (
            patch(
                f"{REBALANCE_MODULE}.is_notification_enabled",
                return_value=True,
            ),
            patch(
                f"{REBALANCE_MODULE}.send_telegram_message_dual",
            ) as mock_send,
        ):
            result = send_xray_warnings(xray_entries, "USD", db_session)

        assert len(result) == 1
        assert "NVDA" in result[0]
        mock_send.assert_called_once()

    def test_no_telegram_when_notification_disabled(self, db_session: Session) -> None:
        """When notification is disabled, warning is generated but Telegram is NOT sent."""
        from domain.constants import XRAY_SINGLE_STOCK_WARN_PCT

        xray_entries = [
            {
                "symbol": "MSFT",
                "total_weight_pct": XRAY_SINGLE_STOCK_WARN_PCT + 5.0,
                "direct_weight_pct": 6.0,
                "indirect_value": 500.0,
                "indirect_sources": ["SPY"],
            }
        ]

        with (
            patch(
                f"{REBALANCE_MODULE}.is_notification_enabled",
                return_value=False,
            ),
            patch(f"{REBALANCE_MODULE}.send_telegram_message_dual") as mock_send,
        ):
            result = send_xray_warnings(xray_entries, "USD", db_session)

        assert len(result) == 1
        mock_send.assert_not_called()

    def test_silent_on_telegram_failure(self, db_session: Session) -> None:
        """Telegram failure should not raise — function should return warnings gracefully."""
        from domain.constants import XRAY_SINGLE_STOCK_WARN_PCT

        xray_entries = [
            {
                "symbol": "GOOG",
                "total_weight_pct": XRAY_SINGLE_STOCK_WARN_PCT + 3.0,
                "direct_weight_pct": 7.0,
                "indirect_value": 200.0,
                "indirect_sources": ["QQQ"],
            }
        ]

        with (
            patch(f"{REBALANCE_MODULE}.is_notification_enabled", return_value=True),
            patch(
                f"{REBALANCE_MODULE}.send_telegram_message_dual",
                side_effect=RuntimeError("network error"),
            ),
        ):
            result = send_xray_warnings(xray_entries, "USD", db_session)

        # Should still return the warning string, not raise
        assert len(result) == 1

    def test_entry_above_threshold_but_zero_indirect_skipped(
        self, db_session: Session
    ) -> None:
        """Entry with indirect_value=0 should be skipped even if weight is high."""
        from domain.constants import XRAY_SINGLE_STOCK_WARN_PCT

        xray_entries = [
            {
                "symbol": "AMZN",
                "total_weight_pct": XRAY_SINGLE_STOCK_WARN_PCT + 10.0,
                "direct_weight_pct": 15.0,
                "indirect_value": 0.0,  # No indirect exposure → skip
                "indirect_sources": [],
            }
        ]

        result = send_xray_warnings(xray_entries, "USD", db_session)

        assert result == []

    def test_multiple_warnings_aggregated_in_single_message(
        self, db_session: Session
    ) -> None:
        from domain.constants import XRAY_SINGLE_STOCK_WARN_PCT

        xray_entries = [
            {
                "symbol": "TSLA",
                "total_weight_pct": XRAY_SINGLE_STOCK_WARN_PCT + 5.0,
                "direct_weight_pct": 10.0,
                "indirect_value": 500.0,
                "indirect_sources": ["ARKK"],
            },
            {
                "symbol": "AMD",
                "total_weight_pct": XRAY_SINGLE_STOCK_WARN_PCT + 2.0,
                "direct_weight_pct": 8.0,
                "indirect_value": 300.0,
                "indirect_sources": ["SMH"],
            },
        ]

        with (
            patch(f"{REBALANCE_MODULE}.is_notification_enabled", return_value=True),
            patch(f"{REBALANCE_MODULE}.send_telegram_message_dual") as mock_send,
        ):
            result = send_xray_warnings(xray_entries, "USD", db_session)

        assert len(result) == 2
        # Both warnings sent in a single Telegram call
        mock_send.assert_called_once()
