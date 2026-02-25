"""Tests for GET /stress-test endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from application.stock.stock_service import StockNotFoundError


# ---------------------------------------------------------------------------
# Mock Data
# ---------------------------------------------------------------------------

MOCK_STRESS_TEST_RESULT = {
    "portfolio_beta": 1.25,
    "scenario_drop_pct": -20.0,
    "total_value": 100000.0,
    "total_loss": -25000.0,
    "total_loss_pct": -25.0,
    "display_currency": "USD",
    "pain_level": {
        "level": "high",
        "label": "傷筋動骨 (Bear Market)",
        "emoji": "orange",
    },
    "advice": [],
    "disclaimer": "⚠️ 此為線性 CAPM 簡化模型，實際崩盤中相關性會趨近 1、流動性枯竭可能導致更大跌幅。本模擬僅供參考，不構成投資建議。",
    "holdings_breakdown": [
        {
            "ticker": "NVDA",
            "category": "Growth",
            "beta": 1.8,
            "market_value": 50000.0,
            "expected_drop_pct": -36.0,
            "expected_loss": -18000.0,
        },
        {
            "ticker": "BRK.B",
            "category": "Moat",
            "beta": 0.8,
            "market_value": 30000.0,
            "expected_drop_pct": -16.0,
            "expected_loss": -4800.0,
        },
        {
            "ticker": "TLT",
            "category": "Bond",
            "beta": 0.3,
            "market_value": 20000.0,
            "expected_drop_pct": -6.0,
            "expected_loss": -1200.0,
        },
    ],
}


# ---------------------------------------------------------------------------
# Happy Path Tests
# ---------------------------------------------------------------------------


class TestGetStressTestHappyPath:
    """Tests for stress test endpoint happy path."""

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_return_200_with_default_params(
        self, mock_service, client: TestClient
    ):
        # Arrange
        mock_service.return_value = MOCK_STRESS_TEST_RESULT

        # Act
        response = client.get("/stress-test")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["portfolio_beta"] == 1.25
        assert data["scenario_drop_pct"] == -20.0
        assert data["total_value"] == 100000.0
        assert data["total_loss"] == -25000.0
        assert data["display_currency"] == "USD"
        assert data["pain_level"]["level"] == "high"
        assert len(data["holdings_breakdown"]) == 3

        # Verify service called with defaults
        mock_service.assert_called_once()
        call_args = mock_service.call_args
        assert call_args[1]["scenario_drop_pct"] == -20.0
        assert call_args[1]["display_currency"] == "USD"

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_accept_custom_scenario(self, mock_service, client: TestClient):
        # Arrange
        mock_result = MOCK_STRESS_TEST_RESULT.copy()
        mock_result["scenario_drop_pct"] = -30.0
        mock_service.return_value = mock_result

        # Act
        response = client.get("/stress-test?scenario_drop_pct=-30")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["scenario_drop_pct"] == -30.0

        # Verify service called with custom scenario
        call_args = mock_service.call_args
        assert call_args[1]["scenario_drop_pct"] == -30.0

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_accept_custom_display_currency(
        self, mock_service, client: TestClient
    ):
        # Arrange
        mock_result = MOCK_STRESS_TEST_RESULT.copy()
        mock_result["display_currency"] = "TWD"
        mock_service.return_value = mock_result

        # Act
        response = client.get("/stress-test?display_currency=TWD")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["display_currency"] == "TWD"

        # Verify service called with TWD (uppercased)
        call_args = mock_service.call_args
        assert call_args[1]["display_currency"] == "TWD"

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_uppercase_display_currency(self, mock_service, client: TestClient):
        # Arrange
        mock_result = MOCK_STRESS_TEST_RESULT.copy()
        mock_result["display_currency"] = "TWD"
        mock_service.return_value = mock_result

        # Act
        response = client.get("/stress-test?display_currency=twd")

        # Assert
        assert response.status_code == 200

        # Verify service receives uppercased
        call_args = mock_service.call_args
        assert call_args[1]["display_currency"] == "TWD"

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_handle_extreme_drop_scenario(
        self, mock_service, client: TestClient
    ):
        # Arrange
        mock_result = MOCK_STRESS_TEST_RESULT.copy()
        mock_result["scenario_drop_pct"] = -50.0
        mock_result["pain_level"] = {
            "level": "panic",
            "label": "睡不著覺 (Panic Zone)",
            "emoji": "red",
        }
        mock_service.return_value = mock_result

        # Act
        response = client.get("/stress-test?scenario_drop_pct=-50")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["scenario_drop_pct"] == -50.0
        assert data["pain_level"]["level"] == "panic"

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_handle_mild_drop_scenario(self, mock_service, client: TestClient):
        # Arrange
        mock_result = MOCK_STRESS_TEST_RESULT.copy()
        mock_result["scenario_drop_pct"] = -5.0
        mock_result["total_loss"] = -6250.0
        mock_result["total_loss_pct"] = -6.25
        mock_result["pain_level"] = {
            "level": "low",
            "label": "微風輕拂 (Just a Scratch)",
            "emoji": "green",
        }
        mock_service.return_value = mock_result

        # Act
        response = client.get("/stress-test?scenario_drop_pct=-5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["scenario_drop_pct"] == -5.0
        assert data["pain_level"]["level"] == "low"


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestGetStressTestErrorHandling:
    """Tests for stress test endpoint error handling."""

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_return_404_when_no_holdings(self, mock_service, client: TestClient):
        # Arrange
        mock_service.side_effect = StockNotFoundError(
            "尚未輸入任何持倉，請先新增資產。"
        )

        # Act
        response = client.get("/stress-test")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "error_code" in data["detail"]
        assert data["detail"]["error_code"] == "HOLDING_NOT_FOUND"
        assert "尚未輸入任何持倉" in data["detail"]["detail"]

    def test_should_return_422_when_scenario_too_positive(self, client: TestClient):
        # Act
        response = client.get("/stress-test?scenario_drop_pct=10")

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "error_code" in data["detail"]
        assert data["detail"]["error_code"] == "INVALID_SCENARIO_DROP"
        assert "-50 到 0 之間" in data["detail"]["detail"]

    def test_should_return_422_when_scenario_too_negative(self, client: TestClient):
        # Act
        response = client.get("/stress-test?scenario_drop_pct=-60")

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error_code"] == "INVALID_SCENARIO_DROP"

    def test_should_return_422_when_scenario_at_boundary_minus_51(
        self, client: TestClient
    ):
        # Act
        response = client.get("/stress-test?scenario_drop_pct=-51")

        # Assert
        assert response.status_code == 422

    def test_should_return_422_when_scenario_at_boundary_plus_1(
        self, client: TestClient
    ):
        # Act
        response = client.get("/stress-test?scenario_drop_pct=1")

        # Assert
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Boundary Tests
# ---------------------------------------------------------------------------


class TestGetStressTestBoundary:
    """Tests for stress test endpoint boundary conditions."""

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_accept_scenario_at_minus_50(self, mock_service, client: TestClient):
        # Arrange
        mock_result = MOCK_STRESS_TEST_RESULT.copy()
        mock_result["scenario_drop_pct"] = -50.0
        mock_service.return_value = mock_result

        # Act
        response = client.get("/stress-test?scenario_drop_pct=-50")

        # Assert
        assert response.status_code == 200

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_should_accept_scenario_at_zero(self, mock_service, client: TestClient):
        # Arrange
        mock_result = MOCK_STRESS_TEST_RESULT.copy()
        mock_result["scenario_drop_pct"] = 0.0
        mock_result["total_loss"] = 0.0
        mock_result["total_loss_pct"] = 0.0
        mock_service.return_value = mock_result

        # Act
        response = client.get("/stress-test?scenario_drop_pct=0")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["scenario_drop_pct"] == 0.0


# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------


class TestGetStressTestSchemaValidation:
    """Tests for response schema validation."""

    @patch("api.routes.holding_routes.calculate_stress_test")
    def test_response_should_match_schema(self, mock_service, client: TestClient):
        # Arrange
        mock_service.return_value = MOCK_STRESS_TEST_RESULT

        # Act
        response = client.get("/stress-test")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify all required fields present
        assert "portfolio_beta" in data
        assert "scenario_drop_pct" in data
        assert "total_value" in data
        assert "total_loss" in data
        assert "total_loss_pct" in data
        assert "display_currency" in data
        assert "pain_level" in data
        assert "advice" in data
        assert "disclaimer" in data
        assert "holdings_breakdown" in data

        # Verify pain_level structure
        assert "level" in data["pain_level"]
        assert "label" in data["pain_level"]
        assert "emoji" in data["pain_level"]

        # Verify holdings_breakdown structure
        assert isinstance(data["holdings_breakdown"], list)
        if len(data["holdings_breakdown"]) > 0:
            holding = data["holdings_breakdown"][0]
            assert "ticker" in holding
            assert "category" in holding
            assert "beta" in holding
            assert "market_value" in holding
            assert "expected_drop_pct" in holding
            assert "expected_loss" in holding
