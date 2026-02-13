"""
Domain — 聰明提款機 (Smart Withdrawal) 純函式單元測試。
測試 Liquidity Waterfall 三層優先演算法的所有場景。
"""

import pytest

from domain.withdrawal import HoldingData, plan_withdrawal


# ---------------------------------------------------------------------------
# Fixtures — 常用持倉快照
# ---------------------------------------------------------------------------


def _make_holding(
    ticker: str = "NVDA",
    category: str = "Growth",
    quantity: float = 10.0,
    cost_basis: float | None = 100.0,
    current_price: float | None = 120.0,
    currency: str = "USD",
    is_cash: bool = False,
    fx_rate: float = 1.0,
) -> HoldingData:
    """建立測試用 HoldingData。"""
    price = current_price if current_price is not None else (cost_basis or 0.0)
    mv = quantity * price * fx_rate
    return HoldingData(
        ticker=ticker,
        category=category,
        quantity=quantity,
        cost_basis=cost_basis,
        current_price=current_price,
        market_value=mv,
        currency=currency,
        is_cash=is_cash,
        fx_rate=fx_rate,
    )


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestPlanWithdrawalEdgeCases:
    """邊界情境測試。"""

    def test_zero_amount_should_return_empty_plan(self):
        # Arrange
        holdings = [_make_holding()]

        # Act
        plan = plan_withdrawal(0.0, holdings, {}, 1200.0, {"Growth": 100})

        # Assert
        assert plan.recommendations == []
        assert plan.total_sell_value == 0.0
        assert plan.shortfall == 0.0

    def test_negative_amount_should_return_empty_plan(self):
        # Arrange
        holdings = [_make_holding()]

        # Act
        plan = plan_withdrawal(-100.0, holdings, {}, 1200.0, {"Growth": 100})

        # Assert
        assert plan.recommendations == []

    def test_no_holdings_should_return_shortfall(self):
        # Arrange / Act
        plan = plan_withdrawal(1000.0, [], {}, 0.0, {"Growth": 100})

        # Assert
        assert plan.recommendations == []
        assert plan.shortfall == 1000.0

    def test_single_holding_exact_amount_should_sell_all(self):
        # Arrange — 一檔持倉市值剛好等於提款金額
        h = _make_holding(quantity=10.0, current_price=100.0)  # mv=1000
        holdings = [h]

        # Act
        plan = plan_withdrawal(
            1000.0, holdings, {"Growth": 10.0}, 1000.0, {"Growth": 100}
        )

        # Assert
        assert len(plan.recommendations) >= 1
        assert plan.total_sell_value == pytest.approx(1000.0, abs=1.0)
        assert plan.shortfall == pytest.approx(0.0, abs=1.0)


# ---------------------------------------------------------------------------
# Priority 1 — Rebalancing (超配再平衡)
# ---------------------------------------------------------------------------


class TestPriority1Rebalancing:
    """Priority 1: 賣出超配分類資產。"""

    def test_overweight_category_should_sell_first(self):
        # Arrange — Growth 超配 20%，目標只需 500
        h_growth = _make_holding(
            ticker="NVDA", category="Growth", quantity=10, current_price=100
        )  # mv=1000
        h_bond = _make_holding(
            ticker="SGOV", category="Bond", quantity=50, current_price=100
        )  # mv=5000
        holdings = [h_growth, h_bond]
        drifts = {"Growth": 20.0, "Bond": -20.0}  # Growth 超配 20%
        target = {"Growth": 10, "Bond": 90}

        # Act
        plan = plan_withdrawal(500.0, holdings, drifts, 6000.0, target)

        # Assert
        assert len(plan.recommendations) >= 1
        first = plan.recommendations[0]
        assert first.ticker == "NVDA"
        assert first.priority == 1
        assert "超配" in first.reason
        assert plan.shortfall == pytest.approx(0.0, abs=1.0)

    def test_overweight_partial_sell_should_not_exceed_drift_cap(self):
        # Arrange — Growth 超配 5%，總市值 10000 → 最多賣 500 元
        h = _make_holding(
            ticker="NVDA", category="Growth", quantity=100, current_price=100
        )  # mv=10000
        holdings = [h]
        drifts = {"Growth": 5.0}  # 超配 5%
        target = {"Growth": 95}

        # Act — 要提 2000，但超配上限只有 500
        plan = plan_withdrawal(2000.0, holdings, drifts, 10000.0, target)

        # Assert — Priority 1 只賣約 500，剩下走 Priority 3
        p1_recs = [r for r in plan.recommendations if r.priority == 1]
        assert len(p1_recs) == 1
        assert p1_recs[0].sell_value == pytest.approx(500.0, abs=5.0)


# ---------------------------------------------------------------------------
# Priority 2 — Tax-Loss Harvesting (節稅)
# ---------------------------------------------------------------------------


