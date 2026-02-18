"""Tests for POST /webhook — AI agent unified entry point."""

from unittest.mock import patch

from domain.constants import WEBHOOK_ACTION_REGISTRY
from i18n import t


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
        # Act — mock run_scan so it doesn't actually run the scan in the background
        with patch("application.webhook_service.run_scan"):
            resp = client.post("/webhook", json={"action": "scan"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        expected_msg = t("webhook.scan_started", lang="zh-TW")
        assert body["message"] == expected_msg


class TestWebhookMoat:
    """Tests for the 'moat' action."""

    def test_moat_should_return_analysis_with_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "moat", "ticker": "NVDA"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        expected_key = t("webhook.moat_result", lang="zh-TW")
        assert expected_key in body["message"]

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
        expected_msg = t("webhook.no_alerts", lang="zh-TW")
        assert expected_msg in body["message"]

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


class TestWebhookFXWatch:
    """Tests for the 'fx_watch' webhook action — AI agent entry point for FX alerts."""

    @patch("application.fx_watch_service.send_telegram_message_dual")
    @patch("application.fx_watch_service.get_forex_history_long")
    @patch("application.fx_watch_service.is_notification_enabled")
    def test_fx_watch_should_return_success_with_counts(
        self, mock_notif, mock_history, mock_telegram, client
    ):
        # Arrange: create an FX watch config
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
                "recent_high_days": 5,
                "consecutive_increase_days": 2,
            },
        )
        mock_notif.return_value = True
        mock_history.return_value = [
            {"date": "2026-02-07", "close": 30.0},
            {"date": "2026-02-08", "close": 30.5},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.5},
        ]

        # Act
        resp = client.post("/webhook", json={"action": "fx_watch"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        # Check that the expected translated message parts are present
        expected_complete = t(
            "webhook.fx_watch_complete", total=1, triggered=1, sent=1, lang="zh-TW"
        )
        assert body["message"] == expected_complete
        assert body["data"]["total_watches"] == 1
        assert body["data"]["triggered_alerts"] == 1
        assert body["data"]["sent_alerts"] == 1

    def test_fx_watch_should_return_success_when_no_watches(self, client):
        # Act — no FX watch configs exist
        resp = client.post("/webhook", json={"action": "fx_watch"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total_watches"] == 0
        assert body["data"]["triggered_alerts"] == 0
        assert body["data"]["sent_alerts"] == 0

    @patch(
        "application.webhook_service.send_fx_watch_alerts",
        side_effect=RuntimeError("DB connection lost"),
    )
    def test_fx_watch_should_return_failure_on_service_exception(
        self, _mock_alert, client
    ):
        # Act
        resp = client.post("/webhook", json={"action": "fx_watch"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        expected_msg = t("webhook.fx_watch_failed", lang="zh-TW")
        assert expected_msg in body["message"]


class TestWebhookDiscoverability:
    """Tests ensuring AI agent discoverability stays in sync with WEBHOOK_ACTION_REGISTRY."""

    def test_help_should_include_all_registry_actions(self, client):
        """Dynamic guard: every action in WEBHOOK_ACTION_REGISTRY must appear in help response."""
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        assert resp.status_code == 200
        actions = resp.json()["data"]["actions"]
        for action_name in WEBHOOK_ACTION_REGISTRY:
            assert action_name in actions, f"Missing action in help: {action_name}"
        # Also verify no extra actions beyond registry
        assert set(actions.keys()) == set(WEBHOOK_ACTION_REGISTRY.keys())

    @patch("application.fx_watch_service.send_telegram_message_dual")
    @patch("application.fx_watch_service.get_forex_history_long")
    @patch("application.fx_watch_service.is_notification_enabled")
    def test_fx_watch_response_data_should_have_required_keys(
        self, mock_notif, mock_history, mock_telegram, client
    ):
        """Response schema contract test — ensures AI agent gets expected keys."""
        # Arrange
        mock_notif.return_value = True
        mock_history.return_value = [
            {"date": "2026-02-10", "close": 31.0},
            {"date": "2026-02-11", "close": 31.5},
        ]

        # Act
        resp = client.post("/webhook", json={"action": "fx_watch"})

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        required_keys = {"total_watches", "triggered_alerts", "sent_alerts", "alerts"}
        assert (
            required_keys == set(data.keys())
        ), f"Response data keys mismatch: expected {required_keys}, got {set(data.keys())}"


class TestWebhookUnknownAction:
    """Tests for unsupported actions."""

    def test_unknown_action_should_return_error(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "nonexistent"})

        # Assert
        body = resp.json()
        assert body["success"] is False
        expected_msg = t(
            "webhook.unsupported_action", action="nonexistent", lang="zh-TW"
        )
        assert body["message"] == expected_msg
