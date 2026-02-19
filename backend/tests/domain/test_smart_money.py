"""Tests for Smart Money pure functions in domain/smart_money.py."""

from domain.constants import GURU_HOLDING_CHANGE_THRESHOLD_PCT
from domain.enums import HoldingAction
from domain.smart_money import (
    classify_holding_change,
    compute_change_pct,
    compute_holding_weight,
    compute_resonance_matches,
)

THRESHOLD = GURU_HOLDING_CHANGE_THRESHOLD_PCT  # 20.0


# ---------------------------------------------------------------------------
# classify_holding_change
# ---------------------------------------------------------------------------


class TestClassifyHoldingChange:
    """Tests for classify_holding_change()."""

    # --- NEW_POSITION ---

    def test_classify_holding_change_should_return_new_position_when_no_previous(self):
        result = classify_holding_change(current_shares=1000.0, previous_shares=None)
        assert result == HoldingAction.NEW_POSITION

    def test_classify_holding_change_should_return_new_position_when_previous_is_zero(
        self,
    ):
        result = classify_holding_change(current_shares=500.0, previous_shares=0.0)
        assert result == HoldingAction.NEW_POSITION

    # --- SOLD_OUT ---

    def test_classify_holding_change_should_return_sold_out_when_current_is_zero(self):
        result = classify_holding_change(current_shares=0.0, previous_shares=1000.0)
        assert result == HoldingAction.SOLD_OUT

    # --- INCREASED ---

    def test_classify_holding_change_should_return_increased_when_change_at_exact_threshold(
        self,
    ):
        # +20% exactly meets threshold
        result = classify_holding_change(
            current_shares=1200.0, previous_shares=1000.0, threshold_pct=20.0
        )
        assert result == HoldingAction.INCREASED

    def test_classify_holding_change_should_return_increased_when_change_above_threshold(
        self,
    ):
        result = classify_holding_change(
            current_shares=1500.0, previous_shares=1000.0, threshold_pct=20.0
        )
        assert result == HoldingAction.INCREASED

    # --- DECREASED ---

    def test_classify_holding_change_should_return_decreased_when_change_at_exact_negative_threshold(
        self,
    ):
        # -20% exactly meets threshold
        result = classify_holding_change(
            current_shares=800.0, previous_shares=1000.0, threshold_pct=20.0
        )
        assert result == HoldingAction.DECREASED

    def test_classify_holding_change_should_return_decreased_when_change_below_negative_threshold(
        self,
    ):
        result = classify_holding_change(
            current_shares=500.0, previous_shares=1000.0, threshold_pct=20.0
        )
        assert result == HoldingAction.DECREASED

    # --- UNCHANGED ---

    def test_classify_holding_change_should_return_unchanged_when_shares_identical(
        self,
    ):
        result = classify_holding_change(current_shares=1000.0, previous_shares=1000.0)
        assert result == HoldingAction.UNCHANGED

    def test_classify_holding_change_should_return_unchanged_when_change_just_below_positive_threshold(
        self,
    ):
        # +19.99% < 20.0 threshold
        result = classify_holding_change(
            current_shares=1199.9, previous_shares=1000.0, threshold_pct=20.0
        )
        assert result == HoldingAction.UNCHANGED

    def test_classify_holding_change_should_return_unchanged_when_change_just_below_negative_threshold(
        self,
    ):
        # -19.99% < 20.0 threshold
        result = classify_holding_change(
            current_shares=800.1, previous_shares=1000.0, threshold_pct=20.0
        )
        assert result == HoldingAction.UNCHANGED

    def test_classify_holding_change_should_return_unchanged_when_previous_none_and_current_zero(
        self,
    ):
        # Edge: no previous holding, no current holding — stays UNCHANGED
        result = classify_holding_change(current_shares=0.0, previous_shares=None)
        assert result == HoldingAction.UNCHANGED

    # --- default threshold via constant ---

    def test_classify_holding_change_should_use_default_threshold_constant(self):
        # Increase just at the default threshold (20%)
        prev = 1000.0
        curr = prev * (1 + THRESHOLD / 100)
        result = classify_holding_change(current_shares=curr, previous_shares=prev)
        assert result == HoldingAction.INCREASED


# ---------------------------------------------------------------------------
# compute_change_pct
# ---------------------------------------------------------------------------