class TestPriority2TaxLossHarvesting:
    """Priority 2: 賣出帳面虧損持倉。"""

    def test_loss_holding_should_be_sold_for_tax_benefit(self):
        # Arrange — 沒有超配，但有虧損持倉
        h_loss = _make_holding(
            ticker="INTC",
            category="Moat",
            quantity=20,
            cost_basis=50.0,
            current_price=30.0,
        )  # mv=600, loss
        h_gain = _make_holding(
            ticker="NVDA",
            category="Growth",
            quantity=10,
            cost_basis=80.0,
            current_price=120.0,
        )  # mv=1200, gain
        holdings = [h_loss, h_gain]
        drifts = {"Moat": 0.0, "Growth": 0.0}  # 沒有超配
        target = {"Moat": 50, "Growth": 50}

        # Act
        plan = plan_withdrawal(500.0, holdings, drifts, 1800.0, target)

        # Assert — 應優先賣 INTC（虧損）
        assert len(plan.recommendations) >= 1
        first = plan.recommendations[0]
        assert first.ticker == "INTC"
        assert first.priority == 2
        assert "Tax-Loss" in first.reason
        assert first.unrealized_pl is not None
        assert first.unrealized_pl < 0  # 確認是虧損

    def test_largest_loss_should_be_sold_first(self):
        # Arrange — 兩檔都虧損，大虧的先賣
        h_big_loss = _make_holding(
            ticker="INTC",
            category="Moat",
            quantity=20,
            cost_basis=100.0,
            current_price=50.0,
        )  # mv=1000
        h_small_loss = _make_holding(
            ticker="F",
            category="Growth",
            quantity=10,
            cost_basis=20.0,
            current_price=15.0,
        )  # mv=150
        holdings = [h_small_loss, h_big_loss]
        drifts = {"Moat": 0.0, "Growth": 0.0}
        target = {"Moat": 50, "Growth": 50}

        # Act
        plan = plan_withdrawal(300.0, holdings, drifts, 1150.0, target)

        # Assert — INTC（大虧）應排在前面
        p2_recs = [r for r in plan.recommendations if r.priority == 2]
        assert len(p2_recs) >= 1
        assert p2_recs[0].ticker == "INTC"


# ---------------------------------------------------------------------------
# Priority 3 — Liquidity Order (流動性)
# ---------------------------------------------------------------------------


class TestPriority3LiquidityOrder:
    """Priority 3: 按流動性順序賣出（Cash → Bond → Growth → Moat → Trend_Setter）。"""

    def test_cash_should_be_sold_before_bond(self):
        # Arrange — 沒有超配也沒有虧損
        h_cash = _make_holding(
            ticker="TWD",
            category="Cash",
            quantity=10000,
            cost_basis=1.0,
            current_price=1.0,
            is_cash=True,
        )
        h_bond = _make_holding(
            ticker="SGOV",
            category="Bond",
            quantity=100,
            cost_basis=100.0,
            current_price=100.0,
        )
        holdings = [h_bond, h_cash]  # 故意倒序
        drifts = {"Cash": 0.0, "Bond": 0.0}
        target = {"Cash": 50, "Bond": 50}

        # Act
        plan = plan_withdrawal(5000.0, holdings, drifts, 20000.0, target)

        # Assert — Cash 應在 Bond 之前
        p3_recs = [r for r in plan.recommendations if r.priority == 3]
        assert len(p3_recs) >= 1
        assert p3_recs[0].category == "Cash"

    def test_trend_setter_should_be_sold_last(self):
        # Arrange
        h_trend = _make_holding(
            ticker="AAPL",
            category="Trend_Setter",
            quantity=5,
            cost_basis=150.0,
            current_price=200.0,
        )  # mv=1000
        h_growth = _make_holding(
            ticker="NVDA",
            category="Growth",
            quantity=5,
            cost_basis=100.0,
            current_price=200.0,
        )  # mv=1000
        holdings = [h_trend, h_growth]
        drifts = {"Trend_Setter": 0.0, "Growth": 0.0}
        target = {"Trend_Setter": 50, "Growth": 50}

        # Act — 只需部分金額
        plan = plan_withdrawal(500.0, holdings, drifts, 2000.0, target)

        # Assert — Growth 排在 Trend_Setter 前面
        p3_recs = [r for r in plan.recommendations if r.priority == 3]
        assert len(p3_recs) >= 1
        assert p3_recs[0].category == "Growth"

    def test_liquidity_reason_text_should_mention_liquidity(self):
        # Arrange
        h_cash = _make_holding(
            ticker="TWD",
            category="Cash",
            quantity=5000,
            cost_basis=1.0,
            current_price=1.0,
            is_cash=True,
        )
        holdings = [h_cash]
        drifts = {"Cash": 0.0}
        target = {"Cash": 100}

        # Act
        plan = plan_withdrawal(1000.0, holdings, drifts, 5000.0, target)

        # Assert
        assert len(plan.recommendations) >= 1
        assert "流動性" in plan.recommendations[0].reason


# ---------------------------------------------------------------------------
# Mixed Priorities (跨優先級)
# ---------------------------------------------------------------------------


