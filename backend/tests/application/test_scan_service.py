"""
Tests for scan_service: Rogue Wave integration, _check_price_alerts, and scan alert isolation.

Covers:
- bias_percentile and is_rogue_wave present in scan results
- rogue_wave_alert appended when conditions met
- rogue_wave_alert NOT appended when conditions unmet (high bias but low volume)
- is_rogue_wave skipped for Cash category (SKIP_SIGNALS_CATEGORIES)
- get_bias_distribution empty dict → bias_percentile stays None, no rogue wave
- _check_price_alerts: threshold trigger, cooldown, naive datetime safety, isolation
"""

from __future__ import annotations

from unittest.mock import patch

from sqlmodel import Session

from application.scan_service import run_scan
from domain.entities import PriceAlert, Stock
from domain.enums import ScanSignal, StockCategory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_BIAS_DIST = {
    # 200 values from -20.0 to 28.0 (step 0.24) — meets ROGUE_WAVE_MIN_HISTORY_DAYS=200
    # p95 index = int(200 * 0.95) = 190, value ≈ 25.6
    "historical_biases": sorted([round(-20.0 + i * 0.24, 2) for i in range(200)]),
    "count": 200,
    "p95": round(-20.0 + 190 * 0.24, 2),
    "fetched_at": "2026-02-18T00:00:00+00:00",
}

_BASE_SIGNALS = {
    "ticker": "AAPL",
    "price": 200.0,
    "previous_close": 195.0,
    "change_pct": 2.56,
    "rsi": 55.0,
    "ma200": 150.0,
    "ma60": 170.0,
    "bias": 17.6,  # below 95th percentile of _MOCK_BIAS_DIST (p95=28.0)
    "volume_ratio": 1.0,
    "status": [],
}

_ROGUE_WAVE_SIGNALS = {
    **_BASE_SIGNALS,
    "bias": 26.0,  # above p95 of _MOCK_BIAS_DIST → percentile >= 95
    "volume_ratio": 1.6,  # >= ROGUE_WAVE_VOLUME_RATIO_THRESHOLD (1.5)
}

_MOCK_MOAT = {"moat": "STABLE", "details": "ok"}

_MOCK_FG = {
    "composite_score": 50,
    "composite_level": "NEUTRAL",
    "fetched_at": "2026-02-18T00:00:00+00:00",
}

_MOCK_MARKET_SENTIMENT = {
    "status": "BULLISH",
    "details": "ok",
    "below_60ma_pct": 20.0,
}


def _add_growth_stock(session: Session, ticker: str = "AAPL") -> None:
    session.add(
        Stock(ticker=ticker, category=StockCategory.GROWTH, current_thesis="test")
    )
    session.commit()


def _add_cash_stock(session: Session, ticker: str = "CASH") -> None:
    session.add(
        Stock(ticker=ticker, category=StockCategory.CASH, current_thesis="cash")
    )
    session.commit()


# ---------------------------------------------------------------------------
# TestScanRogueWaveFields
# ---------------------------------------------------------------------------


