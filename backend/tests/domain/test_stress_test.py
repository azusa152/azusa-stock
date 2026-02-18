"""Tests for stress test domain logic (pure functions)."""

from domain.stress_test import (
    calculate_portfolio_beta,
    calculate_stress_test,
    classify_pain_level,
    generate_advice,
)


# ---------------------------------------------------------------------------
# calculate_portfolio_beta
# ---------------------------------------------------------------------------


class TestCalculatePortfolioBeta:
    """Tests for portfolio beta calculation."""

    def test_should_return_weighted_average_beta(self):
        # Arrange
        holdings = [
            {"weight_pct": 50.0, "beta": 1.0},  # 50% × 1.0 = 0.5
            {"weight_pct": 30.0, "beta": 1.5},  # 30% × 1.5 = 0.45
            {"weight_pct": 20.0, "beta": 0.5},  # 20% × 0.5 = 0.1
        ]

        # Act
        result = calculate_portfolio_beta(holdings)

        # Assert
        assert result == 1.05  # 0.5 + 0.45 + 0.1

    def test_should_return_zero_for_empty_holdings(self):
        # Act
        result = calculate_portfolio_beta([])

        # Assert
        assert result == 0.0

    def test_should_handle_single_holding(self):
        # Arrange
        holdings = [{"weight_pct": 100.0, "beta": 1.8}]

        # Act
        result = calculate_portfolio_beta(holdings)

        # Assert
        assert result == 1.8

    def test_should_handle_all_cash(self):
        # Arrange — Cash beta = 0
        holdings = [
            {"weight_pct": 60.0, "beta": 0.0},
            {"weight_pct": 40.0, "beta": 0.0},
        ]

        # Act
        result = calculate_portfolio_beta(holdings)

        # Assert
        assert result == 0.0

    def test_should_handle_negative_beta(self):
        # Arrange — Inverse ETF
        holdings = [
            {"weight_pct": 70.0, "beta": 1.2},
            {"weight_pct": 30.0, "beta": -0.5},  # Inverse ETF
        ]

        # Act
        result = calculate_portfolio_beta(holdings)

        # Assert
        assert result == 0.69  # 0.7*1.2 + 0.3*(-0.5) = 0.84 - 0.15 = 0.69

    def test_should_round_to_two_decimals(self):
        # Arrange
        holdings = [
            {"weight_pct": 33.33, "beta": 1.111},
            {"weight_pct": 33.33, "beta": 1.222},
            {"weight_pct": 33.34, "beta": 1.333},
        ]

        # Act
        result = calculate_portfolio_beta(holdings)

        # Assert — should be rounded
        assert isinstance(result, float)
        assert len(str(result).split(".")[-1]) <= 2


# ---------------------------------------------------------------------------
# classify_pain_level
# ---------------------------------------------------------------------------


class TestClassifyPainLevel:
    """Tests for pain level classification."""

    def test_loss_below_10_should_be_low(self):
        # Act
        result = classify_pain_level(5.0)

        # Assert
        assert result["level"] == "low"
        assert "微風輕拂" in result["label"]
        assert result["emoji"] == "green"

    def test_loss_10_to_20_should_be_moderate(self):
        # Act
        result = classify_pain_level(15.0)

        # Assert
        assert result["level"] == "moderate"
        assert "有感修正" in result["label"]
        assert result["emoji"] == "yellow"

    def test_loss_20_to_30_should_be_high(self):
        # Act
        result = classify_pain_level(25.0)

        # Assert
        assert result["level"] == "high"
        assert "傷筋動骨" in result["label"]
        assert result["emoji"] == "orange"

    def test_loss_above_30_should_be_panic(self):
        # Act
        result = classify_pain_level(35.0)

        # Assert
        assert result["level"] == "panic"
        assert "睡不著覺" in result["label"]
        assert result["emoji"] == "red"

    def test_boundary_10_should_be_moderate(self):
        # Act
        result = classify_pain_level(10.0)

        # Assert
        assert result["level"] == "moderate"

    def test_boundary_20_should_be_high(self):
        # Act
        result = classify_pain_level(20.0)

        # Assert
        assert result["level"] == "high"

    def test_boundary_30_should_be_panic(self):
        # Act
        result = classify_pain_level(30.0)

        # Assert
        assert result["level"] == "panic"

    def test_zero_loss_should_be_low(self):
        # Act
        result = classify_pain_level(0.0)

        # Assert
        assert result["level"] == "low"

    def test_extreme_loss_should_be_panic(self):
        # Act
        result = classify_pain_level(99.0)

        # Assert
        assert result["level"] == "panic"

    def test_negative_loss_pct_should_be_low(self):
        # Arrange — Negative loss (gain) from inverse/negative-beta holdings
        # Act
        result = classify_pain_level(-5.0)

        # Assert — Should match threshold 0 and return low
        assert result["level"] == "low"
        assert result["emoji"] == "green"


