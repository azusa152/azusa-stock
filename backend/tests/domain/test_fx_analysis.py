"""Tests for FX rate-change analysis pure functions in domain/fx_analysis.py."""

from domain.enums import FXAlertType
from domain.fx_analysis import (
    FXRateAlert,
    analyze_fx_rate_changes,
    determine_fx_risk_level,
)

# ---------------------------------------------------------------------------
# analyze_fx_rate_changes
# ---------------------------------------------------------------------------


class TestAnalyzeFxRateChanges:
    """Three-tier rate-change detection."""

    def test_should_return_empty_when_no_history(self):
        result = analyze_fx_rate_changes("USD/TWD", 32.0, [], [])
        assert result == []

    def test_should_detect_daily_spike_when_above_threshold(self):
        # Arrange: last day jumps ~2.03% (> 1.5%)
        short = [
            {"date": "2026-02-10", "close": 31.0},
            {"date": "2026-02-11", "close": 31.5},
            {"date": "2026-02-12", "close": 32.14},
        ]

        # Act
        result = analyze_fx_rate_changes("USD/TWD", 32.14, short, [])

        # Assert
        spike_alerts = [a for a in result if a.alert_type == FXAlertType.DAILY_SPIKE]
        assert len(spike_alerts) == 1
        assert spike_alerts[0].direction == "up"
        assert spike_alerts[0].period_label == "1 日"
        assert spike_alerts[0].change_pct > 1.5

    def test_should_not_detect_daily_spike_when_below_threshold(self):
        # Arrange: ~0.94% daily change (< 1.5%)
        short = [
            {"date": "2026-02-11", "close": 32.0},
            {"date": "2026-02-12", "close": 32.3},
        ]

        result = analyze_fx_rate_changes("USD/TWD", 32.3, short, [])

        spike_alerts = [a for a in result if a.alert_type == FXAlertType.DAILY_SPIKE]
        assert len(spike_alerts) == 0

    def test_should_detect_short_term_swing_when_above_threshold(self):
        # Arrange: 5-day change ~2.26% (> 2.0%)
        short = [
            {"date": "2026-02-07", "close": 31.0},
            {"date": "2026-02-08", "close": 31.1},
            {"date": "2026-02-09", "close": 31.2},
            {"date": "2026-02-10", "close": 31.4},
            {"date": "2026-02-11", "close": 31.7},
        ]

        result = analyze_fx_rate_changes("USD/TWD", 31.7, short, [])

        swing_alerts = [
            a for a in result if a.alert_type == FXAlertType.SHORT_TERM_SWING
        ]
        assert len(swing_alerts) == 1
        assert swing_alerts[0].period_label == "5 日"

    def test_should_not_detect_short_term_swing_when_below_threshold(self):
        # Arrange: 5-day change ~0.97% (< 2.0%)
        short = [
            {"date": "2026-02-07", "close": 31.0},
            {"date": "2026-02-08", "close": 31.1},
            {"date": "2026-02-09", "close": 31.1},
            {"date": "2026-02-10", "close": 31.2},
            {"date": "2026-02-11", "close": 31.3},
        ]

        result = analyze_fx_rate_changes("USD/TWD", 31.3, short, [])

        swing_alerts = [
            a for a in result if a.alert_type == FXAlertType.SHORT_TERM_SWING
        ]
        assert len(swing_alerts) == 0

    def test_should_detect_long_term_trend_when_above_threshold(self):
        # Arrange: 3-month change ~8.33% (> 8.0%)
        long = [
            {"date": "2025-11-12", "close": 30.0},
            {"date": "2025-12-15", "close": 30.5},
            {"date": "2026-02-12", "close": 32.5},
        ]

        result = analyze_fx_rate_changes("USD/TWD", 32.5, [], long)

        trend_alerts = [
            a for a in result if a.alert_type == FXAlertType.LONG_TERM_TREND
        ]
        assert len(trend_alerts) == 1
        assert trend_alerts[0].period_label == "3 個月"

    def test_should_not_detect_long_term_trend_when_below_threshold(self):
        # Arrange: 3-month change ~5.0% (< 8.0%)
        long = [
            {"date": "2025-11-12", "close": 30.0},
            {"date": "2026-02-12", "close": 31.5},
        ]

        result = analyze_fx_rate_changes("USD/TWD", 31.5, [], long)

        trend_alerts = [
            a for a in result if a.alert_type == FXAlertType.LONG_TERM_TREND
        ]
        assert len(trend_alerts) == 0

    def test_should_detect_multiple_alert_types_simultaneously(self):
        # Arrange: all three tiers fire
        short = [
            {"date": "2026-02-07", "close": 30.0},
            {"date": "2026-02-08", "close": 30.1},
            {"date": "2026-02-09", "close": 30.2},
            {"date": "2026-02-10", "close": 30.3},
            {"date": "2026-02-11", "close": 31.0},  # daily 2.31%, 5d 3.33%
        ]
        long = [
            {"date": "2025-11-12", "close": 28.0},
            {"date": "2026-02-11", "close": 31.0},  # 10.71%
        ]

        result = analyze_fx_rate_changes("USD/TWD", 31.0, short, long)

        types = {a.alert_type for a in result}
        assert FXAlertType.DAILY_SPIKE in types
        assert FXAlertType.SHORT_TERM_SWING in types
        assert FXAlertType.LONG_TERM_TREND in types

    def test_should_detect_downward_direction(self):
        # Arrange: daily drop of ~1.56%
        short = [
            {"date": "2026-02-10", "close": 32.0},
            {"date": "2026-02-11", "close": 31.5},
        ]

        result = analyze_fx_rate_changes("USD/TWD", 31.5, short, [])

        spike_alerts = [a for a in result if a.alert_type == FXAlertType.DAILY_SPIKE]
        assert len(spike_alerts) == 1
        assert spike_alerts[0].direction == "down"
        assert spike_alerts[0].change_pct < 0

    def test_should_handle_single_data_point(self):
        short = [{"date": "2026-02-12", "close": 32.0}]
        long = [{"date": "2025-11-12", "close": 30.0}]

        result = analyze_fx_rate_changes("USD/TWD", 32.0, short, long)
        assert result == []

    def test_should_handle_zero_close_price(self):
        short = [
            {"date": "2026-02-10", "close": 0.0},
            {"date": "2026-02-11", "close": 32.0},
        ]

        result = analyze_fx_rate_changes("USD/TWD", 32.0, short, [])
        # Zero first close → _compute_change_pct returns None → no alert
        spike_alerts = [a for a in result if a.alert_type == FXAlertType.DAILY_SPIKE]
        assert len(spike_alerts) == 0


