"""
Domain — 再平衡計算（純函式，無副作用）。
輸入為已計算好的市值與目標配置，輸出偏移分析與建議。
可獨立單元測試，不依賴框架或 I/O。
"""

from domain.constants import (
    CATEGORY_ICON,
    DRIFT_THRESHOLD_PCT,
    XRAY_SINGLE_STOCK_WARN_PCT,
)


def calculate_rebalance(
    category_values: dict[str, float],
    target_config: dict[str, float],
    threshold: float = DRIFT_THRESHOLD_PCT,
) -> dict:
    """
    計算再平衡分析。

    Args:
        category_values: 各分類的實際市值 {"Bond": 50000.0, "Cash": 20000.0, ...}
        target_config: 目標配置百分比 {"Bond": 50, "Cash": 10, ...}
        threshold: 偏移門檻（百分點），超過此值才產生建議

    Returns:
        {
            "total_value": float,
            "categories": {cat: {"target_pct", "current_pct", "drift_pct", "market_value"}},
            "advice": [str, ...],
        }
    """
    total_value = sum(category_values.values())
    if total_value <= 0:
        return {
            "total_value": 0.0,
            "categories": {},
            "advice": ["⚠️ 持倉總市值為零，無法計算配置。"],
        }

    all_categories = sorted(
        set(list(target_config.keys()) + list(category_values.keys()))
    )
    categories_result: dict[str, dict] = {}
    advice: list[str] = []

    for cat in all_categories:
        target_pct = target_config.get(cat, 0.0)
        mv = category_values.get(cat, 0.0)
        current_pct = round((mv / total_value) * 100, 2)
        drift = round(current_pct - target_pct, 2)

        categories_result[cat] = {
            "target_pct": target_pct,
            "current_pct": current_pct,
            "drift_pct": drift,
            "market_value": round(mv, 2),
        }

        if abs(drift) > threshold:
            icon = CATEGORY_ICON.get(cat, "📊")
            if drift > 0:
                advice.append(f"{icon} {cat} 超配 {drift:+.1f}%，考慮減碼。")
            else:
                advice.append(f"{icon} {cat} 低配 {drift:+.1f}%，考慮加碼。")

    if not advice:
        advice.append("✅ 各分類配置均在目標範圍內，無需調整。")

    return {
        "total_value": round(total_value, 2),
        "categories": categories_result,
        "advice": advice,
    }


def compute_portfolio_health_score(
    categories_result: dict[str, dict],
    xray_entries: list[dict],
    xray_warn_threshold: float = XRAY_SINGLE_STOCK_WARN_PCT,
) -> tuple[int, str]:
    """
    計算投資組合健康分數（0–100）及等級。

    扣分規則：
    - 各分類偏移 5–10%：-8 分（每個分類獨立計算，累計扣分）
    - 各分類偏移 10–20%：-15 分
    - 各分類偏移 > 20%：-25 分
    - X-Ray 單一標的超過門檻（預設 15%）：每筆 -10 分（最多扣 20 分）

    注意：每個分類的偏移懲罰會累計。例如 5 個分類均偏移 6% 時，
    總扣分為 -40（5 × -8），最終分數 60（caution 等級）。
    此設計為刻意行為：任何分類偏移均代表配置偏差，應於分數上反映。

    等級：
    - healthy (80–100)：配置均衡
    - caution (60–79)：需要關注
    - alert (0–59)：需要調整

    Args:
        categories_result: calculate_rebalance 回傳的 categories dict
        xray_entries: X-Ray 穿透式分析條目列表
        xray_warn_threshold: X-Ray 單一標的警戒門檻（%）

    Returns:
        (score, level) tuple
    """
    score = 100

    for cat_data in categories_result.values():
        drift = abs(cat_data.get("drift_pct", 0.0))
        if drift > 20:
            score -= 25
        elif drift > 10:
            score -= 15
        elif drift > 5:
            score -= 8

    xray_penalty = sum(
        10
        for entry in xray_entries
        if entry.get("total_weight_pct", 0.0) > xray_warn_threshold
    )
    score -= min(xray_penalty, 20)

    score = max(0, min(100, score))

    if score >= 80:
        level = "healthy"
    elif score >= 60:
        level = "caution"
    else:
        level = "alert"

    return score, level
