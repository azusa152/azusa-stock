"""
Application — Holding Service。
封裝持倉的 CRUD 與匯入/匯出邏輯，路由層不直接存取 ORM。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

from domain.constants import (
    DEFAULT_USER_ID,
    ERROR_HOLDING_NOT_FOUND,
    ERROR_INVALID_INPUT,
    GENERIC_VALIDATION_ERROR,
)
from domain.entities import Holding
from domain.enums import StockCategory
from i18n import t
from infrastructure import repositories as repo
from infrastructure.market_data import get_exchange_rate
from logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _holding_to_dict(h: Holding) -> dict:
    return {
        "id": h.id,
        "ticker": h.ticker,
        "category": h.category,
        "quantity": h.quantity,
        "cost_basis": h.cost_basis,
        "broker": h.broker,
        "currency": h.currency,
        "account_type": h.account_type,
        "is_cash": h.is_cash,
        "purchase_fx_rate": h.purchase_fx_rate,
        "updated_at": h.updated_at.isoformat(),
    }


def _get_holding_or_raise(session: Session, holding_id: int, lang: str) -> Holding:
    holding = repo.find_holding_by_id(session, holding_id)
    if not holding:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_HOLDING_NOT_FOUND,
                "detail": t("api.holding_not_found", lang=lang),
            },
        )
    return holding


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def list_holdings(session: Session) -> list[dict]:
    """Return all holdings as dicts, ordered by id."""
    holdings = repo.find_all_holdings(session)
    return [_holding_to_dict(h) for h in holdings]


def create_holding(session: Session, payload: dict, lang: str) -> dict:
    """Create a new holding. Returns the created holding dict."""
    currency = payload["currency"].strip().upper()
    purchase_fx_rate = get_exchange_rate("USD", currency) if currency != "USD" else 1.0
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=payload["ticker"].strip().upper(),
        category=payload["category"],
        quantity=payload["quantity"],
        cost_basis=payload.get("cost_basis"),
        broker=payload.get("broker"),
        currency=currency,
        account_type=payload.get("account_type"),
        is_cash=payload.get("is_cash", False),
        purchase_fx_rate=purchase_fx_rate,
    )
    saved = repo.save_holding(session, holding)
    logger.info("新增持倉：%s（%s）", saved.ticker, saved.category)
    return _holding_to_dict(saved)


def create_cash_holding(session: Session, payload: dict, lang: str) -> dict:
    """Create a cash holding. Returns the created holding dict."""
    currency_upper = payload["currency"].strip().upper()
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=currency_upper,
        category=StockCategory.CASH,
        quantity=payload["amount"],
        cost_basis=1.0,
        broker=payload.get("broker"),
        currency=currency_upper,
        account_type=payload.get("account_type"),
        is_cash=True,
    )
    saved = repo.save_holding(session, holding)
    logger.info("新增現金持倉：%s %.2f", saved.ticker, saved.quantity)
    return _holding_to_dict(saved)


def update_holding(session: Session, holding_id: int, payload: dict, lang: str) -> dict:
    """Partially update an existing holding. Only provided fields are overwritten.

    Raises HTTPException 404 if not found.
    """
    holding = _get_holding_or_raise(session, holding_id, lang)
    if "ticker" in payload:
        holding.ticker = payload["ticker"].strip().upper()
    if "category" in payload:
        holding.category = payload["category"]
    if "quantity" in payload:
        holding.quantity = payload["quantity"]
    if "cost_basis" in payload:
        holding.cost_basis = payload["cost_basis"]
    if "broker" in payload:
        holding.broker = payload["broker"]
    if "currency" in payload:
        holding.currency = payload["currency"].strip().upper()
    if "account_type" in payload:
        holding.account_type = payload["account_type"]
    if "is_cash" in payload:
        holding.is_cash = payload["is_cash"]
    holding.updated_at = datetime.now(UTC)
    saved = repo.save_holding(session, holding)
    return _holding_to_dict(saved)


def delete_holding(session: Session, holding_id: int, lang: str) -> dict:
    """Delete a holding. Raises HTTPException 404 if not found."""
    holding = _get_holding_or_raise(session, holding_id, lang)
    ticker = holding.ticker
    repo.delete_holding(session, holding)
    logger.info("刪除持倉：%s", ticker)
    return {"message": t("api.holding_deleted", lang=lang, ticker=ticker)}


def export_holdings(session: Session) -> list[dict]:
    """Export all holdings as import-compatible dicts."""
    holdings = repo.find_all_holdings(session)
    return [
        {
            "ticker": h.ticker,
            "category": h.category.value
            if hasattr(h.category, "value")
            else h.category,
            "quantity": h.quantity,
            "cost_basis": h.cost_basis,
            "broker": h.broker,
            "currency": h.currency,
            "account_type": h.account_type,
            "is_cash": h.is_cash,
        }
        for h in holdings
    ]


def import_holdings(session: Session, data: list[dict], lang: str) -> dict:
    """Bulk import holdings (replace all). Returns {imported, errors}."""
    if len(data) > 1000:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )

    repo.delete_all_holdings(session)

    count = 0
    errors: list[str] = []
    for i, item in enumerate(data):
        try:
            holding = Holding(
                user_id=DEFAULT_USER_ID,
                ticker=item["ticker"],
                category=item["category"],
                quantity=item["quantity"],
                cost_basis=item.get("cost_basis"),
                broker=item.get("broker"),
                currency=item["currency"],
                account_type=item.get("account_type"),
                is_cash=item.get("is_cash", False),
            )
            session.add(holding)
            count += 1
        except Exception as e:
            logger.warning("持倉匯入第 %d 筆失敗：%s", i + 1, e)
            errors.append(t("api.import_item_failed", lang=lang, index=i + 1))

    session.commit()
    logger.info("匯入持倉完成：%d 筆成功，%d 筆失敗。", count, len(errors))
    return {
        "message": t("api.import_done", lang=lang, count=count),
        "imported": count,
        "errors": errors,
    }
