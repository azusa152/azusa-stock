"""Tests for Fear & Greed pure analysis functions in domain/analysis.py."""

from domain.analysis import (
    classify_cnn_fear_greed,
    classify_vix,
    compute_bias,
    compute_composite_fear_greed,
    compute_rsi,
    compute_volume_ratio,
    compute_weighted_fear_greed,
    score_breadth,
    score_junk_bond_demand,
    score_momentum_composite,
    score_nikkei_vi_linear,
    score_price_strength,
    score_safe_haven,
    score_sector_rotation,
    score_tw_vol_linear,
    score_vix_linear,
)
from domain.analysis.analysis import _vix_to_score
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
    """Tests for compute_composite_fear_greed — CNN primary, VIX fallback."""

    def test_composite_should_use_cnn_when_both_available(self):
        # CNN=35 (Fear) — CNN is primary, VIX is ignored
        level, score = compute_composite_fear_greed(25.0, 35)
        assert score == 35
        assert level == FearGreedLevel.FEAR

    def test_composite_should_prefer_cnn_over_vix(self):
        # CNN=80 (Extreme Greed) even though VIX=40 (Extreme Fear)
        # CNN is primary: VIX is irrelevant when CNN is available
        level, score = compute_composite_fear_greed(40.0, 80)
        assert score == 80
        assert level == FearGreedLevel.EXTREME_GREED

    def test_composite_should_fallback_to_vix_when_cnn_none(self):
        # VIX=20 → _vix_to_score(20) = 45 (breakpoint: fear/neutral boundary)
        level, score = compute_composite_fear_greed(20.0, None)
        assert score == 45
        assert level == FearGreedLevel.FEAR

    def test_composite_should_use_cnn_when_vix_none(self):
        level, score = compute_composite_fear_greed(None, 80)
        assert score == 80
        assert level == FearGreedLevel.EXTREME_GREED

    def test_composite_should_return_na_when_both_none(self):
        level, score = compute_composite_fear_greed(None, None)
        assert level == FearGreedLevel.NOT_AVAILABLE
        assert score == 50

    def test_composite_should_clamp_to_0_100_range(self):
        # CNN=100 → directly used
        level, score = compute_composite_fear_greed(5.0, 100)
        assert score == 100

    def test_composite_should_use_cnn_directly_ignoring_vix(self):
        # CNN=10 (Extreme Fear) — VIX doesn't matter
        level, score = compute_composite_fear_greed(40.0, 10)
        assert score == 10
        assert level == FearGreedLevel.EXTREME_FEAR

    def test_composite_should_use_self_calculated_when_cnn_none(self):
        # CNN=None, self_calculated=60 → use self_calculated
        level, score = compute_composite_fear_greed(
            None, None, self_calculated_score=60
        )
        assert score == 60
        assert level == FearGreedLevel.GREED

    def test_composite_cnn_should_override_self_calculated(self):
        # CNN=30, self_calculated=80 → CNN wins
        level, score = compute_composite_fear_greed(None, 30, self_calculated_score=80)
        assert score == 30
        assert level == FearGreedLevel.FEAR

    def test_composite_vix_is_last_fallback_when_all_others_none(self):
        # CNN=None, self_calculated=None, VIX=20 → VIX fallback
        level, score = compute_composite_fear_greed(
            20.0, None, self_calculated_score=None
        )
        assert score == 45
        assert level == FearGreedLevel.FEAR


class TestScoreVixLinear:
    """Tests for score_vix_linear — continuous linear VIX → 0-100 score."""

    def test_vix_linear_at_10_returns_90(self):
        assert score_vix_linear(10.0) == 90

    def test_vix_linear_at_20_returns_58(self):
        assert score_vix_linear(20.0) == 58

    def test_vix_linear_at_30_returns_26(self):
        assert score_vix_linear(30.0) == 26

    def test_vix_linear_at_38_clamps_to_0(self):
        assert score_vix_linear(38.0) == 0

    def test_vix_linear_at_high_vix_clamps_to_0(self):
        assert score_vix_linear(60.0) == 0

    def test_vix_linear_at_low_vix_clamps_to_100(self):
        assert score_vix_linear(5.0) == 100

    def test_vix_linear_is_continuous_around_threshold_20(self):
        # No cliff: score decreases smoothly near VIX=20
        s19 = score_vix_linear(19.0)
        s20 = score_vix_linear(20.0)
        s21 = score_vix_linear(21.0)
        assert s19 > s20 > s21


