"""Tests for net worth service."""

from datetime import UTC, datetime

from sqlmodel import Session

from application.portfolio.net_worth_service import (
    calculate_net_worth,
    create_item,
    delete_item,
    get_net_worth_history,
    list_items,
    take_net_worth_snapshot,
)
from domain.entities import Holding, PortfolioSnapshot


def test_calculate_net_worth_should_aggregate_investments_assets_and_liabilities(
    db_session: Session,
) -> None:
    db_session.add(
        PortfolioSnapshot(
            snapshot_date=datetime.now(UTC).date(),
            total_value=1000.0,
            category_values="{}",
            display_currency="USD",
        )
    )
    db_session.commit()

    create_item(
        db_session,
        {
            "name": "Savings",
            "kind": "asset",
            "category": "savings",
            "value": 200.0,
            "currency": "USD",
        },
    )
    create_item(
        db_session,
        {
            "name": "Mortgage",
            "kind": "liability",
            "category": "mortgage",
            "value": 300.0,
            "currency": "USD",
        },
    )

    result = calculate_net_worth(db_session, display_currency="USD")

    assert result["investment_value"] == 1000.0
    assert result["other_assets_value"] == 200.0
    assert result["liabilities_value"] == 300.0
    assert result["net_worth"] == 900.0


def test_delete_item_should_soft_delete_and_exclude_from_list(
    db_session: Session,
) -> None:
    created = create_item(
        db_session,
        {
            "name": "Car Loan",
            "kind": "liability",
            "category": "loan",
            "value": 100.0,
            "currency": "USD",
        },
    )
    delete_item(db_session, created["id"], "en")

    items = list_items(db_session, "USD")
    assert items == []


def test_snapshot_and_history_should_return_saved_net_worth(
    db_session: Session,
) -> None:
    db_session.add(
        PortfolioSnapshot(
            snapshot_date=datetime.now(UTC).date(),
            total_value=500.0,
            category_values="{}",
            display_currency="USD",
        )
    )
    db_session.commit()

    snap = take_net_worth_snapshot(db_session, display_currency="USD")
    history = get_net_worth_history(db_session, days=30, display_currency="USD")

    assert snap.net_worth == 500.0
    assert len(history) >= 1
    assert history[-1]["net_worth"] == 500.0


def test_calculate_net_worth_should_fallback_to_holdings_when_snapshot_missing(
    db_session: Session,
) -> None:
    db_session.add(
        Holding(
            ticker="AAPL",
            quantity=2.0,
            cost_basis=100.0,
            category="GROWTH",
            currency="USD",
        )
    )
    db_session.commit()

    result = calculate_net_worth(db_session, display_currency="USD")

    assert result["investment_value"] == 200.0
    assert result["net_worth"] == 200.0
