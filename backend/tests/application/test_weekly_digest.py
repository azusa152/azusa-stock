"""
Unit tests for send_weekly_digest() and get_portfolio_summary()
in application.notification_service.

All external I/O is mocked — no Telegram calls, no yfinance requests.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlmodel import Session

from domain.entities import ScanLog, Stock
from domain.enums import ScanSignal, StockCategory
from tests.conftest import MOCK_FEAR_GREED

NOTIFICATION_MODULE = "application.notification_service"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_stock(
    session: Session,
    ticker: str,
    signal: str = ScanSignal.NORMAL.value,
    category: StockCategory = StockCategory.GROWTH,
) -> Stock:
    s = Stock(ticker=ticker, category=category, last_scan_signal=signal, is_active=True)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def _add_scan_log(
    session: Session,
    ticker: str,
    signal: str,
    days_ago: float = 1.0,
) -> ScanLog:
    log = ScanLog(
        stock_ticker=ticker,
        signal=signal,
        market_status="POSITIVE",
        scanned_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


# Shared context managers for every test that reaches the Fear & Greed call.
# Defined once here so individual tests don't duplicate boilerplate.
_FG_PATCH = f"{NOTIFICATION_MODULE}.get_fear_greed_index"
_TG_PATCH = f"{NOTIFICATION_MODULE}.send_telegram_message_dual"
_NOTIF_PATCH = f"{NOTIFICATION_MODULE}.is_notification_enabled"


# ---------------------------------------------------------------------------
# send_weekly_digest
# ---------------------------------------------------------------------------


class TestSendWeeklyDigest:
    def test_should_include_health_score(self, db_session: Session):
        """Message must contain health score when stocks are present."""
        from application.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)
        _add_stock(db_session, "MSFT", ScanSignal.NORMAL.value)

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED), \
             patch(_TG_PATCH) as mock_send, \
             patch(_NOTIF_PATCH, return_value=True):
            result = send_weekly_digest(db_session)

        assert result["health_score"] == 100.0
        sent_message = mock_send.call_args[0][0]
        assert "100.0" in sent_message

    def test_should_list_abnormal_stocks(self, db_session: Session):
        """Non-normal stocks must appear in the Telegram message."""
        from application.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)
        _add_stock(db_session, "BABA", ScanSignal.THESIS_BROKEN.value)

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED), \
             patch(_TG_PATCH) as mock_send, \
             patch(_NOTIF_PATCH, return_value=True):
            result = send_weekly_digest(db_session)

        assert result["health_score"] == 50.0
        sent_message = mock_send.call_args[0][0]
        assert "BABA" in sent_message
        assert ScanSignal.THESIS_BROKEN.value in sent_message

    def test_should_report_signal_changes(self, db_session: Session):
        """Tickers with signal changes must appear with correct count, not raw keys."""
        from application.notification_service import send_weekly_digest

        _add_stock(db_session, "NIO", ScanSignal.OVERSOLD.value)
        # Two scan logs with different signals → one change detected
        _add_scan_log(db_session, "NIO", ScanSignal.NORMAL.value, days_ago=3)
        _add_scan_log(db_session, "NIO", ScanSignal.OVERSOLD.value, days_ago=1)

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED), \
             patch(_TG_PATCH) as mock_send, \
             patch(_NOTIF_PATCH, return_value=True):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        assert "NIO" in sent_message
        # Change count must be present as a digit
        assert " 1 " in sent_message
        # Translated labels must be present, not raw keys
        assert "notification.change_label" not in sent_message
        assert "notification.times_label" not in sent_message

    def test_should_handle_empty_portfolio(self, db_session: Session):
        """When watchlist is empty the no_stocks key must render as real text."""
        from application.notification_service import send_weekly_digest

        with patch(_TG_PATCH) as mock_send:
            result = send_weekly_digest(db_session)

        mock_send.assert_called_once()
        sent_message = mock_send.call_args[0][0]
        # Must not echo back raw i18n keys
        assert "notification.no_stocks" not in sent_message
        assert "notification.weekly_digest_title" not in sent_message
        # Result dict message must also be a real string
        assert "notification." not in result["message"]

    def test_should_skip_when_notification_disabled(self, db_session: Session):
        """When weekly_digest notification is disabled, Telegram must not be called."""
        from application.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED), \
             patch(_TG_PATCH) as mock_send, \
             patch(_NOTIF_PATCH, return_value=False):
            send_weekly_digest(db_session)

        mock_send.assert_not_called()

    def test_should_report_all_normal(self, db_session: Session):
        """When all stocks are normal the all_normal translation must appear verbatim."""
        from application.notification_service import send_weekly_digest

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value)
        _add_stock(db_session, "MSFT", ScanSignal.NORMAL.value)

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED), \
             patch(_TG_PATCH) as mock_send, \
             patch(_NOTIF_PATCH, return_value=True):
            send_weekly_digest(db_session)

        sent_message = mock_send.call_args[0][0]
        # Raw key must not leak
        assert "notification.all_normal" not in sent_message
        # The translated "all clear" marker must actually be in the message
        assert "✅" in sent_message


# ---------------------------------------------------------------------------
# get_portfolio_summary
# ---------------------------------------------------------------------------


class TestGetPortfolioSummary:
    def test_should_include_categories(self, db_session: Session):
        """Summary must group stocks by category and not echo raw i18n keys."""
        from application.notification_service import get_portfolio_summary

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value, StockCategory.TREND_SETTER)
        _add_stock(db_session, "MSFT", ScanSignal.NORMAL.value, StockCategory.TREND_SETTER)

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED):
            summary = get_portfolio_summary(db_session)

        assert "AAPL" in summary
        assert "MSFT" in summary
        assert "notification.portfolio_summary_health" not in summary

    def test_should_handle_empty(self, db_session: Session):
        """Empty portfolio must return a real string, not a raw i18n key."""
        from application.notification_service import get_portfolio_summary

        summary = get_portfolio_summary(db_session)

        assert "notification.portfolio_summary_no_stocks" not in summary
        assert len(summary) > 0

    def test_should_show_abnormal_section_for_non_normal_stocks(self, db_session: Session):
        """Stocks with active signals must appear in the abnormal section."""
        from application.notification_service import get_portfolio_summary

        _add_stock(db_session, "AAPL", ScanSignal.NORMAL.value, StockCategory.MOAT)
        _add_stock(db_session, "BABA", ScanSignal.THESIS_BROKEN.value, StockCategory.MOAT)
        _add_stock(db_session, "NIO", ScanSignal.OVERSOLD.value, StockCategory.GROWTH)

        with patch(_FG_PATCH, return_value=MOCK_FEAR_GREED):
            summary = get_portfolio_summary(db_session)

        # Raw key must not leak
        assert "notification.portfolio_summary_abnormal" not in summary
        assert "notification.portfolio_summary_normal" not in summary
        # Abnormal tickers and their signals must be present
        assert "BABA" in summary
        assert ScanSignal.THESIS_BROKEN.value in summary
        assert "NIO" in summary
        assert ScanSignal.OVERSOLD.value in summary
        # Normal ticker must not appear in the abnormal section
        # (it will appear in the category group, but not after the abnormal header)
        abnormal_section = summary.split("BABA")[1] if "BABA" in summary else ""
        assert "AAPL" not in abnormal_section
