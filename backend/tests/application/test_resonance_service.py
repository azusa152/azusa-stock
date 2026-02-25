"""
Tests for resonance_service, guru notification extensions, and guru formatters
(Phase 4 application layer).

All external calls (Telegram) are mocked — no I/O in this test suite.
"""

from unittest.mock import patch

import pytest
from sqlmodel import Session

from domain.entities import Guru, GuruFiling, GuruHolding, Holding, Stock
from domain.enums import HoldingAction, StockCategory
from infrastructure.repositories import (
    save_filing,
    save_guru,
    save_holdings_batch,
)

RESONANCE_MODULE = "application.guru.resonance_service"
NOTIFICATION_MODULE = "application.messaging.notification_service"
FORMATTERS_MODULE = "application.formatters"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guru(session: Session, cik: str, display_name: str = "Test Guru") -> Guru:
    return save_guru(
        session,
        Guru(name=f"Corp {cik}", cik=cik, display_name=display_name),
    )


def _make_filing(
    session: Session,
    guru_id: int,
    accession: str = "ACC-001",
    report_date: str = "2024-12-31",
) -> GuruFiling:
    return save_filing(
        session,
        GuruFiling(
            guru_id=guru_id,
            accession_number=accession,
            report_date=report_date,
            filing_date="2025-02-14",
        ),
    )


def _make_holding(
    session: Session,
    filing_id: int,
    guru_id: int,
    ticker: str,
    action: str = HoldingAction.NEW_POSITION.value,
    weight_pct: float = 5.0,
    change_pct: float | None = None,
) -> GuruHolding:
    h = GuruHolding(
        filing_id=filing_id,
        guru_id=guru_id,
        cusip=f"CUSIP-{ticker}",
        ticker=ticker,
        company_name=f"{ticker} Inc",
        value=100.0,
        shares=1000.0,
        action=action,
        change_pct=change_pct,
        weight_pct=weight_pct,
    )
    save_holdings_batch(session, [h])
    return h


