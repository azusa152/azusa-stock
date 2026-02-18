"""Tests for Rogue Wave pure analysis functions in domain/analysis.py."""

from domain.analysis import compute_bias_percentile, detect_rogue_wave
from domain.constants import (
    ROGUE_WAVE_BIAS_PERCENTILE,
    ROGUE_WAVE_MIN_HISTORY_DAYS,
    ROGUE_WAVE_VOLUME_RATIO_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sorted_biases(n: int, low: float = -30.0, high: float = 30.0) -> list[float]:
    """Return a sorted list of n evenly-spaced bias values in [low, high]."""
    step = (high - low) / (n - 1) if n > 1 else 0.0
    return [round(low + i * step, 4) for i in range(n)]


# Minimal valid history (exactly MIN_HISTORY_DAYS values, uniformly spaced -30 to 30)
VALID_HISTORY = _sorted_biases(ROGUE_WAVE_MIN_HISTORY_DAYS)


# ---------------------------------------------------------------------------
# compute_bias_percentile
# ---------------------------------------------------------------------------


class TestComputeBiasPercentile:
    """Tests for compute_bias_percentile()."""

    # --- happy path ---

    def test_compute_bias_percentile_should_return_100_when_above_all_history(self):
        result = compute_bias_percentile(999.0, VALID_HISTORY)
        assert result == 100.0

    def test_compute_bias_percentile_should_return_0_when_below_all_history(self):
        result = compute_bias_percentile(-999.0, VALID_HISTORY)
        assert result == 0.0

    def test_compute_bias_percentile_should_return_near_50_for_median_value(self):
        median_value = VALID_HISTORY[len(VALID_HISTORY) // 2]
        result = compute_bias_percentile(median_value, VALID_HISTORY)
        assert result is not None
        assert 49.0 <= result <= 51.0

    def test_compute_bias_percentile_should_return_float_in_range_0_to_100(self):
        result = compute_bias_percentile(10.0, VALID_HISTORY)
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_compute_bias_percentile_should_round_to_two_decimal_places(self):
        result = compute_bias_percentile(5.0, VALID_HISTORY)
        assert result is not None
        assert result == round(result, 2)

    # --- boundary: exact value present in history ---

    def test_compute_bias_percentile_should_use_bisect_left_for_exact_match(self):
        # bisect_left returns leftmost index of the matching value
        history = sorted([float(i) for i in range(ROGUE_WAVE_MIN_HISTORY_DAYS)])
        val = history[100]
        result = compute_bias_percentile(val, history)
        assert result is not None
        expected = round(100 / len(history) * 100, 2)
        assert result == expected

    # --- negative bias values ---

    def test_compute_bias_percentile_should_handle_negative_bias(self):
        result = compute_bias_percentile(-25.0, VALID_HISTORY)
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_compute_bias_percentile_should_return_0_when_negative_bias_below_all_history(
        self,
    ):
        history = sorted([float(i) for i in range(ROGUE_WAVE_MIN_HISTORY_DAYS)])
        result = compute_bias_percentile(-1.0, history)
        assert result == 0.0

    # --- insufficient history ---

    def test_compute_bias_percentile_should_return_none_when_history_empty(self):
        assert compute_bias_percentile(10.0, []) is None

    def test_compute_bias_percentile_should_return_none_when_history_below_min(self):
        short = _sorted_biases(ROGUE_WAVE_MIN_HISTORY_DAYS - 1)
        assert compute_bias_percentile(10.0, short) is None

    def test_compute_bias_percentile_should_return_value_when_history_exactly_min(self):
        assert compute_bias_percentile(10.0, VALID_HISTORY) is not None

    def test_compute_bias_percentile_should_return_value_when_history_above_min(self):
        long_history = _sorted_biases(ROGUE_WAVE_MIN_HISTORY_DAYS + 50)
        assert compute_bias_percentile(10.0, long_history) is not None

    # --- monotonicity ---

    def test_compute_bias_percentile_should_yield_higher_percentile_for_higher_bias(
        self,
    ):
        p_low = compute_bias_percentile(5.0, VALID_HISTORY)
        p_high = compute_bias_percentile(20.0, VALID_HISTORY)
        assert p_low is not None and p_high is not None
        assert p_high >= p_low

    # --- duplicate values edge case ---

    def test_compute_bias_percentile_should_handle_history_with_many_duplicates(self):
        # 150 zeros followed by 50 ones — bisect_left(0.0) → rank 0 → 0%
        history = sorted([0.0] * 150 + [1.0] * 50)
        assert len(history) == ROGUE_WAVE_MIN_HISTORY_DAYS

        result_at_zero = compute_bias_percentile(0.0, history)
        assert result_at_zero == 0.0  # bisect_left finds leftmost 0.0

        result_at_one = compute_bias_percentile(1.0, history)
        assert result_at_one is not None
        assert result_at_one == round(150 / 200 * 100, 2)  # 75.0

        result_above_all = compute_bias_percentile(2.0, history)
        assert result_above_all == 100.0


# ---------------------------------------------------------------------------
# detect_rogue_wave
# ---------------------------------------------------------------------------


class TestDetectRogueWave:
    """Tests for detect_rogue_wave()."""

    # --- returns True only when BOTH thresholds are met ---

    def test_detect_rogue_wave_should_return_true_when_both_thresholds_met(self):
        assert detect_rogue_wave(
            bias_percentile=float(ROGUE_WAVE_BIAS_PERCENTILE),
            volume_ratio=float(ROGUE_WAVE_VOLUME_RATIO_THRESHOLD),
        )

    def test_detect_rogue_wave_should_return_true_when_both_thresholds_exceeded(self):
        assert detect_rogue_wave(bias_percentile=99.0, volume_ratio=3.0)

    # --- returns False when one condition is below threshold ---

    def test_detect_rogue_wave_should_return_false_when_bias_percentile_below_threshold(
        self,
    ):
        assert not detect_rogue_wave(
            bias_percentile=float(ROGUE_WAVE_BIAS_PERCENTILE) - 0.01,
            volume_ratio=float(ROGUE_WAVE_VOLUME_RATIO_THRESHOLD),
        )

    def test_detect_rogue_wave_should_return_false_when_volume_ratio_below_threshold(
        self,
    ):
        assert not detect_rogue_wave(
            bias_percentile=float(ROGUE_WAVE_BIAS_PERCENTILE),
            volume_ratio=float(ROGUE_WAVE_VOLUME_RATIO_THRESHOLD) - 0.01,
        )

    def test_detect_rogue_wave_should_return_false_when_both_below_threshold(self):
        assert not detect_rogue_wave(bias_percentile=50.0, volume_ratio=1.0)

    # --- None inputs ---

    def test_detect_rogue_wave_should_return_false_when_bias_percentile_is_none(self):
        assert not detect_rogue_wave(
            bias_percentile=None,
            volume_ratio=float(ROGUE_WAVE_VOLUME_RATIO_THRESHOLD),
        )

    def test_detect_rogue_wave_should_return_false_when_volume_ratio_is_none(self):
        assert not detect_rogue_wave(
            bias_percentile=float(ROGUE_WAVE_BIAS_PERCENTILE),
            volume_ratio=None,
        )

    def test_detect_rogue_wave_should_return_false_when_both_none(self):
        assert not detect_rogue_wave(bias_percentile=None, volume_ratio=None)

    # --- exact boundary values (inclusive) ---

    def test_detect_rogue_wave_should_return_true_at_exact_bias_percentile_boundary(
        self,
    ):
        assert detect_rogue_wave(bias_percentile=95.0, volume_ratio=2.0)

    def test_detect_rogue_wave_should_return_true_at_exact_volume_ratio_boundary(self):
        assert detect_rogue_wave(bias_percentile=97.0, volume_ratio=1.5)

    def test_detect_rogue_wave_should_return_false_just_below_bias_percentile_boundary(
        self,
    ):
        assert not detect_rogue_wave(bias_percentile=94.99, volume_ratio=2.0)

    def test_detect_rogue_wave_should_return_false_just_below_volume_ratio_boundary(
        self,
    ):
        assert not detect_rogue_wave(bias_percentile=97.0, volume_ratio=1.49)
