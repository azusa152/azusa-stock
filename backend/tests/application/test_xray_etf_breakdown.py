"""
Tests for X-Ray ETF breakdown behavior in rebalance_service.calculate_rebalance().

Covers:
- ETF with valid holdings is broken down into indirect exposure (happy path).
- Known ETF whose holdings cannot be fetched is excluded from X-Ray entirely
  (not treated as a direct stock holding).
- Non-ETF stock is recorded as direct exposure when get_etf_top_holdings returns None.
- ETF sentinel is not cached to disk (is_error callback prevents L2 write).
"""

import json
import os
import tempfile

os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_xray_etf"
)

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from sqlmodel import Session  # noqa: E402

from application.portfolio.rebalance_service import calculate_rebalance  # noqa: E402
from domain.entities import Holding, Stock, UserInvestmentProfile  # noqa: E402
from domain.enums import StockCategory  # noqa: E402

_MODULE = "application.portfolio.rebalance_service"

_MOCK_SIGNALS_BASE = {
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
    f"{_MODULE}.prewarm_signals_batch",
    f"{_MODULE}.prewarm_etf_holdings_batch",
    f"{_MODULE}.prewarm_etf_sector_weights_batch",
    f"{_MODULE}.get_forex_history",
    f"{_MODULE}.get_forex_history_long",
    f"{_MODULE}.get_etf_sector_weights",
]


def _add_profile(session: Session) -> None:
    session.add(
        UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
    )


def _add_holding(
    session: Session,
    ticker: str,
    quantity: float = 10.0,
    category: StockCategory = StockCategory.GROWTH,
) -> None:
    session.add(
        Holding(
            user_id="default",
            ticker=ticker,
            category=category,
            quantity=quantity,
            cost_basis=100.0,
            currency="USD",
            is_cash=False,
        )
    )


def _add_stock(session: Session, ticker: str, is_etf: bool = False) -> None:
    session.add(
        Stock(
            ticker=ticker,
            category=StockCategory.GROWTH,
            is_active=True,
            is_etf=is_etf,
        )
    )


