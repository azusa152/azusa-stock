"""
Tests for holding_service.
Uses db_session fixture (in-memory SQLite) — no mocks required for pure CRUD.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from application.portfolio.holding_service import (
    create_cash_holding,
    create_holding,
    delete_holding,
    export_holdings,
    import_holdings,
    list_holdings,
    update_holding,
)
from domain.constants import DEFAULT_USER_ID
from domain.entities import Holding
from domain.enums import StockCategory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LANG = "zh-TW"


def _make_payload(**kwargs) -> dict:
    defaults = {
        "ticker": "AAPL",
        "category": StockCategory.TREND_SETTER,
        "quantity": 10.0,
        "cost_basis": 150.0,
        "broker": None,
        "currency": "usd",
        "account_type": None,
        "is_cash": False,
    }
    defaults.update(kwargs)
    return defaults


def _seed_holding(
    session: Session, ticker: str = "AAPL", quantity: float = 5.0
) -> Holding:
    h = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        category=StockCategory.TREND_SETTER,
        quantity=quantity,
        currency="USD",
    )
    session.add(h)
    session.commit()
    session.refresh(h)
    return h


# ---------------------------------------------------------------------------
# list_holdings
# ---------------------------------------------------------------------------


class TestListHoldings:
    def test_returns_empty_when_no_holdings(self, db_session: Session) -> None:
        result = list_holdings(db_session)
        assert result == []

    def test_returns_all_holdings_as_dicts(self, db_session: Session) -> None:
        _seed_holding(db_session, "AAPL")
        _seed_holding(db_session, "MSFT")
        result = list_holdings(db_session)
        assert len(result) == 2
        tickers = {r["ticker"] for r in result}
        assert tickers == {"AAPL", "MSFT"}

    def test_dict_contains_required_keys(self, db_session: Session) -> None:
        _seed_holding(db_session)
        result = list_holdings(db_session)
        keys = set(result[0].keys())
        assert {
            "id",
            "ticker",
            "category",
            "quantity",
            "currency",
            "updated_at",
        } <= keys


# ---------------------------------------------------------------------------
# create_holding
# ---------------------------------------------------------------------------


class TestCreateHolding:
    def test_creates_holding_with_valid_payload(self, db_session: Session) -> None:
        result = create_holding(db_session, _make_payload(), _LANG)
        assert result["ticker"] == "AAPL"
        assert result["currency"] == "USD"  # uppercased
        assert result["quantity"] == 10.0
        assert result["id"] is not None

    def test_normalises_ticker_and_currency_to_uppercase(
        self, db_session: Session
    ) -> None:
        result = create_holding(
            db_session, _make_payload(ticker="msft", currency="usd"), _LANG
        )
        assert result["ticker"] == "MSFT"
        assert result["currency"] == "USD"

    def test_persists_to_database(self, db_session: Session) -> None:
        create_holding(db_session, _make_payload(), _LANG)
        assert len(list_holdings(db_session)) == 1


# ---------------------------------------------------------------------------
# create_cash_holding
# ---------------------------------------------------------------------------


class TestCreateCashHolding:
    def test_creates_cash_holding(self, db_session: Session) -> None:
        payload = {
            "currency": "twd",
            "amount": 100000.0,
            "broker": None,
            "account_type": None,
        }
        result = create_cash_holding(db_session, payload, _LANG)
        assert result["ticker"] == "TWD"
        assert result["currency"] == "TWD"
        assert result["is_cash"] is True
        assert result["cost_basis"] == 1.0
        assert result["category"] == StockCategory.CASH


# ---------------------------------------------------------------------------
# update_holding
# ---------------------------------------------------------------------------


class TestUpdateHolding:
    def test_updates_existing_holding(self, db_session: Session) -> None:
        holding = _seed_holding(db_session)
        payload = _make_payload(quantity=20.0, cost_basis=180.0)
        result = update_holding(db_session, holding.id, payload, _LANG)  # type: ignore[arg-type]
        assert result["quantity"] == 20.0
        assert result["cost_basis"] == 180.0

    def test_raises_404_for_nonexistent_id(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            update_holding(db_session, 99999, _make_payload(), _LANG)
        assert exc_info.value.status_code == 404

    def test_normalises_ticker_and_currency(self, db_session: Session) -> None:
        holding = _seed_holding(db_session)
        payload = _make_payload(ticker="tsla", currency="jpy")
        result = update_holding(db_session, holding.id, payload, _LANG)  # type: ignore[arg-type]
        assert result["ticker"] == "TSLA"
        assert result["currency"] == "JPY"


# ---------------------------------------------------------------------------
# delete_holding
# ---------------------------------------------------------------------------


class TestDeleteHolding:
    def test_deletes_existing_holding(self, db_session: Session) -> None:
        holding = _seed_holding(db_session)
        result = delete_holding(db_session, holding.id, _LANG)  # type: ignore[arg-type]
        assert "message" in result
        assert len(list_holdings(db_session)) == 0

    def test_raises_404_for_nonexistent_id(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            delete_holding(db_session, 99999, _LANG)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# export_holdings
# ---------------------------------------------------------------------------


class TestExportHoldings:
    def test_returns_import_compatible_format(self, db_session: Session) -> None:
        _seed_holding(db_session)
        result = export_holdings(db_session)
        assert len(result) == 1
        item = result[0]
        # Should NOT include id or updated_at (import format)
        assert "id" not in item
        assert "updated_at" not in item
        assert "ticker" in item
        assert "category" in item

    def test_returns_empty_list_when_no_holdings(self, db_session: Session) -> None:
        assert export_holdings(db_session) == []


# ---------------------------------------------------------------------------
# import_holdings
# ---------------------------------------------------------------------------


class TestImportHoldings:
    def _import_payload(self) -> list[dict]:
        return [
            {
                "ticker": "VTI",
                "category": StockCategory.TREND_SETTER,
                "quantity": 50.0,
                "currency": "USD",
                "is_cash": False,
            }
        ]

    def test_imports_holdings_successfully(self, db_session: Session) -> None:
        result = import_holdings(db_session, self._import_payload(), _LANG)
        assert result["imported"] == 1
        assert result["errors"] == []

    def test_replaces_existing_holdings(self, db_session: Session) -> None:
        _seed_holding(db_session, "AAPL")
        _seed_holding(db_session, "MSFT")
        import_holdings(db_session, self._import_payload(), _LANG)
        remaining = list_holdings(db_session)
        assert len(remaining) == 1
        assert remaining[0]["ticker"] == "VTI"

    def test_raises_400_when_data_exceeds_limit(self, db_session: Session) -> None:
        big_data = [self._import_payload()[0]] * 1001
        with pytest.raises(HTTPException) as exc_info:
            import_holdings(db_session, big_data, _LANG)
        assert exc_info.value.status_code == 400

    def test_records_errors_for_invalid_items(self, db_session: Session) -> None:
        bad_item = {"ticker": "BAD"}  # missing required fields
        result = import_holdings(db_session, [bad_item], _LANG)
        assert result["imported"] == 0
        assert len(result["errors"]) == 1
