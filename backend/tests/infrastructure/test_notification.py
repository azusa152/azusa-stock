"""Tests for notification infrastructure — _split_message, _send, rate limiting."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from domain.constants import TELEGRAM_MAX_MESSAGE_LENGTH
from infrastructure.external.notification import _split_message


def _utcnow_naive() -> datetime:
    """Return current UTC time as naive datetime (consistent with SQLite storage)."""
    return datetime.now(UTC).replace(tzinfo=None)


class TestSplitMessage:
    """Unit tests for the Telegram message splitter."""

    def test_short_message_returned_as_single_chunk(self):
        text = "Hello, world!"
        assert _split_message(text) == [text]

    def test_exact_limit_returned_as_single_chunk(self):
        text = "x" * TELEGRAM_MAX_MESSAGE_LENGTH
        result = _split_message(text)
        assert result == [text]

    def test_one_char_over_limit_splits_into_two(self):
        # Two equal-length lines whose combined length (with newline) exceeds the limit
        half = "a" * (TELEGRAM_MAX_MESSAGE_LENGTH // 2)
        text = half + "\n" + half
        result = _split_message(text)
        assert len(result) == 2
        assert result[0] == half
        assert result[1] == half

    def test_splits_at_newline_boundaries(self):
        line_a = "A" * 100
        line_b = "B" * 100
        line_c = "C" * 100
        text = "\n".join([line_a, line_b, line_c])
        # All fit in one chunk
        assert _split_message(text) == [text]

    def test_multiple_chunks_cover_all_content(self):
        # Build a message that needs exactly 3 chunks
        line = "z" * (TELEGRAM_MAX_MESSAGE_LENGTH // 2)
        # 5 such lines: lines 1+2 fit (with separator = max), line 3 starts chunk 2, etc.
        lines = [line] * 5
        text = "\n".join(lines)
        result = _split_message(text)
        assert len(result) >= 2
        # Round-trip: reassembling gives back the original
        assert "\n".join(result) == text

    def test_single_line_exceeding_limit_is_hard_split(self):
        long_line = "X" * (TELEGRAM_MAX_MESSAGE_LENGTH * 2 + 50)
        result = _split_message(long_line)
        assert all(len(chunk) <= TELEGRAM_MAX_MESSAGE_LENGTH for chunk in result)
        assert "".join(result) == long_line

    def test_empty_string_returns_single_empty_chunk(self):
        assert _split_message("") == [""]

    def test_all_chunks_respect_max_length(self):
        # Stress test: many medium-sized lines
        line = "M" * 300
        text = "\n".join([line] * 50)
        result = _split_message(text)
        assert all(len(chunk) <= TELEGRAM_MAX_MESSAGE_LENGTH for chunk in result)

    def test_trailing_newline_preserved(self):
        text = "Line one\nLine two\n"
        result = _split_message(text)
        assert "\n".join(result) == text

    def test_custom_max_length(self):
        text = "ab\ncd\nef"
        result = _split_message(text, max_length=5)
        assert all(len(chunk) <= 5 for chunk in result)
        assert "\n".join(result) == text


class TestSend:
    """Tests for _send() abort-on-failure behaviour."""

    @patch("infrastructure.external.notification.http_requests.post")
    def test_single_chunk_success(self, mock_post):
        from infrastructure.external.notification import _send

        mock_post.return_value = MagicMock(ok=True)
        _send("token", "chat", "short message")
        assert mock_post.call_count == 1

    @patch("infrastructure.external.notification.http_requests.post")
    def test_multi_chunk_aborts_after_first_failure(self, mock_post):
        from infrastructure.external.notification import _send

        # Build a message that splits into 3 chunks
        line = "z" * (TELEGRAM_MAX_MESSAGE_LENGTH // 2)
        text = "\n".join([line] * 5)

        ok_response = MagicMock(ok=True)
        fail_response = MagicMock(
            ok=False, status_code=400, content=b'{"description":"bad"}'
        )
        fail_response.json.return_value = {"description": "message is too long"}

        # First chunk succeeds, second fails → third must NOT be sent
        mock_post.side_effect = [ok_response, fail_response]

        _send("token", "chat", text)

        assert mock_post.call_count == 2  # stopped after second chunk failed

    @patch("infrastructure.external.notification.http_requests.post")
    def test_network_exception_aborts_remaining_chunks(self, mock_post):
        from infrastructure.external.notification import _send

        line = "z" * (TELEGRAM_MAX_MESSAGE_LENGTH // 2)
        text = "\n".join([line] * 5)

        mock_post.side_effect = [MagicMock(ok=True), ConnectionError("timeout")]

        _send("token", "chat", text)

        assert mock_post.call_count == 2  # aborted after exception on second chunk


# ---------------------------------------------------------------------------
# Rate Limit Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def rate_limit_session():
    """In-memory SQLite session with all tables for rate limit tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestIsWithinRateLimit:
    """Tests for is_within_rate_limit."""

    def test_returns_true_when_no_preferences_exist(self, rate_limit_session):
        from infrastructure.external.notification import is_within_rate_limit

        result = is_within_rate_limit(rate_limit_session, "fx_alerts")
        assert result is True

    def test_returns_true_when_no_rate_limit_configured(self, rate_limit_session):
        from domain.entities import UserPreferences
        from infrastructure.external.notification import is_within_rate_limit

        prefs = UserPreferences()
        rate_limit_session.add(prefs)
        rate_limit_session.commit()

        assert is_within_rate_limit(rate_limit_session, "fx_alerts") is True

    def test_returns_true_when_max_count_is_zero(self, rate_limit_session):
        from domain.entities import UserPreferences
        from infrastructure.external.notification import is_within_rate_limit

        prefs = UserPreferences()
        prefs.set_notification_rate_limits(
            {"fx_alerts": {"max_count": 0, "window_hours": 24}}
        )
        rate_limit_session.add(prefs)
        rate_limit_session.commit()

        assert is_within_rate_limit(rate_limit_session, "fx_alerts") is True

    def test_returns_true_when_under_limit(self, rate_limit_session):
        from domain.entities import NotificationLog, UserPreferences
        from infrastructure.external.notification import is_within_rate_limit

        prefs = UserPreferences()
        prefs.set_notification_rate_limits(
            {"fx_alerts": {"max_count": 3, "window_hours": 24}}
        )
        rate_limit_session.add(prefs)

        # Add 2 recent logs (under the limit of 3)
        for _ in range(2):
            rate_limit_session.add(
                NotificationLog(notification_type="fx_alerts", sent_at=_utcnow_naive())
            )
        rate_limit_session.commit()

        assert is_within_rate_limit(rate_limit_session, "fx_alerts") is True

    def test_returns_false_when_at_limit(self, rate_limit_session):
        from domain.entities import NotificationLog, UserPreferences
        from infrastructure.external.notification import is_within_rate_limit

        prefs = UserPreferences()
        prefs.set_notification_rate_limits(
            {"fx_alerts": {"max_count": 2, "window_hours": 24}}
        )
        rate_limit_session.add(prefs)

        # Add exactly 2 recent logs — at the limit
        for _ in range(2):
            rate_limit_session.add(
                NotificationLog(notification_type="fx_alerts", sent_at=_utcnow_naive())
            )
        rate_limit_session.commit()

        assert is_within_rate_limit(rate_limit_session, "fx_alerts") is False

    def test_old_logs_outside_window_are_not_counted(self, rate_limit_session):
        from domain.entities import NotificationLog, UserPreferences
        from infrastructure.external.notification import is_within_rate_limit

        prefs = UserPreferences()
        prefs.set_notification_rate_limits(
            {"fx_alerts": {"max_count": 1, "window_hours": 24}}
        )
        rate_limit_session.add(prefs)

        # Add a log from 48 hours ago — outside the 24h window
        old_time = _utcnow_naive() - timedelta(hours=48)
        rate_limit_session.add(
            NotificationLog(notification_type="fx_alerts", sent_at=old_time)
        )
        rate_limit_session.commit()

        # Should be True since no recent logs exist within the window
        assert is_within_rate_limit(rate_limit_session, "fx_alerts") is True

    def test_different_types_are_counted_separately(self, rate_limit_session):
        from domain.entities import NotificationLog, UserPreferences
        from infrastructure.external.notification import is_within_rate_limit

        prefs = UserPreferences()
        prefs.set_notification_rate_limits(
            {
                "fx_alerts": {"max_count": 1, "window_hours": 24},
            }
        )
        rate_limit_session.add(prefs)

        # Max out fx_alerts but not fx_watch_alerts
        rate_limit_session.add(
            NotificationLog(notification_type="fx_alerts", sent_at=_utcnow_naive())
        )
        rate_limit_session.commit()

        assert is_within_rate_limit(rate_limit_session, "fx_alerts") is False
        assert is_within_rate_limit(rate_limit_session, "fx_watch_alerts") is True