class TestComputeChangePct:
    """Tests for compute_change_pct()."""

    # --- happy path ---

    def test_compute_change_pct_should_return_positive_when_current_greater(self):
        result = compute_change_pct(current=1200.0, previous=1000.0)
        assert result == 20.0

    def test_compute_change_pct_should_return_negative_when_current_less(self):
        result = compute_change_pct(current=800.0, previous=1000.0)
        assert result == -20.0

    def test_compute_change_pct_should_return_zero_when_values_equal(self):
        result = compute_change_pct(current=1000.0, previous=1000.0)
        assert result == 0.0

    def test_compute_change_pct_should_round_to_two_decimal_places(self):
        result = compute_change_pct(current=1001.0, previous=3000.0)
        assert result is not None
        assert result == round(result, 2)

    def test_compute_change_pct_should_return_100_when_doubled(self):
        result = compute_change_pct(current=2000.0, previous=1000.0)
        assert result == 100.0

    def test_compute_change_pct_should_return_negative_100_when_sold_to_zero(self):
        result = compute_change_pct(current=0.0, previous=1000.0)
        assert result == -100.0

    # --- edge: previous is zero ---

    def test_compute_change_pct_should_return_none_when_previous_is_zero(self):
        result = compute_change_pct(current=500.0, previous=0.0)
        assert result is None


# ---------------------------------------------------------------------------
# compute_holding_weight
# ---------------------------------------------------------------------------


class TestComputeHoldingWeight:
    """Tests for compute_holding_weight()."""

    # --- happy path ---

    def test_compute_holding_weight_should_return_50_when_half_of_total(self):
        result = compute_holding_weight(holding_value=500.0, total_value=1000.0)
        assert result == 50.0

    def test_compute_holding_weight_should_return_100_when_all_of_total(self):
        result = compute_holding_weight(holding_value=1000.0, total_value=1000.0)
        assert result == 100.0

    def test_compute_holding_weight_should_return_value_between_0_and_100(self):
        result = compute_holding_weight(holding_value=250.0, total_value=1000.0)
        assert 0.0 <= result <= 100.0

    def test_compute_holding_weight_should_round_to_two_decimal_places(self):
        result = compute_holding_weight(holding_value=1.0, total_value=3.0)
        assert result == round(result, 2)

    # --- edge: total is zero ---

    def test_compute_holding_weight_should_return_zero_when_total_is_zero(self):
        result = compute_holding_weight(holding_value=500.0, total_value=0.0)
        assert result == 0.0

    def test_compute_holding_weight_should_return_zero_when_holding_is_zero(self):
        result = compute_holding_weight(holding_value=0.0, total_value=1000.0)
        assert result == 0.0


# ---------------------------------------------------------------------------
# compute_resonance_matches
# ---------------------------------------------------------------------------


class TestComputeResonanceMatches:
    """Tests for compute_resonance_matches()."""

    # --- happy path ---

    def test_compute_resonance_matches_should_return_intersection(self):
        guru = {"AAPL", "MSFT", "GOOGL"}
        user = {"AAPL", "TSLA", "MSFT"}
        result = compute_resonance_matches(guru, user)
        assert result == {"AAPL", "MSFT"}

    def test_compute_resonance_matches_should_return_empty_when_no_overlap(self):
        guru = {"AAPL", "MSFT"}
        user = {"TSLA", "NVDA"}
        result = compute_resonance_matches(guru, user)
        assert result == set()

    def test_compute_resonance_matches_should_return_all_when_sets_identical(self):
        tickers = {"AAPL", "MSFT", "GOOGL"}
        result = compute_resonance_matches(tickers, tickers.copy())
        assert result == tickers

    # --- edge: empty sets ---

    def test_compute_resonance_matches_should_return_empty_when_guru_empty(self):
        result = compute_resonance_matches(set(), {"AAPL", "MSFT"})
        assert result == set()

    def test_compute_resonance_matches_should_return_empty_when_user_empty(self):
        result = compute_resonance_matches({"AAPL", "MSFT"}, set())
        assert result == set()

    def test_compute_resonance_matches_should_return_empty_when_both_empty(self):
        result = compute_resonance_matches(set(), set())
        assert result == set()

    # --- commutativity ---

    def test_compute_resonance_matches_should_be_commutative(self):
        a = {"AAPL", "MSFT", "GOOGL"}
        b = {"AAPL", "TSLA"}
        assert compute_resonance_matches(a, b) == compute_resonance_matches(b, a)

    # --- single element overlap ---

    def test_compute_resonance_matches_should_return_single_element_set(self):
        result = compute_resonance_matches({"AAPL"}, {"AAPL", "MSFT"})
        assert result == {"AAPL"}
