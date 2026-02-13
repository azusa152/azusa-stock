"""Tests for FX Exchange Timing Analysis pure functions in domain/fx_analysis.py."""

from domain.fx_analysis import (
    FXTimingResult,
    assess_exchange_timing,
    count_consecutive_increases,
    is_recent_high,
)


# ---------------------------------------------------------------------------
# is_recent_high
# ---------------------------------------------------------------------------


class TestIsRecentHigh:
    """Tests for is_recent_high function."""

    def test_should_return_false_when_no_history(self):
        near_high, high = is_recent_high(32.0, [], 30)
        assert near_high is False
        assert high == 0.0

    def test_should_return_false_when_insufficient_history(self):
        history = [
            {"date": "2026-02-10", "close": 31.0},
            {"date": "2026-02-11", "close": 31.5},
        ]
        # With only 2 data points for lookback_days=30, use available data
        near_high, high = is_recent_high(32.0, history, 30)
        assert near_high is True  # 32.0 >= 31.5 * 0.98
        assert high == 31.5

    def test_should_detect_recent_high_within_tolerance(self):
        history = [
            {"date": "2026-01-15", "close": 30.0},
            {"date": "2026-01-20", "close": 31.0},
            {"date": "2026-02-10", "close": 32.0},
            {"date": "2026-02-11", "close": 31.8},
        ]
        # Current rate 31.84 is >= 32.0 * 0.98 (31.36)
        near_high, high = is_recent_high(31.84, history, 30)
        assert near_high is True
        assert high == 32.0

    def test_should_not_detect_when_below_tolerance(self):
        history = [
            {"date": "2026-01-15", "close": 30.0},
            {"date": "2026-02-10", "close": 32.0},
        ]
        # Current rate 31.0 is < 32.0 * 0.98 (31.36)
        near_high, high = is_recent_high(31.0, history, 30)
        assert near_high is False
        assert high == 32.0

    def test_should_use_custom_tolerance(self):
        history = [
            {"date": "2026-02-10", "close": 32.0},
        ]
        # With 5% tolerance, threshold is 32.0 * 0.95 = 30.4
        near_high, high = is_recent_high(30.5, history, 30, tolerance_pct=5.0)
        assert near_high is True
        assert high == 32.0

    def test_should_handle_zero_close_price(self):
        history = [
            {"date": "2026-02-10", "close": 0.0},
        ]
        near_high, high = is_recent_high(32.0, history, 30)
        assert near_high is False
        assert high == 0.0


# ---------------------------------------------------------------------------
# count_consecutive_increases
# ---------------------------------------------------------------------------


class TestCountConsecutiveIncreases:
    """Tests for count_consecutive_increases function."""

    def test_should_return_zero_when_insufficient_history(self):
        assert count_consecutive_increases([]) == 0
        assert count_consecutive_increases([{"date": "2026-02-10", "close": 31.0}]) == 0

    def test_should_count_consecutive_increases_from_end(self):
        history = [
            {"date": "2026-02-08", "close": 30.0},
            {"date": "2026-02-09", "close": 30.5},
            {"date": "2026-02-10", "close": 31.0},
            {"date": "2026-02-11", "close": 31.5},
        ]
        assert count_consecutive_increases(history) == 3

    def test_should_stop_at_first_non_increase(self):
        history = [
            {"date": "2026-02-07", "close": 32.0},  # Decrease here stops counting
            {"date": "2026-02-08", "close": 30.0},
            {"date": "2026-02-09", "close": 30.5},
            {"date": "2026-02-10", "close": 31.0},
        ]
        assert count_consecutive_increases(history) == 2

    def test_should_return_zero_when_last_day_decreased(self):
        history = [
            {"date": "2026-02-09", "close": 31.5},
            {"date": "2026-02-10", "close": 31.0},
        ]
        assert count_consecutive_increases(history) == 0

    def test_should_return_zero_when_flat(self):
        history = [
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.0},
        ]
        assert count_consecutive_increases(history) == 0


# ---------------------------------------------------------------------------
# assess_exchange_timing
# ---------------------------------------------------------------------------