@patch("application.scan_service.batch_download_history", new=lambda *a, **kw: {})
class TestScanRogueWaveFields:
    """bias_percentile and is_rogue_wave should always be present in scan results."""

    @patch("application.scan_service.send_telegram_message_dual")
    @patch("application.scan_service.get_fear_greed_index")
    @patch("application.scan_service.analyze_moat_trend")
    @patch("application.scan_service.get_bias_distribution")
    @patch("application.scan_service.get_technical_signals")
    @patch("application.scan_service.analyze_market_sentiment")
    def test_scan_result_should_include_bias_percentile_and_is_rogue_wave(
        self,
        mock_sentiment,
        mock_signals,
        mock_bias_dist,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ):
        # Arrange
        _add_growth_stock(db_session)
        mock_sentiment.return_value = _MOCK_MARKET_SENTIMENT
        mock_signals.return_value = _BASE_SIGNALS
        mock_bias_dist.return_value = _MOCK_BIAS_DIST
        mock_moat.return_value = _MOCK_MOAT
        mock_fg.return_value = _MOCK_FG

        # Act
        result = run_scan(db_session)

        # Assert
        scan_results = result["results"]
        assert len(scan_results) == 1
        r = scan_results[0]
        assert "bias_percentile" in r
        assert "is_rogue_wave" in r

    @patch("application.scan_service.send_telegram_message_dual")
    @patch("application.scan_service.get_fear_greed_index")
    @patch("application.scan_service.analyze_moat_trend")
    @patch("application.scan_service.get_bias_distribution")
    @patch("application.scan_service.get_technical_signals")
    @patch("application.scan_service.analyze_market_sentiment")
    def test_scan_result_should_have_false_is_rogue_wave_when_no_dist(
        self,
        mock_sentiment,
        mock_signals,
        mock_bias_dist,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ):
        # Arrange — distribution unavailable
        _add_growth_stock(db_session)
        mock_sentiment.return_value = _MOCK_MARKET_SENTIMENT
        mock_signals.return_value = _BASE_SIGNALS
        mock_bias_dist.return_value = {}  # empty dict = error
        mock_moat.return_value = _MOCK_MOAT
        mock_fg.return_value = _MOCK_FG

        # Act
        result = run_scan(db_session)

        # Assert
        r = result["results"][0]
        assert r["bias_percentile"] is None
        assert r["is_rogue_wave"] is False


# ---------------------------------------------------------------------------
# TestScanRogueWaveAlert
# ---------------------------------------------------------------------------


@patch("application.scan_service.batch_download_history", new=lambda *a, **kw: {})
class TestScanRogueWaveAlert:
    """rogue_wave_alert should be appended iff both thresholds are met."""

    @patch("application.scan_service.send_telegram_message_dual")
    @patch("application.scan_service.get_fear_greed_index")
    @patch("application.scan_service.analyze_moat_trend")
    @patch("application.scan_service.get_bias_distribution")
    @patch("application.scan_service.get_technical_signals")
    @patch("application.scan_service.analyze_market_sentiment")
    def test_should_append_rogue_wave_alert_when_both_conditions_met(
        self,
        mock_sentiment,
        mock_signals,
        mock_bias_dist,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ):
        # Arrange — bias above p95 AND volume_ratio above threshold
        _add_growth_stock(db_session)
        mock_sentiment.return_value = _MOCK_MARKET_SENTIMENT
        mock_signals.return_value = _ROGUE_WAVE_SIGNALS
        mock_bias_dist.return_value = _MOCK_BIAS_DIST
        mock_moat.return_value = _MOCK_MOAT
        mock_fg.return_value = _MOCK_FG

        # Act
        result = run_scan(db_session)

        # Assert
        r = result["results"][0]
        assert r["is_rogue_wave"] is True
        assert any("🌊" in alert for alert in r["alerts"])

    @patch("application.scan_service.send_telegram_message_dual")
    @patch("application.scan_service.get_fear_greed_index")
    @patch("application.scan_service.analyze_moat_trend")
    @patch("application.scan_service.get_bias_distribution")
    @patch("application.scan_service.get_technical_signals")
    @patch("application.scan_service.analyze_market_sentiment")
    def test_should_not_append_rogue_wave_alert_when_volume_below_threshold(
        self,
        mock_sentiment,
        mock_signals,
        mock_bias_dist,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ):
        # Arrange — bias above p95 but volume_ratio below threshold
        low_volume_signals = {**_ROGUE_WAVE_SIGNALS, "volume_ratio": 1.2}
        _add_growth_stock(db_session)
        mock_sentiment.return_value = _MOCK_MARKET_SENTIMENT
        mock_signals.return_value = low_volume_signals
        mock_bias_dist.return_value = _MOCK_BIAS_DIST
        mock_moat.return_value = _MOCK_MOAT
        mock_fg.return_value = _MOCK_FG

        # Act
        result = run_scan(db_session)

        # Assert
        r = result["results"][0]
        assert r["is_rogue_wave"] is False
        assert not any("🌊" in alert for alert in r["alerts"])

    @patch("application.scan_service.send_telegram_message_dual")
    @patch("application.scan_service.get_fear_greed_index")
    @patch("application.scan_service.analyze_moat_trend")
    @patch("application.scan_service.get_bias_distribution")
    @patch("application.scan_service.get_technical_signals")
    @patch("application.scan_service.analyze_market_sentiment")
    def test_should_not_append_rogue_wave_alert_when_bias_below_percentile(
        self,
        mock_sentiment,
        mock_signals,
        mock_bias_dist,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ):
        # Arrange — volume above threshold but bias below p95
        below_p95_signals = {**_ROGUE_WAVE_SIGNALS, "bias": 5.0}
        _add_growth_stock(db_session)
        mock_sentiment.return_value = _MOCK_MARKET_SENTIMENT
        mock_signals.return_value = below_p95_signals
        mock_bias_dist.return_value = _MOCK_BIAS_DIST
        mock_moat.return_value = _MOCK_MOAT
        mock_fg.return_value = _MOCK_FG

        # Act
        result = run_scan(db_session)

        # Assert
        r = result["results"][0]
        assert r["is_rogue_wave"] is False
        assert not any("🌊" in alert for alert in r["alerts"])


