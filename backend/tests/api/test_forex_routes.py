"""Tests for GET /forex/{base}/{quote}/history-long endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient


MOCK_HISTORY = [
    {"date": "2026-02-08", "close": 30.0},
    {"date": "2026-02-09", "close": 30.5},
    {"date": "2026-02-10", "close": 31.0},
]


class TestGetForexHistory:
    """Tests for forex history endpoint."""

    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    def test_should_return_200_with_data(self, mock_get_history, client: TestClient):
        # Arrange
        mock_get_history.return_value = MOCK_HISTORY

        # Act
        response = client.get("/forex/USD/TWD/history-long")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["date"] == "2026-02-08"
        assert data[0]["close"] == 30.0
        assert data[2]["close"] == 31.0

    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    def test_should_return_empty_list_when_no_data(
        self, mock_get_history, client: TestClient
    ):
        # Arrange
        mock_get_history.return_value = []

        # Act
        response = client.get("/forex/USD/TWD/history-long")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    def test_should_accept_lowercase_currency_codes(
        self, mock_get_history, client: TestClient
    ):
        # Arrange
        mock_get_history.return_value = MOCK_HISTORY

        # Act
        response = client.get("/forex/usd/twd/history-long")

        # Assert
        assert response.status_code == 200
        # Verify the service receives uppercased codes
        mock_get_history.assert_called_once_with("USD", "TWD")

    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    def test_should_return_200_with_empty_list_on_api_failure(
        self, mock_get_history, client: TestClient
    ):
        # Arrange: infrastructure raises
        mock_get_history.side_effect = RuntimeError("yfinance down")

        # Act
        response = client.get("/forex/USD/TWD/history-long")

        # Assert: graceful degradation, not 500
        assert response.status_code == 200
        assert response.json() == []
