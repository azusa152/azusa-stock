"""Tests for domain/rebalance.py — pure rebalance calculation logic."""

from domain.rebalance import calculate_rebalance


def _advice_keys(result: dict) -> list[str]:
    """Extract i18n keys from the structured advice list."""
    return [item["key"] for item in result["advice"]]


def _advice_params(result: dict) -> list[dict]:
    """Extract params dicts from the structured advice list."""
    return [item["params"] for item in result["advice"]]


class TestCalculateRebalanceZeroTotal:
    """Edge case: total value is zero."""

    def test_should_return_empty_when_total_is_zero(self):
        # Act
        result = calculate_rebalance({}, {"Bond": 50, "Growth": 50})

        # Assert
        assert result["total_value"] == 0.0
        assert result["categories"] == {}
        assert "rebalance.advice_zero" in _advice_keys(result)

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
        assert "rebalance.advice_ok" in _advice_keys(result)


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
        keys = _advice_keys(result)
        params = _advice_params(result)
        assert "rebalance.advice_over" in keys
        over_params = next(
            p for k, p in zip(keys, params, strict=True) if k == "rebalance.advice_over"
        )
        assert over_params["category"] == "Growth"
        assert over_params["drift"] == "30.0"

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
        keys = _advice_keys(result)
        params = _advice_params(result)
        assert "rebalance.advice_under" in keys
        under_params = next(
            p
            for k, p in zip(keys, params, strict=True)
            if k == "rebalance.advice_under"
        )
        assert under_params["category"] == "Bond"
        assert under_params["drift"] == "30.0"

    def test_should_not_advise_when_drift_below_threshold(self):
        # Arrange — drift = 1% which is below default threshold
        values = {"Bond": 49500.0, "Growth": 50500.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert
        assert "rebalance.advice_ok" in _advice_keys(result)


class TestCalculateRebalanceCustomThreshold:
    """Custom threshold parameter."""

    def test_should_use_custom_threshold(self):
        # Arrange — 2% drift, threshold set to 1%
        values = {"Bond": 48000.0, "Growth": 52000.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets, threshold=1.0)

        # Assert
        keys = _advice_keys(result)
        assert "rebalance.advice_over" in keys or "rebalance.advice_under" in keys


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


class TestCalculateRebalanceAdviceStructure:
    """Advice items are structured dicts with key and params fields."""

    def test_advice_items_have_key_and_params(self):
        # Arrange
        values = {"Bond": 20000.0, "Growth": 80000.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert — every advice item must be a dict with "key" and "params"
        for item in result["advice"]:
            assert isinstance(item, dict)
            assert "key" in item
            assert "params" in item
            assert isinstance(item["key"], str)
            assert isinstance(item["params"], dict)

    def test_zero_total_advice_has_no_params(self):
        # Arrange / Act
        result = calculate_rebalance({}, {})

        # Assert
        advice = result["advice"]
        assert len(advice) == 1
        assert advice[0]["key"] == "rebalance.advice_zero"
        assert advice[0]["params"] == {}

    def test_ok_advice_has_no_params(self):
        # Arrange
        values = {"Bond": 50000.0, "Growth": 50000.0}
        targets = {"Bond": 50, "Growth": 50}

        # Act
        result = calculate_rebalance(values, targets)

        # Assert
        ok_items = [
            item for item in result["advice"] if item["key"] == "rebalance.advice_ok"
        ]
        assert len(ok_items) == 1
        assert ok_items[0]["params"] == {}
