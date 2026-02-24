from unittest.mock import MagicMock, patch


def test_not_available_without_env():
    """Without JQUANTS_API_KEY, adapter returns None."""
    with patch.dict("os.environ", {}, clear=True):
        from infrastructure import jquants_adapter

        jquants_adapter._client = None  # reset singleton
        assert not jquants_adapter.is_available()
        assert jquants_adapter.get_financials("7203") is None


@patch("infrastructure.jquants_adapter._get_client")
def test_get_financials_returns_data(mock_get_client):
    """When client is available, returns financial data."""
    mock_row = MagicMock()
    mock_row.get.side_effect = lambda key, *_: {
        "GrossProfit": 3000000,
        "NetSales": 10000000,
    }.get(key)

    mock_statements = MagicMock()
    mock_statements.empty = False
    mock_statements.iloc.__getitem__ = MagicMock(return_value=mock_row)

    mock_client = MagicMock()
    mock_client.get_statements_range.return_value = mock_statements
    mock_get_client.return_value = mock_client

    from infrastructure import jquants_adapter

    result = jquants_adapter.get_financials("7203.T")
    assert result is not None
    assert result["gross_profit"] == 3000000
    assert result["revenue"] == 10000000


@patch("infrastructure.jquants_adapter._get_client")
def test_get_financials_returns_none_when_empty(mock_get_client):
    """When statements DataFrame is empty, returns None."""
    mock_statements = MagicMock()
    mock_statements.empty = True

    mock_client = MagicMock()
    mock_client.get_statements_range.return_value = mock_statements
    mock_get_client.return_value = mock_client

    from infrastructure import jquants_adapter

    result = jquants_adapter.get_financials("7203.T")
    assert result is None


@patch("infrastructure.jquants_adapter._get_client")
def test_get_financials_returns_none_on_exception(mock_get_client):
    """When client raises, returns None without crashing."""
    mock_client = MagicMock()
    mock_client.get_statements_range.side_effect = RuntimeError("API error")
    mock_get_client.return_value = mock_client

    from infrastructure import jquants_adapter

    result = jquants_adapter.get_financials("7203.T")
    assert result is None


@patch("infrastructure.jquants_adapter._get_client")
def test_get_financials_strips_t_suffix(mock_get_client):
    """Ticker suffix .T is stripped and 0 appended for J-Quants code."""
    mock_statements = MagicMock()
    mock_statements.empty = True

    mock_client = MagicMock()
    mock_client.get_statements_range.return_value = mock_statements
    mock_get_client.return_value = mock_client

    from infrastructure import jquants_adapter

    jquants_adapter.get_financials("7203.T")
    mock_client.get_statements_range.assert_called_once_with(code="72030")
