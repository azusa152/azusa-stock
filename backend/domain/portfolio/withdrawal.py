"""
Domain — 聰明提款機 (Smart Withdrawal / Liquidity Waterfall)。
純函式，無副作用。輸入持倉資料與目標金額，輸出賣出建議。
可獨立單元測試，不依賴框架或 I/O。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.constants import (
    CATEGORY_ICON,
    CATEGORY_LIQUIDITY_ORDER,
    WITHDRAWAL_MIN_SELL_VALUE,
)
from domain.enums import I18nKey

# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HoldingData:
    """持倉快照（已計算好市值，供提款演算法使用）。"""

    ticker: str
    category: str
    quantity: float
    cost_basis: float | None  # 每單位成本（None 表示未知）
    current_price: float | None  # 當前每單位價格（None 表示無法取得）
    market_value: float  # 已換算為 display_currency 的市值
    currency: str
    is_cash: bool
    fx_rate: float = 1.0  # 持倉幣別 → display_currency 的匯率


@dataclass(frozen=True)
class SellRecommendation:
    """單筆賣出建議。"""

    ticker: str
    category: str
    quantity_to_sell: float
    sell_value: float  # 以 display_currency 計算
    # reason_key + reason_vars are the machine-readable i18n contract.
    # The application layer translates them into `reason` before returning to the caller.
    reason_key: I18nKey
    unrealized_pl: float | None  # 未實現損益（None 表示無成本資訊）
    priority: int  # 1=再平衡, 2=節稅, 3=流動性
    # Fields with defaults must come last in a frozen dataclass.
    # reason_vars excluded from __hash__: dict is not hashable and is not part of identity.
    reason_vars: dict = field(default_factory=dict, hash=False, compare=False)
    reason: str = field(
        default=""
    )  # Localised text — set by the application layer via t(reason_key, **reason_vars).


@dataclass
class WithdrawalPlan:
    """提款計劃：包含建議清單、總金額與不足額。"""

    recommendations: list[SellRecommendation] = field(default_factory=list)
    total_sell_value: float = 0.0
    target_amount: float = 0.0
    shortfall: float = 0.0  # > 0 表示持倉不足以覆蓋目標金額
    post_sell_drifts: dict[str, dict] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _unit_price(h: HoldingData) -> float:
    """取得每單位價格（優先用 current_price，否則用 cost_basis）。"""
    if h.current_price is not None and h.current_price > 0:
        return h.current_price
    if h.cost_basis is not None and h.cost_basis > 0:
        return h.cost_basis
    return 0.0


def _calc_unrealized_pl(h: HoldingData, qty_to_sell: float) -> float | None:
    """計算指定賣出數量的未實現損益。"""
    if h.cost_basis is None or h.current_price is None:
        return None
    return round((h.current_price - h.cost_basis) * qty_to_sell * h.fx_rate, 2)


def _qty_for_value(h: HoldingData, target_value: float) -> float:
    """計算要賣出多少數量才能達到 target_value（以 display_currency）。"""
    price = _unit_price(h)
    if price <= 0 or h.fx_rate <= 0:
        return 0.0
    return target_value / (price * h.fx_rate)


def _sell_from_holding(
    h: HoldingData,
    remaining: float,
    reason_key: I18nKey,
    reason_vars: dict,
    priority: int,
    already_sold: dict[str, float],
) -> SellRecommendation | None:
    """
    從單一持倉中產生賣出建議，最多賣到 remaining 金額。
    回傳 None 如果此持倉已無可賣或金額過小。
    """
    available_qty = h.quantity - already_sold.get(h.ticker, 0.0)
    if available_qty <= 0:
        return None

    price = _unit_price(h)
    if price <= 0:
        return None

    available_value = available_qty * price * h.fx_rate
    sell_value = min(available_value, remaining)

    if sell_value < WITHDRAWAL_MIN_SELL_VALUE:
        return None

    qty_to_sell = min(_qty_for_value(h, sell_value), available_qty)
    if qty_to_sell <= 0:
        return None

    actual_sell_value = round(qty_to_sell * price * h.fx_rate, 2)
    unrealized_pl = _calc_unrealized_pl(h, qty_to_sell)

    return SellRecommendation(
        ticker=h.ticker,
        category=h.category,
        quantity_to_sell=round(qty_to_sell, 4),
        sell_value=actual_sell_value,
        reason_key=reason_key,
        unrealized_pl=unrealized_pl,
        priority=priority,
        reason_vars=reason_vars,
    )


def _compute_post_sell_drifts(
    category_values: dict[str, float],
    sell_by_category: dict[str, float],
    target_config: dict[str, float],
) -> dict[str, dict]:
    """計算賣出後的預估配置偏移。"""
    post_values = {
        cat: max(0.0, val - sell_by_category.get(cat, 0.0))
        for cat, val in category_values.items()
    }
    # 加入可能只在 target_config 中的分類
    for cat in target_config:
        if cat not in post_values:
            post_values[cat] = 0.0

    post_total = sum(post_values.values())
    result: dict[str, dict] = {}

    all_cats = sorted(set(list(target_config.keys()) + list(post_values.keys())))
    for cat in all_cats:
        target_pct = target_config.get(cat, 0.0)
        mv = post_values.get(cat, 0.0)
        current_pct = round((mv / post_total) * 100, 2) if post_total > 0 else 0.0
        drift = round(current_pct - target_pct, 2)
        result[cat] = {
            "target_pct": target_pct,
            "current_pct": current_pct,
            "drift_pct": drift,
            "market_value": round(mv, 2),
        }

    return result


# ---------------------------------------------------------------------------
# Main Algorithm — Liquidity Waterfall
# ---------------------------------------------------------------------------


def plan_withdrawal(
    target_amount: float,
    holdings_data: list[HoldingData],
    category_drifts: dict[str, float],
    total_portfolio_value: float,
    target_config: dict[str, float],
) -> WithdrawalPlan:
    """
    聰明提款演算法 (Liquidity Waterfall)。

    依三層優先順序產生賣出建議，直到達成目標金額：
      1. 再平衡 — 賣出超配分類的資產（順便獲利了結）
      2. 節稅   — 賣出帳面虧損的持倉（Tax-Loss Harvesting）
      3. 流動性 — 按 Cash → Bond → Growth → Moat → Trend Setter 順序賣出

    所有輸入皆已換算為同一 display_currency，本函式為純函式。

    Args:
        target_amount: 目標提款金額（display_currency）
        holdings_data: 各持倉快照（含市值、成本、價格）
        category_drifts: 各分類的偏移百分點 {category: drift_pct}
        total_portfolio_value: 投資組合總市值
        target_config: 目標配置百分比 {category: pct}

    Returns:
        WithdrawalPlan 包含建議清單、總金額、不足額、賣後配置偏移
    """
    if target_amount <= 0 or not holdings_data:
        return WithdrawalPlan(
            target_amount=target_amount,
            shortfall=max(0.0, target_amount),
        )

    recommendations: list[SellRecommendation] = []
    remaining = target_amount
    already_sold: dict[str, float] = {}  # ticker -> qty already allocated to sell

    # 建立分類→市值快查表（供 post-sell drift 計算）
    category_values: dict[str, float] = {}
    for h in holdings_data:
        category_values[h.category] = (
            category_values.get(h.category, 0.0) + h.market_value
        )
    sell_by_category: dict[str, float] = {}

    # === Priority 1: 再平衡 — 賣出超配分類 ===
    overweight_cats = sorted(
        [(cat, drift) for cat, drift in category_drifts.items() if drift > 0],
        key=lambda x: -x[1],  # 最超配的先賣
    )

    for cat, drift_pct in overweight_cats:
        if remaining <= 0:
            break

        # 此分類超配的金額上限 = drift% * total_value / 100
        max_rebalance_value = (drift_pct / 100.0) * total_portfolio_value
        sellable_value = min(max_rebalance_value, remaining)

        # 找出此分類的持倉，按市值降序
        cat_holdings = sorted(
            [h for h in holdings_data if h.category == cat],
            key=lambda h: -h.market_value,
        )

        for h in cat_holdings:
            if remaining <= 0 or sellable_value <= 0:
                break

            icon = CATEGORY_ICON.get(cat, "📊")
            rec = _sell_from_holding(
                h,
                min(remaining, sellable_value),
                reason_key=I18nKey("withdrawal.rebalance_reason"),
                reason_vars={
                    "icon": icon,
                    "category": cat,
                    "drift": f"{drift_pct:+.1f}",
                },
                priority=1,
                already_sold=already_sold,
            )
            if rec:
                recommendations.append(rec)
                already_sold[h.ticker] = (
                    already_sold.get(h.ticker, 0.0) + rec.quantity_to_sell
                )
                remaining -= rec.sell_value
                sellable_value -= rec.sell_value
                sell_by_category[cat] = sell_by_category.get(cat, 0.0) + rec.sell_value

    # === Priority 2: 節稅 — 賣出帳面虧損持倉 (Tax-Loss Harvesting) ===
    if remaining > 0:
        loss_holdings = []
        for h in holdings_data:
            avail = h.quantity - already_sold.get(h.ticker, 0.0)
            if avail <= 0:
                continue
            if (
                h.cost_basis is not None
                and h.current_price is not None
                and h.current_price < h.cost_basis
            ):
                total_loss = (h.cost_basis - h.current_price) * avail * h.fx_rate
                loss_holdings.append((h, total_loss))

        # 按虧損金額降序（最大虧損先賣）
        loss_holdings.sort(key=lambda x: -x[1])

        for h, _loss in loss_holdings:
            if remaining <= 0:
                break

            rec = _sell_from_holding(
                h,
                remaining,
                reason_key=I18nKey("withdrawal.tax_reason"),
                reason_vars={},
                priority=2,
                already_sold=already_sold,
            )
            if rec:
                recommendations.append(rec)
                already_sold[h.ticker] = (
                    already_sold.get(h.ticker, 0.0) + rec.quantity_to_sell
                )
                remaining -= rec.sell_value
                sell_by_category[h.category] = (
                    sell_by_category.get(h.category, 0.0) + rec.sell_value
                )

    # === Priority 3: 流動性 — 按類別流動性順序賣出 ===
    if remaining > 0:
        liquidity_rank = {cat: i for i, cat in enumerate(CATEGORY_LIQUIDITY_ORDER)}

        remaining_holdings = []
        for h in holdings_data:
            avail = h.quantity - already_sold.get(h.ticker, 0.0)
            if avail > 0:
                remaining_holdings.append(h)

        # 按流動性排序（Cash 最先），同類別則按市值降序
        remaining_holdings.sort(
            key=lambda h: (liquidity_rank.get(h.category, 999), -h.market_value),
        )

        for h in remaining_holdings:
            if remaining <= 0:
                break

            cat = h.category
            rank = liquidity_rank.get(cat, 999)
            icon = CATEGORY_ICON.get(cat, "📊")
            if rank <= 1:  # Cash, Bond
                reason_key = I18nKey("withdrawal.liquidity_high_reason")
            else:
                reason_key = I18nKey("withdrawal.liquidity_default_reason")

            rec = _sell_from_holding(
                h,
                remaining,
                reason_key=reason_key,
                reason_vars={"icon": icon, "category": cat},
                priority=3,
                already_sold=already_sold,
            )
            if rec:
                recommendations.append(rec)
                already_sold[h.ticker] = (
                    already_sold.get(h.ticker, 0.0) + rec.quantity_to_sell
                )
                remaining -= rec.sell_value
                sell_by_category[h.category] = (
                    sell_by_category.get(h.category, 0.0) + rec.sell_value
                )

    # === 彙總結果 ===
    total_sell = sum(r.sell_value for r in recommendations)
    shortfall = max(0.0, target_amount - total_sell)
    post_sell = _compute_post_sell_drifts(
        category_values, sell_by_category, target_config
    )

    return WithdrawalPlan(
        recommendations=recommendations,
        total_sell_value=round(total_sell, 2),
        target_amount=target_amount,
        shortfall=round(shortfall, 2),
        post_sell_drifts=post_sell,
    )
