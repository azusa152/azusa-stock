import time
from unittest.mock import MagicMock, patch


def _reset_adapter():
    """Reset all module-level state between tests."""
    import infrastructure.finmind_adapter as adapter

    adapter._consecutive_failures = 0
    adapter._circuit_open_until = 0


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def test_not_available_without_env():
    """Without FINMIND_API_TOKEN, adapter reports unavailable."""
    with patch.dict("os.environ", {}, clear=True):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        assert not adapter.is_available()


def test_available_with_env():
    """With FINMIND_API_TOKEN set, adapter reports available (circuit closed)."""
    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        assert adapter.is_available()


def test_not_available_when_circuit_open():
    """When circuit breaker is open, is_available returns False even with token."""
    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        adapter._circuit_open_until = time.time() + 3600  # open for 1 hour
        assert not adapter.is_available()
        _reset_adapter()


# ---------------------------------------------------------------------------
# Successful fetch and response parsing
# ---------------------------------------------------------------------------


@patch("infrastructure.finmind_adapter.requests.get")
def test_get_financials_returns_gross_profit_and_revenue(mock_get):
    """Parses GrossProfit and Revenue rows from FinMind response."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": [
            {
                "date": "2025-09-30",
                "stock_id": "2330",
                "type": "GrossProfit",
                "value": 250000,
            },
            {
                "date": "2025-09-30",
                "stock_id": "2330",
                "type": "Revenue",
                "value": 1000000,
            },
            {
                "date": "2025-06-30",
                "stock_id": "2330",
                "type": "GrossProfit",
                "value": 230000,
            },
        ]
    }
    mock_get.return_value = mock_resp

    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        result = adapter.get_financials("2330.TW")

    assert result is not None
    assert result["gross_profit"] == 250000.0
    assert result["revenue"] == 1000000.0


@patch("infrastructure.finmind_adapter.requests.get")
def test_get_financials_strips_tw_suffix(mock_get):
    """Ticker .TW suffix is stripped before building the request."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": []}
    mock_get.return_value = mock_resp

    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        adapter.get_financials("2330.TW")

    call_kwargs = mock_get.call_args.kwargs["params"]
    assert call_kwargs["data_id"] == "2330"
    assert call_kwargs["dataset"] == "TaiwanStockFinancialStatements"


@patch("infrastructure.finmind_adapter.requests.get")
def test_get_financials_returns_none_when_no_token(mock_get):
    """Returns None immediately when token is not set (no HTTP call)."""
    with patch.dict("os.environ", {}, clear=True):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        result = adapter.get_financials("2330.TW")

    assert result is None
    mock_get.assert_not_called()


@patch("infrastructure.finmind_adapter.requests.get")
def test_get_financials_returns_none_when_data_empty(mock_get):
    """Returns None when API returns empty data list (no useful financial rows)."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": []}
    mock_get.return_value = mock_resp

    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        result = adapter.get_financials("2330.TW")

    # Empty response = no useful data; return None so resolver skips gracefully.
    # Failure counter is NOT incremented (200 OK is not a network failure).
    assert result is None
    assert adapter._consecutive_failures == 0


@patch("infrastructure.finmind_adapter.requests.get")
def test_latest_value_picks_most_recent_row(mock_get):
    """_latest_value returns the row with the latest date, regardless of API order."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": [
            # Intentionally out of chronological order
            {"date": "2025-06-30", "type": "GrossProfit", "value": 230000},
            {"date": "2025-03-31", "type": "GrossProfit", "value": 210000},
            {"date": "2025-09-30", "type": "GrossProfit", "value": 250000},
        ]
    }
    mock_get.return_value = mock_resp

    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        adapter.get_financials("2330.TW")

    # Verify via _latest_value directly that the most-recent date is picked
    rows = [
        {"date": "2025-06-30", "type": "GrossProfit", "value": 230000},
        {"date": "2025-03-31", "type": "GrossProfit", "value": 210000},
        {"date": "2025-09-30", "type": "GrossProfit", "value": 250000},
    ]
    assert adapter._latest_value(rows, "GrossProfit") == 250000.0
    _reset_adapter()


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


@patch("infrastructure.finmind_adapter.requests.get")
def test_circuit_breaker_opens_after_threshold_failures(mock_get):
    """Circuit opens after _CIRCUIT_BREAKER_THRESHOLD consecutive failures."""
    mock_get.side_effect = RuntimeError("network error")

    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        threshold = adapter._CIRCUIT_BREAKER_THRESHOLD

        for _ in range(threshold):
            adapter.get_financials("2330.TW")

        assert adapter._circuit_open_until > time.time()
        assert not adapter.is_available()
        _reset_adapter()


@patch("infrastructure.finmind_adapter.requests.get")
def test_circuit_breaker_resets_on_success(mock_get):
    """Consecutive failure counter resets to 0 after a successful call."""
    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        # Simulate 1 failure then a success
        mock_get.side_effect = [
            RuntimeError("fail"),
            MagicMock(
                **{
                    "json.return_value": {
                        "data": [
                            {"type": "GrossProfit", "value": 100},
                            {"type": "Revenue", "value": 500},
                        ]
                    }
                }
            ),
        ]
        adapter.get_financials("2330.TW")  # fails
        assert adapter._consecutive_failures == 1

        adapter.get_financials("2330.TW")  # succeeds
        assert adapter._consecutive_failures == 0
        _reset_adapter()


@patch("infrastructure.finmind_adapter.requests.get")
def test_get_financials_skips_when_circuit_open(mock_get):
    """No HTTP call is made when circuit breaker is open."""
    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        adapter._circuit_open_until = time.time() + 3600

        result = adapter.get_financials("2330.TW")

    assert result is None
    mock_get.assert_not_called()
    _reset_adapter()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@patch("infrastructure.finmind_adapter.requests.get")
def test_get_financials_returns_none_on_http_error(mock_get):
    """HTTP errors are caught; None is returned without raising."""
    mock_get.side_effect = RuntimeError("connection refused")

    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        result = adapter.get_financials("2330.TW")

    assert result is None
    _reset_adapter()


@patch("infrastructure.finmind_adapter.requests.get")
def test_get_financials_returns_none_on_malformed_json(mock_get):
    """Malformed JSON is caught; None is returned without raising."""
    mock_resp = MagicMock()
    mock_resp.json.side_effect = ValueError("invalid JSON")
    mock_get.return_value = mock_resp

    with patch.dict("os.environ", {"FINMIND_API_TOKEN": "test-token"}):
        import infrastructure.finmind_adapter as adapter

        _reset_adapter()
        result = adapter.get_financials("2330.TW")

    assert result is None
    _reset_adapter()