def _add_watchlist_stock(session: Session, ticker: str) -> Stock:
    s = Stock(
        ticker=ticker,
        category=StockCategory.GROWTH,
        is_active=True,
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def _add_holding(session: Session, ticker: str) -> Holding:
    h = Holding(
        ticker=ticker,
        category=StockCategory.GROWTH,
        quantity=10.0,
    )
    session.add(h)
    session.commit()
    session.refresh(h)
    return h


# ===========================================================================
# TestComputePortfolioResonance
# ===========================================================================


class TestComputePortfolioResonance:
    def test_should_return_empty_when_no_gurus(self, db_session: Session):
        from application.guru.resonance_service import compute_portfolio_resonance

        _add_watchlist_stock(db_session, "AAPL")
        result = compute_portfolio_resonance(db_session)
        assert result == []

    def test_should_return_empty_overlap_when_no_user_stocks(self, db_session: Session):
        from application.guru.resonance_service import compute_portfolio_resonance

        guru = _make_guru(db_session, cik="0001000001")
        filing = _make_filing(db_session, guru.id, accession="ACC-R001")
        _make_holding(db_session, filing.id, guru.id, "AAPL")

        result = compute_portfolio_resonance(db_session)
        assert len(result) == 1
        assert result[0]["guru_id"] == guru.id
        assert result[0]["overlap_count"] == 0
        assert result[0]["overlapping_tickers"] == []

    def test_should_detect_watchlist_overlap(self, db_session: Session):
        from application.guru.resonance_service import compute_portfolio_resonance

        guru = _make_guru(db_session, cik="0001000002", display_name="Buffett")
        filing = _make_filing(db_session, guru.id, accession="ACC-R002")
        _make_holding(db_session, filing.id, guru.id, "AAPL")
        _make_holding(db_session, filing.id, guru.id, "MSFT")
        _add_watchlist_stock(db_session, "AAPL")

        result = compute_portfolio_resonance(db_session)
        assert len(result) == 1
        assert result[0]["overlap_count"] == 1
        assert "AAPL" in result[0]["overlapping_tickers"]
        assert "MSFT" not in result[0]["overlapping_tickers"]

    def test_should_detect_holding_overlap(self, db_session: Session):
        from application.guru.resonance_service import compute_portfolio_resonance

        guru = _make_guru(db_session, cik="0001000003")
        filing = _make_filing(db_session, guru.id, accession="ACC-R003")
        _make_holding(db_session, filing.id, guru.id, "NVDA")
        _add_holding(db_session, "NVDA")

        result = compute_portfolio_resonance(db_session)
        assert result[0]["overlap_count"] == 1
        assert "NVDA" in result[0]["overlapping_tickers"]

    def test_should_combine_watchlist_and_holding_tickers(self, db_session: Session):
        from application.guru.resonance_service import compute_portfolio_resonance

        guru = _make_guru(db_session, cik="0001000004")
        filing = _make_filing(db_session, guru.id, accession="ACC-R004")
        _make_holding(db_session, filing.id, guru.id, "AAPL")
        _make_holding(db_session, filing.id, guru.id, "NVDA")
        _add_watchlist_stock(db_session, "AAPL")
        _add_holding(db_session, "NVDA")

        result = compute_portfolio_resonance(db_session)
        assert result[0]["overlap_count"] == 2
        assert set(result[0]["overlapping_tickers"]) == {"AAPL", "NVDA"}

    def test_should_sort_by_overlap_count_descending(self, db_session: Session):
        from application.guru.resonance_service import compute_portfolio_resonance

        g1 = _make_guru(db_session, cik="0001000005", display_name="G1")
        g2 = _make_guru(db_session, cik="0001000006", display_name="G2")
        f1 = _make_filing(db_session, g1.id, accession="ACC-R005A")
        f2 = _make_filing(db_session, g2.id, accession="ACC-R005B")
        # G1 has 2 overlapping, G2 has 1
        _make_holding(db_session, f1.id, g1.id, "AAPL")
        _make_holding(db_session, f1.id, g1.id, "MSFT")
        _make_holding(db_session, f2.id, g2.id, "AAPL")
        _add_watchlist_stock(db_session, "AAPL")
        _add_watchlist_stock(db_session, "MSFT")

        result = compute_portfolio_resonance(db_session)
        assert result[0]["overlap_count"] >= result[1]["overlap_count"]

    def test_should_include_action_in_holdings(self, db_session: Session):
        from application.guru.resonance_service import compute_portfolio_resonance

        guru = _make_guru(db_session, cik="0001000007")
        filing = _make_filing(db_session, guru.id, accession="ACC-R006")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "AAPL",
            action=HoldingAction.INCREASED.value,
        )
        _add_watchlist_stock(db_session, "AAPL")

        result = compute_portfolio_resonance(db_session)
        holdings = result[0]["holdings"]
        assert len(holdings) == 1
        assert holdings[0]["action"] == HoldingAction.INCREASED.value

    def test_should_skip_holdings_with_no_ticker(self, db_session: Session):
        from application.guru.resonance_service import compute_portfolio_resonance

        guru = _make_guru(db_session, cik="0001000008")
        filing = _make_filing(db_session, guru.id, accession="ACC-R007")
        # Holding with no ticker (CUSIP-only)
        h = GuruHolding(
            filing_id=filing.id,
            guru_id=guru.id,
            cusip="NOTIICKER",
            ticker=None,
            company_name="Unknown Corp",
            value=50.0,
            shares=500.0,
            action=HoldingAction.NEW_POSITION.value,
        )
        save_holdings_batch(db_session, [h])
        _add_watchlist_stock(db_session, "AAPL")

        result = compute_portfolio_resonance(db_session)
        assert result[0]["overlap_count"] == 0


# ===========================================================================
# TestGetResonanceForTicker
# ===========================================================================


class TestGetResonanceForTicker:
    def test_should_return_empty_when_no_guru_holds_ticker(self, db_session: Session):
        from application.guru.resonance_service import get_resonance_for_ticker

        result = get_resonance_for_ticker(db_session, "AAPL")
        assert result == []

    def test_should_return_guru_info_when_ticker_held(self, db_session: Session):
        from application.guru.resonance_service import get_resonance_for_ticker

        guru = _make_guru(db_session, cik="0002000001", display_name="Dalio")
        filing = _make_filing(db_session, guru.id, accession="ACC-T001")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "NVDA",
            action=HoldingAction.NEW_POSITION.value,
            weight_pct=3.5,
        )

        result = get_resonance_for_ticker(db_session, "NVDA")
        assert len(result) == 1
        assert result[0]["guru_id"] == guru.id
        assert result[0]["guru_display_name"] == "Dalio"
        assert result[0]["action"] == HoldingAction.NEW_POSITION.value
        assert result[0]["weight_pct"] == pytest.approx(3.5)

    def test_should_include_report_date_and_filing_date(self, db_session: Session):
        from application.guru.resonance_service import get_resonance_for_ticker

        guru = _make_guru(db_session, cik="0002000002")
        filing = _make_filing(
            db_session,
            guru.id,
            accession="ACC-T002",
            report_date="2024-12-31",
        )
        _make_holding(db_session, filing.id, guru.id, "MSFT")

        result = get_resonance_for_ticker(db_session, "MSFT")
        assert result[0]["report_date"] == "2024-12-31"
        assert result[0]["filing_date"] == "2025-02-14"

    def test_should_return_multiple_gurus(self, db_session: Session):
        from application.guru.resonance_service import get_resonance_for_ticker

        g1 = _make_guru(db_session, cik="0002000003")
        g2 = _make_guru(db_session, cik="0002000004")
        f1 = _make_filing(db_session, g1.id, accession="ACC-T003")
        f2 = _make_filing(db_session, g2.id, accession="ACC-T004")
        _make_holding(db_session, f1.id, g1.id, "TSLA")
        _make_holding(db_session, f2.id, g2.id, "TSLA")

        result = get_resonance_for_ticker(db_session, "TSLA")
        assert len(result) == 2
        guru_ids = {r["guru_id"] for r in result}
        assert g1.id in guru_ids
        assert g2.id in guru_ids