# ---------------------------------------------------------------------------
# generate_advice
# ---------------------------------------------------------------------------


class TestGenerateAdvice:
    """Tests for advice generation (returns i18n keys)."""

    def test_panic_with_high_beta_should_return_aggressive_advice(self):
        # Act
        result = generate_advice("panic", 1.5)

        # Assert
        assert len(result) > 0
        assert "stress_test.panic_intro" in result
        assert "stress_test.advice_beta_high" in result

    def test_panic_with_moderate_beta_should_return_balanced_advice(self):
        # Act
        result = generate_advice("panic", 1.3)

        # Assert
        assert len(result) > 0
        assert "stress_test.advice_beta_moderate" in result

    def test_panic_with_low_beta_should_return_concentration_advice(self):
        # Act
        result = generate_advice("panic", 0.9)

        # Assert
        assert len(result) > 0
        assert "stress_test.advice_beta_low" in result

    def test_low_pain_should_return_empty_advice(self):
        # Act
        result = generate_advice("low", 1.2)

        # Assert
        assert result == []

    def test_moderate_pain_should_return_empty_advice(self):
        # Act
        result = generate_advice("moderate", 1.2)

        # Assert
        assert result == []

    def test_high_pain_should_return_empty_advice(self):
        # Act
        result = generate_advice("high", 1.2)

        # Assert
        assert result == []

    def test_panic_advice_should_include_emergency_fund_check(self):
        # Act
        result = generate_advice("panic", 1.0)

        # Assert
        assert "stress_test.advice_emergency_fund" in result

    def test_panic_advice_should_include_leverage_warning(self):
        # Act
        result = generate_advice("panic", 1.0)

        # Assert
        assert "stress_test.advice_leverage" in result

    def test_panic_advice_should_include_thesis_broken_check(self):
        # Act
        result = generate_advice("panic", 1.0)

        # Assert
        assert "stress_test.advice_thesis_broken" in result


# ---------------------------------------------------------------------------
# calculate_stress_test (integration)
# ---------------------------------------------------------------------------


