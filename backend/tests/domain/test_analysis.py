"""Tests for pure analysis functions in domain/analysis.py."""

from domain.analysis import (
    compute_bias_percentile,
    compute_twr,
    detect_rogue_wave,
    determine_market_sentiment,
    determine_scan_signal,
)
from domain.constants import (
    ROGUE_WAVE_BIAS_PERCENTILE,
    ROGUE_WAVE_MIN_HISTORY_DAYS,
    ROGUE_WAVE_VOLUME_RATIO_THRESHOLD,
)
from domain.enums import MarketSentiment, MoatStatus, ScanSignal

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


# ---------------------------------------------------------------------------
# determine_scan_signal — 9-priority cascade
# ---------------------------------------------------------------------------

STABLE = MoatStatus.STABLE.value
DETERIORATING = MoatStatus.DETERIORATING.value


class TestDetermineScanSignal:
    """Tests for the 9-priority determine_scan_signal() cascade."""

    # --- P1: THESIS_BROKEN ---

    def test_p1_thesis_broken_when_moat_deteriorating(self):
        assert (
            determine_scan_signal(DETERIORATING, rsi=30.0, bias=-25.0)
            == ScanSignal.THESIS_BROKEN
        )

    def test_p1_thesis_broken_trumps_deep_value_scenario(self):
        # moat=DETERIORATING wins even when both RSI+bias would otherwise trigger DEEP_VALUE
        assert (
            determine_scan_signal(DETERIORATING, rsi=20.0, bias=-40.0)
            == ScanSignal.THESIS_BROKEN
        )

    # --- P2: DEEP_VALUE ---

    def test_p2_deep_value_when_both_indicators_confirm(self):
        assert (
            determine_scan_signal(STABLE, rsi=30.0, bias=-25.0) == ScanSignal.DEEP_VALUE
        )

    def test_p2_deep_value_boundary_exactly_at_thresholds(self):
        # bias=-20.01, rsi=34.99 → both just cross the boundary
        assert (
            determine_scan_signal(STABLE, rsi=34.99, bias=-20.01)
            == ScanSignal.DEEP_VALUE
        )

    # --- P3: OVERSOLD ---

    def test_p3_oversold_when_bias_extreme_rsi_not_confirming(self):
        # APP-like: bias=-31.26, RSI=38.7 (RSI ≥ 35, so P2 skipped)
        assert (
            determine_scan_signal(STABLE, rsi=38.7, bias=-31.26) == ScanSignal.OVERSOLD
        )

    def test_p3_oversold_boundary_rsi_just_misses_p2(self):
        # bias=-20.01 (crosses P3), RSI=35.01 (misses P2)
        assert (
            determine_scan_signal(STABLE, rsi=35.01, bias=-20.01) == ScanSignal.OVERSOLD
        )

    def test_p3_oversold_when_rsi_is_none(self):
        # Without RSI, P2 is skipped; bias alone triggers P3
        assert (
            determine_scan_signal(STABLE, rsi=None, bias=-25.0) == ScanSignal.OVERSOLD
        )

    # --- P4: CONTRARIAN_BUY ---

    def test_p4_contrarian_buy_rsi_oversold_bias_normal(self):
        assert (
            determine_scan_signal(STABLE, rsi=32.0, bias=-5.0)
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_p4_contrarian_buy_bias_just_misses_p2_and_p3(self):
        # bias=-19.99 (doesn't cross -20), rsi=34.99 → falls to P4
        assert (
            determine_scan_signal(STABLE, rsi=34.99, bias=-19.99)
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_p4_contrarian_buy_with_bias_none(self):
        # bias=None: P2/P3 skipped; P4 condition `bias is None or bias < 20` → True
        assert (
            determine_scan_signal(STABLE, rsi=32.0, bias=None)
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_p4_not_contrarian_buy_when_bias_over_20_contradicts(self):
        # Issue 2 fix: RSI=30 + bias=+25 must NOT be CONTRARIAN_BUY
        result = determine_scan_signal(STABLE, rsi=30.0, bias=25.0)
        assert result != ScanSignal.CONTRARIAN_BUY
        assert result == ScanSignal.CAUTION_HIGH

    # --- P5: OVERHEATED ---

    def test_p5_overheated_when_both_indicators_confirm(self):
        assert (
            determine_scan_signal(STABLE, rsi=75.0, bias=25.0) == ScanSignal.OVERHEATED
        )

    def test_p5_overheated_boundary_exactly_at_thresholds(self):
        # bias=20.01, rsi=70.01 → both just cross
        assert (
            determine_scan_signal(STABLE, rsi=70.01, bias=20.01)
            == ScanSignal.OVERHEATED
        )

    # --- P6: CAUTION_HIGH ---

    def test_p6_caution_high_bias_only(self):
        assert (
            determine_scan_signal(STABLE, rsi=50.0, bias=22.0)
            == ScanSignal.CAUTION_HIGH
        )

    def test_p6_caution_high_rsi_only(self):
        assert (
            determine_scan_signal(STABLE, rsi=72.0, bias=5.0) == ScanSignal.CAUTION_HIGH
        )

    def test_p6_caution_high_bias_only_rsi_none(self):
        assert (
            determine_scan_signal(STABLE, rsi=None, bias=22.0)
            == ScanSignal.CAUTION_HIGH
        )

    def test_p6_caution_high_rsi_only_bias_none(self):
        assert (
            determine_scan_signal(STABLE, rsi=72.0, bias=None)
            == ScanSignal.CAUTION_HIGH
        )

    def test_p6_caution_high_boundary_rsi_just_misses_p5(self):
        # bias=20.01, rsi=69.99 → bias crosses P5 bias threshold but RSI misses → P6
        assert (
            determine_scan_signal(STABLE, rsi=69.99, bias=20.01)
            == ScanSignal.CAUTION_HIGH
        )

    # --- P7: WEAKENING ---

    def test_p7_weakening_both_thresholds_met(self):
        assert (
            determine_scan_signal(STABLE, rsi=37.0, bias=-16.0) == ScanSignal.WEAKENING
        )

    def test_p7_weakening_exact_boundary(self):
        # bias=-15.01, rsi=37.99 → both just cross
        assert (
            determine_scan_signal(STABLE, rsi=37.99, bias=-15.01)
            == ScanSignal.WEAKENING
        )

    def test_p7_just_misses_weakening_both(self):
        # bias=-14.99, rsi=37.99 → bias doesn't cross -15 → NORMAL
        assert (
            determine_scan_signal(STABLE, rsi=37.99, bias=-14.99) == ScanSignal.NORMAL
        )

    # --- P8: NORMAL ---

    def test_p8_normal_all_neutral(self):
        assert determine_scan_signal(STABLE, rsi=50.0, bias=0.0) == ScanSignal.NORMAL

    def test_p8_normal_both_none(self):
        assert determine_scan_signal(STABLE, rsi=None, bias=None) == ScanSignal.NORMAL

    # --- None-handling (Issue 5 fix) ---

    def test_none_rsi_none_bias_moat_deteriorating_returns_thesis_broken(self):
        assert (
            determine_scan_signal(DETERIORATING, rsi=None, bias=None)
            == ScanSignal.THESIS_BROKEN
        )

    def test_none_rsi_with_normal_bias_falls_to_normal(self):
        # rsi=None, bias=-5 → P2/P3/P4/P7 all need rsi or bias threshold → NORMAL
        assert determine_scan_signal(STABLE, rsi=None, bias=-5.0) == ScanSignal.NORMAL

    def test_none_bias_with_normal_rsi_falls_to_normal(self):
        # rsi=50, bias=None → no thresholds triggered → NORMAL
        assert determine_scan_signal(STABLE, rsi=50.0, bias=None) == ScanSignal.NORMAL

    # --- Real-world regression (2026-02-19 scan log) ---

    def test_regression_app_oversold(self):
        # APP: RSI=38.7, bias=-31.26 → was NORMAL, now OVERSOLD
        assert (
            determine_scan_signal(STABLE, rsi=38.7, bias=-31.26) == ScanSignal.OVERSOLD
        )

    def test_regression_coin_oversold(self):
        # COIN: RSI=37.35, bias=-28.25 → was NORMAL, now OVERSOLD
        assert (
            determine_scan_signal(STABLE, rsi=37.35, bias=-28.25) == ScanSignal.OVERSOLD
        )

    def test_regression_amzn_contrarian_buy(self):
        # AMZN: RSI=31.95, bias=-10.66 → was NORMAL, now CONTRARIAN_BUY
        assert (
            determine_scan_signal(STABLE, rsi=31.95, bias=-10.66)
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_regression_googl_contrarian_buy(self):
        # GOOGL: RSI=31.84, bias=-5.04 → was NORMAL, now CONTRARIAN_BUY
        assert (
            determine_scan_signal(STABLE, rsi=31.84, bias=-5.04)
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_regression_asml_caution_high(self):
        # ASML: RSI=64.81, bias=20.41 → was OVERHEATED, now CAUTION_HIGH (RSI<70)
        assert (
            determine_scan_signal(STABLE, rsi=64.81, bias=20.41)
            == ScanSignal.CAUTION_HIGH
        )

    def test_regression_lite_overheated(self):
        # LITE: RSI=74.03, bias=54.63 → still OVERHEATED
        assert (
            determine_scan_signal(STABLE, rsi=74.03, bias=54.63)
            == ScanSignal.OVERHEATED
        )

    def test_regression_vrt_overheated(self):
        # VRT: RSI=71.62, bias=34.56 → still OVERHEATED
        assert (
            determine_scan_signal(STABLE, rsi=71.62, bias=34.56)
            == ScanSignal.OVERHEATED
        )

    def test_regression_snps_thesis_broken(self):
        # SNPS: RSI=45.14, bias=-5.06, moat=DETERIORATING → still THESIS_BROKEN
        assert (
            determine_scan_signal(DETERIORATING, rsi=45.14, bias=-5.06)
            == ScanSignal.THESIS_BROKEN
        )

    def test_regression_aapl_normal(self):
        # AAPL: RSI=49.08, bias=-1.52 → still NORMAL
        assert determine_scan_signal(STABLE, rsi=49.08, bias=-1.52) == ScanSignal.NORMAL


class TestDetermineScanSignalEnhancements:
    """Tests for P4.5 APPROACHING_BUY, category-aware thresholds, and MA200 amplifier."""

    # --- P4.5: APPROACHING_BUY base signal ---

    def test_p45_approaching_buy_rsi_in_accumulation_zone(self):
        # RSI=36 (35 < 36 < 37), bias=-16 (< -15) → APPROACHING_BUY (no category)
        assert (
            determine_scan_signal(STABLE, rsi=36.0, bias=-16.0)
            == ScanSignal.APPROACHING_BUY
        )

    def test_p45_approaching_buy_boundary_exactly_at_threshold(self):
        # RSI=36.99, bias=-15.01 → just inside both boundaries
        assert (
            determine_scan_signal(STABLE, rsi=36.99, bias=-15.01)
            == ScanSignal.APPROACHING_BUY
        )

    def test_p45_not_approaching_buy_when_rsi_above_threshold(self):
        # RSI=37.1 (≥ 37+0), bias=-16 → falls to WEAKENING
        assert (
            determine_scan_signal(STABLE, rsi=37.1, bias=-16.0) == ScanSignal.WEAKENING
        )

    def test_p45_not_approaching_buy_when_bias_above_weakening_threshold(self):
        # RSI=36, bias=-14 (> -15) → misses P4.5 bias condition → NORMAL
        assert determine_scan_signal(STABLE, rsi=36.0, bias=-14.0) == ScanSignal.NORMAL

    # --- Category-aware thresholds: buy side ---

    def test_category_growth_offset_upgrades_to_contrarian_buy(self):
        # Growth offset=+2; rsi_contrarian=37; RSI=36 < 37 → CONTRARIAN_BUY
        assert (
            determine_scan_signal(STABLE, rsi=36.0, bias=-5.0, category="Growth")
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_category_trend_setter_no_offset_stays_approaching_buy(self):
        # Trend_Setter offset=0; rsi_contrarian=35; RSI=36 > 35 → only APPROACHING_BUY
        assert (
            determine_scan_signal(STABLE, rsi=36.0, bias=-16.0, category="Trend_Setter")
            == ScanSignal.APPROACHING_BUY
        )

    def test_category_moat_offset_plus1_approaching_buy(self):
        # Moat offset=+1; rsi_contrarian=36; RSI=36.5 > 36 → rsi_approaching=38; RSI=36.5 < 38 → APPROACHING_BUY
        assert (
            determine_scan_signal(STABLE, rsi=36.5, bias=-16.0, category="Moat")
            == ScanSignal.APPROACHING_BUY
        )

    def test_category_bond_offset_minus3_tighter_buy_threshold(self):
        # Bond offset=-3; rsi_contrarian=32; RSI=33 > 32 → misses P4; rsi_approaching=34; RSI=33 < 34, bias=-16 < -15 → APPROACHING_BUY
        assert (
            determine_scan_signal(STABLE, rsi=33.0, bias=-16.0, category="Bond")
            == ScanSignal.APPROACHING_BUY
        )

    def test_category_bond_offset_rsi_above_approaching_threshold_is_weakening(self):
        # Bond offset=-3; rsi_weakening=35; RSI=34 < 35 → WEAKENING
        assert (
            determine_scan_signal(STABLE, rsi=34.0, bias=-16.0, category="Bond")
            == ScanSignal.WEAKENING
        )

    # --- Category-aware thresholds: sell side ---

    def test_category_growth_rsi71_stays_caution_high(self):
        # Growth offset=+2; rsi_overbought=72; RSI=71 < 72, bias=21 > 20 → only bias triggers → CAUTION_HIGH
        assert (
            determine_scan_signal(STABLE, rsi=71.0, bias=21.0, category="Growth")
            == ScanSignal.CAUTION_HIGH
        )

    def test_category_trend_setter_rsi71_becomes_overheated(self):
        # Trend_Setter offset=0; rsi_overbought=70; RSI=71 > 70 AND bias=21 > 20 → OVERHEATED
        assert (
            determine_scan_signal(STABLE, rsi=71.0, bias=21.0, category="Trend_Setter")
            == ScanSignal.OVERHEATED
        )

    def test_category_bond_rsi68_becomes_overheated(self):
        # Bond offset=-3; rsi_overbought=67; RSI=68 > 67 AND bias=21 > 20 → OVERHEATED
        assert (
            determine_scan_signal(STABLE, rsi=68.0, bias=21.0, category="Bond")
            == ScanSignal.OVERHEATED
        )

    def test_category_growth_rsi72_becomes_overheated(self):
        # Growth offset=+2; rsi_overbought=72; RSI=72.5 > 72 AND bias=22 > 20 → OVERHEATED
        assert (
            determine_scan_signal(STABLE, rsi=72.5, bias=22.0, category="Growth")
            == ScanSignal.OVERHEATED
        )

    # --- MA200 buy-side amplifier ---

    def test_ma200_buy_amplifier_weakening_to_approaching_buy(self):
        # RSI=37.5, bias=-16 → WEAKENING; bias_200=-16 < -15 → upgraded to APPROACHING_BUY
        assert (
            determine_scan_signal(STABLE, rsi=37.5, bias=-16.0, bias_200=-16.0)
            == ScanSignal.APPROACHING_BUY
        )

    def test_ma200_buy_amplifier_approaching_buy_to_contrarian_buy(self):
        # P4.5 produces APPROACHING_BUY; bias_200=-16 < -15 → upgraded to CONTRARIAN_BUY
        assert (
            determine_scan_signal(STABLE, rsi=36.0, bias=-16.0, bias_200=-16.0)
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_ma200_buy_amplifier_no_op_when_bias_200_above_threshold(self):
        # WEAKENING + bias_200=-14 (> -15) → no upgrade
        assert (
            determine_scan_signal(STABLE, rsi=37.5, bias=-16.0, bias_200=-14.0)
            == ScanSignal.WEAKENING
        )

    # --- MA200 sell-side amplifier ---

    def test_ma200_sell_amplifier_caution_high_to_overheated(self):
        # P6 CAUTION_HIGH (bias=22, RSI=65); bias_200=21 > 20 → upgraded to OVERHEATED
        assert (
            determine_scan_signal(STABLE, rsi=65.0, bias=22.0, bias_200=21.0)
            == ScanSignal.OVERHEATED
        )

    def test_ma200_sell_amplifier_no_double_upgrade_already_overheated(self):
        # Already OVERHEATED (RSI=75, bias=25); bias_200=21 > 20 → still OVERHEATED
        assert (
            determine_scan_signal(STABLE, rsi=75.0, bias=25.0, bias_200=21.0)
            == ScanSignal.OVERHEATED
        )

    def test_ma200_sell_amplifier_no_op_when_bias_200_below_threshold(self):
        # CAUTION_HIGH + bias_200=19 (< 20) → no upgrade
        assert (
            determine_scan_signal(STABLE, rsi=65.0, bias=22.0, bias_200=19.0)
            == ScanSignal.CAUTION_HIGH
        )

    # --- MA200 amplifier no-op for NORMAL and extreme signals ---

    def test_ma200_amplifier_noop_for_normal_buy_side(self):
        assert (
            determine_scan_signal(STABLE, rsi=50.0, bias=0.0, bias_200=-16.0)
            == ScanSignal.NORMAL
        )

    def test_ma200_amplifier_noop_for_normal_sell_side(self):
        assert (
            determine_scan_signal(STABLE, rsi=50.0, bias=0.0, bias_200=21.0)
            == ScanSignal.NORMAL
        )

    def test_ma200_amplifier_noop_for_deep_value(self):
        # DEEP_VALUE is never downgraded by amplifier
        assert (
            determine_scan_signal(STABLE, rsi=30.0, bias=-25.0, bias_200=-16.0)
            == ScanSignal.DEEP_VALUE
        )

    # --- Combined: category + MA200 amplifier ---

    def test_combined_growth_and_ma200_buy_amplifier(self):
        # Growth offset=+2; RSI=37.5 < 39 (rsi_approaching) → APPROACHING_BUY
        # bias_200=-16 < -15 → upgraded to CONTRARIAN_BUY
        assert (
            determine_scan_signal(
                STABLE, rsi=37.5, bias=-16.0, bias_200=-16.0, category="Growth"
            )
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_combined_bond_and_ma200_sell_amplifier(self):
        # Bond offset=-3; rsi_overbought=67; RSI=65 < 67, bias=22 → CAUTION_HIGH
        # bias_200=21 > 20 → upgraded to OVERHEATED
        assert (
            determine_scan_signal(
                STABLE, rsi=65.0, bias=22.0, bias_200=21.0, category="Bond"
            )
            == ScanSignal.OVERHEATED
        )

    # --- Regression: CRWD-like scenario ---

    def test_regression_crwd_growth_contrarian_buy(self):
        # CRWD: RSI=35.74, bias=-16.34, bias_200=-17.55, category=Growth
        # Growth offset=+2; rsi_contrarian=37; RSI=35.74 < 37 → CONTRARIAN_BUY
        # MA200 amplifier: already CONTRARIAN_BUY → no further upgrade
        assert (
            determine_scan_signal(
                STABLE, rsi=35.74, bias=-16.34, bias_200=-17.55, category="Growth"
            )
            == ScanSignal.CONTRARIAN_BUY
        )

    def test_regression_crwd_no_category_was_weakening(self):
        # Same CRWD values without category → falls to WEAKENING (dead zone scenario)
        # RSI=35.74 > 35 (misses P4); RSI=35.74 < 37 but bias=-16.34 < -15 → APPROACHING_BUY
        assert (
            determine_scan_signal(STABLE, rsi=35.74, bias=-16.34)
            == ScanSignal.APPROACHING_BUY
        )


# ---------------------------------------------------------------------------
# compute_twr
# ---------------------------------------------------------------------------


def _snap(date_str: str, value: float) -> dict:
    return {"snapshot_date": date_str, "total_value": value}


class TestComputeTwr:
    """Tests for compute_twr()."""

    # --- happy path ---

    def test_should_return_zero_for_flat_portfolio(self):
        snaps = [_snap("2025-01-01", 100_000), _snap("2025-01-31", 100_000)]
        assert compute_twr(snaps) == 0.0

    def test_should_return_positive_for_growing_portfolio(self):
        snaps = [_snap("2025-01-01", 100_000), _snap("2025-12-31", 110_000)]
        assert compute_twr(snaps) == 10.0

    def test_should_return_negative_for_declining_portfolio(self):
        snaps = [_snap("2025-01-01", 100_000), _snap("2025-12-31", 90_000)]
        assert compute_twr(snaps) == -10.0

    def test_should_chain_multiply_sub_period_returns(self):
        # +10% then +10% → TWR = (1.1 * 1.1 - 1) * 100 = 21%
        snaps = [
            _snap("2025-01-01", 100_000),
            _snap("2025-06-01", 110_000),
            _snap("2025-12-31", 121_000),
        ]
        assert compute_twr(snaps) == 21.0

    def test_should_handle_non_contiguous_dates(self):
        # Gaps between snapshots (weekends/holidays) are handled correctly
        snaps = [
            _snap("2025-01-01", 100_000),
            _snap("2025-01-06", 102_000),  # +2% over a weekend gap
            _snap("2025-01-13", 99_960),  # back down
        ]
        result = compute_twr(snaps)
        assert result is not None
        # chain: 1.02 * (99960/102000) = 1.02 * 0.98 = 0.9996 → -0.04%
        assert abs(result - (-0.04)) < 0.01

    # --- edge cases / error handling ---

    def test_should_return_none_for_empty_list(self):
        assert compute_twr([]) is None

    def test_should_return_none_for_single_snapshot(self):
        assert compute_twr([_snap("2025-01-01", 100_000)]) is None

    def test_should_return_none_when_first_value_is_zero(self):
        snaps = [_snap("2025-01-01", 0), _snap("2025-01-31", 100_000)]
        assert compute_twr(snaps) is None

    def test_should_return_none_when_intermediate_value_is_zero(self):
        snaps = [
            _snap("2025-01-01", 100_000),
            _snap("2025-06-01", 0),
            _snap("2025-12-31", 110_000),
        ]
        assert compute_twr(snaps) is None

    def test_should_return_none_when_value_is_none(self):
        snaps = [
            {"snapshot_date": "2025-01-01", "total_value": None},
            _snap("2025-01-31", 100_000),
        ]
        assert compute_twr(snaps) is None

    def test_should_not_require_last_value_to_be_nonzero(self):
        # Only intermediate values (not the last) must be non-zero
        snaps = [_snap("2025-01-01", 100_000), _snap("2025-12-31", 0)]
        result = compute_twr(snaps)
        # product = 0/100000 = 0, TWR = -100%
        assert result == -100.0


# ---------------------------------------------------------------------------
# determine_market_sentiment — 5-tier breadth classification
# ---------------------------------------------------------------------------


class TestDetermineMarketSentiment:
    """Tests for the 5-tier determine_market_sentiment() function."""

    # --- Edge case: no valid stocks ---

    def test_no_valid_stocks_returns_bullish(self):
        sentiment, pct = determine_market_sentiment(0, 0)
        assert sentiment == MarketSentiment.BULLISH
        assert pct == 0.0

    # --- STRONG_BULLISH: 0–10% ---

    def test_zero_below_returns_strong_bullish(self):
        sentiment, pct = determine_market_sentiment(0, 10)
        assert sentiment == MarketSentiment.STRONG_BULLISH
        assert pct == 0.0

    def test_exactly_10_pct_returns_strong_bullish(self):
        sentiment, pct = determine_market_sentiment(1, 10)
        assert sentiment == MarketSentiment.STRONG_BULLISH
        assert pct == 10.0

    # --- BULLISH: 10–30% ---

    def test_just_above_10_pct_returns_bullish(self):
        # 2/10 = 20%
        sentiment, pct = determine_market_sentiment(2, 10)
        assert sentiment == MarketSentiment.BULLISH
        assert pct == 20.0

    def test_exactly_30_pct_returns_bullish(self):
        sentiment, pct = determine_market_sentiment(3, 10)
        assert sentiment == MarketSentiment.BULLISH
        assert pct == 30.0

    # --- NEUTRAL: 30–50% ---

    def test_just_above_30_pct_returns_neutral(self):
        # 4/10 = 40%
        sentiment, pct = determine_market_sentiment(4, 10)
        assert sentiment == MarketSentiment.NEUTRAL
        assert pct == 40.0

    def test_exactly_50_pct_returns_neutral(self):
        sentiment, pct = determine_market_sentiment(5, 10)
        assert sentiment == MarketSentiment.NEUTRAL
        assert pct == 50.0

    # --- BEARISH: 50–70% ---

    def test_just_above_50_pct_returns_bearish(self):
        # 6/10 = 60%
        sentiment, pct = determine_market_sentiment(6, 10)
        assert sentiment == MarketSentiment.BEARISH
        assert pct == 60.0

    def test_exactly_70_pct_returns_bearish(self):
        sentiment, pct = determine_market_sentiment(7, 10)
        assert sentiment == MarketSentiment.BEARISH
        assert pct == 70.0

    # --- STRONG_BEARISH: >70% ---

    def test_just_above_70_pct_returns_strong_bearish(self):
        # 8/10 = 80%
        sentiment, pct = determine_market_sentiment(8, 10)
        assert sentiment == MarketSentiment.STRONG_BEARISH
        assert pct == 80.0

    def test_all_below_returns_strong_bearish(self):
        sentiment, pct = determine_market_sentiment(10, 10)
        assert sentiment == MarketSentiment.STRONG_BEARISH
        assert pct == 100.0

    # --- Fractional edge cases ---

    def test_boundary_10_1_pct(self):
        # 10.7% → BULLISH (just above 10% boundary)
        sentiment, pct = determine_market_sentiment(3, 28)
        assert sentiment == MarketSentiment.BULLISH

    def test_boundary_30_pct_exact(self):
        # 3/10 = 30.0% → exactly at boundary → BULLISH (≤30)
        sentiment, pct = determine_market_sentiment(3, 10)
        assert sentiment == MarketSentiment.BULLISH
        assert pct == 30.0