# ---------------------------------------------------------------------------
# TestScanRogueWaveSkippedForCash
# ---------------------------------------------------------------------------


@patch("application.scan_service.batch_download_history", new=lambda *a, **kw: {})
class TestScanRogueWaveSkippedForCash:
    """Cash category stocks skip signal fetching and must not trigger rogue wave."""

    @patch("application.scan_service.send_telegram_message_dual")
    @patch("application.scan_service.get_fear_greed_index")
    @patch("application.scan_service.analyze_moat_trend")
    @patch("application.scan_service.get_bias_distribution")
    @patch("application.scan_service.get_technical_signals")
    @patch("application.scan_service.analyze_market_sentiment")
    def test_should_not_call_bias_distribution_for_cash_stock(
        self,
        mock_sentiment,
        mock_signals,
        mock_bias_dist,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ):
        # Arrange
        _add_cash_stock(db_session)
        mock_sentiment.return_value = _MOCK_MARKET_SENTIMENT
        mock_signals.return_value = None  # Cash: not called
        mock_bias_dist.return_value = _MOCK_BIAS_DIST
        mock_moat.return_value = _MOCK_MOAT
        mock_fg.return_value = _MOCK_FG

        # Act
        result = run_scan(db_session)

        # Assert
        r = result["results"][0]
        assert r["is_rogue_wave"] is False
        assert r["bias_percentile"] is None
        mock_bias_dist.assert_not_called()


# ---------------------------------------------------------------------------
# TestGetLastScanStatus
# ---------------------------------------------------------------------------


