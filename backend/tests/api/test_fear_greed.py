"""Tests for GET /market/fear-greed endpoint and fear_greed webhook action."""

from unittest.mock import patch

from domain.enums import FearGreedLevel
from i18n import t


class TestGetFearGreedEndpoint:
    """Tests for GET /market/fear-greed — composite Fear & Greed Index."""

    def test_fear_greed_should_return_200_with_composite_data(self, client):
        # Act — uses mock from conftest
        resp = client.get("/market/fear-greed")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["composite_score"] == 38
        assert data["composite_level"] == "FEAR"
        # Expect the translated label (defaults to zh-TW in tests)
        expected_label = t("formatter.fear_greed_fear", score=38, lang="zh-TW")
        assert data["composite_label"] == expected_label
        assert data["vix"] is not None
        assert data["vix"]["value"] == 22.5
        assert data["cnn"] is not None
        assert data["cnn"]["score"] == 38

    def test_fear_greed_should_return_vix_only_when_cnn_unavailable(self, client):
        # Arrange
        mock_fg_vix_only = {
            "composite_score": 47,
            "composite_level": "NEUTRAL",
            "vix": {
                "value": 25.0,
                "change_1d": -0.5,
                "level": "FEAR",
                "fetched_at": "2025-06-15T10:00:00+00:00",
            },
            "cnn": None,
            "fetched_at": "2025-06-15T10:00:00+00:00",
        }

        with patch(
            "application.scan_service.get_fear_greed_index",
            return_value=mock_fg_vix_only,
        ):
            # Act
            resp = client.get("/market/fear-greed")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["composite_score"] == 47
        assert data["composite_level"] == "NEUTRAL"
        assert data["vix"]["value"] == 25.0
        assert data["cnn"] is None

    def test_fear_greed_should_return_na_when_both_sources_fail(self, client):
        # Arrange
        mock_fg_na = {
            "composite_score": 50,
            "composite_level": FearGreedLevel.NOT_AVAILABLE.value,
            "vix": {
                "value": None,
                "change_1d": None,
                "level": FearGreedLevel.NOT_AVAILABLE.value,
                "fetched_at": "2025-06-15T10:00:00+00:00",
            },
            "cnn": None,
            "fetched_at": "2025-06-15T10:00:00+00:00",
        }

        with patch(
            "application.scan_service.get_fear_greed_index", return_value=mock_fg_na
        ):
            # Act
            resp = client.get("/market/fear-greed")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["composite_level"] == "N/A"
        expected_label = t("formatter.fear_greed_n/a", score=50, lang="zh-TW")
        assert data["composite_label"] == expected_label

    def test_fear_greed_should_include_fetched_at_timestamp(self, client):
        # Act
        resp = client.get("/market/fear-greed")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["fetched_at"] != ""


class TestScanLastWithFearGreed:
    """Tests for GET /scan/last — including fear_greed fields."""

    def test_scan_last_should_include_fear_greed_fields_in_response(self, client):
        # Act — no scan logs, but F&G data still comes from infrastructure
        resp = client.get("/scan/last")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        # Fear & Greed fields should be present (either from scan or live API)
        assert "fear_greed_level" in data
        assert "fear_greed_score" in data


class TestFearGreedWebhookAction:
    """Tests for POST /webhook with action=fear_greed."""

    def test_webhook_fear_greed_should_return_composite_data(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "fear_greed"})

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        expected_prefix = t("webhook.fear_greed_prefix", lang="zh-TW")
        assert expected_prefix in data["message"]
        assert data["data"]["composite_score"] == 38
        assert data["data"]["composite_level"] == "FEAR"
