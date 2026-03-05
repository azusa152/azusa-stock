"""Tests for net worth domain entities."""

from datetime import date

from domain.entities import NetWorthItem, NetWorthSnapshot


def test_net_worth_item_should_have_expected_defaults() -> None:
    item = NetWorthItem(
        name="Primary Residence",
        kind="asset",
        category="property",
        value=1000000.0,
    )

    assert item.currency == "USD"
    assert item.is_active is True
    assert item.note == ""
    assert item.minimum_payment is None
    assert item.user_id == "default"


def test_net_worth_snapshot_should_store_totals() -> None:
    snap = NetWorthSnapshot(
        snapshot_date=date(2026, 3, 5),
        investment_value=200000.0,
        other_assets_value=300000.0,
        liabilities_value=100000.0,
        net_worth=400000.0,
    )

    assert snap.display_currency == "USD"
    assert snap.breakdown == "{}"
    assert snap.net_worth == 400000.0
