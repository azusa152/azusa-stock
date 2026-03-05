"""
Application — Net Worth Service。
管理非投資資產 / 負債項目，並提供淨資產彙總與歷史快照。
"""

from __future__ import annotations

import json as _json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import desc
from sqlmodel import select

from domain.constants import (
    DEFAULT_USER_ID,
    ERROR_NET_WORTH_ITEM_NOT_FOUND,
    NET_WORTH_STALE_DAYS,
)
from domain.entities import Holding, NetWorthItem, NetWorthSnapshot, PortfolioSnapshot
from i18n import t
from infrastructure.market_data import get_exchange_rates
from logging_config import get_logger

if TYPE_CHECKING:
    from sqlmodel import Session

logger = get_logger(__name__)


def _convert_with_stored_rate(
    amount: float,
    from_currency: str,
    to_currency: str,
    fx_rate_to_usd: float | None = None,
) -> float:
    """Convert without external API calls using stored/local rates only."""
    from_cur = from_currency.upper()
    to_cur = to_currency.upper()
    if from_cur == to_cur:
        return amount

    if fx_rate_to_usd is None or fx_rate_to_usd <= 0:
        # Unknown conversion path — keep original amount to avoid external call side effects.
        return amount

    if to_cur == "USD":
        return amount * fx_rate_to_usd
    if from_cur == "USD":
        return amount / fx_rate_to_usd
    # Cross-currency path without external data; keep original amount.
    return amount


def _item_to_dict(item: NetWorthItem, display_currency: str = "USD") -> dict:
    value_display = _convert_with_stored_rate(
        float(item.value),
        item.currency,
        display_currency,
        item.fx_rate_to_usd,
    )
    updated_date = item.updated_at.date()
    days_since_update = max((datetime.now(UTC).date() - updated_date).days, 0)
    return {
        "id": item.id,
        "name": item.name,
        "kind": item.kind,
        "category": item.category,
        "value": item.value,
        "value_display": value_display,
        "currency": item.currency,
        "fx_rate_to_usd": item.fx_rate_to_usd,
        "interest_rate": item.interest_rate,
        "minimum_payment": item.minimum_payment,
        "source": item.source or "manual",
        "note": item.note,
        "is_active": item.is_active,
        "is_stale": days_since_update >= NET_WORTH_STALE_DAYS,
        "days_since_update": days_since_update,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def _get_item_or_raise(session: Session, item_id: int, lang: str) -> NetWorthItem:
    item = session.get(NetWorthItem, item_id)
    if item is None or not item.is_active:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_NET_WORTH_ITEM_NOT_FOUND,
                "detail": t("api.net_worth_item_not_found", lang=lang),
            },
        )
    return item


def list_items(session: Session, display_currency: str = "USD") -> list[dict]:
    statement = (
        select(NetWorthItem)
        .where(
            NetWorthItem.user_id == DEFAULT_USER_ID,
            NetWorthItem.is_active == True,  # noqa: E712
        )
        .order_by(
            NetWorthItem.kind, NetWorthItem.category, desc(NetWorthItem.updated_at)
        )
    )
    items = list(session.exec(statement).all())
    return [_item_to_dict(item, display_currency=display_currency) for item in items]