class TestCalculateStressTest:
    """Tests for the full stress test calculation."""

    def test_should_calculate_simple_portfolio(self):
        # Arrange
        holdings = [
            {
                "ticker": "NVDA",
                "category": "Growth",
                "market_value": 10000.0,
                "beta": 2.0,
                "weight_pct": 100.0,
            }
        ]
        scenario_drop = -10.0

        # Act
        result = calculate_stress_test(holdings, scenario_drop)

        # Assert
        assert result["portfolio_beta"] == 2.0
        assert result["scenario_drop_pct"] == -10.0
        assert result["total_value"] == 10000.0
        assert result["total_loss"] == -2000.0  # 10000 * (-10%) * 2.0
        assert result["total_loss_pct"] == -20.0
        assert result["pain_level"]["level"] == "high"
        assert len(result["holdings_breakdown"]) == 1

    def test_should_calculate_mixed_portfolio(self):
        # Arrange
        holdings = [
            {
                "ticker": "NVDA",
                "category": "Growth",
                "market_value": 50000.0,
                "beta": 1.8,
                "weight_pct": 50.0,
            },
            {
                "ticker": "BRK.B",
                "category": "Moat",
                "market_value": 30000.0,
                "beta": 0.8,
                "weight_pct": 30.0,
            },
            {
                "ticker": "TLT",
                "category": "Bond",
                "market_value": 20000.0,
                "beta": 0.3,
                "weight_pct": 20.0,
            },
        ]
        scenario_drop = -20.0

        # Act
        result = calculate_stress_test(holdings, scenario_drop)

        # Assert
        # Portfolio beta = 50%*1.8 + 30%*0.8 + 20%*0.3 = 0.9 + 0.24 + 0.06 = 1.2
        assert result["portfolio_beta"] == 1.2

        # Total loss:
        # NVDA: 50000 * (-20%) * 1.8 = -18000
        # BRK:  30000 * (-20%) * 0.8 = -4800
        # TLT:  20000 * (-20%) * 0.3 = -1200
        # Total: -24000
        assert result["total_value"] == 100000.0
        assert result["total_loss"] == -24000.0
        assert result["total_loss_pct"] == -24.0
        assert result["pain_level"]["level"] == "high"

        # Check breakdown
        nvda_breakdown = next(
            h for h in result["holdings_breakdown"] if h["ticker"] == "NVDA"
        )
        assert nvda_breakdown["expected_drop_pct"] == -36.0
        assert nvda_breakdown["expected_loss"] == -18000.0

    def test_empty_portfolio_should_return_zero_loss(self):
        # Act
        result = calculate_stress_test([], -20.0)

        # Assert
        assert result["portfolio_beta"] == 0.0
        assert result["total_value"] == 0.0
        assert result["total_loss"] == 0.0
        assert result["total_loss_pct"] == 0.0
        assert result["pain_level"]["level"] == "low"
        assert result["holdings_breakdown"] == []

    def test_all_cash_portfolio_should_have_zero_loss(self):
        # Arrange
        holdings = [
            {
                "ticker": "USD",
                "category": "Cash",
                "market_value": 100000.0,
                "beta": 0.0,
                "weight_pct": 100.0,
            }
        ]
        scenario_drop = -50.0

        # Act
        result = calculate_stress_test(holdings, scenario_drop)

        # Assert
        assert result["portfolio_beta"] == 0.0
        assert result["total_loss"] == 0.0
        assert result["pain_level"]["level"] == "low"

    def test_extreme_drop_scenario(self):
        # Arrange
        holdings = [
            {
                "ticker": "NVDA",
                "category": "Growth",
                "market_value": 10000.0,
                "beta": 2.0,
                "weight_pct": 100.0,
            }
        ]
        scenario_drop = -50.0

        # Act
        result = calculate_stress_test(holdings, scenario_drop)

        # Assert
        assert result["total_loss"] == -10000.0  # 10000 * (-50%) * 2.0 = -10000
        assert result["total_loss_pct"] == -100.0
        assert result["pain_level"]["level"] == "panic"
        assert len(result["advice"]) > 0

    def test_negative_beta_portfolio(self):
        # Arrange — Inverse ETF
        holdings = [
            {
                "ticker": "SH",
                "category": "Growth",
                "market_value": 10000.0,
                "beta": -1.0,
                "weight_pct": 100.0,
            }
        ]
        scenario_drop = -20.0

        # Act
        result = calculate_stress_test(holdings, scenario_drop)

        # Assert
        # Inverse ETF should gain when market drops
        assert result["portfolio_beta"] == -1.0
        assert result["total_loss"] == 2000.0  # 10000 * (-20%) * (-1.0) = +2000 (gain)
        assert result["total_loss_pct"] == 20.0  # gain

    def test_should_include_disclaimer(self):
        # Arrange
        holdings = [
            {
                "ticker": "NVDA",
                "category": "Growth",
                "market_value": 10000.0,
                "beta": 1.5,
                "weight_pct": 100.0,
            }
        ]

        # Act
        result = calculate_stress_test(holdings, -20.0)

        # Assert
        assert "disclaimer" in result
        assert "CAPM" in result["disclaimer"]
        assert "不構成投資建議" in result["disclaimer"]

    def test_should_round_all_monetary_values(self):
        # Arrange
        holdings = [
            {
                "ticker": "TEST",
                "category": "Growth",
                "market_value": 12345.678,
                "beta": 1.234,
                "weight_pct": 100.0,
            }
        ]

        # Act
        result = calculate_stress_test(holdings, -10.5)

        # Assert
        assert result["total_value"] == 12345.68
        # total_loss should be rounded to 2 decimals
        # expected_drop_pct = -10.5 * 1.234 = -12.957 → -12.96
        # expected_loss = 12345.68 * (-12.96) / 100 = -1599.633728 → -1599.63
        assert result["total_loss"] == -1599.63
        assert len(str(abs(result["total_loss"])).split(".")[-1]) <= 2

        # Check breakdown rounding
        breakdown = result["holdings_breakdown"][0]
        assert breakdown["market_value"] == 12345.68
        assert breakdown["expected_drop_pct"] == -12.96  # -10.5 * 1.234 rounded
        assert breakdown["expected_loss"] == -1599.63  # 12345.68 * -12.96 / 100 rounded
        assert len(str(abs(breakdown["expected_loss"])).split(".")[-1]) <= 2

    def test_should_handle_missing_category(self):
        # Arrange — category not provided
        holdings = [
            {
                "ticker": "TEST",
                "market_value": 10000.0,
                "beta": 1.0,
                "weight_pct": 100.0,
            }
        ]

        # Act
        result = calculate_stress_test(holdings, -10.0)

        # Assert
        assert result["holdings_breakdown"][0]["category"] == "Unknown"

    def test_small_drop_should_be_low_pain(self):
        # Arrange
        holdings = [
            {
                "ticker": "BRK.B",
                "category": "Moat",
                "market_value": 100000.0,
                "beta": 0.8,
                "weight_pct": 100.0,
            }
        ]
        scenario_drop = -5.0

        # Act
        result = calculate_stress_test(holdings, scenario_drop)

        # Assert
        assert result["total_loss_pct"] == -4.0  # -5% * 0.8
        assert result["pain_level"]["level"] == "low"
        assert result["advice"] == []


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestStressTestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_market_value_should_not_crash(self):
        # Arrange
        holdings = [
            {
                "ticker": "DUST",
                "category": "Growth",
                "market_value": 0.0,
                "beta": 1.5,
                "weight_pct": 100.0,
            }
        ]

        # Act
        result = calculate_stress_test(holdings, -20.0)

        # Assert
        assert result["total_value"] == 0.0
        assert result["total_loss"] == 0.0

    def test_very_high_beta_should_amplify_loss(self):
        # Arrange — Leveraged ETF
        holdings = [
            {
                "ticker": "TQQQ",
                "category": "Growth",
                "market_value": 10000.0,
                "beta": 3.0,
                "weight_pct": 100.0,
            }
        ]
        scenario_drop = -10.0

        # Act
        result = calculate_stress_test(holdings, scenario_drop)

        # Assert
        assert result["total_loss"] == -3000.0  # 10000 * (-10%) * 3.0
        assert result["total_loss_pct"] == -30.0
        assert result["pain_level"]["level"] == "panic"

    def test_multiple_holdings_with_same_ticker_should_preserve_both_entries(self):
        # Arrange — Same ticker in different accounts (e.g., taxable + IRA)
        # Domain layer does NOT deduplicate; deduplication is service layer's job
        holdings = [
            {
                "ticker": "NVDA",
                "category": "Growth",
                "market_value": 5000.0,
                "beta": 1.8,
                "weight_pct": 50.0,
            },
            {
                "ticker": "NVDA",
                "category": "Growth",
                "market_value": 5000.0,
                "beta": 1.8,
                "weight_pct": 50.0,
            },
        ]

        # Act
        result = calculate_stress_test(holdings, -10.0)

        # Assert
        assert result["total_value"] == 10000.0
        assert len(result["holdings_breakdown"]) == 2  # Both entries preserved