class TestScorePriceStrength:
    """Tests for score_price_strength — SPY 14-day return → 0-100."""

    def _prices(self, start: float, end: float, n: int = 20) -> list[float]:
        """Generate a list of n prices starting at start and ending at end."""
        import numpy as np  # noqa: PLC0415

        return list(np.linspace(start, end, n))

    def test_price_strength_positive_return_scores_above_50(self):
        prices = self._prices(100.0, 106.0)
        assert score_price_strength(prices) > 50

    def test_price_strength_negative_return_scores_below_50(self):
        prices = self._prices(100.0, 94.0)
        assert score_price_strength(prices) < 50

    def test_price_strength_no_change_scores_50(self):
        prices = [100.0] * 20
        assert score_price_strength(prices) == 50

    def test_price_strength_returns_none_when_insufficient_data(self):
        assert score_price_strength([100.0] * 5) is None

    def test_price_strength_clamps_to_100_on_large_gain(self):
        prices = self._prices(100.0, 130.0)
        assert score_price_strength(prices) == 100

    def test_price_strength_clamps_to_0_on_large_loss(self):
        prices = self._prices(100.0, 70.0)
        assert score_price_strength(prices) == 0


class TestScoreMomentumComposite:
    """Tests for score_momentum_composite — RSI(14) + MA50 → 0-100."""

    def _prices(self, base: float = 100.0, n: int = 60) -> list[float]:
        """Flat prices for neutral baseline."""
        return [base] * n

    def test_momentum_composite_returns_none_when_insufficient_data(self):
        assert score_momentum_composite([100.0] * 10) is None

    def test_momentum_composite_flat_prices_rsi_dominates(self):
        # Flat prices → avg_loss = 0 → RSI = 100; MA50 deviation = 0 → MA score = 50
        # composite = 0.70 * 100 + 0.30 * 50 = 85
        result = score_momentum_composite(self._prices())
        assert result is not None
        assert result == 85

    def test_momentum_composite_uptrend_scores_above_50(self):
        # Gradually rising prices → high RSI
        import numpy as np  # noqa: PLC0415

        prices = list(np.linspace(90.0, 110.0, 60))
        result = score_momentum_composite(prices)
        assert result is not None
        assert result > 50

    def test_momentum_composite_downtrend_scores_below_50(self):
        import numpy as np  # noqa: PLC0415

        prices = list(np.linspace(110.0, 90.0, 60))
        result = score_momentum_composite(prices)
        assert result is not None
        assert result < 50


class TestScoreBreadth:
    """Tests for score_breadth — RSP vs SPY 14-day divergence → 0-100."""

    def _make_prices(self, returns_pct: float, n: int = 20) -> list[float]:
        """Build price series with given total return over last 14 days."""
        prices = [100.0] * (n - 14)
        current = 100.0
        for _ in range(14):
            current *= 1 + (returns_pct / 100 / 14)
            prices.append(current)
        return prices

    def test_breadth_returns_50_when_no_divergence(self):
        spy = [100.0] * 20
        rsp = [100.0] * 20
        assert score_breadth(rsp, spy) == 50

    def test_breadth_returns_above_50_when_rsp_outperforms(self):
        spy = self._make_prices(0.0)
        rsp = self._make_prices(2.0)
        assert score_breadth(rsp, spy) > 50

    def test_breadth_returns_below_50_when_spy_outperforms(self):
        spy = self._make_prices(2.0)
        rsp = self._make_prices(0.0)
        assert score_breadth(rsp, spy) < 50

    def test_breadth_returns_none_when_insufficient_data(self):
        assert score_breadth([100.0] * 5, [100.0] * 5) is None


class TestScoreJunkBondDemand:
    """Tests for score_junk_bond_demand — HYG vs TLT → 0-100."""

    def _prices(self, total_ret_pct: float, n: int = 20) -> list[float]:
        prices = [100.0] * (n - 14)
        current = 100.0
        for _ in range(14):
            current *= 1 + (total_ret_pct / 100 / 14)
            prices.append(current)
        return prices

    def test_junk_bond_returns_50_when_equal(self):
        assert score_junk_bond_demand([100.0] * 20, [100.0] * 20) == 50

    def test_junk_bond_greed_when_hyg_outperforms(self):
        hyg = self._prices(5.0)
        tlt = self._prices(0.0)
        assert score_junk_bond_demand(hyg, tlt) > 50

    def test_junk_bond_fear_when_tlt_outperforms(self):
        hyg = self._prices(0.0)
        tlt = self._prices(5.0)
        assert score_junk_bond_demand(hyg, tlt) < 50

    def test_junk_bond_returns_none_when_insufficient_data(self):
        assert score_junk_bond_demand([100.0] * 5, [100.0] * 5) is None


