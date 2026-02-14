"""
Folio — Stress Test Component (壓力測試).
Reusable component for rendering portfolio stress test analysis.
"""

import streamlit as st

from config import (
    PAIN_LEVEL_COLORS,
    STRESS_SLIDER_DEFAULT,
    STRESS_SLIDER_MAX,
    STRESS_SLIDER_MIN,
    STRESS_SLIDER_STEP,
)
from utils import fetch_stress_test, mask_money as _mask_money


def render_stress_test(display_currency: str = "USD") -> None:
    """Render the portfolio stress test simulator.

    Args:
        display_currency: Currency for display (USD, TWD, JPY, etc.)
    """
    st.markdown(
        """
        **模擬大盤崩盤情境，檢視你的組合能承受多大衝擊。**

        基於線性 CAPM 模型（β 值）估算各持倉在市場大跌時的預期損失。
        此工具幫助你評估：
        - 組合整體抗跌能力
        - 高 Beta 持倉的風險暴露
        - 現金與債券的緩衝效果
        """
    )

    # Slider for crash scenario
    scenario_drop_pct = st.slider(
        "🌊 大盤崩盤情境 (Market Crash Scenario)",
        min_value=STRESS_SLIDER_MIN,
        max_value=STRESS_SLIDER_MAX,
        value=STRESS_SLIDER_DEFAULT,
        step=STRESS_SLIDER_STEP,
        help="模擬大盤（如 S&P 500）下跌的百分比。例如 -20% 代表大盤跌 20%。",
    )

    # Fetch stress test results
    result = fetch_stress_test(
        scenario_drop_pct=scenario_drop_pct,
        display_currency=display_currency,
    )

    if result is None:
        st.warning("⚠️ 尚未輸入任何持倉，或無法取得壓力測試資料。請先在 Step 2 新增持倉。")
        return

    # Extract data
    portfolio_beta = result.get("portfolio_beta", 0.0)
    total_value = result.get("total_value", 0.0)
    total_loss = result.get("total_loss", 0.0)
    total_loss_pct = result.get("total_loss_pct", 0.0)
    pain_level = result.get("pain_level", {})
    advice = result.get("advice", [])
    disclaimer = result.get("disclaimer", "")
    holdings_breakdown = result.get("holdings_breakdown", [])

    # Pain level info
    pain_level_name = pain_level.get("level", "low")
    pain_level_label = pain_level.get("label", "")
    pain_level_emoji = pain_level.get("emoji", "green")
    pain_color = PAIN_LEVEL_COLORS.get(pain_level_name, "#9CA3AF")

    # Key metrics row (3 columns)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="組合加權 Beta",
            value=f"{portfolio_beta:.2f}",
            help="組合整體 Beta 值。Beta > 1.0 表示比大盤波動更大，Beta < 1.0 表示較穩健。",
        )

    with col2:
        loss_display = _mask_money(total_loss, "${:,.0f}")
        st.metric(
            label="預期蒸發金額",
            value=loss_display,
            delta=f"{total_loss_pct:.1f}%",
            delta_color="inverse",  # Red for losses
            help="在此崩盤情境下，組合預期損失的金額與百分比。",
        )

    with col3:
        # Pain level indicator with colored badge
        st.markdown(
            f"""
            <div style="text-align: center; padding: 10px; border-radius: 8px; background-color: {pain_color}15; border: 2px solid {pain_color};">
                <div style="font-size: 0.9em; color: #666; margin-bottom: 4px;">痛苦等級</div>
                <div style="font-size: 1.5em; font-weight: bold; color: {pain_color};">{pain_level_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Pain meter - Conditional colored alert
    if pain_level_name == "panic":
        st.error(
            f"🚨 **{pain_level_label}** — 組合在此情境下可能蒸發 {abs(total_loss_pct):.1f}%，風險極高！"
        )
    elif pain_level_name == "high":
        st.warning(
            f"⚠️ **{pain_level_label}** — 組合將承受明顯損失 ({abs(total_loss_pct):.1f}%)，需關注風險。"
        )
    elif pain_level_name == "moderate":
        st.info(
            f"📊 **{pain_level_label}** — 組合有一定損失 ({abs(total_loss_pct):.1f}%)，屬於正常修正範圍。"
        )
    else:
        st.success(
            f"✅ **{pain_level_label}** — 組合相當穩健，僅受輕微影響 ({abs(total_loss_pct):.1f}%)。"
        )

    # Holdings breakdown table
    st.markdown("#### 📋 各持倉預期損失明細")

    if holdings_breakdown:
        # Sort by absolute expected loss (largest impact first)
        sorted_breakdown = sorted(
            holdings_breakdown,
            key=lambda h: abs(h.get("expected_loss", 0)),
            reverse=True,
        )

        # Build table data
        table_data = []
        for holding in sorted_breakdown:
            ticker = holding.get("ticker", "")
            category = holding.get("category", "")
            beta = holding.get("beta", 0.0)
            market_value = holding.get("market_value", 0.0)
            expected_drop_pct = holding.get("expected_drop_pct", 0.0)
            expected_loss = holding.get("expected_loss", 0.0)

            table_data.append(
                {
                    "標的": ticker,
                    "分類": category,
                    "Beta": f"{beta:.2f}",
                    "市值": _mask_money(market_value, "${:,.0f}"),
                    "預期跌幅": f"{expected_drop_pct:.1f}%",
                    "預期損失": _mask_money(expected_loss, "${:,.0f}"),
                }
            )

        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("暫無持倉明細資料。")

    # Advice box (only in panic zone)
    if advice:
        st.markdown("#### 💡 建議事項")
        with st.container():
            st.info("\n".join(advice))

    # Disclaimer
    st.caption(disclaimer)