# ---------------------------------------------------------------------------
# determine_fx_risk_level
# ---------------------------------------------------------------------------


class TestDetermineFxRiskLevel:
    """Alert-severity-based risk classification."""

    def test_should_return_high_when_daily_spike_present(self):
        alerts = [
            FXRateAlert("USD/TWD", FXAlertType.DAILY_SPIKE, 2.0, "up", 32.0, "1 日"),
        ]
        assert determine_fx_risk_level(alerts) == "high"

    def test_should_return_medium_when_short_term_swing_present(self):
        alerts = [
            FXRateAlert(
                "USD/TWD", FXAlertType.SHORT_TERM_SWING, 2.5, "up", 32.0, "5 日"
            ),
        ]
        assert determine_fx_risk_level(alerts) == "medium"

    def test_should_return_low_when_only_long_term_trend(self):
        alerts = [
            FXRateAlert(
                "USD/TWD", FXAlertType.LONG_TERM_TREND, 9.0, "up", 32.0, "3 個月"
            ),
        ]
        assert determine_fx_risk_level(alerts) == "low"

    def test_should_return_low_when_no_alerts(self):
        assert determine_fx_risk_level([]) == "low"

    def test_should_return_high_when_mixed_alerts_include_spike(self):
        alerts = [
            FXRateAlert(
                "USD/TWD", FXAlertType.LONG_TERM_TREND, 9.0, "up", 32.0, "3 個月"
            ),
            FXRateAlert("JPY/TWD", FXAlertType.DAILY_SPIKE, -1.8, "down", 0.21, "1 日"),
        ]
        assert determine_fx_risk_level(alerts) == "high"

    def test_should_return_medium_when_swing_and_trend_present(self):
        alerts = [
            FXRateAlert(
                "USD/TWD", FXAlertType.SHORT_TERM_SWING, 2.5, "up", 32.0, "5 日"
            ),
            FXRateAlert(
                "USD/TWD", FXAlertType.LONG_TERM_TREND, 9.0, "up", 32.0, "3 個月"
            ),
        ]
        assert determine_fx_risk_level(alerts) == "medium"
