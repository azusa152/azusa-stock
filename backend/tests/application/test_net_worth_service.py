"""Tests for net worth service."""

import json
from datetime import UTC, datetime
from unittest.mock import patch

from sqlmodel import Session

from application.portfolio.net_worth_service import (
    calculate_net_worth,
    create_item,
    delete_item,
    get_net_worth_history,
    get_seed_preview,
    list_items,
    seed_from_portfolio,
    take_net_worth_snapshot,
)
from domain.entities import Holding, PortfolioSnapshot
from domain.enums import StockCategory


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


def test_create_item_should_store_minimum_payment(db_session: Session) -> None:
    created = create_item(
        db_session,
        {
            "name": "Card Debt",
            "kind": "liability",
            "category": "credit_card",
            "value": 500.0,
            "currency": "USD",
            "minimum_payment": 50.0,
        },
    )

    assert created["minimum_payment"] == 50.0


def test_seed_from_portfolio_should_create_items_and_be_idempotent(
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            Holding(
                ticker="USD",
                quantity=1000.0,
                cost_basis=1.0,
                category=StockCategory.CASH,
                currency="USD",
                is_cash=True,
            ),
            Holding(
                ticker="TWD",
                quantity=6000.0,
                cost_basis=1.0,
                category=StockCategory.CASH,
                currency="TWD",
                is_cash=True,
            ),
        ]
    )
    db_session.commit()

    first = seed_from_portfolio(db_session)
    second = seed_from_portfolio(db_session)

    assert len(first["created_items"]) == 2
    assert first["skipped_currencies"] == []
    assert len(second["created_items"]) == 0
    assert set(second["skipped_currencies"]) == {"USD", "TWD"}

    items = list_items(db_session, "USD")
    seeded = [item for item in items if item["source"] == "portfolio_cash"]
    assert len(seeded) == 2
    assert all(item["category"] == "savings" for item in seeded)


def test_get_seed_preview_should_return_non_cash_investment_and_cash_positions(
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            Holding(
                ticker="AAPL",
                quantity=2.0,
                cost_basis=100.0,
                category=StockCategory.GROWTH,
                currency="USD",
                is_cash=False,
                purchase_fx_rate=1.0,
            ),
            Holding(
                ticker="USD",
                quantity=300.0,
                cost_basis=1.0,
                category=StockCategory.CASH,
                currency="USD",
                is_cash=True,
            ),
        ]
    )
    db_session.commit()

    preview = get_seed_preview(db_session, display_currency="USD")

    assert preview["has_holdings"] is True
    assert preview["investment_value"] == 200.0
    assert preview["cash_value"] == 300.0
    assert preview["cash_positions"] == [{"currency": "USD", "amount": 300.0}]
    assert preview["existing_item_count"] == 0


def test_get_seed_preview_should_convert_cash_value_with_rates_when_no_snapshot(
    db_session: Session,
) -> None:
    db_session.add(
        Holding(
            ticker="JPY",
            quantity=10000.0,
            cost_basis=1.0,
            category=StockCategory.CASH,
            currency="JPY",
            is_cash=True,
            purchase_fx_rate=None,
        )
    )
    db_session.commit()

    with patch(
        "application.portfolio.net_worth_service.get_exchange_rates",
        return_value={"USD": 1.0, "JPY": 0.01},
    ):
        preview = get_seed_preview(db_session, display_currency="USD")

    assert preview["cash_positions"] == [{"currency": "JPY", "amount": 10000.0}]
    assert preview["cash_value"] == 100.0


def test_calculate_net_worth_should_exclude_cash_from_investment_when_seeded(
    db_session: Session,
) -> None:
    db_session.add(
        PortfolioSnapshot(
            snapshot_date=datetime.now(UTC).date(),
            total_value=1000.0,
            category_values=json.dumps({"Cash": 200.0, "Growth": 800.0}),
            display_currency="USD",
        )
    )
    db_session.commit()
    create_item(
        db_session,
        {
            "name": "Cash (USD)",
            "kind": "asset",
            "category": "savings",
            "value": 200.0,
            "currency": "USD",
            "source": "portfolio_cash",
        },
    )

    result = calculate_net_worth(db_session, display_currency="USD")
    assert result["investment_value"] == 800.0
    assert result["other_assets_value"] == 200.0
    assert result["net_worth"] == 1000.0