def create_item(session: Session, payload: dict) -> dict:
    item = NetWorthItem(
        user_id=DEFAULT_USER_ID,
        name=payload["name"].strip(),
        kind=payload["kind"].strip().lower(),
        category=payload["category"].strip().lower(),
        value=float(payload["value"]),
        currency=payload.get("currency", "USD").strip().upper(),
        fx_rate_to_usd=payload.get("fx_rate_to_usd"),
        interest_rate=payload.get("interest_rate"),
        minimum_payment=payload.get("minimum_payment"),
        source=(payload.get("source") or "manual").strip().lower(),
        note=(payload.get("note") or "").strip(),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    logger.info("新增淨資產項目：%s (%s/%s)", item.name, item.kind, item.category)
    return _item_to_dict(item)


def update_item(session: Session, item_id: int, payload: dict, lang: str) -> dict:
    item = _get_item_or_raise(session, item_id, lang)
    if "name" in payload and payload["name"] is not None:
        item.name = str(payload["name"]).strip()
    if "kind" in payload and payload["kind"] is not None:
        item.kind = str(payload["kind"]).strip().lower()
    if "category" in payload and payload["category"] is not None:
        item.category = str(payload["category"]).strip().lower()
    if "value" in payload and payload["value"] is not None:
        item.value = float(payload["value"])
    if "currency" in payload and payload["currency"] is not None:
        item.currency = str(payload["currency"]).strip().upper()
    if "fx_rate_to_usd" in payload:
        item.fx_rate_to_usd = payload["fx_rate_to_usd"]
    if "interest_rate" in payload:
        item.interest_rate = payload["interest_rate"]
    if "minimum_payment" in payload:
        item.minimum_payment = payload["minimum_payment"]
    if "note" in payload:
        item.note = str(payload["note"] or "").strip()
    item.updated_at = datetime.now(UTC)

    session.add(item)
    session.commit()
    session.refresh(item)
    return _item_to_dict(item)


def delete_item(session: Session, item_id: int, lang: str) -> dict:
    item = _get_item_or_raise(session, item_id, lang)
    item.is_active = False
    item.updated_at = datetime.now(UTC)
    session.add(item)
    session.commit()
    return {"message": t("api.net_worth_item_deleted", lang=lang, name=item.name)}


def _get_latest_portfolio_snapshot(session: Session) -> PortfolioSnapshot | None:
    return session.exec(
        select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.snapshot_date))
    ).first()


def _list_user_holdings(session: Session) -> list[Holding]:
    return list(
        session.exec(select(Holding).where(Holding.user_id == DEFAULT_USER_ID)).all()
    )


def _calculate_investment_from_holdings(
    holdings: list[Holding], display_currency: str, include_cash: bool = True
) -> float:
    total = 0.0
    for holding in holdings:
        if not include_cash and holding.is_cash:
            continue
        base_amount = (
            float(holding.quantity)
            if holding.is_cash
            else float(holding.quantity) * float(holding.cost_basis or 0.0)
        )
        total += _convert_with_stored_rate(
            base_amount,
            holding.currency,
            display_currency,
            holding.purchase_fx_rate,
        )
    return total


def _extract_cash_value_from_snapshot(snapshot: PortfolioSnapshot | None) -> float:
    if snapshot is None:
        return 0.0
    try:
        category_values = _json.loads(snapshot.category_values or "{}")
    except (TypeError, ValueError):
        return 0.0
    return float(category_values.get("Cash", 0.0))


def _group_cash_holdings_by_currency(
    holdings: list[Holding],
) -> defaultdict[str, float]:
    cash_by_currency: defaultdict[str, float] = defaultdict(float)
    for holding in holdings:
        if not holding.is_cash:
            continue
        cash_by_currency[holding.currency.upper()] += float(holding.quantity)
    return cash_by_currency


def _calculate_cash_value_from_positions(
    cash_by_currency: dict[str, float], display_currency: str
) -> float:
    if not cash_by_currency:
        return 0.0

    currency = display_currency.strip().upper()
    rates = get_exchange_rates(currency, list(cash_by_currency.keys()))
    total = 0.0
    for holding_currency, amount in cash_by_currency.items():
        rate = (
            1.0
            if holding_currency == currency
            else float(rates.get(holding_currency, 1.0))
        )
        total += amount * rate
    return total


def _has_seeded_cash_items(session: Session) -> bool:
    statement = select(NetWorthItem.id).where(
        NetWorthItem.user_id == DEFAULT_USER_ID,
        NetWorthItem.is_active == True,  # noqa: E712
        NetWorthItem.source == "portfolio_cash",
    )
    return session.exec(statement).first() is not None


