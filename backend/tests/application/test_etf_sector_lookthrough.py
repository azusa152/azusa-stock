"""
Tests for ETF sector look-through in the sector exposure calculation.

Covers:
- Approach B: ETF with sector_weightings distributes MV by official weights.
- Approach B fallback to A: ETF with no sector_weightings uses top-N constituents.
- Approach A residual: unattributed remainder distributed proportionally (not dumped to Unknown).
- Direct holdings: non-ETF tickers use get_ticker_sector unchanged.
- Mixed portfolio: ETF + direct holdings combined correctly.
"""

import json
import os
import tempfile

os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants  # noqa: E402

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_sector_lookthrough"
)

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from sqlmodel import Session  # noqa: E402

from application.rebalance_service import calculate_rebalance  # noqa: E402
from domain.entities import Holding, UserInvestmentProfile  # noqa: E402
from domain.enums import StockCategory  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_SIGNALS = {
    "price": 100.0,
    "previous_close": 100.0,
    "change_pct": 0.0,
    "rsi": 50.0,
    "ma200": 90.0,
    "ma60": 95.0,
    "bias": 0.0,
    "volume_ratio": 1.0,
    "status": [],
}

_BASE_PATCHES = [
    "application.rebalance_service.prewarm_signals_batch",
    "application.rebalance_service.prewarm_etf_holdings_batch",
    "application.rebalance_service.get_forex_history",
    "application.rebalance_service.get_forex_history_long",
]


def _add_profile(session: Session) -> None:
    session.add(
        UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
    )