class TestLogNotificationSent:
    """Tests for log_notification_sent and count_recent_notifications."""

    def test_log_notification_sent_creates_record(self, rate_limit_session):
        from infrastructure.persistence.repositories import (
            count_recent_notifications,
            log_notification_sent,
        )

        log_notification_sent(rate_limit_session, "fx_alerts")

        count = count_recent_notifications(
            rate_limit_session, "fx_alerts", _utcnow_naive() - timedelta(hours=1)
        )
        assert count == 1

    def test_count_excludes_other_types(self, rate_limit_session):
        from infrastructure.persistence.repositories import (
            count_recent_notifications,
            log_notification_sent,
        )

        log_notification_sent(rate_limit_session, "fx_alerts")
        log_notification_sent(rate_limit_session, "fx_watch_alerts")

        count = count_recent_notifications(
            rate_limit_session, "fx_alerts", _utcnow_naive() - timedelta(hours=1)
        )
        assert count == 1  # fx_watch_alerts entry not counted

    def test_count_excludes_records_before_since(self, rate_limit_session):
        from domain.entities import NotificationLog
        from infrastructure.persistence.repositories import count_recent_notifications

        old_log = NotificationLog(
            notification_type="fx_alerts",
            sent_at=_utcnow_naive() - timedelta(hours=48),
        )
        rate_limit_session.add(old_log)
        rate_limit_session.commit()

        count = count_recent_notifications(
            rate_limit_session,
            "fx_alerts",
            _utcnow_naive() - timedelta(hours=24),
        )
        assert count == 0
