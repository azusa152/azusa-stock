"""Tests for notification infrastructure — _split_message and _send."""

from unittest.mock import MagicMock, patch

from domain.constants import TELEGRAM_MAX_MESSAGE_LENGTH
from infrastructure.external.notification import _split_message


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