def _add_holding(session: Session, ticker: str, quantity: float = 10.0) -> None:
    session.add(
        Holding(
            user_id="default",
            ticker=ticker,
            category=StockCategory.GROWTH,
            quantity=quantity,
            cost_basis=100.0,
            currency="USD",
            is_cash=False,
        )
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEtfSectorLookthrough:
    """Sector exposure correctly decomposes ETF holdings."""

    @patch("application.rebalance_service.get_etf_sector_weights")
    @patch("application.rebalance_service.get_etf_top_holdings")
    @patch("application.rebalance_service.get_ticker_sector")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_signals_batch")
    def test_approach_b_distributes_mv_by_sector_weights(
        self,
        _mock_prewarm_signals,
        _mock_prewarm_etf,
        _mock_prewarm_etf_sw,
        mock_signals,
        mock_fx,
        mock_sector,
        mock_etf_holdings,
        mock_etf_weights,
        db_session: Session,
    ):
        """Approach B: ETF with sector_weightings distributes MV proportionally."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "VTI", quantity=10.0)
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS, "price": 200.0}
        mock_fx.return_value = {"USD": 1.0}
        # VTI is detected as ETF (has constituents)
        mock_etf_holdings.return_value = [
            {"symbol": "AAPL", "name": "Apple", "weight": 0.05},
        ]
        # Approach B: official sector weights for VTI
        mock_etf_weights.return_value = {
            "Technology": 0.30,
            "Consumer Cyclical": 0.12,
            "Financial Services": 0.13,
        }
        mock_sector.return_value = "Unknown"  # should NOT be called for VTI

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        sector_exposure = {s["sector"]: s for s in result["sector_exposure"]}
        total_mv = 10.0 * 200.0  # 2000

        assert "Technology" in sector_exposure
        assert "Consumer Cyclical" in sector_exposure
        assert "Financial Services" in sector_exposure
        assert "Unknown" not in sector_exposure

        assert sector_exposure["Technology"]["value"] == pytest.approx(
            total_mv * 0.30, rel=0.01
        )
        assert sector_exposure["Consumer Cyclical"]["value"] == pytest.approx(
            total_mv * 0.12, rel=0.01
        )

    @patch("application.rebalance_service.get_etf_sector_weights")
    @patch("application.rebalance_service.get_etf_top_holdings")
    @patch("application.rebalance_service.get_ticker_sector")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_signals_batch")
    def test_approach_a_fallback_uses_constituent_sectors(
        self,
        _mock_prewarm_signals,
        _mock_prewarm_etf,
        _mock_prewarm_etf_sw,
        mock_signals,
        mock_fx,
        mock_sector,
        mock_etf_holdings,
        mock_etf_weights,
        db_session: Session,
    ):
        """Approach A fallback: when sector_weightings unavailable, use top-N constituents."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "VTI", quantity=10.0)
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS, "price": 200.0}
        mock_fx.return_value = {"USD": 1.0}
        mock_etf_holdings.return_value = [
            {"symbol": "AAPL", "name": "Apple", "weight": 0.06},
            {"symbol": "MSFT", "name": "Microsoft", "weight": 0.06},
        ]
        mock_etf_weights.return_value = None  # Approach B unavailable

        def _sector_side_effect(ticker: str) -> str | None:
            return {"AAPL": "Technology", "MSFT": "Technology"}.get(ticker)

        mock_sector.side_effect = _sector_side_effect

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert — Technology should absorb both AAPL + MSFT constituent weight
        sector_exposure = {s["sector"]: s for s in result["sector_exposure"]}
        total_mv = 10.0 * 200.0  # 2000

        assert "Technology" in sector_exposure
        # Direct constituent MV: (0.06 + 0.06) * 2000 = 240
        # Residual (1 - 0.12) = 0.88 distributed proportionally to Technology (100%)
        # Total Technology ≈ 2000
        assert sector_exposure["Technology"]["value"] == pytest.approx(
            total_mv, rel=0.01
        )

    @patch("application.rebalance_service.get_etf_sector_weights")
    @patch("application.rebalance_service.get_etf_top_holdings")
    @patch("application.rebalance_service.get_ticker_sector")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_signals_batch")
    def test_approach_a_residual_not_dumped_to_unknown(
        self,
        _mock_prewarm_signals,
        _mock_prewarm_etf,
        _mock_prewarm_etf_sw,
        mock_signals,
        mock_fx,
        mock_sector,
        mock_etf_holdings,
        mock_etf_weights,
        db_session: Session,
    ):
        """Approach A: unattributed residual MV is distributed proportionally, not dumped to Unknown."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "VTI", quantity=10.0)
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS, "price": 200.0}
        mock_fx.return_value = {"USD": 1.0}
        # Top-N covers only 20% of ETF weight
        mock_etf_holdings.return_value = [
            {"symbol": "AAPL", "name": "Apple", "weight": 0.10},
            {"symbol": "NVDA", "name": "NVDA", "weight": 0.10},
        ]
        mock_etf_weights.return_value = None

        def _sector_side_effect(ticker: str) -> str | None:
            return "Technology"

        mock_sector.side_effect = _sector_side_effect

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert — total sector exposure equals full ETF MV (no residual lost to Unknown)
        total_mv = 10.0 * 200.0  # 2000
        total_attributed = sum(s["value"] for s in result["sector_exposure"])
        assert total_attributed == pytest.approx(total_mv, rel=0.01)
        sector_exposure = {s["sector"]: s for s in result["sector_exposure"]}
        assert "Unknown" not in sector_exposure

    @patch("application.rebalance_service.get_etf_sector_weights")
    @patch("application.rebalance_service.get_etf_top_holdings")
    @patch("application.rebalance_service.get_ticker_sector")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_signals_batch")
    def test_direct_holding_uses_get_ticker_sector(
        self,
        _mock_prewarm_signals,
        _mock_prewarm_etf,
        _mock_prewarm_etf_sw,
        mock_signals,
        mock_fx,
        mock_sector,
        mock_etf_holdings,
        mock_etf_weights,
        db_session: Session,
    ):
        """Non-ETF direct holdings still use get_ticker_sector (no regression)."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "NVDA", quantity=5.0)
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS, "price": 120.0}
        mock_fx.return_value = {"USD": 1.0}
        mock_etf_holdings.return_value = None  # not an ETF
        mock_etf_weights.return_value = None
        mock_sector.return_value = "Technology"

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        sector_exposure = {s["sector"]: s for s in result["sector_exposure"]}
        assert "Technology" in sector_exposure
        assert sector_exposure["Technology"]["value"] == pytest.approx(
            5.0 * 120.0, rel=0.01
        )
        mock_sector.assert_called_once_with("NVDA")

    @patch("application.rebalance_service.get_etf_sector_weights")
    @patch("application.rebalance_service.get_etf_top_holdings")
    @patch("application.rebalance_service.get_ticker_sector")
    @patch("application.rebalance_service.get_exchange_rates")
    @patch("application.rebalance_service.get_technical_signals")
    @patch("application.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.rebalance_service.prewarm_signals_batch")
    def test_mixed_portfolio_etf_and_direct(
        self,
        _mock_prewarm_signals,
        _mock_prewarm_etf,
        _mock_prewarm_etf_sw,
        mock_signals,
        mock_fx,
        mock_sector,
        mock_etf_holdings,
        mock_etf_weights,
        db_session: Session,
    ):
        """Mixed portfolio: ETF (Approach B) + direct stock combine sector values correctly."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "VTI", quantity=10.0)
        _add_holding(db_session, "NVDA", quantity=5.0)
        db_session.commit()

        def _signals_side_effect(ticker: str, *a, **kw):
            prices = {"VTI": 200.0, "NVDA": 100.0}
            return {**_MOCK_SIGNALS, "price": prices.get(ticker, 100.0)}

        mock_signals.side_effect = _signals_side_effect
        mock_fx.return_value = {"USD": 1.0}

        def _etf_holdings_side_effect(ticker: str):
            if ticker == "VTI":
                return [{"symbol": "AAPL", "name": "Apple", "weight": 0.05}]
            return None

        mock_etf_holdings.side_effect = _etf_holdings_side_effect

        def _etf_weights_side_effect(ticker: str):
            if ticker == "VTI":
                return {"Technology": 0.30, "Financial Services": 0.15}
            return None

        mock_etf_weights.side_effect = _etf_weights_side_effect
        mock_sector.return_value = "Technology"  # NVDA → Technology

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        sector_exposure = {s["sector"]: s for s in result["sector_exposure"]}
        vti_mv = 10.0 * 200.0  # 2000
        nvda_mv = 5.0 * 100.0  # 500

        # Technology = VTI * 0.30 + NVDA direct
        expected_tech = vti_mv * 0.30 + nvda_mv
        assert "Technology" in sector_exposure
        assert sector_exposure["Technology"]["value"] == pytest.approx(
            expected_tech, rel=0.01
        )

        # Financial Services = VTI * 0.15 only
        assert "Financial Services" in sector_exposure
        assert sector_exposure["Financial Services"]["value"] == pytest.approx(
            vti_mv * 0.15, rel=0.01
        )