# ===========================================================================
# TestGetGreatMindsList
# ===========================================================================


class TestGetGreatMindsList:
    def test_should_return_empty_when_no_resonance(self, db_session: Session):
        from application.guru.resonance_service import get_great_minds_list

        result = get_great_minds_list(db_session)
        assert result == []

    def test_should_aggregate_by_ticker(self, db_session: Session):
        from application.guru.resonance_service import get_great_minds_list

        g1 = _make_guru(db_session, cik="0003000001", display_name="A")
        g2 = _make_guru(db_session, cik="0003000002", display_name="B")
        f1 = _make_filing(db_session, g1.id, accession="ACC-GM001")
        f2 = _make_filing(db_session, g2.id, accession="ACC-GM002")
        _make_holding(db_session, f1.id, g1.id, "AAPL")
        _make_holding(db_session, f2.id, g2.id, "AAPL")
        _add_watchlist_stock(db_session, "AAPL")

        result = get_great_minds_list(db_session)
        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"
        assert result[0]["guru_count"] == 2

    def test_should_sort_by_guru_count_descending(self, db_session: Session):
        from application.guru.resonance_service import get_great_minds_list

        g1 = _make_guru(db_session, cik="0003000003", display_name="G1")
        g2 = _make_guru(db_session, cik="0003000004", display_name="G2")
        f1 = _make_filing(db_session, g1.id, accession="ACC-GM003")
        f2 = _make_filing(db_session, g2.id, accession="ACC-GM004")
        # AAPL held by 2 gurus, MSFT by 1
        _make_holding(db_session, f1.id, g1.id, "AAPL")
        _make_holding(db_session, f2.id, g2.id, "AAPL")
        _make_holding(db_session, f1.id, g1.id, "MSFT")
        _add_watchlist_stock(db_session, "AAPL")
        _add_watchlist_stock(db_session, "MSFT")

        result = get_great_minds_list(db_session)
        assert result[0]["ticker"] == "AAPL"
        assert result[0]["guru_count"] == 2
        assert result[-1]["guru_count"] <= result[0]["guru_count"]

    def test_should_include_guru_action_in_result(self, db_session: Session):
        from application.guru.resonance_service import get_great_minds_list

        guru = _make_guru(db_session, cik="0003000005")
        filing = _make_filing(db_session, guru.id, accession="ACC-GM005")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "NVDA",
            action=HoldingAction.SOLD_OUT.value,
        )
        _add_watchlist_stock(db_session, "NVDA")

        result = get_great_minds_list(db_session)
        assert len(result) == 1
        guru_entry = result[0]["gurus"][0]
        assert guru_entry["action"] == HoldingAction.SOLD_OUT.value


# ===========================================================================
# TestSendFilingSeasonDigest
# ===========================================================================