class TestGetLastScanStatus:
    def test_returns_none_timestamps_when_no_logs(self, db_session: Session) -> None:
        from application.scan_service import get_last_scan_status

        result = get_last_scan_status(db_session)
        assert result["last_scanned_at"] is None
        assert result["epoch"] is None

    def test_returns_scan_metadata_when_logs_exist(self, db_session: Session) -> None:
        from application.scan_service import get_last_scan_status
        from domain.entities import ScanLog

        log = ScanLog(
            stock_ticker="AAPL",
            signal="NORMAL",
            market_status="BULLISH",
            market_status_details="ok",
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        mock_fg = {"composite_level": "NEUTRAL", "composite_score": 50}
        with patch(
            "application.scan_service.get_fear_greed_index", return_value=mock_fg
        ):
            result = get_last_scan_status(db_session)

        assert result["last_scanned_at"] is not None
        assert result["epoch"] is not None
        assert result["market_status"] == "BULLISH"
        assert result["fear_greed_level"] == "NEUTRAL"
        assert result["fear_greed_score"] == 50


# ---------------------------------------------------------------------------
# TestGetFearGreed
# ---------------------------------------------------------------------------


class TestGetFearGreed:
    def test_delegates_to_infrastructure(self) -> None:
        from application.scan_service import get_fear_greed

        mock_fg = {"composite_level": "GREED", "composite_score": 72}
        with patch(
            "application.scan_service.get_fear_greed_index", return_value=mock_fg
        ):
            result = get_fear_greed()

        assert result == mock_fg


# ---------------------------------------------------------------------------
# TestCheckPriceAlerts
# ---------------------------------------------------------------------------


class TestCheckPriceAlerts:
    """Tests for _check_price_alerts: trigger, cooldown, timezone safety, isolation."""

    _RESULTS = [{"ticker": "AAPL", "rsi": 25.0, "price": 150.0, "bias": -10.0}]

    def _make_alert(
        self, metric: str = "rsi", operator: str = "lt", threshold: float = 30.0
    ) -> PriceAlert:
        return PriceAlert(
            stock_ticker="AAPL", metric=metric, operator=operator, threshold=threshold
        )

    @patch("application.scan_service.send_telegram_message_dual")
    def test_should_send_notification_when_threshold_exceeded(
        self, mock_telegram, db_session: Session
    ) -> None:
        from application.scan_service import _check_price_alerts

        alert = self._make_alert(metric="rsi", operator="lt", threshold=30.0)
        db_session.add(alert)
        db_session.commit()

        _check_price_alerts(db_session, self._RESULTS, "en")

        mock_telegram.assert_called_once()
        db_session.refresh(alert)
        assert alert.last_triggered_at is not None

    @patch("application.scan_service.send_telegram_message_dual")
    def test_should_not_send_notification_when_threshold_not_exceeded(
        self, mock_telegram, db_session: Session
    ) -> None:
        from application.scan_service import _check_price_alerts

        alert = self._make_alert(metric="rsi", operator="gt", threshold=30.0)
        db_session.add(alert)
        db_session.commit()

        _check_price_alerts(db_session, self._RESULTS, "en")

        mock_telegram.assert_not_called()

    @patch("application.scan_service.send_telegram_message_dual")
    def test_should_not_send_notification_within_cooldown(
        self, mock_telegram, db_session: Session
    ) -> None:
        from datetime import datetime, timezone

        from application.scan_service import _check_price_alerts

        alert = self._make_alert()
        alert.last_triggered_at = datetime.now(timezone.utc)
        db_session.add(alert)
        db_session.commit()

        _check_price_alerts(db_session, self._RESULTS, "en")

        mock_telegram.assert_not_called()

    @patch("application.scan_service.send_telegram_message_dual")
    def test_should_not_crash_when_last_triggered_at_is_naive_datetime(
        self, mock_telegram, db_session: Session
    ) -> None:
        """Regression: SQLite may return naive datetimes; comparison must not raise TypeError."""
        from datetime import datetime, timezone

        from application.scan_service import _check_price_alerts

        alert = self._make_alert()
        # Simulate what SQLite returns after a round-trip: naive datetime
        alert.last_triggered_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add(alert)
        db_session.commit()

        # Should not raise even though last_triggered_at is naive
        _check_price_alerts(db_session, self._RESULTS, "en")

    @patch("application.scan_service.send_telegram_message_dual")
    @patch("application.scan_service.get_fear_greed_index")
    @patch("application.scan_service.analyze_moat_trend")
    @patch("application.scan_service.get_bias_distribution")
    @patch("application.scan_service.get_technical_signals")
    @patch("application.scan_service.analyze_market_sentiment")
    @patch("application.scan_service.batch_download_history", return_value={})
    def test_scan_alerts_still_sent_when_price_alerts_raise(
        self,
        mock_batch,
        mock_sentiment,
        mock_signals,
        mock_bias_dist,
        mock_moat,
        mock_fg,
        mock_telegram,
        db_session: Session,
    ) -> None:
        """Regression: a crash in _check_price_alerts must not prevent scan signal alerts."""
        stock = Stock(
            ticker="AAPL",
            category=StockCategory.GROWTH,
            current_thesis="test",
            last_scan_signal=ScanSignal.NORMAL.value,
        )
        db_session.add(stock)
        db_session.commit()

        mock_sentiment.return_value = _MOCK_MARKET_SENTIMENT
        mock_signals.return_value = {**_BASE_SIGNALS, "rsi": 25.0, "bias": -15.0}
        mock_bias_dist.return_value = {}
        mock_moat.return_value = _MOCK_MOAT
        mock_fg.return_value = _MOCK_FG

        with patch(
            "application.scan_service._check_price_alerts",
            side_effect=RuntimeError("simulated crash"),
        ):
            run_scan(db_session)

        # Scan signal alert should still have been attempted
        mock_telegram.assert_called()
