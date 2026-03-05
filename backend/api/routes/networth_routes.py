"""
API — Net Worth routes.
"""

import json

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.schemas import (
    MessageResponse,
    NetWorthItemRequest,
    NetWorthItemResponse,
    NetWorthSnapshotResponse,
    NetWorthSummaryResponse,
    UpdateNetWorthItemRequest,
)
from application.portfolio import net_worth_service
from i18n import get_user_language
from infrastructure.database import get_session

router = APIRouter()


@router.get(
    "/net-worth",
    response_model=NetWorthSummaryResponse,
    summary="Get net worth summary",
)
def get_net_worth(
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> dict:
    return net_worth_service.calculate_net_worth(
        session, display_currency=display_currency.strip().upper()
    )


@router.get(
    "/net-worth/items",
    response_model=list[NetWorthItemResponse],
    summary="List net worth items",
)
def list_net_worth_items(
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> list[dict]:
    return net_worth_service.list_items(
        session, display_currency=display_currency.strip().upper()
    )


@router.post(
    "/net-worth/items",
    response_model=NetWorthItemResponse,
    summary="Create net worth item",
)
def create_net_worth_item(
    payload: NetWorthItemRequest,
    session: Session = Depends(get_session),
) -> dict:
    return net_worth_service.create_item(session, payload.model_dump())


@router.put(
    "/net-worth/items/{item_id}",
    response_model=NetWorthItemResponse,
    summary="Update net worth item",
)
def update_net_worth_item(
    item_id: int,
    payload: UpdateNetWorthItemRequest,
    session: Session = Depends(get_session),
) -> dict:
    lang = get_user_language(session)
    return net_worth_service.update_item(
        session, item_id, payload.model_dump(exclude_unset=True), lang
    )


@router.delete(
    "/net-worth/items/{item_id}",
    response_model=MessageResponse,
    summary="Delete net worth item",
)
def delete_net_worth_item(
    item_id: int,
    session: Session = Depends(get_session),
) -> dict:
    lang = get_user_language(session)
    return net_worth_service.delete_item(session, item_id, lang)


@router.get(
    "/net-worth/history",
    response_model=list[NetWorthSnapshotResponse],
    summary="Get net worth history",
)
def get_net_worth_history(
    days: int = Query(default=30, ge=1, le=730),
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> list[dict]:
    return net_worth_service.get_net_worth_history(
        session, days=days, display_currency=display_currency.strip().upper()
    )


@router.post(
    "/net-worth/snapshot",
    response_model=NetWorthSnapshotResponse,
    summary="Take net worth snapshot",
)
def take_net_worth_snapshot(
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> dict:
    snap = net_worth_service.take_net_worth_snapshot(
        session, display_currency=display_currency.strip().upper()
    )
    try:
        breakdown = json.loads(snap.breakdown)
    except (TypeError, ValueError):
        breakdown = {}
    return {
        "snapshot_date": snap.snapshot_date.isoformat(),
        "investment_value": snap.investment_value,
        "other_assets_value": snap.other_assets_value,
        "liabilities_value": snap.liabilities_value,
        "net_worth": snap.net_worth,
        "display_currency": snap.display_currency,
        "breakdown": breakdown,
    }