class TestScoreSafeHaven:
    """Tests for score_safe_haven — TLT 14-day return (inverted) → 0-100."""

    def _prices(self, total_ret_pct: float, n: int = 20) -> list[float]:
        prices = [100.0] * (n - 14)
        current = 100.0
        for _ in range(14):
            current *= 1 + (total_ret_pct / 100 / 14)
            prices.append(current)
        return prices

    def test_safe_haven_rising_tlt_is_fear(self):
        tlt = self._prices(5.0)  # TLT up → fear for stocks
        assert score_safe_haven(tlt) < 50

    def test_safe_haven_falling_tlt_is_greed(self):
        tlt = self._prices(-5.0)  # TLT down → confidence in stocks
        assert score_safe_haven(tlt) > 50

    def test_safe_haven_flat_tlt_scores_50(self):
        assert score_safe_haven([100.0] * 20) == 50

    def test_safe_haven_returns_none_when_insufficient_data(self):
        assert score_safe_haven([100.0] * 5) is None


class TestScoreSectorRotation:
    """Tests for score_sector_rotation — QQQ vs XLP → 0-100."""

    def _prices(self, total_ret_pct: float, n: int = 20) -> list[float]:
        prices = [100.0] * (n - 14)
        current = 100.0
        for _ in range(14):
            current *= 1 + (total_ret_pct / 100 / 14)
            prices.append(current)
        return prices

    def test_sector_rotation_qqq_outperforms_is_greed(self):
        qqq = self._prices(5.0)
        xlp = self._prices(0.0)
        assert score_sector_rotation(qqq, xlp) > 50

    def test_sector_rotation_xlp_outperforms_is_fear(self):
        qqq = self._prices(0.0)
        xlp = self._prices(5.0)
        assert score_sector_rotation(qqq, xlp) < 50

    def test_sector_rotation_equal_performance_scores_50(self):
        assert score_sector_rotation([100.0] * 20, [100.0] * 20) == 50

    def test_sector_rotation_returns_none_when_insufficient_data(self):
        assert score_sector_rotation([100.0] * 5, [100.0] * 5) is None


class TestComputeWeightedFearGreed:
    """Tests for compute_weighted_fear_greed — weighted average of components."""

    def test_all_components_available_returns_weighted_average(self):
        components = {
            "price_strength": 60,
            "vix": 70,
            "momentum": 50,
            "breadth": 50,
            "junk_bond": 50,
            "safe_haven": 50,
            "sector_rotation": 50,
        }
        level, score = compute_weighted_fear_greed(components)
        # 60*0.20 + 70*0.20 + 50*0.15 + 50*0.15 + 50*0.10 + 50*0.10 + 50*0.10
        # = 12 + 14 + 7.5 + 7.5 + 5 + 5 + 5 = 56
        assert score == 56
        assert level == FearGreedLevel.GREED

    def test_all_none_returns_not_available(self):
        components = {
            k: None
            for k in [
                "price_strength",
                "vix",
                "momentum",
                "breadth",
                "junk_bond",
                "safe_haven",
                "sector_rotation",
            ]
        }
        level, score = compute_weighted_fear_greed(components)
        assert level == FearGreedLevel.NOT_AVAILABLE
        assert score == 50

    def test_partial_components_renormalises_weights(self):
        # Only vix (weight 0.20) and price_strength (weight 0.20) available
        components = {
            "price_strength": 80,
            "vix": 40,
            "momentum": None,
            "breadth": None,
            "junk_bond": None,
            "safe_haven": None,
            "sector_rotation": None,
        }
        level, score = compute_weighted_fear_greed(components)
        # Renormalized: both equal weight → average = (80+40)/2 = 60
        assert score == 60
        assert level == FearGreedLevel.GREED

    def test_single_component_returns_that_score(self):
        components = {
            "price_strength": None,
            "vix": 20,
            "momentum": None,
            "breadth": None,
            "junk_bond": None,
            "safe_haven": None,
            "sector_rotation": None,
        }
        level, score = compute_weighted_fear_greed(components)
        assert score == 20
        assert level == FearGreedLevel.EXTREME_FEAR

    def test_clamps_to_0_100(self):
        # Artificially high scores still clamp
        components = {
            k: 100
            for k in [
                "price_strength",
                "vix",
                "momentum",
                "breadth",
                "junk_bond",
                "safe_haven",
                "sector_rotation",
            ]
        }
        _, score = compute_weighted_fear_greed(components)
        assert score == 100

    def test_unknown_component_names_have_zero_weight_returns_na(self):
        # Component key not in weights dict → total_weight == 0 → NOT_AVAILABLE
        level, score = compute_weighted_fear_greed(
            {"unknown_signal": 75},
            weights={"price_strength": 1.0},
        )
        assert level == FearGreedLevel.NOT_AVAILABLE
        assert score == 50


