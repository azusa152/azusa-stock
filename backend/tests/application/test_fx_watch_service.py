"""Tests for FX Watch application service (orchestration logic)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


from domain.fx_analysis import FXTimingResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_watch(
    watch_id=1,
    base="USD",
    quote="TWD",
    recent_high_days=30,
    consecutive_increase_days=3,
    alert_on_recent_high=True,
    alert_on_consecutive_increase=True,
    reminder_interval_hours=24,
    is_active=True,
    last_alerted_at=None,
    user_id="default",
):
    """Build a lightweight FXWatchConfig-like mock object."""
    w = MagicMock()
    w.id = watch_id
    w.user_id = user_id
    w.base_currency = base
    w.quote_currency = quote
    w.recent_high_days = recent_high_days
    w.consecutive_increase_days = consecutive_increase_days
    w.alert_on_recent_high = alert_on_recent_high
    w.alert_on_consecutive_increase = alert_on_consecutive_increase
    w.reminder_interval_hours = reminder_interval_hours
    w.is_active = is_active
    w.last_alerted_at = last_alerted_at
    return w


def _make_timing_result(should_alert=True, **overrides):
    """Build a FXTimingResult with sensible defaults."""
    base = overrides.get("base_currency", "USD")
    quote = overrides.get("quote_currency", "TWD")
    defaults = dict(
        base_currency=base,
        quote_currency=quote,
        current_rate=32.0,
        is_recent_high=True,
        lookback_high=32.0,
        lookback_days=30,
        consecutive_increases=3,
        consecutive_threshold=3,
        alert_on_recent_high=True,
        alert_on_consecutive_increase=True,
        should_alert=should_alert,
        recommendation_zh="建議考慮換匯：USD → TWD（近期高點 + 連續上漲）",
        reasoning_zh="USD/TWD 已接近 30 日高點 (32.0000)，且連續上漲 3 日。",
        scenario="should_alert_both",
        scenario_vars={
            "base": base,
            "quote": quote,
            "pair": f"{base}/{quote}",
            "high_days": 30,
            "high": 32.0,
            "consec": 3,
            "consec_threshold": 3,
        },
    )
    defaults.update(overrides)
    return FXTimingResult(**defaults)


MOCK_HISTORY = [
    {"date": "2026-02-08", "close": 30.0},
    {"date": "2026-02-09", "close": 30.5},
    {"date": "2026-02-10", "close": 31.0},
    {"date": "2026-02-11", "close": 32.0},
]

MODULE = "application.fx_watch_service"


# ===========================================================================
# CRUD Tests
# ===========================================================================


class TestCreateWatch:
    """Tests for create_watch service function."""

    @patch(f"{MODULE}.create_fx_watch")
    @patch(f"{MODULE}.logger")
    def test_create_watch_should_uppercase_currency_codes(
        self, _mock_logger, mock_repo_create
    ):
        from application.fx_watch_service import create_watch

        mock_repo_create.return_value = _make_watch(base="USD", quote="TWD")
        session = MagicMock()

        create_watch(session, base_currency="usd", quote_currency="twd")

        # Verify the entity passed to repo has uppercased currencies
        created_entity = mock_repo_create.call_args[0][1]
        assert created_entity.base_currency == "USD"
        assert created_entity.quote_currency == "TWD"

    @patch(f"{MODULE}.create_fx_watch")
    @patch(f"{MODULE}.logger")
    def test_create_watch_should_delegate_to_repository(
        self, _mock_logger, mock_repo_create
    ):
        from application.fx_watch_service import create_watch

        expected = _make_watch()
        mock_repo_create.return_value = expected
        session = MagicMock()

        result = create_watch(session, base_currency="USD", quote_currency="TWD")

        mock_repo_create.assert_called_once()
        assert result == expected


class TestGetAllWatches:
    """Tests for get_all_watches service function."""

    @patch(f"{MODULE}.find_active_fx_watches")
    def test_active_only_true_should_call_find_active(self, mock_find_active):
        from application.fx_watch_service import get_all_watches

        mock_find_active.return_value = [_make_watch()]
        session = MagicMock()

        result = get_all_watches(session, active_only=True)

        mock_find_active.assert_called_once_with(session, "default")
        assert len(result) == 1

    @patch(f"{MODULE}.find_all_fx_watches")
    def test_active_only_false_should_call_find_all(self, mock_find_all):
        from application.fx_watch_service import get_all_watches

        mock_find_all.return_value = [_make_watch(), _make_watch(watch_id=2)]
        session = MagicMock()

        result = get_all_watches(session, active_only=False)

        mock_find_all.assert_called_once_with(session, "default")
        assert len(result) == 2


class TestUpdateWatch:
    """Tests for update_watch service function."""

    @patch(f"{MODULE}.update_fx_watch")
    @patch(f"{MODULE}.find_fx_watch_by_id", return_value=None)
    @patch(f"{MODULE}.logger")
    def test_should_return_none_when_not_found(self, _logger, mock_find, _mock_update):
        from application.fx_watch_service import update_watch

        result = update_watch(MagicMock(), watch_id=999)

        assert result is None

    @patch(f"{MODULE}.update_fx_watch")
    @patch(f"{MODULE}.find_fx_watch_by_id")
    @patch(f"{MODULE}.logger")
    def test_should_apply_only_provided_fields(self, _logger, mock_find, mock_update):
        from application.fx_watch_service import update_watch

        watch = _make_watch(recent_high_days=30, is_active=True)
        mock_find.return_value = watch
        mock_update.return_value = watch
        session = MagicMock()

        update_watch(session, watch_id=1, is_active=False)

        # is_active should be updated
        assert watch.is_active is False
        # recent_high_days should remain unchanged
        assert watch.recent_high_days == 30
        mock_update.assert_called_once()


class TestRemoveWatch:
    """Tests for remove_watch service function."""

    @patch(f"{MODULE}.find_fx_watch_by_id", return_value=None)
    @patch(f"{MODULE}.logger")
    def test_should_return_false_when_not_found(self, _logger, _mock_find):
        from application.fx_watch_service import remove_watch

        result = remove_watch(MagicMock(), watch_id=999)

        assert result is False

    @patch(f"{MODULE}.delete_fx_watch")
    @patch(f"{MODULE}.find_fx_watch_by_id")
    @patch(f"{MODULE}.logger")
    def test_should_return_true_and_delete(self, _logger, mock_find, mock_delete):
        from application.fx_watch_service import remove_watch

        mock_find.return_value = _make_watch()
        session = MagicMock()

        result = remove_watch(session, watch_id=1)

        assert result is True
        mock_delete.assert_called_once()


# ===========================================================================
# get_forex_history Tests
# ===========================================================================


class TestGetForexHistory:
    """Tests for get_forex_history wrapper."""

    @patch(f"{MODULE}.get_forex_history_long")
    def test_should_uppercase_and_delegate(self, mock_infra):
        from application.fx_watch_service import get_forex_history

        mock_infra.return_value = MOCK_HISTORY

        result = get_forex_history("usd", "twd")

        mock_infra.assert_called_once_with("USD", "TWD")
        assert result == MOCK_HISTORY

    @patch(
        f"{MODULE}.get_forex_history_long", side_effect=RuntimeError("yfinance down")
    )
    @patch(f"{MODULE}.logger")
    def test_should_return_empty_list_on_infrastructure_failure(
        self, _mock_logger, _mock_infra
    ):
        from application.fx_watch_service import get_forex_history

        result = get_forex_history("USD", "TWD")

        assert result == []


# ===========================================================================
# check_fx_watches Tests
# ===========================================================================


class TestCheckFXWatches:
    """Tests for check_fx_watches monitoring logic."""

    @patch(f"{MODULE}.find_active_fx_watches", return_value=[])
    @patch(f"{MODULE}.logger")
    def test_should_return_empty_when_no_active_watches(self, _logger, _mock_find):
        from application.fx_watch_service import check_fx_watches

        result = check_fx_watches(MagicMock())

        assert result == []

    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_return_results_for_each_active_watch(
        self, _logger, mock_find, mock_history, mock_assess
    ):
        from application.fx_watch_service import check_fx_watches

        mock_find.return_value = [
            _make_watch(watch_id=1, base="USD", quote="TWD"),
            _make_watch(watch_id=2, base="EUR", quote="TWD"),
        ]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result()

        results = check_fx_watches(MagicMock())

        assert len(results) == 2
        assert results[0]["watch_id"] == 1
        assert results[0]["pair"] == "USD/TWD"
        assert results[1]["watch_id"] == 2
        assert results[1]["pair"] == "EUR/TWD"

    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_skip_failed_watch_and_continue(
        self, _logger, mock_find, mock_history, mock_assess
    ):
        from application.fx_watch_service import check_fx_watches

        mock_find.return_value = [
            _make_watch(watch_id=1, base="USD", quote="TWD"),
            _make_watch(watch_id=2, base="EUR", quote="TWD"),
        ]
        # First call raises, second succeeds
        mock_history.side_effect = [RuntimeError("yfinance error"), MOCK_HISTORY]
        mock_assess.return_value = _make_timing_result()

        results = check_fx_watches(MagicMock())

        assert len(results) == 1
        assert results[0]["watch_id"] == 2

    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_pass_watch_config_params_to_domain(
        self, _logger, mock_find, mock_history, mock_assess
    ):
        from application.fx_watch_service import check_fx_watches

        watch = _make_watch(
            recent_high_days=60,
            consecutive_increase_days=5,
            alert_on_recent_high=False,
            alert_on_consecutive_increase=True,
        )
        mock_find.return_value = [watch]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result()

        check_fx_watches(MagicMock())

        mock_assess.assert_called_once_with(
            base_currency="USD",
            quote_currency="TWD",
            history=MOCK_HISTORY,
            recent_high_days=60,
            consecutive_threshold=5,
            alert_on_recent_high=False,
            alert_on_consecutive_increase=True,
        )


# ===========================================================================
# send_fx_watch_alerts Tests (Cooldown & Telegram)
# ===========================================================================


class TestSendFXWatchAlerts:
    """Tests for send_fx_watch_alerts with cooldown and Telegram logic."""

    @patch(f"{MODULE}.find_active_fx_watches", return_value=[])
    @patch(f"{MODULE}.logger")
    def test_should_return_zero_counts_when_no_active_watches(
        self, _logger, _mock_find
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        result = send_fx_watch_alerts(MagicMock())

        assert result["total_watches"] == 0
        assert result["triggered_alerts"] == 0
        assert result["sent_alerts"] == 0
        assert result["alerts"] == []

    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_skip_watch_within_cooldown_period(
        self, _logger, mock_find, mock_history
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        now = datetime.now(timezone.utc)
        # last_alerted_at was 1 hour ago, cooldown is 24 hours -> still in cooldown
        watch = _make_watch(
            last_alerted_at=now - timedelta(hours=1),
            reminder_interval_hours=24,
        )
        mock_find.return_value = [watch]

        result = send_fx_watch_alerts(MagicMock())

        # Should not even call get_forex_history_long
        mock_history.assert_not_called()
        assert result["total_watches"] == 1
        assert result["triggered_alerts"] == 0

    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_handle_naive_datetime_in_cooldown(
        self, _logger, mock_find, mock_history
    ):
        """SQLite may return naive datetimes — verify UTC fallback works."""
        from application.fx_watch_service import send_fx_watch_alerts

        # Naive datetime (no tzinfo) — simulates SQLite returning without tz
        naive_last_alerted = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(hours=1)
        assert naive_last_alerted.tzinfo is None  # confirm it's truly naive

        watch = _make_watch(
            last_alerted_at=naive_last_alerted,
            reminder_interval_hours=24,
        )
        mock_find.return_value = [watch]

        result = send_fx_watch_alerts(MagicMock())

        # Should still be within cooldown — no history fetch
        mock_history.assert_not_called()
        assert result["total_watches"] == 1
        assert result["triggered_alerts"] == 0

    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_process_watch_after_cooldown_expires(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        mock_update_alerted,
        _mock_telegram,
        _mock_notif,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        now = datetime.now(timezone.utc)
        # last_alerted_at was 25 hours ago, cooldown is 24 hours -> expired
        watch = _make_watch(
            last_alerted_at=now - timedelta(hours=25),
            reminder_interval_hours=24,
        )
        mock_find.return_value = [watch]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result(should_alert=True)

        result = send_fx_watch_alerts(MagicMock())

        mock_history.assert_called_once()
        assert result["triggered_alerts"] == 1

    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_update_last_alerted_at_on_trigger(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        mock_update_alerted,
        _mock_telegram,
        _mock_notif,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        watch = _make_watch(last_alerted_at=None)
        mock_find.return_value = [watch]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result(should_alert=True)

        send_fx_watch_alerts(MagicMock())

        mock_update_alerted.assert_called_once()
        assert mock_update_alerted.call_args[0][1] == watch.id

    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_not_update_last_alerted_when_no_trigger(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        mock_update_alerted,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        watch = _make_watch(last_alerted_at=None)
        mock_find.return_value = [watch]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result(should_alert=False)

        send_fx_watch_alerts(MagicMock())

        mock_update_alerted.assert_not_called()

    @patch(f"{MODULE}.is_notification_enabled", return_value=False)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_not_send_telegram_when_notification_disabled(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        _mock_update,
        mock_telegram,
        _mock_notif,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        watch = _make_watch(last_alerted_at=None)
        mock_find.return_value = [watch]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result(should_alert=True)

        result = send_fx_watch_alerts(MagicMock())

        mock_telegram.assert_not_called()
        assert result["triggered_alerts"] == 1
        assert result["sent_alerts"] == 0

    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_send_telegram_when_enabled_and_triggered(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        _mock_update,
        mock_telegram,
        _mock_notif,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        watch = _make_watch(last_alerted_at=None)
        mock_find.return_value = [watch]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result(should_alert=True)

        result = send_fx_watch_alerts(MagicMock())

        mock_telegram.assert_called_once()
        assert result["sent_alerts"] == 1

    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(
        f"{MODULE}.send_telegram_message_dual",
        side_effect=RuntimeError("Telegram down"),
    )
    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_handle_telegram_failure_gracefully(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        _mock_update,
        _mock_telegram,
        _mock_notif,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        watch = _make_watch(last_alerted_at=None)
        mock_find.return_value = [watch]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result(should_alert=True)

        # Should not raise
        result = send_fx_watch_alerts(MagicMock())

        assert result["triggered_alerts"] == 1
        assert result["sent_alerts"] == 0

    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_should_skip_failed_watch_and_continue_others(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        _mock_update,
        _mock_telegram,
        _mock_notif,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        mock_find.return_value = [
            _make_watch(watch_id=1, base="USD", quote="TWD", last_alerted_at=None),
            _make_watch(watch_id=2, base="EUR", quote="TWD", last_alerted_at=None),
        ]
        # First watch fails, second succeeds
        mock_history.side_effect = [RuntimeError("yfinance error"), MOCK_HISTORY]
        mock_assess.return_value = _make_timing_result(should_alert=True)

        result = send_fx_watch_alerts(MagicMock())

        assert result["total_watches"] == 2
        assert result["triggered_alerts"] == 1

    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_telegram_message_should_contain_pair_and_details(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        _mock_update,
        mock_telegram,
        _mock_notif,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        watch = _make_watch(last_alerted_at=None, base="USD", quote="TWD")
        mock_find.return_value = [watch]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.return_value = _make_timing_result(
            should_alert=True,
            current_rate=32.1234,
            scenario_vars={
                "base": "USD",
                "quote": "TWD",
                "pair": "USD/TWD",
                "high_days": 30,
                "high": 32.0,
                "consec": 3,
                "consec_threshold": 3,
            },
        )

        send_fx_watch_alerts(MagicMock())

        msg = mock_telegram.call_args[0][0]
        assert "USD/TWD" in msg
        assert "USD" in msg  # currency present in i18n'd recommendation
        assert "TWD" in msg
        assert "32.1234" in msg

    @patch(f"{MODULE}.is_notification_enabled", return_value=True)
    @patch(f"{MODULE}.send_telegram_message_dual")
    @patch(f"{MODULE}.update_fx_watch_last_alerted")
    @patch(f"{MODULE}.assess_exchange_timing")
    @patch(f"{MODULE}.get_forex_history_long")
    @patch(f"{MODULE}.find_active_fx_watches")
    @patch(f"{MODULE}.logger")
    def test_multiple_alerts_should_produce_combined_telegram_message(
        self,
        _logger,
        mock_find,
        mock_history,
        mock_assess,
        _mock_update,
        mock_telegram,
        _mock_notif,
    ):
        from application.fx_watch_service import send_fx_watch_alerts

        mock_find.return_value = [
            _make_watch(watch_id=1, base="USD", quote="TWD", last_alerted_at=None),
            _make_watch(watch_id=2, base="EUR", quote="TWD", last_alerted_at=None),
        ]
        mock_history.return_value = MOCK_HISTORY
        mock_assess.side_effect = [
            _make_timing_result(
                should_alert=True,
                base_currency="USD",
                quote_currency="TWD",
                current_rate=32.0,
                scenario_vars={
                    "base": "USD",
                    "quote": "TWD",
                    "pair": "USD/TWD",
                    "high_days": 30,
                    "high": 32.0,
                    "consec": 3,
                    "consec_threshold": 3,
                },
            ),
            _make_timing_result(
                should_alert=True,
                base_currency="EUR",
                quote_currency="TWD",
                current_rate=35.0,
                scenario_vars={
                    "base": "EUR",
                    "quote": "TWD",
                    "pair": "EUR/TWD",
                    "high_days": 30,
                    "high": 35.0,
                    "consec": 4,
                    "consec_threshold": 3,
                },
            ),
        ]

        result = send_fx_watch_alerts(MagicMock())

        assert result["triggered_alerts"] == 2
        assert result["sent_alerts"] == 2
        mock_telegram.assert_called_once()

        msg = mock_telegram.call_args[0][0]
        # Header appears exactly once
        assert msg.count("外匯換匯時機警報") == 1
        # Both pairs present with their currencies in the recommendation
        assert "USD/TWD" in msg
        assert "EUR/TWD" in msg
        assert "USD → TWD" in msg  # i18n'd recommendation contains currency pair
        assert "EUR → TWD" in msg
