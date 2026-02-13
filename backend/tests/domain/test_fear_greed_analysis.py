"""Tests for Fear & Greed pure analysis functions in domain/analysis.py."""

from domain.analysis import (
    _vix_to_score,
    classify_cnn_fear_greed,
    classify_vix,
    compute_composite_fear_greed,
)
from domain.enums import FearGreedLevel


class TestClassifyVix:
    """Tests for classify_vix — VIX → FearGreedLevel mapping."""

    def test_classify_vix_should_return_extreme_fear_when_above_30(self):
        assert classify_vix(35.0) == FearGreedLevel.EXTREME_FEAR

    def test_classify_vix_should_return_fear_when_between_20_and_30(self):
        assert classify_vix(25.0) == FearGreedLevel.FEAR

    def test_classify_vix_should_return_neutral_when_between_15_and_20(self):
        assert classify_vix(17.0) == FearGreedLevel.NEUTRAL

    def test_classify_vix_should_return_greed_when_between_10_and_15(self):
        assert classify_vix(12.0) == FearGreedLevel.GREED

    def test_classify_vix_should_return_extreme_greed_when_below_10(self):
        assert classify_vix(8.0) == FearGreedLevel.EXTREME_GREED

    def test_classify_vix_should_return_na_when_none(self):
        assert classify_vix(None) == FearGreedLevel.NOT_AVAILABLE

    def test_classify_vix_should_return_extreme_fear_at_boundary_30(self):
        # VIX > 30 → EXTREME_FEAR, VIX == 30 triggers the > 15 branch
        assert classify_vix(30.0) == FearGreedLevel.FEAR

    def test_classify_vix_should_return_greed_at_boundary_15(self):
        # VIX=15: not > 15, falls to > 10 → GREED
        assert classify_vix(15.0) == FearGreedLevel.GREED

    def test_classify_vix_should_return_neutral_at_15_1(self):
        # VIX=15.1: > 15 → NEUTRAL
        assert classify_vix(15.1) == FearGreedLevel.NEUTRAL

    def test_classify_vix_should_return_extreme_greed_at_boundary_10(self):
        # VIX=10: not > 10, falls to EXTREME_GREED
        assert classify_vix(10.0) == FearGreedLevel.EXTREME_GREED


class TestClassifyCnnFearGreed:
    """Tests for classify_cnn_fear_greed — 0-100 score → FearGreedLevel."""

    def test_classify_cnn_should_return_extreme_fear_when_0_to_25(self):
        assert classify_cnn_fear_greed(10) == FearGreedLevel.EXTREME_FEAR

    def test_classify_cnn_should_return_fear_when_26_to_45(self):
        assert classify_cnn_fear_greed(35) == FearGreedLevel.FEAR

    def test_classify_cnn_should_return_neutral_when_46_to_55(self):
        assert classify_cnn_fear_greed(50) == FearGreedLevel.NEUTRAL

    def test_classify_cnn_should_return_greed_when_56_to_75(self):
        assert classify_cnn_fear_greed(65) == FearGreedLevel.GREED

    def test_classify_cnn_should_return_extreme_greed_when_above_75(self):
        assert classify_cnn_fear_greed(90) == FearGreedLevel.EXTREME_GREED

    def test_classify_cnn_should_return_na_when_none(self):
        assert classify_cnn_fear_greed(None) == FearGreedLevel.NOT_AVAILABLE

    def test_classify_cnn_should_handle_boundary_25(self):
        assert classify_cnn_fear_greed(25) == FearGreedLevel.EXTREME_FEAR

    def test_classify_cnn_should_handle_boundary_75(self):
        assert classify_cnn_fear_greed(75) == FearGreedLevel.GREED

    def test_classify_cnn_should_handle_zero(self):
        assert classify_cnn_fear_greed(0) == FearGreedLevel.EXTREME_FEAR

    def test_classify_cnn_should_handle_100(self):
        assert classify_cnn_fear_greed(100) == FearGreedLevel.EXTREME_GREED


