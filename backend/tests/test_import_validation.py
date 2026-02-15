"""
Import validation tests — stock and holding import endpoints.
Tests Pydantic field validation, max payload size, and error responses.
"""

from domain.constants import ERROR_INVALID_INPUT, GENERIC_VALIDATION_ERROR

# Valid categories: Trend_Setter, Moat, Growth, Bond, Cash
VALID_CATEGORY = "Growth"


def test_stock_import_empty_list(client):
    """Stock import with empty list succeeds (no-op)."""
    response = client.post("/stocks/import", json=[])
    assert response.status_code == 200


def test_stock_import_valid_payload(client):
    """Stock import with valid payload succeeds."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "thesis": "Strong ecosystem",
            "tags": ["tech", "growth"],
            "is_etf": False,
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["imported"] == 1
    assert len(data["errors"]) == 0


def test_stock_import_ticker_uppercase_normalization(client):
    """Stock import normalizes ticker to uppercase."""
    payload = [
        {
            "ticker": "aapl",  # lowercase
            "category": VALID_CATEGORY,
            "thesis": "Test",
            "tags": [],
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 200

    # Verify ticker is stored as uppercase
    stocks_response = client.get("/stocks")
    stocks = stocks_response.json()
    assert any(s["ticker"] == "AAPL" for s in stocks)


def test_stock_import_missing_required_field(client):
    """Stock import rejects payload with missing required field."""
    payload = [
        {
            # Missing "ticker" field
            "category": VALID_CATEGORY,
            "thesis": "Test",
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_stock_import_ticker_too_long(client):
    """Stock import rejects ticker exceeding 20 chars."""
    payload = [
        {
            "ticker": "A" * 21,  # 21 chars
            "category": VALID_CATEGORY,
            "thesis": "Test",
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 422


def test_stock_import_thesis_too_long(client):
    """Stock import rejects thesis exceeding 5000 chars."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "thesis": "X" * 5001,  # 5001 chars
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 422


def test_stock_import_oversized_list(client):
    """Stock import rejects payload with > 1000 items."""
    payload = [
        {
            "ticker": f"TICK{i}",
            "category": VALID_CATEGORY,
            "thesis": "Test",
        }
        for i in range(1001)
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == ERROR_INVALID_INPUT
    assert data["detail"]["detail"] == GENERIC_VALIDATION_ERROR


def test_stock_import_tags_validation(client):
    """Stock import validates tags list length."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "thesis": "Test",
            "tags": ["tag" + str(i) for i in range(21)],  # 21 tags
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 422


def test_holding_import_empty_list(client):
    """Holding import with empty list succeeds (clears existing)."""
    response = client.post("/holdings/import", json=[])
    assert response.status_code == 200


def test_holding_import_valid_payload(client):
    """Holding import with valid payload succeeds."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "quantity": 10.0,
            "cost_basis": 150.0,
            "broker": "IB",
            "currency": "USD",
            "account_type": "IRA",
            "is_cash": False,
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["imported"] == 1
    assert len(data["errors"]) == 0


def test_holding_import_ticker_uppercase_normalization(client):
    """Holding import normalizes ticker to uppercase."""
    payload = [
        {
            "ticker": "aapl",  # lowercase
            "category": VALID_CATEGORY,
            "quantity": 10.0,
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 200

    # Verify ticker is stored as uppercase
    holdings_response = client.get("/holdings")
    holdings = holdings_response.json()
    assert any(h["ticker"] == "AAPL" for h in holdings)


def test_holding_import_currency_uppercase_normalization(client):
    """Holding import normalizes currency to uppercase."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "quantity": 10.0,
            "currency": "usd",  # lowercase
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 200

    # Verify currency is stored as uppercase
    holdings_response = client.get("/holdings")
    holdings = holdings_response.json()
    assert any(h["currency"] == "USD" for h in holdings)


def test_holding_import_missing_required_field(client):
    """Holding import rejects payload with missing required field."""
    payload = [
        {
            # Missing "quantity" field
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 422


def test_holding_import_negative_quantity(client):
    """Holding import rejects negative quantity."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "quantity": -10.0,
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 422


def test_holding_import_zero_quantity(client):
    """Holding import rejects zero quantity."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "quantity": 0.0,
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 422


def test_holding_import_negative_cost_basis(client):
    """Holding import rejects negative cost_basis."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "quantity": 10.0,
            "cost_basis": -150.0,
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 422


def test_holding_import_oversized_list(client):
    """Holding import rejects payload with > 1000 items."""
    payload = [
        {
            "ticker": f"TICK{i}",
            "category": VALID_CATEGORY,
            "quantity": 10.0,
        }
        for i in range(1001)
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == ERROR_INVALID_INPUT
    assert data["detail"]["detail"] == GENERIC_VALIDATION_ERROR


def test_holding_import_ticker_too_long(client):
    """Holding import rejects ticker exceeding 20 chars."""
    payload = [
        {
            "ticker": "A" * 21,
            "category": VALID_CATEGORY,
            "quantity": 10.0,
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 422


def test_holding_import_currency_too_short(client):
    """Holding import rejects currency with < 3 chars."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "quantity": 10.0,
            "currency": "US",  # Only 2 chars
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 422


def test_holding_import_currency_too_long(client):
    """Holding import rejects currency with > 3 chars."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "quantity": 10.0,
            "currency": "USDD",  # 4 chars
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 422


def test_holding_import_cash_holding(client):
    """Holding import accepts cash holding with is_cash=True."""
    payload = [
        {
            "ticker": "USD",
            "category": "Cash",
            "quantity": 1000.0,
            "currency": "USD",
            "is_cash": True,
        }
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["imported"] == 1

    # Verify cash holding is stored
    holdings_response = client.get("/holdings")
    holdings = holdings_response.json()
    cash_holding = next((h for h in holdings if h["is_cash"]), None)
    assert cash_holding is not None
    assert cash_holding["ticker"] == "USD"