class TestMixedPriorities:
    """金額跨越多個優先級的場景。"""

    def test_amount_spanning_all_three_priorities(self):
        # Arrange
        # Priority 1: Growth 超配 10%，總市值 10000 → 可賣 1000
        h_growth = _make_holding(
            ticker="NVDA",
            category="Growth",
            quantity=30,
            cost_basis=80.0,
            current_price=100.0,
        )  # mv=3000
        # Priority 2: Moat 有虧損
        h_loss = _make_holding(
            ticker="INTC",
            category="Moat",
            quantity=10,
            cost_basis=50.0,
            current_price=30.0,
        )  # mv=300
        # Priority 3: Bond 流動性高
        h_bond = _make_holding(
            ticker="SGOV",
            category="Bond",
            quantity=50,
            cost_basis=100.0,
            current_price=100.0,
        )  # mv=5000
        # Trend Setter 應最後賣
        h_trend = _make_holding(
            ticker="AAPL",
            category="Trend_Setter",
            quantity=10,
            cost_basis=150.0,
            current_price=170.0,
        )  # mv=1700

        holdings = [h_growth, h_loss, h_bond, h_trend]
        drifts = {"Growth": 10.0, "Moat": -5.0, "Bond": 0.0, "Trend_Setter": -5.0}
        target = {"Growth": 20, "Moat": 10, "Bond": 50, "Trend_Setter": 20}
        total = 10000.0

        # Act — 需要 2000，超過 P1 上限 (1000)
        plan = plan_withdrawal(2000.0, holdings, drifts, total, target)

        # Assert
        assert plan.total_sell_value == pytest.approx(2000.0, abs=5.0)
        assert plan.shortfall == pytest.approx(0.0, abs=5.0)

        priorities = [r.priority for r in plan.recommendations]
        # P1 應排在最前面
        assert priorities[0] == 1


# ---------------------------------------------------------------------------
# Shortfall (持倉不足)
# ---------------------------------------------------------------------------


class TestShortfall:
    """持倉不足以覆蓋目標金額的場景。"""

    def test_shortfall_when_portfolio_too_small(self):
        # Arrange — 總市值 1000，但要提 5000
        h = _make_holding(
            ticker="NVDA", category="Growth", quantity=10, current_price=100.0
        )  # mv=1000
        holdings = [h]
        drifts = {"Growth": 0.0}
        target = {"Growth": 100}

        # Act
        plan = plan_withdrawal(5000.0, holdings, drifts, 1000.0, target)

        # Assert
        assert plan.shortfall > 0
        assert plan.total_sell_value == pytest.approx(1000.0, abs=5.0)
        assert plan.shortfall == pytest.approx(4000.0, abs=5.0)


# ---------------------------------------------------------------------------
# Post-Sell Drifts (賣後配置偏移)
# ---------------------------------------------------------------------------


class TestPostSellDrifts:
    """驗證賣出後的預估配置偏移計算。"""

    def test_post_sell_drifts_should_be_populated(self):
        # Arrange
        h_growth = _make_holding(
            ticker="NVDA", category="Growth", quantity=10, current_price=100.0
        )  # mv=1000
        h_bond = _make_holding(
            ticker="SGOV", category="Bond", quantity=50, current_price=100.0
        )  # mv=5000
        holdings = [h_growth, h_bond]
        drifts = {"Growth": 10.0, "Bond": -10.0}
        target = {"Growth": 20, "Bond": 80}

        # Act
        plan = plan_withdrawal(500.0, holdings, drifts, 6000.0, target)

        # Assert — post_sell_drifts 應包含 Growth 和 Bond
        assert "Growth" in plan.post_sell_drifts
        assert "Bond" in plan.post_sell_drifts
        # 賣出 Growth 後，Growth drift 應該更接近 0
        assert plan.post_sell_drifts["Growth"]["drift_pct"] < drifts["Growth"]


# ---------------------------------------------------------------------------
# Holdings with missing data
# ---------------------------------------------------------------------------


class TestMissingData:
    """持倉資料不完整的場景。"""

    def test_holding_without_cost_basis_should_still_sell(self):
        # Arrange — 沒有成本資訊
        h = _make_holding(
            ticker="NVDA",
            category="Growth",
            quantity=10,
            cost_basis=None,
            current_price=100.0,
        )
        holdings = [h]
        drifts = {"Growth": 0.0}
        target = {"Growth": 100}

        # Act
        plan = plan_withdrawal(500.0, holdings, drifts, 1000.0, target)

        # Assert
        assert len(plan.recommendations) >= 1
        assert plan.recommendations[0].unrealized_pl is None  # 無法計算損益

    def test_holding_without_price_should_fallback_to_cost_basis(self):
        # Arrange — 沒有即時價格，使用成本
        h = _make_holding(
            ticker="NVDA",
            category="Growth",
            quantity=10,
            cost_basis=100.0,
            current_price=None,
        )
        holdings = [h]
        drifts = {"Growth": 0.0}
        target = {"Growth": 100}

        # Act
        plan = plan_withdrawal(500.0, holdings, drifts, 1000.0, target)

        # Assert
        assert len(plan.recommendations) >= 1
        assert plan.total_sell_value == pytest.approx(500.0, abs=5.0)
