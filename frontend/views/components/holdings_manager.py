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
from i18n import t
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
        st.caption(t("components.holdings.no_data"))
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
            "ticker": t("components.holdings.col.ticker"),
            "category": t("components.holdings.col.category"),
            "quantity": t("components.holdings.col.quantity"),
            "cost_basis": t("components.holdings.col.cost_basis"),
            "broker": t("components.holdings.col.broker"),
            "currency": t("components.holdings.col.currency"),
            "account_type": t("components.holdings.col.account_type"),
            "is_cash": t("components.holdings.col.is_cash"),
        },
        use_container_width=True,
        hide_index=True,
    )
    st.caption(t("components.holdings.privacy_hint"))
    return df  # no edits in privacy mode


def _render_editable_table(df: pd.DataFrame) -> pd.DataFrame:
    """Render the interactive data editor."""
    return st.data_editor(
        df,
        column_config={
            "ID": None,  # hidden
            "raw_ticker": None,  # hidden
            "ticker": st.column_config.TextColumn(
                t("components.holdings.col.ticker"), disabled=True
            ),
            "category": st.column_config.SelectboxColumn(
                t("components.holdings.col.category"),
                options=CATEGORY_OPTIONS,
                required=True,
            ),
            "quantity": st.column_config.NumberColumn(
                t("components.holdings.col.quantity"), min_value=0.0, format="%.4f"
            ),
            "cost_basis": st.column_config.NumberColumn(
                t("components.holdings.col.cost_basis"), min_value=0.0, format="%.2f"
            ),
            "broker": st.column_config.TextColumn(t("components.holdings.col.broker")),
            "currency": st.column_config.TextColumn(
                t("components.holdings.col.currency"), disabled=True
            ),
            "account_type": st.column_config.TextColumn(t("components.holdings.col.account_type")),
            "is_cash": st.column_config.CheckboxColumn(
                t("components.holdings.col.is_cash"), disabled=True
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
        t("components.holdings.save_button"),
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
        st.success(t("components.holdings.save_success", count=changed))
    if errors:
        st.error(t("components.holdings.save_error", tickers=", ".join(errors)))
    if changed == 0 and not errors:
        st.info(t("components.holdings.no_changes"))
    if changed > 0:
        invalidate_holding_caches()
        st.rerun()


def _render_delete_section(holdings: list[dict]) -> None:
    """Render the holding delete selector and button."""
    del_cols = st.columns([3, 1])
    _priv = _is_privacy()
    with del_cols[0]:
        del_id = st.selectbox(
            t("components.holdings.delete_label"),
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
        if st.button(t("components.holdings.delete_button"), key="del_holding_btn"):
            result = api_delete(f"/holdings/{del_id}")
            if result:
                st.success(result.get("message", t("components.holdings.delete_success")))
                invalidate_holding_caches()
                st.rerun()
