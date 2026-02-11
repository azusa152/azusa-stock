"""Tests for domain/rebalance.py — pure rebalance calculation logic."""

from domain.rebalance import calculate_rebalance


class TestCalculateRebalanceZeroTotal:
    """Edge case: total value is zero."""

    def test_should_return_empty_when_total_is_zero(self):
        # Act
        result = calculate_rebalance({}, {"Bond": 50, "Growth": 50})

        # Assert
        assert result["total_value"] == 0.0
        assert result["categories"] == {}
        assert any("市值為零" in a for a in result["advice"])

    def test_should_return_empty_when_all_values_zero(self):
        # Arrange
        values = {"Bond": 0.0, "Growth": 0.0}

        # Act
        result = calculate_rebalance(values, {"Bond": 50, "Growth": 50})

        # Assert
        assert result["total_value"] == 0.0


class TestCalculateRebalanceBalanced:
    """Balanced portfolio — no drift advice expected."""

    def test_should_report_no_adjustment_when_perfectly_balanced(self):
        # Arrange
        values = {"Bond": 50000.0, "Growth": 50000.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert
        assert result["total_value"] == 100000.0
        assert result["categories"]["Bond"]["current_pct"] == 50.0
        assert result["categories"]["Bond"]["drift_pct"] == 0.0
        assert any("無需調整" in a for a in result["advice"])


class TestCalculateRebalanceDrift:
    """Portfolio with significant drift — advice expected."""

    def test_should_advise_reduce_when_overweight(self):
        # Arrange — Growth overweight: 80% vs target 50%
        values = {"Bond": 20000.0, "Growth": 80000.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert
        growth = result["categories"]["Growth"]
        assert growth["current_pct"] == 80.0
        assert growth["drift_pct"] == 30.0
        assert any("超配" in a and "Growth" in a for a in result["advice"])

    def test_should_advise_add_when_underweight(self):
        # Arrange — Bond underweight: 20% vs target 50%
        values = {"Bond": 20000.0, "Growth": 80000.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert
        bond = result["categories"]["Bond"]
        assert bond["current_pct"] == 20.0
        assert bond["drift_pct"] == -30.0
        assert any("低配" in a and "Bond" in a for a in result["advice"])

    def test_should_not_advise_when_drift_below_threshold(self):
        # Arrange — drift = 1% which is below default threshold
        values = {"Bond": 49500.0, "Growth": 50500.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert
        assert any("無需調整" in a for a in result["advice"])


class TestCalculateRebalanceCustomThreshold:
    """Custom threshold parameter."""

    def test_should_use_custom_threshold(self):
        # Arrange — 2% drift, threshold set to 1%
        values = {"Bond": 48000.0, "Growth": 52000.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets, threshold=1.0)

        # Assert
        assert any("超配" in a or "低配" in a for a in result["advice"])


class TestCalculateRebalanceMismatchedCategories:
    """Categories in values vs targets don't fully overlap."""

    def test_should_handle_extra_categories_in_values(self):
        # Arrange — Cash exists in values but not in target
        values = {"Bond": 40000.0, "Growth": 40000.0, "Cash": 20000.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert
        assert "Cash" in result["categories"]
        assert result["categories"]["Cash"]["target_pct"] == 0.0
        assert result["total_value"] == 100000.0

    def test_should_handle_extra_categories_in_targets(self):
        # Arrange — Moat has target but no actual value
        values = {"Bond": 50000.0, "Growth": 50000.0}
        targets = {"Bond": 40, "Growth": 40, "Moat": 20}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert
        assert "Moat" in result["categories"]
        assert result["categories"]["Moat"]["current_pct"] == 0.0
        assert result["categories"]["Moat"]["drift_pct"] == -20.0