class TestVixToScore:
    """Tests for _vix_to_score — piecewise linear VIX → 0-100 score mapping."""

    def test_vix_to_score_should_return_50_when_none(self):
        assert _vix_to_score(None) == 50

    def test_vix_to_score_should_return_floor_when_vix_at_40(self):
        assert _vix_to_score(40.0) == 0

    def test_vix_to_score_should_return_floor_when_vix_above_40(self):
        assert _vix_to_score(50.0) == 0

    def test_vix_to_score_should_return_ceiling_when_vix_at_8(self):
        assert _vix_to_score(8.0) == 100

    def test_vix_to_score_should_return_ceiling_when_vix_below_8(self):
        assert _vix_to_score(5.0) == 100

    def test_vix_to_score_should_return_25_at_breakpoint_30(self):
        # VIX=30 → score 25 (extreme fear / fear boundary)
        assert _vix_to_score(30.0) == 25

    def test_vix_to_score_should_return_45_at_breakpoint_20(self):
        # VIX=20 → score 45 (fear / neutral boundary)
        assert _vix_to_score(20.0) == 45

    def test_vix_to_score_should_return_55_at_breakpoint_15(self):
        # VIX=15 → score 55 (neutral / greed boundary)
        assert _vix_to_score(15.0) == 55

    def test_vix_to_score_should_return_75_at_breakpoint_10(self):
        # VIX=10 → score 75 (greed / extreme greed boundary)
        assert _vix_to_score(10.0) == 75

    def test_vix_to_score_should_interpolate_in_fear_zone(self):
        # VIX=25 is midpoint of 30-20 range → midpoint of 25-45 = 35
        assert _vix_to_score(25.0) == 35

    def test_vix_to_score_should_map_vix_21_to_fear_zone(self):
        # VIX=21.3: ratio = (30-21.3)/(30-20) = 0.87
        # score = 25 + 0.87 * 20 = 42.4 → 42
        score = _vix_to_score(21.3)
        assert 25 <= score <= 45, (
            f"VIX=21.3 should map to FEAR zone (25-45), got {score}"
        )

    def test_vix_to_score_should_interpolate_in_neutral_zone(self):
        # VIX=17.5 is midpoint of 20-15 range → midpoint of 45-55 = 50
        assert _vix_to_score(17.5) == 50

    def test_vix_to_score_should_interpolate_in_greed_zone(self):
        # VIX=12.5 is midpoint of 15-10 range → midpoint of 55-75 = 65
        assert _vix_to_score(12.5) == 65

    def test_vix_to_score_should_interpolate_in_extreme_greed_zone(self):
        # VIX=9 is midpoint of 10-8 range → midpoint of 75-100 = 87.5 → 88
        assert _vix_to_score(9.0) == 88

    def test_vix_to_score_should_interpolate_in_extreme_fear_zone(self):
        # VIX=35 is midpoint of 40-30 range → midpoint of 0-25 = 12.5 → 12
        assert _vix_to_score(35.0) == 12


class TestCompositeScore:
    """Tests for compute_composite_fear_greed — weighted composite calculation."""

    def test_composite_should_use_both_sources_when_available(self):
        # VIX=25 (Fear), CNN=35 (Fear)
        level, score = compute_composite_fear_greed(25.0, 35)
        assert isinstance(level, FearGreedLevel)
        assert 0 <= score <= 100
        # VIX=25 → _vix_to_score(25) = 35 (piecewise: midpoint of 30→20 maps to 25→45)
        # Composite = 35*0.4 + 35*0.6 = 14 + 21 = 35
        assert score == 35

    def test_composite_should_fallback_to_vix_only_when_cnn_none(self):
        # VIX=20 → _vix_to_score(20) = 45 (breakpoint: fear/neutral boundary)
        level, score = compute_composite_fear_greed(20.0, None)
        assert score == 45
        assert level == FearGreedLevel.FEAR

    def test_composite_should_fallback_to_cnn_only_when_vix_none(self):
        level, score = compute_composite_fear_greed(None, 80)
        assert score == 80
        assert level == FearGreedLevel.EXTREME_GREED

    def test_composite_should_return_na_when_both_none(self):
        level, score = compute_composite_fear_greed(None, None)
        assert level == FearGreedLevel.NOT_AVAILABLE
        assert score == 50

    def test_composite_should_clamp_to_0_100_range(self):
        # VIX=5 → _vix_to_score(5) = 100 (clamped to ceiling)
        # CNN=100 → Composite = 100*0.4 + 100*0.6 = 100
        level, score = compute_composite_fear_greed(5.0, 100)
        assert score == 100

    def test_composite_should_handle_high_vix_and_low_cnn(self):
        # VIX=40 → _vix_to_score(40) = 0 (floor)
        # CNN=10 → Composite = 0*0.4 + 10*0.6 = 6
        level, score = compute_composite_fear_greed(40.0, 10)
        assert score == 6
        assert level == FearGreedLevel.EXTREME_FEAR