class TestAssessExchangeTiming:
    """Tests for assess_exchange_timing function."""

    def test_should_return_no_data_result_when_empty_history(self):
        result = assess_exchange_timing("USD", "TWD", [], 30, 3)
        assert isinstance(result, FXTimingResult)
        assert result.current_rate == 0.0
        assert result.should_alert is False
        assert "無歷史資料" in result.recommendation_zh

    def test_should_trigger_alert_when_near_high_and_consecutive(self):
        # Arrange: price at recent high and 3 consecutive increases
        history = [
            {"date": "2026-01-15", "close": 30.0},
            {"date": "2026-02-08", "close": 30.5},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.5},
            {"date": "2026-02-11", "close": 32.0},
        ]

        result = assess_exchange_timing("USD", "TWD", history, 30, 3)

        assert result.base_currency == "USD"
        assert result.quote_currency == "TWD"
        assert result.current_rate == 32.0
        assert result.is_recent_high is True
        assert result.lookback_high == 32.0
        assert result.consecutive_increases == 4
        assert result.should_alert is True
        assert "建議考慮換匯" in result.recommendation_zh
        assert "接近 30 日高點" in result.reasoning_zh

    def test_should_alert_when_near_high_with_or_logic(self):
        """With OR logic and both toggles enabled, alert fires when near high even if consecutive insufficient."""
        history = [
            {"date": "2026-01-15", "close": 30.0},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.8},
            {"date": "2026-02-11", "close": 32.0},
        ]

        # Set threshold to 4 so consecutive is not met (actual consecutive is 3)
        # But with OR logic, should still alert because near_high is True
        result = assess_exchange_timing("USD", "TWD", history, 30, 4)

        assert result.is_recent_high is True
        assert result.consecutive_increases == 3
        assert result.should_alert is True  # OR logic: high condition met
        assert "近期高點" in result.recommendation_zh

    def test_should_alert_when_consecutive_with_or_logic(self):
        """With OR logic and both toggles enabled, alert fires when consecutive met even if not near high."""
        history = [
            {"date": "2026-01-15", "close": 30.0},
            {"date": "2026-02-07", "close": 35.0},  # Recent high far above current
            {"date": "2026-02-08", "close": 31.0},
            {"date": "2026-02-09", "close": 31.2},
            {"date": "2026-02-10", "close": 31.4},
            {"date": "2026-02-11", "close": 31.6},
        ]

        result = assess_exchange_timing("USD", "TWD", history, 30, 3)

        assert result.is_recent_high is False
        assert result.consecutive_increases >= 3
        assert result.should_alert is True  # OR logic: consecutive condition met
        assert "連續上漲" in result.recommendation_zh

    def test_should_return_no_signal_when_neither_condition_met(self):
        history = [
            {"date": "2026-01-15", "close": 30.0},
            {"date": "2026-02-09", "close": 35.0},
            {"date": "2026-02-10", "close": 31.0},
            {"date": "2026-02-11", "close": 30.8},
        ]

        result = assess_exchange_timing("USD", "TWD", history, 30, 3)

        assert result.is_recent_high is False
        assert result.consecutive_increases == 0
        assert result.should_alert is False
        assert "暫無換匯訊號" in result.recommendation_zh

    def test_should_respect_custom_thresholds(self):
        history = [
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.2},
            {"date": "2026-02-11", "close": 31.4},
        ]

        # With lookback_days=2 and consecutive_threshold=2, should trigger
        result = assess_exchange_timing("USD", "TWD", history, 2, 2)

        assert result.is_recent_high is True
        assert result.consecutive_increases == 2
        assert result.should_alert is True

    def test_should_alert_when_only_recent_high_enabled_and_met(self):
        """Alert fires when only recent high is enabled and condition is met."""
        history = [
            {"date": "2026-01-15", "close": 30.0},
            {"date": "2026-02-11", "close": 32.0},
        ]

        result = assess_exchange_timing(
            "USD",
            "TWD",
            history,
            30,
            3,
            alert_on_recent_high=True,
            alert_on_consecutive_increase=False,
        )

        assert result.should_alert is True
        assert result.alert_on_recent_high is True
        assert result.alert_on_consecutive_increase is False
        assert "近期高點" in result.recommendation_zh
        # Alert fires successfully, so no "監控已關閉" message

    def test_should_alert_when_only_consecutive_enabled_and_met(self):
        """Alert fires when only consecutive is enabled and condition is met."""
        history = [
            {"date": "2026-02-07", "close": 35.0},  # Recent high far above
            {"date": "2026-02-08", "close": 30.0},
            {"date": "2026-02-09", "close": 30.5},
            {"date": "2026-02-10", "close": 31.0},
            {"date": "2026-02-11", "close": 31.5},
        ]

        result = assess_exchange_timing(
            "USD",
            "TWD",
            history,
            30,
            3,
            alert_on_recent_high=False,
            alert_on_consecutive_increase=True,
        )

        assert result.should_alert is True
        assert result.alert_on_recent_high is False
        assert result.alert_on_consecutive_increase is True
        assert "連續上漲" in result.recommendation_zh
        # Alert fires successfully, so no "監控已關閉" message

    def test_should_not_alert_when_both_toggles_disabled(self):
        """No alert when both toggles are disabled."""
        history = [
            {"date": "2026-02-08", "close": 30.0},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 32.0},
        ]

        result = assess_exchange_timing(
            "USD",
            "TWD",
            history,
            30,
            2,
            alert_on_recent_high=False,
            alert_on_consecutive_increase=False,
        )

        assert result.should_alert is False
        assert result.alert_on_recent_high is False
        assert result.alert_on_consecutive_increase is False
        assert "監控已停用" in result.recommendation_zh
        assert "兩項條件皆關閉" in result.recommendation_zh

    def test_should_alert_with_or_logic_when_only_one_condition_met(self):
        """Alert fires when EITHER condition is met (both enabled, OR logic)."""
        # Arrange: Near high but not consecutive
        history = [
            {"date": "2026-01-15", "close": 30.0},
            {"date": "2026-02-10", "close": 31.8},
            {"date": "2026-02-11", "close": 32.0},
        ]

        result = assess_exchange_timing(
            "USD",
            "TWD",
            history,
            30,
            5,  # High threshold that won't be met
            alert_on_recent_high=True,
            alert_on_consecutive_increase=True,
        )

        # With OR logic, should alert because near high is true
        assert result.should_alert is True
        assert result.is_recent_high is True
        assert result.consecutive_increases < 5  # Not enough consecutive
        assert "近期高點" in result.recommendation_zh

    def test_should_show_both_triggers_when_both_conditions_met(self):
        """Recommendation shows both conditions when both are met."""
        history = [
            {"date": "2026-02-08", "close": 30.0},
            {"date": "2026-02-09", "close": 30.5},
            {"date": "2026-02-10", "close": 31.0},
            {"date": "2026-02-11", "close": 32.0},
        ]

        result = assess_exchange_timing(
            "USD",
            "TWD",
            history,
            30,
            3,
            alert_on_recent_high=True,
            alert_on_consecutive_increase=True,
        )

        assert result.should_alert is True
        assert result.is_recent_high is True
        assert result.consecutive_increases >= 3
        # Should mention both conditions
        assert "近期高點 + 連續上漲" in result.recommendation_zh or (
            "近期高點" in result.recommendation_zh
            and "連續上漲" in result.recommendation_zh
        )
