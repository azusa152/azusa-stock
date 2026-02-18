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
from i18n import t
from utils import fetch_stress_test, mask_money as _mask_money


def render_stress_test(display_currency: str = "USD") -> None:
    """Render the portfolio stress test simulator.

    Args:
        display_currency: Currency for display (USD, TWD, JPY, etc.)
    """
    st.markdown(t("components.stress.description"))

    # Slider for crash scenario
    scenario_drop_pct = st.slider(
        t("components.stress.slider_label"),
        min_value=STRESS_SLIDER_MIN,
        max_value=STRESS_SLIDER_MAX,
        value=STRESS_SLIDER_DEFAULT,
        step=STRESS_SLIDER_STEP,
        help=t("components.stress.slider_help"),
    )

    # Fetch stress test results
    result = fetch_stress_test(
        scenario_drop_pct=scenario_drop_pct,
        display_currency=display_currency,
    )

    if result is None:
        st.warning(t("components.stress.no_data"))
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
            label=t("components.stress.beta_label"),
            value=f"{portfolio_beta:.2f}",
            help=t("components.stress.beta_help"),
        )

    with col2:
        loss_display = _mask_money(total_loss, "${:,.0f}")
        st.metric(
            label=t("components.stress.loss_label"),
            value=loss_display,
            delta=f"{total_loss_pct:.1f}%",
            delta_color="inverse",  # Red for losses
            help=t("components.stress.loss_help"),
        )

    with col3:
        # Pain level indicator with colored badge
        st.markdown(
            f"""
            <div style="text-align: center; padding: 10px; border-radius: 8px; background-color: {pain_color}15; border: 2px solid {pain_color};">
                <div style="font-size: 0.9em; color: #666; margin-bottom: 4px;">{t("components.stress.pain_label")}</div>
                <div style="font-size: 1.5em; font-weight: bold; color: {pain_color};">{pain_level_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Pain meter - Conditional colored alert
    if pain_level_name == "panic":
        st.error(
            t("components.stress.pain.panic", label=pain_level_label, loss=abs(total_loss_pct))
        )
    elif pain_level_name == "high":
        st.warning(
            t("components.stress.pain.high", label=pain_level_label, loss=abs(total_loss_pct))
        )
    elif pain_level_name == "moderate":
        st.info(
            t("components.stress.pain.moderate", label=pain_level_label, loss=abs(total_loss_pct))
        )
    else:
        st.success(
            t("components.stress.pain.low", label=pain_level_label, loss=abs(total_loss_pct))
        )

    # Holdings breakdown table
    st.markdown(t("components.stress.breakdown_title"))

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
                    t("components.stress.table.ticker"): ticker,
                    t("components.stress.table.category"): category,
                    t("components.stress.table.beta"): f"{beta:.2f}",
                    t("components.stress.table.market_value"): _mask_money(market_value, "${:,.0f}"),
                    t("components.stress.table.expected_drop"): f"{expected_drop_pct:.1f}%",
                    t("components.stress.table.expected_loss"): _mask_money(expected_loss, "${:,.0f}"),
                }
            )

        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(t("components.stress.no_breakdown"))

    # Advice box (only in panic zone)
    if advice:
        st.markdown(t("components.stress.advice_title"))
        with st.container():
            st.info("\n".join(advice))

    # Disclaimer
    st.caption(disclaimer)
