"""Tests for POST /webhook — AI agent unified entry point."""

from unittest.mock import patch


class TestWebhookHelp:
    """Tests for the 'help' action (discoverability)."""

    def test_help_should_return_all_actions(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        actions = body["data"]["actions"]
        assert "help" in actions
        assert "summary" in actions
        assert "signals" in actions
        assert "scan" in actions
        assert "moat" in actions
        assert "alerts" in actions
        assert "add_stock" in actions

    def test_help_should_include_descriptions(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        actions = resp.json()["data"]["actions"]
        for action_info in actions.values():
            assert "description" in action_info
            assert "requires_ticker" in action_info


class TestWebhookSummary:
    """Tests for the 'summary' action."""

    def test_summary_should_return_success(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "summary"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["message"], str)


class TestWebhookSignals:
    """Tests for the 'signals' action."""

    def test_signals_should_return_data_with_ticker(self, client):
        # Arrange — add a stock first
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.post("/webhook", json={"action": "signals", "ticker": "NVDA"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "RSI" in body["message"]

    def test_signals_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "signals"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "ticker" in body["message"]


class TestWebhookScan:
    """Tests for the 'scan' action."""

    def test_scan_should_accept_background_job(self, client):
        # Act — mock Thread so _bg_scan doesn't run against the test DB
        with patch("threading.Thread"):
            resp = client.post("/webhook", json={"action": "scan"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "背景" in body["message"] or "Telegram" in body["message"]


class TestWebhookMoat:
    """Tests for the 'moat' action."""

    def test_moat_should_return_analysis_with_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "moat", "ticker": "NVDA"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "護城河" in body["message"]

    def test_moat_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "moat"})

        # Assert
        body = resp.json()
        assert body["success"] is False


class TestWebhookAlerts:
    """Tests for the 'alerts' action."""

    def test_alerts_should_return_empty_for_new_stock(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "AAPL", "category": "Moat", "thesis": "Ecosystem"},
        )

        # Act
        resp = client.post("/webhook", json={"action": "alerts", "ticker": "AAPL"})

        # Assert
        body = resp.json()
        assert body["success"] is True
        assert "沒有" in body["message"]

    def test_alerts_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "alerts"})

        # Assert
        body = resp.json()
        assert body["success"] is False


class TestWebhookAddStock:
    """Tests for the 'add_stock' action."""

    def test_add_stock_should_create_new_stock(self, client):
        # Act
        resp = client.post(
            "/webhook",
            json={
                "action": "add_stock",
                "params": {
                    "ticker": "AMD",
                    "category": "Growth",
                    "thesis": "ASIC competitor",
                    "tags": ["AI", "Semiconductor"],
                },
            },
        )

        # Assert
        body = resp.json()
        assert body["success"] is True
        assert "AMD" in body["message"]

    def test_add_stock_should_fail_for_duplicate(self, client):
        # Arrange
        client.post(
            "/webhook",
            json={
                "action": "add_stock",
                "params": {"ticker": "AMD", "category": "Growth", "thesis": "Test"},
            },
        )

        # Act
        resp = client.post(
            "/webhook",
            json={
                "action": "add_stock",
                "params": {
                    "ticker": "AMD",
                    "category": "Growth",
                    "thesis": "Duplicate",
                },
            },
        )

        # Assert
        body = resp.json()
        assert body["success"] is False

    def test_add_stock_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "add_stock", "params": {}})

        # Assert
        body = resp.json()
        assert body["success"] is False


class TestWebhookUnknownAction:
    """Tests for unsupported actions."""

    def test_unknown_action_should_return_error(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "nonexistent"})

        # Assert
        body = resp.json()
        assert body["success"] is False
        assert "不支援" in body["message"]
