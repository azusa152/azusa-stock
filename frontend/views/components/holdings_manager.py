"""
Folio — Holdings Manager Component (持倉管理).
Reusable component for rendering Step 2: inline holdings editor, save, and delete.
"""

import pandas as pd
import streamlit as st

from config import (
    CATEGORY_OPTIONS,
    PRIVACY_MASK,
)
from utils import (
    api_delete,
    api_put,
    invalidate_holding_caches,
    is_privacy as _is_privacy,
    mask_money as _mask_money,
    mask_qty as _mask_qty,
)


def render_holdings(holdings: list[dict]) -> None:
    """Render Step 2 — Holdings Management (inline editor + save + delete).

    Args:
        holdings: Current holdings list from backend.
    """
    if not holdings:
        st.caption(
            "目前無持倉資料，請透過左側面板新增股票、債券或現金。"
        )
        return

    # Build DataFrame with raw API values for round-trip editing
    rows = []
    for h in holdings:
        is_cash = h.get("is_cash", False)
        rows.append(
            {
                "ID": h["id"],
                "ticker": "" if is_cash else h["ticker"],
                "raw_ticker": h["ticker"],
                "category": h["category"],
                "quantity": float(h["quantity"]),
                "cost_basis": (
                    float(h["cost_basis"])
                    if h.get("cost_basis") is not None
                    else None
                ),
                "broker": h.get("broker") or "",
                "currency": h.get("currency", "USD"),
                "account_type": h.get("account_type") or "",
                "is_cash": is_cash,
            }
        )
    df = pd.DataFrame(rows)

    if _is_privacy():
        edited_df = _render_privacy_table(df)
    else:
        edited_df = _render_editable_table(df)

    # --- Save button ---
    _render_save_button(df, edited_df)

    # --- Delete logic ---
    st.divider()
    _render_delete_section(holdings)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _render_privacy_table(df: pd.DataFrame) -> pd.DataFrame:
    """Render a masked read-only table in privacy mode."""
    masked_df = df.copy()
    masked_df["quantity"] = PRIVACY_MASK
    masked_df["cost_basis"] = PRIVACY_MASK
    st.dataframe(
        masked_df.drop(columns=["ID", "raw_ticker"]),
        column_config={
            "ticker": "代號",
            "category": "分類",
            "quantity": "數量",
            "cost_basis": "平均成本",
            "broker": "銀行/券商",
            "currency": "幣別",
            "account_type": "帳戶類型",
            "is_cash": "現金",
        },
        use_container_width=True,
        hide_index=True,
    )
    st.caption("🔒 隱私模式已開啟，關閉後可編輯持倉。")
    return df  # no edits in privacy mode


def _render_editable_table(df: pd.DataFrame) -> pd.DataFrame:
    """Render the interactive data editor."""
    return st.data_editor(
        df,
        column_config={
            "ID": None,  # hidden
            "raw_ticker": None,  # hidden
            "ticker": st.column_config.TextColumn(
                "代號", disabled=True
            ),
            "category": st.column_config.SelectboxColumn(
                "分類",
                options=CATEGORY_OPTIONS,
                required=True,
            ),
            "quantity": st.column_config.NumberColumn(
                "數量", min_value=0.0, format="%.4f"
            ),
            "cost_basis": st.column_config.NumberColumn(
                "平均成本", min_value=0.0, format="%.2f"
            ),
            "broker": st.column_config.TextColumn("銀行/券商"),
            "currency": st.column_config.TextColumn(
                "幣別", disabled=True
            ),
            "account_type": st.column_config.TextColumn("帳戶類型"),
            "is_cash": st.column_config.CheckboxColumn(
                "現金", disabled=True
            ),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="holdings_editor",
    )


def _render_save_button(
    df: pd.DataFrame, edited_df: pd.DataFrame
) -> None:
    """Render save button and handle diff-based update logic."""
    save_clicked = st.button(
        "💾 儲存變更",
        key="save_holdings_btn",
        disabled=_is_privacy(),
    )

    if not save_clicked:
        return

    changed = 0
    errors: list[str] = []
    for idx in range(len(df)):
        orig = df.iloc[idx]
        edit = edited_df.iloc[idx]
        # Check if any editable field changed
        if (
            orig["category"] != edit["category"]
            or orig["quantity"] != edit["quantity"]
            or orig["cost_basis"] != edit["cost_basis"]
            or (orig["broker"] or "") != (edit["broker"] or "")
            or (orig["account_type"] or "")
            != (edit["account_type"] or "")
        ):
            h_id = int(orig["ID"])
            result = api_put(
                f"/holdings/{h_id}",
                {
                    "ticker": orig["raw_ticker"],
                    "category": edit["category"],
                    "quantity": float(edit["quantity"]),
                    "cost_basis": (
                        float(edit["cost_basis"])
                        if pd.notna(edit["cost_basis"])
                        else None
                    ),
                    "broker": (
                        edit["broker"] if edit["broker"] else None
                    ),
                    "currency": edit.get("currency", "USD"),
                    "account_type": (
                        edit["account_type"]
                        if edit["account_type"]
                        else None
                    ),
                    "is_cash": bool(edit["is_cash"]),
                },
            )
            if result:
                changed += 1
            else:
                errors.append(orig["raw_ticker"])

    if changed > 0:
        st.success(f"✅ 已更新 {changed} 筆持倉")
    if errors:
        st.error(f"❌ 更新失敗：{', '.join(errors)}")
    if changed == 0 and not errors:
        st.info("ℹ️ 沒有偵測到變更")
    if changed > 0:
        invalidate_holding_caches()
        st.rerun()


def _render_delete_section(holdings: list[dict]) -> None:
    """Render the holding delete selector and button."""
    del_cols = st.columns([3, 1])
    _priv = _is_privacy()
    with del_cols[0]:
        del_id = st.selectbox(
            "選擇要刪除的持倉",
            options=[h["id"] for h in holdings],
            format_func=lambda x: next(
                (
                    (
                        h["ticker"]
                        if _priv
                        else f"{h['ticker']} ({h['quantity']})"
                    )
                    for h in holdings
                    if h["id"] == x
                ),
                str(x),
            ),
            key="del_holding_id",
        )
    with del_cols[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ 刪除", key="del_holding_btn"):
            result = api_delete(f"/holdings/{del_id}")
            if result:
                st.success(result.get("message", "✅ 已刪除"))
                invalidate_holding_caches()
                st.rerun()