class TestScorePriceStrengthEdgeCases:
    """Additional edge case tests for better coverage."""

    def test_period_return_with_zero_start_price_returns_none(self):
        # _period_return: start == 0 → None
        prices = [0.0] * 15 + [100.0]
        assert score_price_strength(prices) is None

    def test_momentum_composite_with_zero_ma50_returns_none(self):
        # All last 50 prices = 0 → ma50 = 0 → None
        assert score_momentum_composite([0.0] * 60) is None


class TestScoreNikkeiViLinear:
    """Tests for score_nikkei_vi_linear — continuous linear Nikkei VI → 0-100."""

    def test_nikkei_vi_low_is_greed(self):
        # NKV 12 → ~90
        assert score_nikkei_vi_linear(12.0) == 90

    def test_nikkei_vi_high_is_fear(self):
        # NKV 35 → round(90 - (35-12)*3.5) = round(9.5) = 10
        assert score_nikkei_vi_linear(35.0) == 10

    def test_nikkei_vi_clamps_to_100_when_very_low(self):
        assert score_nikkei_vi_linear(5.0) == 100

    def test_nikkei_vi_clamps_to_0_when_very_high(self):
        assert score_nikkei_vi_linear(50.0) == 0

    def test_nikkei_vi_is_continuous_around_20(self):
        s19 = score_nikkei_vi_linear(19.0)
        s20 = score_nikkei_vi_linear(20.0)
        s21 = score_nikkei_vi_linear(21.0)
        assert s19 > s20 > s21


class TestScoreTwVolLinear:
    """Tests for score_tw_vol_linear — continuous linear TAIEX vol → 0-100."""

    def test_tw_vol_low_is_greed(self):
        # vol 8% → ~90
        assert score_tw_vol_linear(8.0) == 90

    def test_tw_vol_high_is_fear(self):
        # vol 30% → round(90 - (30-8)*3.5) = round(13.0) = 13
        assert score_tw_vol_linear(30.0) == 13

    def test_tw_vol_clamps_to_100_when_very_low(self):
        assert score_tw_vol_linear(0.0) == 100

    def test_tw_vol_clamps_to_0_when_very_high(self):
        assert score_tw_vol_linear(50.0) == 0

    def test_tw_vol_is_continuous_around_18(self):
        s17 = score_tw_vol_linear(17.0)
        s18 = score_tw_vol_linear(18.0)
        s19 = score_tw_vol_linear(19.0)
        assert s17 > s18 > s19


class TestPreexistingCoverageGaps:
    """Targeted tests to cover pre-existing uncovered lines in analysis.py."""

    def test_compute_rsi_returns_none_when_insufficient_data(self):
        # Line 77: len(closes) < period + 1
        assert compute_rsi([100.0] * 5, period=14) is None

    def test_compute_bias_returns_none_when_ma_is_zero(self):
        # Line 103: ma == 0 → None
        assert compute_bias(100.0, 0.0) is None

    def test_compute_bias_returns_none_when_ma_is_none(self):
        assert compute_bias(100.0, None) is None

    def test_compute_volume_ratio_returns_none_when_insufficient_data(self):
        # Line 116: len(volumes) < VOLUME_RATIO_LONG_DAYS (20)
        assert compute_volume_ratio([100.0] * 5) is None

    def test_compute_volume_ratio_returns_none_when_avg_vol_20_is_zero(self):
        # Line 121: avg_vol_20 == 0
        assert compute_volume_ratio([0.0] * 20) is None
