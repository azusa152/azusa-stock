"""
Folio — Smart Withdrawal Component (聰明提款).
Reusable component for rendering Step 5: withdrawal form, recommendations, and post-sell drifts.
"""

import pandas as pd
import streamlit as st

from config import (
    CATEGORY_ICON_SHORT,
    DISPLAY_CURRENCY_OPTIONS,
    PRIVACY_MASK,
    WITHDRAW_PRIORITY_LABELS,
)
from utils import (
    fetch_withdraw,
    is_privacy as _is_privacy,
    mask_money as _mask_money,
    mask_qty as _mask_qty,
)


def render_withdrawal(
    profile: dict,
    holdings: list[dict],
) -> None:
    """Render Step 5 — Smart Withdrawal.

    Includes withdrawal form, fetch logic, metrics, recommendations table,
    and post-sell drift analysis.

    Args:
        profile: Current user profile (reserved for future use).
        holdings: Current holdings list (reserved for future use).
    """
    with st.form("withdraw_form"):
        w_cols = st.columns([2, 2, 2])
        with w_cols[0]:
            w_amount = st.number_input(
                "提款金額",
                min_value=0.01,
                value=1000.0,
                step=100.0,
                format="%.2f",
            )
        with w_cols[1]:
            w_currency = st.selectbox(
                "幣別",
                options=DISPLAY_CURRENCY_OPTIONS,
                key="withdraw_currency",
            )
        with w_cols[2]:
            st.write("")  # vertical spacer
            w_notify = st.toggle(
                "📡 發送 Telegram 通知",
                value=False,
                key="withdraw_notify",
            )
        w_submit = st.form_submit_button(
            "💰 計算提款建議", type="primary"
        )

    # Fetch on submit; persist result in session_state so it
    # survives Streamlit re-runs (e.g. privacy toggle).
    if w_submit and w_amount > 0:
        _fetch_and_persist(w_amount, w_currency, w_notify)

    # Render persisted result (survives re-runs).
    wd = st.session_state.get("withdraw_result")
    wd_cur = st.session_state.get(
        "withdraw_display_cur", "USD"
    )
    if wd:
        _render_result(wd, wd_cur)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _fetch_and_persist(
    amount: float, currency: str, notify: bool
) -> None:
    """Fetch withdrawal recommendation and persist to session_state."""
    with st.status(
        "💰 計算聰明提款中...", expanded=True
    ) as _wd_status:
        result = fetch_withdraw(amount, currency, notify)
        if result and "error_code" in result:
            # 404: no profile or no holdings
            _wd_status.update(
                label="⚠️ 計算失敗",
                state="error",
                expanded=True,
            )
            st.warning(
                result.get(
                    "detail", "請先完成 Step 1 與 Step 2。"
                )
            )
            st.session_state.pop("withdraw_result", None)
        elif result:
            st.session_state["withdraw_result"] = result
            st.session_state["withdraw_display_cur"] = currency
            _wd_status.update(
                label="✅ 聰明提款建議完成",
                state="complete",
                expanded=False,
            )
        else:
            st.session_state.pop("withdraw_result", None)
            _wd_status.update(
                label="⚠️ 計算失敗",
                state="error",
                expanded=True,
            )
            st.warning(
                "計算提款建議失敗，"
                "請稍後再試或確認網路連線正常。"
            )


def _render_result(wd: dict, wd_cur: str) -> None:
    """Render the persisted withdrawal result."""
    # --- Summary message ---
    msg = wd.get("message", "")
    if msg:
        st.markdown(f"**{msg}**")

    # --- Metrics row ---
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "目標提款",
        _mask_money(
            wd["target_amount"], f"{wd_cur} {{:,.0f}}"
        ),
    )
    m2.metric(
        "可賣出總額",
        _mask_money(
            wd["total_sell_value"], f"{wd_cur} {{:,.0f}}"
        ),
    )
    shortfall = wd.get("shortfall", 0)
    if shortfall > 0:
        m3.metric(
            "缺口",
            _mask_money(shortfall, f"{wd_cur} {{:,.0f}}"),
            delta="不足",
            delta_color="inverse",
        )
        st.warning("投資組合市值不足以完全覆蓋提款需求。")
    else:
        m3.metric(
            "缺口", "0", delta="充足", delta_color="normal"
        )

    _render_recommendations(wd, wd_cur)
    _render_post_sell_drifts(wd)


def _render_recommendations(wd: dict, wd_cur: str) -> None:
    """Render the sell recommendations table."""
    recs = wd.get("recommendations", [])
    if not recs:
        return

    st.markdown("**📋 賣出建議：**")
    rows = []
    for r in recs:
        cat = r["category"]
        icon = CATEGORY_ICON_SHORT.get(cat, "")
        upl = r.get("unrealized_pl")
        rows.append(
            {
                "優先序": WITHDRAW_PRIORITY_LABELS.get(
                    r["priority"], "?"
                ),
                "標的": r["ticker"],
                "類別": f"{icon} {cat}",
                "賣出數量": _mask_qty(r["quantity_to_sell"]),
                "賣出金額": _mask_money(
                    r["sell_value"], f"{wd_cur} {{:,.2f}}"
                ),
                "未實現損益": (
                    _mask_money(
                        upl, f"{wd_cur} {{:+,.2f}}"
                    )
                    if upl is not None
                    else "—"
                ),
                "原因": (
                    PRIVACY_MASK
                    if _is_privacy()
                    else r["reason"]
                ),
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def _render_post_sell_drifts(wd: dict) -> None:
    """Render the post-sell drift analysis table."""
    drifts = wd.get("post_sell_drifts", {})
    if not drifts:
        return

    st.markdown("**📊 賣出後預估配置偏移：**")
    drift_rows = []
    for cat, d in drifts.items():
        icon = CATEGORY_ICON_SHORT.get(cat, "")
        drift_rows.append(
            {
                "類別": f"{icon} {cat}",
                "目標 %": f"{d['target_pct']:.1f}%",
                "預估 %": f"{d['current_pct']:.1f}%",
                "偏移": f"{d['drift_pct']:+.1f}%",
            }
        )
    st.dataframe(
        pd.DataFrame(drift_rows),
        use_container_width=True,
        hide_index=True,
    )
