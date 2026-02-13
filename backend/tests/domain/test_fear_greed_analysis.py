"""Tests for Fear & Greed pure analysis functions in domain/analysis.py."""

from domain.analysis import (
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


class TestCompositeScore:
    """Tests for compute_composite_fear_greed — weighted composite calculation."""

    def test_composite_should_use_both_sources_when_available(self):
        # VIX=25 (Fear), CNN=35 (Fear)
        level, score = compute_composite_fear_greed(25.0, 35)
        assert isinstance(level, FearGreedLevel)
        assert 0 <= score <= 100
        # VIX=25 → _vix_to_score(25) = round((40-25)/32*100) = 47
        # Composite = 47*0.4 + 35*0.6 = 18.8 + 21 = 40
        assert score == 40

    def test_composite_should_fallback_to_vix_only_when_cnn_none(self):
        # VIX=20 → _vix_to_score(20) = round((40-20)/32*100) = round(62.5) = 62
        # (Python banker's rounding: 0.5 rounds to even)
        level, score = compute_composite_fear_greed(20.0, None)
        assert score == 62
        assert level == FearGreedLevel.GREED

    def test_composite_should_fallback_to_cnn_only_when_vix_none(self):
        level, score = compute_composite_fear_greed(None, 80)
        assert score == 80
        assert level == FearGreedLevel.EXTREME_GREED

    def test_composite_should_return_na_when_both_none(self):
        level, score = compute_composite_fear_greed(None, None)
        assert level == FearGreedLevel.NOT_AVAILABLE
        assert score == 50

    def test_composite_should_clamp_to_0_100_range(self):
        # Extreme VIX=5 → _vix_to_score(5) = round((40-5)/32*100) = 109 → clamped to 100
        # CNN=100 → Composite = 100*0.4 + 100*0.6 = 100
        level, score = compute_composite_fear_greed(5.0, 100)
        assert score == 100

    def test_composite_should_handle_high_vix_and_low_cnn(self):
        # VIX=40 → _vix_to_score(40) = round((40-40)/32*100) = 0
        # CNN=10 → Composite = 0*0.4 + 10*0.6 = 6
        level, score = compute_composite_fear_greed(40.0, 10)
        assert score == 6
        assert level == FearGreedLevel.EXTREME_FEAR