def get_seed_preview(session: Session, display_currency: str = "USD") -> dict:
    currency = display_currency.strip().upper()
    holdings = _list_user_holdings(session)
    latest_snapshot = _get_latest_portfolio_snapshot(session)
    has_holdings = len(holdings) > 0

    # Cash positions grouped by native currency for intuitive onboarding.
    cash_by_currency = _group_cash_holdings_by_currency(holdings)

    cash_positions = [
        {"currency": ccy, "amount": amount}
        for ccy, amount in sorted(cash_by_currency.items(), key=lambda item: item[0])
        if amount > 0
    ]

    investment_non_cash = (
        (
            float(latest_snapshot.total_value)
            - _extract_cash_value_from_snapshot(latest_snapshot)
        )
        if latest_snapshot is not None
        else _calculate_investment_from_holdings(
            holdings, display_currency=currency, include_cash=False
        )
    )
    investment_non_cash = max(0.0, investment_non_cash)

    cash_in_display_currency = (
        _extract_cash_value_from_snapshot(latest_snapshot)
        if latest_snapshot is not None
        else _calculate_cash_value_from_positions(cash_by_currency, currency)
    )

    existing_item_count = len(
        list(
            session.exec(
                select(NetWorthItem.id).where(
                    NetWorthItem.user_id == DEFAULT_USER_ID,
                    NetWorthItem.is_active == True,  # noqa: E712
                )
            ).all()
        )
    )

    return {
        "has_holdings": has_holdings,
        "investment_value": investment_non_cash,
        "cash_positions": cash_positions,
        "cash_value": cash_in_display_currency,
        "existing_item_count": int(existing_item_count or 0),
        "display_currency": currency,
    }


def seed_from_portfolio(session: Session) -> dict:
    holdings = _list_user_holdings(session)
    cash_by_currency = _group_cash_holdings_by_currency(holdings)

    existing_seeded = list(
        session.exec(
            select(NetWorthItem).where(
                NetWorthItem.user_id == DEFAULT_USER_ID,
                NetWorthItem.is_active == True,  # noqa: E712
                NetWorthItem.source == "portfolio_cash",
            )
        ).all()
    )
    existing_by_currency = {
        (item.currency or "").upper() for item in existing_seeded if item.currency
    }

    created_items: list[dict] = []
    skipped_currencies: list[str] = []
    for currency, amount in sorted(cash_by_currency.items(), key=lambda item: item[0]):
        if amount <= 0:
            continue
        if currency in existing_by_currency:
            skipped_currencies.append(currency)
            continue
        item = NetWorthItem(
            user_id=DEFAULT_USER_ID,
            name=f"Cash ({currency})",
            kind="asset",
            category="savings",
            value=amount,
            currency=currency,
            source="portfolio_cash",
            note="",
        )
        session.add(item)
        session.flush()
        created_items.append(_item_to_dict(item))

    session.commit()
    return {
        "created_items": created_items,
        "skipped_currencies": skipped_currencies,
    }


