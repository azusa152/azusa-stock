"""
Domain — 再平衡計算（純函式，無副作用）。
輸入為已計算好的市值與目標配置，輸出偏移分析與建議。
可獨立單元測試，不依賴框架或 I/O。
"""

from domain.constants import CATEGORY_ICON, DRIFT_THRESHOLD_PCT


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
