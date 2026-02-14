"""
Domain — 壓力測試純計算函式。
負責組合 Beta 加權、損失估算、痛苦等級分類、建議生成。
所有函式均為純函式（無副作用），便於單元測試與複用。
"""

from domain.constants import STRESS_DISCLAIMER, STRESS_PAIN_LEVELS


def calculate_portfolio_beta(holdings_with_beta: list[dict]) -> float:
    """
    計算組合加權 Beta：Sum(weight_i × beta_i)。

    Args:
        holdings_with_beta: 持倉清單，每筆須含 weight_pct 與 beta。
            [{"weight_pct": 25.0, "beta": 1.8}, ...]

    Returns:
        組合加權 Beta（四捨五入至小數點後 2 位）。
        空組合回傳 0.0。
    """
    if not holdings_with_beta:
        return 0.0

    weighted_beta = sum(h["weight_pct"] * h["beta"] / 100.0 for h in holdings_with_beta)
    return round(weighted_beta, 2)


def calculate_stress_test(
    holdings_with_beta: list[dict], scenario_drop_pct: float
) -> dict:
    """
    壓力測試計算：基於線性 CAPM 模型估算崩盤損失。

    公式：
    - 預期跌幅 % = 市場跌幅 % × 股票 Beta
    - 預期損失金額 = 市值 × 預期跌幅 % / 100

    Args:
        holdings_with_beta: 持倉清單，每筆須含：
            - ticker: str
            - category: str (optional, for breakdown)
            - market_value: float
            - beta: float
            - weight_pct: float
        scenario_drop_pct: 市場崩盤情境 %（負數，如 -20.0 表示大盤跌 20%）

    Returns:
        dict 含：
            - portfolio_beta: float
            - scenario_drop_pct: float
            - total_value: float
            - total_loss: float（負數）
            - total_loss_pct: float（負數）
            - pain_level: dict (level, label, emoji)
            - advice: list[str]
            - disclaimer: str
            - holdings_breakdown: list[dict]
    """
    if not holdings_with_beta:
        return {
            "portfolio_beta": 0.0,
            "scenario_drop_pct": scenario_drop_pct,
            "total_value": 0.0,
            "total_loss": 0.0,
            "total_loss_pct": 0.0,
            "pain_level": {"level": "low", "label": "無持倉", "emoji": "green"},
            "advice": [],
            "disclaimer": STRESS_DISCLAIMER,
            "holdings_breakdown": [],
        }

    # 計算組合 Beta
    portfolio_beta = calculate_portfolio_beta(holdings_with_beta)

    # 逐筆計算預期損失
    holdings_breakdown = []

    for holding in holdings_with_beta:
        beta = holding["beta"]
        market_value = holding["market_value"]

        # 預期跌幅 = 情境跌幅 × Beta
        expected_drop_pct = scenario_drop_pct * beta

        # 預期損失 = 市值 × 預期跌幅 / 100
        expected_loss = market_value * expected_drop_pct / 100.0

        holdings_breakdown.append(
            {
                "ticker": holding["ticker"],
                "category": holding.get("category", "Unknown"),
                "beta": round(beta, 2),
                "market_value": round(market_value, 2),
                "expected_drop_pct": round(expected_drop_pct, 2),
                "expected_loss": round(expected_loss, 2),
            }
        )

    # 計算總市值與總損失（從已四捨五入的 breakdown 值彙總，確保一致性）
    total_value = sum(h["market_value"] for h in holdings_breakdown)
    total_loss = sum(h["expected_loss"] for h in holdings_breakdown)

    # 組合層級損失百分比
    total_loss_pct = (total_loss / total_value * 100.0) if total_value > 0 else 0.0

    # 痛苦等級分類（取絕對值）
    pain_level = classify_pain_level(abs(total_loss_pct))

    # 生成建議（僅 panic 等級）
    advice = generate_advice(pain_level["level"], portfolio_beta)

    return {
        "portfolio_beta": portfolio_beta,
        "scenario_drop_pct": round(scenario_drop_pct, 2),
        "total_value": round(total_value, 2),
        "total_loss": round(total_loss, 2),
        "total_loss_pct": round(total_loss_pct, 2),
        "pain_level": pain_level,
        "advice": advice,
        "disclaimer": STRESS_DISCLAIMER,
        "holdings_breakdown": holdings_breakdown,
    }


def classify_pain_level(loss_pct: float) -> dict:
    """
    根據絕對損失 % 分類痛苦等級。

    門檻遞增匹配邏輯：
    - loss_pct < 10%  → low
    - 10% <= loss_pct < 20% → moderate
    - 20% <= loss_pct < 30% → high
    - loss_pct >= 30% → panic

    Args:
        loss_pct: 組合損失百分比（絕對值，如 25.5）

    Returns:
        dict 含 level, label, emoji
    """
    # 從低到高掃描，最後一個滿足 loss_pct >= threshold 的為答案
    matched_level = STRESS_PAIN_LEVELS[0]  # default: low

    for pain_config in STRESS_PAIN_LEVELS:
        if loss_pct >= pain_config["threshold"]:
            matched_level = pain_config
        # 繼續掃描，找最高滿足條件的等級

    return {
        "level": matched_level["level"],
        "label": matched_level["label"],
        "emoji": matched_level["emoji"],
    }


def generate_advice(pain_level: str, portfolio_beta: float) -> list[str]:
    """
    根據痛苦等級與組合 Beta 生成建議（繁體中文，Gooaye 風格）。

    僅在 panic 等級（損失 >= 30%）時提供建議。

    Args:
        pain_level: 痛苦等級 (low / moderate / high / panic)
        portfolio_beta: 組合加權 Beta

    Returns:
        建議清單（Traditional Chinese）
    """
    if pain_level != "panic":
        return []

    advice = [
        "🔴 組合在極端崩盤下將蒸發 30% 以上，已進入「睡不著覺」區間。",
        "💡 建議立即檢視以下事項：",
    ]

    # 根據 Beta 給出具體建議
    if portfolio_beta >= 1.5:
        advice.append(
            "   • 組合 Beta >= 1.5，高度激進。考慮增持低波動資產（債券、現金）以降低風險暴露。"
        )
    elif portfolio_beta >= 1.2:
        advice.append(
            "   • 組合 Beta >= 1.2，偏激進。建議部分獲利了結高 Beta 標的，鎖定帳面利潤。"
        )
    else:
        advice.append("   • 組合 Beta < 1.2，但仍需關注個股集中度風險。")

    advice.extend(
        [
            "   • 確認緊急備用金充足（至少 6 個月生活費）。",
            "   • 若使用槓桿或融資，務必預留安全邊際以防強制平倉。",
            "   • 檢視持倉中是否有「Thesis Broken」訊號，優先減碼基本面惡化的標的。",
            "⚠️ 壓力測試僅為情境推演，實際市場可能更極端。投資前請三思。",
        ]
    )

    return advice