class TestXRayEtfBreakdown:
    """X-Ray decomposes ETF holdings and handles fetch failures gracefully."""

    @patch(f"{_MODULE}.get_etf_top_holdings")
    @patch(f"{_MODULE}.get_exchange_rates")
    @patch(f"{_MODULE}.get_technical_signals")
    def test_etf_with_holdings_produces_indirect_exposure(
        self,
        mock_signals,
        mock_fx,
        mock_etf_holdings,
        db_session: Session,
    ):
        """Happy path: ETF with valid holdings breaks down into indirect exposure."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "SOXX", quantity=10.0)
        _add_stock(db_session, "SOXX", is_etf=True)
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS_BASE, "price": 200.0}
        mock_fx.return_value = {"USD": 1.0}
        mock_etf_holdings.return_value = [
            {"symbol": "NVDA", "name": "NVIDIA", "weight": 0.08},
            {"symbol": "AVGO", "name": "Broadcom", "weight": 0.07},
        ]

        patchers = [patch(p, return_value=None) for p in _BASE_PATCHES]
        for p in patchers:
            p.start()

        try:
            # Act
            result = calculate_rebalance(db_session, "USD")
        finally:
            for p in patchers:
                p.stop()

        # Assert — SOXX itself must NOT appear in X-Ray; its constituents should
        xray = {e["symbol"]: e for e in result["xray"]}
        assert "SOXX" not in xray, "ETF should be decomposed, not listed directly"
        assert "NVDA" in xray
        assert "AVGO" in xray

        soxx_mv = 10.0 * 200.0  # 2000
        total_value = soxx_mv

        assert xray["NVDA"]["indirect_weight_pct"] == pytest.approx(
            (soxx_mv * 0.08 / total_value) * 100, rel=0.01
        )
        assert xray["NVDA"]["direct_weight_pct"] == pytest.approx(0.0, abs=0.001)
        assert xray["AVGO"]["indirect_weight_pct"] == pytest.approx(
            (soxx_mv * 0.07 / total_value) * 100, rel=0.01
        )

    @patch(f"{_MODULE}.get_etf_top_holdings")
    @patch(f"{_MODULE}.get_exchange_rates")
    @patch(f"{_MODULE}.get_technical_signals")
    def test_known_etf_with_failed_holdings_fetch_excluded_from_xray(
        self,
        mock_signals,
        mock_fx,
        mock_etf_holdings,
        db_session: Session,
    ):
        """Known ETF with unavailable holdings is excluded — not treated as a stock."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "SOXX", quantity=10.0)
        _add_stock(db_session, "SOXX", is_etf=True)
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS_BASE, "price": 200.0}
        mock_fx.return_value = {"USD": 1.0}
        mock_etf_holdings.return_value = None  # yfinance temporarily unavailable

        patchers = [patch(p, return_value=None) for p in _BASE_PATCHES]
        for p in patchers:
            p.start()

        try:
            result = calculate_rebalance(db_session, "USD")
        finally:
            for p in patchers:
                p.stop()

        # Assert — SOXX must NOT appear as a direct holding in X-Ray
        xray_symbols = {e["symbol"] for e in result["xray"]}
        assert "SOXX" not in xray_symbols, (
            "Known ETF with failed holdings fetch must be excluded from X-Ray, "
            "not shown as direct exposure"
        )

    @patch(f"{_MODULE}.get_etf_top_holdings")
    @patch(f"{_MODULE}.get_exchange_rates")
    @patch(f"{_MODULE}.get_technical_signals")
    def test_non_etf_stock_with_no_holdings_is_direct_exposure(
        self,
        mock_signals,
        mock_fx,
        mock_etf_holdings,
        db_session: Session,
    ):
        """Non-ETF stock should still appear as direct exposure when holdings returns None."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "NVDA", quantity=5.0)
        # NVDA is NOT in Stock table as is_etf=True
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS_BASE, "price": 100.0}
        mock_fx.return_value = {"USD": 1.0}
        mock_etf_holdings.return_value = None

        patchers = [patch(p, return_value=None) for p in _BASE_PATCHES]
        for p in patchers:
            p.start()

        try:
            result = calculate_rebalance(db_session, "USD")
        finally:
            for p in patchers:
                p.stop()

        # Assert — NVDA must appear with direct exposure only
        xray = {e["symbol"]: e for e in result["xray"]}
        assert "NVDA" in xray
        assert xray["NVDA"]["direct_weight_pct"] == pytest.approx(100.0, rel=0.01)
        assert xray["NVDA"]["indirect_weight_pct"] == pytest.approx(0.0, abs=0.001)

    @patch(f"{_MODULE}.get_etf_top_holdings")
    @patch(f"{_MODULE}.get_exchange_rates")
    @patch(f"{_MODULE}.get_technical_signals")
    def test_mixed_portfolio_etf_and_stock(
        self,
        mock_signals,
        mock_fx,
        mock_etf_holdings,
        db_session: Session,
    ):
        """Mixed portfolio: ETF decomposed + direct stock both appear correctly."""
        # Arrange
        _add_profile(db_session)
        _add_holding(db_session, "SOXX", quantity=10.0)
        _add_holding(db_session, "NVDA", quantity=5.0)
        _add_stock(db_session, "SOXX", is_etf=True)
        db_session.commit()

        def _signals_side_effect(ticker: str, *a, **kw):
            return {
                **_MOCK_SIGNALS_BASE,
                "price": {"SOXX": 200.0, "NVDA": 100.0}.get(ticker, 100.0),
            }

        mock_signals.side_effect = _signals_side_effect
        mock_fx.return_value = {"USD": 1.0}

        def _holdings_side_effect(ticker: str):
            if ticker == "SOXX":
                return [{"symbol": "NVDA", "name": "NVIDIA", "weight": 0.08}]
            return None

        mock_etf_holdings.side_effect = _holdings_side_effect

        patchers = [patch(p, return_value=None) for p in _BASE_PATCHES]
        for p in patchers:
            p.start()

        try:
            result = calculate_rebalance(db_session, "USD")
        finally:
            for p in patchers:
                p.stop()

        # Assert
        soxx_mv = 10.0 * 200.0  # 2000
        nvda_mv = 5.0 * 100.0  # 500
        total_value = soxx_mv + nvda_mv  # 2500

        xray = {e["symbol"]: e for e in result["xray"]}

        # SOXX should not appear — decomposed
        assert "SOXX" not in xray

        # NVDA has both direct (500) and indirect (2000 * 0.08 = 160) exposure
        assert "NVDA" in xray
        expected_direct_pct = (nvda_mv / total_value) * 100
        expected_indirect_pct = (soxx_mv * 0.08 / total_value) * 100
        assert xray["NVDA"]["direct_weight_pct"] == pytest.approx(
            expected_direct_pct, rel=0.01
        )
        assert xray["NVDA"]["indirect_weight_pct"] == pytest.approx(
            expected_indirect_pct, rel=0.01
        )


class TestEtfHoldingsSentinelCaching:
    """Sentinel caching prevents repeated yfinance calls for non-ETF tickers."""

    def test_sentinel_cached_in_l1_prevents_repeated_fetches(self):
        """After a failed fetch, the L1 sentinel prevents further yfinance calls."""
        from infrastructure.market_data.market_data import (
            _etf_holdings_cache,
            get_etf_top_holdings,
        )

        _etf_holdings_cache.pop("TEST_SENTINEL_TICKER", None)

        mock_fetch = patch(
            "infrastructure.market_data.market_data._fetch_etf_top_holdings",
            return_value=None,
        )
        with mock_fetch as m:
            result1 = get_etf_top_holdings("TEST_SENTINEL_TICKER")
            result2 = get_etf_top_holdings("TEST_SENTINEL_TICKER")

        assert result1 is None
        assert result2 is None
        # _fetch_etf_top_holdings should only be called once — second call
        # is served from L1 cache (sentinel).
        assert m.call_count == 1, (
            f"Expected 1 yfinance call (L1 sentinel dedup), got {m.call_count}"
        )