def calculate_net_worth(session: Session, display_currency: str = "USD") -> dict:
    currency = display_currency.strip().upper()
    latest_snapshot = _get_latest_portfolio_snapshot(session)
    investment_value = float(latest_snapshot.total_value) if latest_snapshot else 0.0
    holdings: list[Holding] = []
    if latest_snapshot is None:
        holdings = _list_user_holdings(session)
        investment_value = _calculate_investment_from_holdings(
            holdings, display_currency=currency, include_cash=True
        )

    if _has_seeded_cash_items(session):
        if latest_snapshot is not None:
            investment_value = max(
                0.0,
                investment_value - _extract_cash_value_from_snapshot(latest_snapshot),
            )
        else:
            total_with_cash = _calculate_investment_from_holdings(
                holdings,
                display_currency=currency,
                include_cash=True,
            )
            total_without_cash = _calculate_investment_from_holdings(
                holdings,
                display_currency=currency,
                include_cash=False,
            )
            cash_only = total_with_cash - total_without_cash
            investment_value = max(0.0, investment_value - max(0.0, cash_only))

    items = list_items(session, display_currency=currency)
    other_assets_value = 0.0
    liabilities_value = 0.0
    breakdown: dict[str, dict[str, float]] = {"asset": {}, "liability": {}}
    stale_count = 0
    for item in items:
        val = float(item["value_display"])
        if item["kind"] == "asset":
            other_assets_value += val
            breakdown["asset"][item["category"]] = (
                breakdown["asset"].get(item["category"], 0.0) + val
            )
        else:
            liabilities_value += val
            breakdown["liability"][item["category"]] = (
                breakdown["liability"].get(item["category"], 0.0) + val
            )
        if item["is_stale"]:
            stale_count += 1

    net_worth = investment_value + other_assets_value - liabilities_value
    return {
        "display_currency": currency,
        "investment_value": investment_value,
        "other_assets_value": other_assets_value,
        "liabilities_value": liabilities_value,
        "net_worth": net_worth,
        "breakdown": breakdown,
        "stale_count": stale_count,
        "items": items,
        "calculated_at": datetime.now(UTC).isoformat(),
    }


def take_net_worth_snapshot(
    session: Session, display_currency: str = "USD"
) -> NetWorthSnapshot:
    summary = calculate_net_worth(session, display_currency=display_currency)
    today = datetime.now(UTC).date()
    existing = session.exec(
        select(NetWorthSnapshot).where(NetWorthSnapshot.snapshot_date == today)
    ).first()
    if existing is not None:
        existing.investment_value = summary["investment_value"]
        existing.other_assets_value = summary["other_assets_value"]
        existing.liabilities_value = summary["liabilities_value"]
        existing.net_worth = summary["net_worth"]
        existing.display_currency = summary["display_currency"]
        existing.breakdown = _json.dumps(summary["breakdown"])
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    snap = NetWorthSnapshot(
        snapshot_date=today,
        investment_value=summary["investment_value"],
        other_assets_value=summary["other_assets_value"],
        liabilities_value=summary["liabilities_value"],
        net_worth=summary["net_worth"],
        display_currency=summary["display_currency"],
        breakdown=_json.dumps(summary["breakdown"]),
    )
    session.add(snap)
    session.commit()
    session.refresh(snap)
    return snap


def get_net_worth_history(
    session: Session, days: int = 30, display_currency: str = "USD"
) -> list[dict]:
    cutoff = datetime.now(UTC).date() - timedelta(days=days)
    snaps = list(
        session.exec(
            select(NetWorthSnapshot)
            .where(NetWorthSnapshot.snapshot_date >= cutoff)
            .order_by(NetWorthSnapshot.snapshot_date)
        ).all()
    )
    if snaps:
        result = []
        for snap in snaps:
            try:
                breakdown = _json.loads(snap.breakdown)
            except (TypeError, ValueError):
                breakdown = {}
            result.append(
                {
                    "snapshot_date": snap.snapshot_date.isoformat(),
                    "investment_value": snap.investment_value,
                    "other_assets_value": snap.other_assets_value,
                    "liabilities_value": snap.liabilities_value,
                    "net_worth": snap.net_worth,
                    "display_currency": snap.display_currency,
                    "breakdown": breakdown,
                }
            )
        return result

    # Empty history fallback: return today's computed summary to keep UI intuitive.
    summary = calculate_net_worth(session, display_currency=display_currency)
    return [
        {
            "snapshot_date": datetime.now(UTC).date().isoformat(),
            "investment_value": summary["investment_value"],
            "other_assets_value": summary["other_assets_value"],
            "liabilities_value": summary["liabilities_value"],
            "net_worth": summary["net_worth"],
            "display_currency": summary["display_currency"],
            "breakdown": summary["breakdown"],
        }
    ]