class TestSendFilingSeasonDigest:
    @patch(f"{NOTIFICATION_MODULE}.send_telegram_message_dual")
    def test_should_send_when_filings_available(self, mock_send, db_session: Session):
        from application.messaging.notification_service import send_filing_season_digest

        guru = _make_guru(db_session, cik="0004000001", display_name="Buffett")
        filing = _make_filing(db_session, guru.id, accession="ACC-N001")
        _make_holding(db_session, filing.id, guru.id, "AAPL")

        result = send_filing_season_digest(db_session)

        assert result["status"] == "sent"
        assert result["guru_count"] == 1
        mock_send.assert_called_once()

    def test_should_return_no_data_when_no_filings(self, db_session: Session):
        from application.messaging.notification_service import send_filing_season_digest

        _make_guru(db_session, cik="0004000002")
        result = send_filing_season_digest(db_session)
        assert result["status"] == "no_data"
        assert result["guru_count"] == 0

    @patch(f"{NOTIFICATION_MODULE}.send_telegram_message_dual")
    def test_should_skip_when_guru_alerts_disabled(
        self, mock_send, db_session: Session
    ):
        from application.messaging.notification_service import send_filing_season_digest
        from domain.constants import DEFAULT_NOTIFICATION_PREFERENCES
        from domain.entities import UserPreferences

        prefs = UserPreferences(user_id="default")
        prefs.set_notification_prefs(
            {**DEFAULT_NOTIFICATION_PREFERENCES, "guru_alerts": False}
        )
        db_session.add(prefs)
        db_session.commit()

        result = send_filing_season_digest(db_session)

        assert result["status"] == "skipped"
        mock_send.assert_not_called()

    def test_should_return_no_data_when_no_gurus(self, db_session: Session):
        from application.messaging.notification_service import send_filing_season_digest

        result = send_filing_season_digest(db_session)
        assert result["status"] == "no_data"


# ===========================================================================
# TestSendResonanceAlerts
# ===========================================================================


class TestSendResonanceAlerts:
    @patch(f"{NOTIFICATION_MODULE}.send_telegram_message_dual")
    def test_should_send_alert_for_new_position_overlap(
        self, mock_send, db_session: Session
    ):
        from application.messaging.notification_service import send_resonance_alerts

        guru = _make_guru(db_session, cik="0005000001", display_name="Burry")
        filing = _make_filing(db_session, guru.id, accession="ACC-RA001")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "NVDA",
            action=HoldingAction.NEW_POSITION.value,
        )
        _add_watchlist_stock(db_session, "NVDA")

        result = send_resonance_alerts(db_session)

        assert result["alert_count"] == 1
        assert result["alerts"][0]["ticker"] == "NVDA"
        assert result["alerts"][0]["action"] == HoldingAction.NEW_POSITION.value
        mock_send.assert_called_once()

    @patch(f"{NOTIFICATION_MODULE}.send_telegram_message_dual")
    def test_should_send_alert_for_sold_out_overlap(
        self, mock_send, db_session: Session
    ):
        from application.messaging.notification_service import send_resonance_alerts

        guru = _make_guru(db_session, cik="0005000002")
        filing = _make_filing(db_session, guru.id, accession="ACC-RA002")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "AAPL",
            action=HoldingAction.SOLD_OUT.value,
        )
        _add_watchlist_stock(db_session, "AAPL")

        result = send_resonance_alerts(db_session)

        assert result["alert_count"] == 1
        assert result["alerts"][0]["action"] == HoldingAction.SOLD_OUT.value
        mock_send.assert_called_once()

    @patch(f"{NOTIFICATION_MODULE}.send_telegram_message_dual")
    def test_should_not_send_alert_for_unchanged_overlap(
        self, mock_send, db_session: Session
    ):
        from application.messaging.notification_service import send_resonance_alerts

        guru = _make_guru(db_session, cik="0005000003")
        filing = _make_filing(db_session, guru.id, accession="ACC-RA003")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "MSFT",
            action=HoldingAction.UNCHANGED.value,
        )
        _add_watchlist_stock(db_session, "MSFT")

        result = send_resonance_alerts(db_session)

        assert result["alert_count"] == 0
        mock_send.assert_not_called()

    @patch(f"{NOTIFICATION_MODULE}.send_telegram_message_dual")
    def test_should_not_send_alert_for_increased_or_decreased(
        self, mock_send, db_session: Session
    ):
        from application.messaging.notification_service import send_resonance_alerts

        guru = _make_guru(db_session, cik="0005000004")
        filing = _make_filing(db_session, guru.id, accession="ACC-RA004")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "TSLA",
            action=HoldingAction.INCREASED.value,
        )
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "AMD",
            action=HoldingAction.DECREASED.value,
        )
        _add_watchlist_stock(db_session, "TSLA")
        _add_watchlist_stock(db_session, "AMD")

        result = send_resonance_alerts(db_session)

        assert result["alert_count"] == 0
        mock_send.assert_not_called()

    @patch(f"{NOTIFICATION_MODULE}.send_telegram_message_dual")
    def test_should_skip_when_guru_alerts_disabled(
        self, mock_send, db_session: Session
    ):
        from application.messaging.notification_service import send_resonance_alerts
        from domain.constants import DEFAULT_NOTIFICATION_PREFERENCES
        from domain.entities import UserPreferences

        prefs = UserPreferences(user_id="default")
        prefs.set_notification_prefs(
            {**DEFAULT_NOTIFICATION_PREFERENCES, "guru_alerts": False}
        )
        db_session.add(prefs)
        db_session.commit()

        guru = _make_guru(db_session, cik="0005000005")
        filing = _make_filing(db_session, guru.id, accession="ACC-RA005")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "AAPL",
            action=HoldingAction.NEW_POSITION.value,
        )
        _add_watchlist_stock(db_session, "AAPL")

        result = send_resonance_alerts(db_session)

        assert result["status"] == "skipped"
        assert result["alert_count"] == 0
        mock_send.assert_not_called()

    @patch(f"{NOTIFICATION_MODULE}.send_telegram_message_dual")
    def test_should_return_empty_when_no_overlap(self, mock_send, db_session: Session):
        from application.messaging.notification_service import send_resonance_alerts

        guru = _make_guru(db_session, cik="0005000006")
        filing = _make_filing(db_session, guru.id, accession="ACC-RA006")
        _make_holding(
            db_session,
            filing.id,
            guru.id,
            "AAPL",
            action=HoldingAction.NEW_POSITION.value,
        )
        # No user watchlist / holdings — no overlap

        result = send_resonance_alerts(db_session)

        assert result["alert_count"] == 0
        mock_send.assert_not_called()


