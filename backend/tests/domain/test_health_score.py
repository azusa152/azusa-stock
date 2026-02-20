"""Tests for domain/rebalance.py — compute_portfolio_health_score."""

import pytest

from domain.rebalance import compute_portfolio_health_score


def _cats(**kwargs: float) -> dict[str, dict]:
    """Build a categories dict with drift_pct values.  e.g. _cats(Bond=-3, Growth=6)."""
    return {k: {"drift_pct": v} for k, v in kwargs.items()}


def _xray(*weights: float) -> list[dict]:
    """Build an xray list with total_weight_pct values."""
    return [{"total_weight_pct": w} for w in weights]


class TestHealthScorePerfect:
    """Score = 100 when no drift and no X-Ray concentration."""

    def test_empty_categories_and_xray(self):
        score, level = compute_portfolio_health_score({}, [])
        assert score == 100
        assert level == "healthy"

    def test_all_drift_within_threshold(self):
        score, level = compute_portfolio_health_score(_cats(Bond=2.0, Growth=-4.9), [])
        assert score == 100
        assert level == "healthy"


class TestHealthScoreDriftDeductions:
    """Drift-based deductions per category."""

    def test_single_category_drift_5_to_10(self):
        score, _ = compute_portfolio_health_score(_cats(Growth=6.0), [])
        assert score == 92  # 100 - 8

    def test_single_category_drift_10_to_20(self):
        score, _ = compute_portfolio_health_score(_cats(Growth=15.0), [])
        assert score == 85  # 100 - 15

    def test_single_category_drift_above_20(self):
        score, _ = compute_portfolio_health_score(_cats(Growth=25.0), [])
        assert score == 75  # 100 - 25

    def test_cumulative_drift_across_categories(self):
        score, level = compute_portfolio_health_score(
            _cats(Bond=6.0, Growth=-7.0, Moat=8.0), []
        )
        assert score == 76  # 100 - 3*8 = 76
        assert level == "caution"

    def test_five_categories_moderate_drift_produces_caution(self):
        cats = _cats(A=6, B=-6, C=7, D=-8, E=9)
        score, level = compute_portfolio_health_score(cats, [])
        assert score == 60  # 100 - 5*8 = 60
        assert level == "caution"

    def test_negative_drift_treated_as_absolute(self):
        score_pos, _ = compute_portfolio_health_score(_cats(Growth=12.0), [])
        score_neg, _ = compute_portfolio_health_score(_cats(Growth=-12.0), [])
        assert score_pos == score_neg

    def test_boundary_exactly_5_not_penalized(self):
        score, _ = compute_portfolio_health_score(_cats(Growth=5.0), [])
        assert score == 100

    def test_boundary_exactly_10_stays_in_5_to_10_bracket(self):
        score, _ = compute_portfolio_health_score(_cats(Growth=10.0), [])
        assert score == 92  # 100 - 8

    def test_boundary_exactly_20_stays_in_10_to_20_bracket(self):
        score, _ = compute_portfolio_health_score(_cats(Growth=20.0), [])
        assert score == 85  # 100 - 15


class TestHealthScoreXRayDeductions:
    """X-Ray concentration deductions (capped at 20)."""

    def test_single_concentrated_stock(self):
        score, _ = compute_portfolio_health_score({}, _xray(16.0))
        assert score == 90  # 100 - 10

    def test_two_concentrated_stocks_capped(self):
        score, _ = compute_portfolio_health_score({}, _xray(16.0, 20.0))
        assert score == 80  # 100 - min(20, 20)

    def test_three_concentrated_stocks_still_capped_at_20(self):
        score, _ = compute_portfolio_health_score({}, _xray(16.0, 20.0, 18.0))
        assert score == 80  # 100 - 20 (cap)

    def test_xray_below_threshold_no_penalty(self):
        score, _ = compute_portfolio_health_score({}, _xray(14.9, 10.0))
        assert score == 100

    def test_custom_xray_threshold(self):
        score, _ = compute_portfolio_health_score(
            {}, _xray(11.0), xray_warn_threshold=10.0
        )
        assert score == 90  # 100 - 10


class TestHealthScoreLevels:
    """Level classification boundaries."""

    def test_score_80_is_healthy(self):
        _, level = compute_portfolio_health_score({}, _xray(16.0, 20.0))
        assert level == "healthy"

    def test_score_79_is_caution(self):
        # 1 category drift 25% (-25) + 0 xray = 75
        _, level = compute_portfolio_health_score(_cats(Growth=25.0), [])
        assert level == "caution"

    def test_score_60_is_caution(self):
        cats = _cats(A=6, B=6, C=6, D=6, E=6)
        score, level = compute_portfolio_health_score(cats, [])
        assert score == 60
        assert level == "caution"

    def test_score_59_is_alert(self):
        cats = _cats(A=6, B=6, C=6, D=6, E=6)
        score, level = compute_portfolio_health_score(cats, _xray(16.0))
        assert score == 50  # 60 - 10
        assert level == "alert"


class TestHealthScoreFloorAndCeiling:
    """Score is clamped to 0–100."""

    def test_massive_drift_floors_at_zero(self):
        cats = _cats(A=30, B=30, C=30, D=30, E=30)
        score, level = compute_portfolio_health_score(cats, _xray(20, 20, 20))
        assert score == 0
        assert level == "alert"

    @pytest.mark.parametrize("drift", [0.0, -0.0, 4.9])
    def test_no_deductions_caps_at_100(self, drift):
        score, _ = compute_portfolio_health_score(_cats(Growth=drift), [])
        assert score == 100
