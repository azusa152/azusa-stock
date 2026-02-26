"""Tests for send_fx_alerts rate-limit integration in rebalance_service."""

from unittest.mock import MagicMock, patch

MODULE = "application.portfolio.rebalance_service"


class TestSendFxAlertsRateLimit:
    """Verify that send_fx_alerts respects rate limits."""

    @patch(f"{MODULE}.log_notification_sent")
    @patch(f"{MODULE}.is_within_rate_limit", return_value=False)
    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.check_fx_alerts", return_value=["alert1"])
    def test_should_skip_telegram_when_rate_limited(
        self,
        _mock_check,
        mock_telegram,
        _mock_enabled,
        _mock_rate_limit,
        mock_log,
    ):
        from application.portfolio.rebalance_service import send_fx_alerts

        result = send_fx_alerts(MagicMock())

        mock_telegram.assert_not_called()
        mock_log.assert_not_called()
        assert result == ["alert1"]

    @patch(f"{MODULE}.log_notification_sent")
    @patch(f"{MODULE}.is_within_rate_limit", return_value=True)
    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.check_fx_alerts", return_value=["alert1"])
    def test_should_send_and_log_when_within_rate_limit(
        self,
        _mock_check,
        mock_telegram,
        _mock_enabled,
        _mock_rate_limit,
        mock_log,
    ):
        from application.portfolio.rebalance_service import send_fx_alerts

        session = MagicMock()
        result = send_fx_alerts(session)

        mock_telegram.assert_called_once()
        mock_log.assert_called_once_with(session, "fx_alerts")
        assert result == ["alert1"]