# ===========================================================================
# TestGuruFormatters
# ===========================================================================


class TestGuruFormatters:
    def test_format_guru_filing_digest_should_include_guru_name(self):
        from application.formatters import format_guru_filing_digest

        summaries = [
            {
                "guru_display_name": "Warren Buffett",
                "report_date": "2024-12-31",
                "new_positions": 3,
                "sold_out": 1,
                "increased": 5,
                "decreased": 2,
                "top_holdings": [],
            }
        ]
        result = format_guru_filing_digest(summaries, lang="en")
        assert "Warren Buffett" in result
        assert "2024-12-31" in result

    def test_format_guru_filing_digest_should_show_no_changes(self):
        from application.formatters import format_guru_filing_digest

        summaries = [
            {
                "guru_display_name": "Ray Dalio",
                "report_date": "2024-12-31",
                "new_positions": 0,
                "sold_out": 0,
                "increased": 0,
                "decreased": 0,
                "top_holdings": [],
            }
        ]
        result = format_guru_filing_digest(summaries, lang="en")
        assert "No significant" in result

    def test_format_guru_filing_digest_should_return_no_updates_when_empty(self):
        from application.formatters import format_guru_filing_digest

        result = format_guru_filing_digest([], lang="en")
        assert "No guru filing updates" in result

    def test_format_guru_filing_digest_should_include_top_holdings(self):
        from application.formatters import format_guru_filing_digest

        summaries = [
            {
                "guru_display_name": "Buffett",
                "report_date": "2024-12-31",
                "new_positions": 1,
                "sold_out": 0,
                "increased": 0,
                "decreased": 0,
                "top_holdings": [
                    {"ticker": "AAPL", "action": "NEW_POSITION", "weight_pct": 42.5},
                    {"ticker": "BAC", "action": "UNCHANGED", "weight_pct": 10.0},
                    {"ticker": "AXP", "action": "UNCHANGED", "weight_pct": 8.0},
                    # 4th should not appear
                    {"ticker": "KO", "action": "UNCHANGED", "weight_pct": 5.0},
                ],
            }
        ]
        result = format_guru_filing_digest(summaries, lang="en")
        assert "AAPL" in result
        assert "BAC" in result
        assert "AXP" in result
        assert "KO" not in result  # only top 3

    def test_format_resonance_alert_new_position(self):
        from application.formatters import format_resonance_alert

        result = format_resonance_alert(
            "NVDA", "Michael Burry", "NEW_POSITION", lang="en"
        )
        assert "NVDA" in result
        assert "Michael Burry" in result
        assert "🟢" in result

    def test_format_resonance_alert_sold_out(self):
        from application.formatters import format_resonance_alert

        result = format_resonance_alert("TSLA", "Cathie Wood", "SOLD_OUT", lang="zh-TW")
        assert "TSLA" in result
        assert "Cathie Wood" in result
        assert "🔴" in result

    def test_format_resonance_alert_unknown_action_uses_fallback_icon(self):
        from application.formatters import format_resonance_alert

        result = format_resonance_alert("AAPL", "Buffett", "UNKNOWN_ACTION", lang="en")
        assert "⚪" in result
        assert "AAPL" in result
