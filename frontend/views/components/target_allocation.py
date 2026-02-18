"""
Folio — Target Allocation Component (設定目標配置).
Reusable component for rendering Step 1: persona selection and target config editing.
"""

import streamlit as st

from config import (
    CATEGORY_OPTIONS,
    DISPLAY_CURRENCY_OPTIONS,
    get_category_labels,
)
from i18n import t
from utils import (
    api_post,
    api_put,
    invalidate_profile_caches,
)


def render_target(
    templates: list[dict],
    profile: dict | None,
    holdings: list[dict],
) -> None:
    """Render Step 1 — Target Allocation (persona picker + config editor).

    Args:
        templates: Available persona templates from backend.
        profile: Current user profile (or None if not yet configured).
        holdings: Current holdings list (unused here, reserved for future).
    """
    if profile:
        _render_existing_profile(templates, profile)
    else:
        _render_initial_setup(templates)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _render_template_card(
    tmpl: dict,
    *,
    key_prefix: str,
    home_currency: str,
    success_msg: str,
) -> None:
    """Render a single persona template card with a selection button.

    Args:
        tmpl: Template dict from the backend.
        key_prefix: Unique prefix for the button key (e.g. "switch_tmpl", "pick_template").
        home_currency: Currency to attach to the new profile.
        success_msg: Toast message shown after successful selection.
    """
    with st.container(border=True):
        st.markdown(f"**{tmpl['name']}**")
        st.caption(tmpl["description"])
        if tmpl.get("quote"):
            st.markdown(f"*「{tmpl['quote']}」*")

        cfg = tmpl.get("default_config", {})
        non_zero = {k: v for k, v in cfg.items() if v > 0}
        if non_zero:
            parts = [
                f"{get_category_labels().get(k, k).split(' ')[0]} {v}%"
                for k, v in non_zero.items()
            ]
            st.caption(" · ".join(parts))

        if st.button(
            t("components.target.select_template"),
            key=f"{key_prefix}_{tmpl['id']}",
            use_container_width=True,
        ):
            result = api_post(
                "/profiles",
                {
                    "name": tmpl["name"],
                    "source_template_id": tmpl["id"],
                    "config": cfg,
                    "home_currency": home_currency,
                },
            )
            if result:
                st.success(t("components.target.template_applied", name=tmpl['name']))
                invalidate_profile_caches()
                st.rerun()


def _render_existing_profile(
    templates: list[dict], profile: dict
) -> None:
    """Render UI when a profile already exists."""
    prof_cols = st.columns([5, 1])
    with prof_cols[0]:
        home_cur = profile.get("home_currency", "TWD")
        st.success(
            t("components.target.current_profile", name=profile['name'], currency=home_cur)
        )
    with prof_cols[1]:
        switch_clicked = st.button(
            t("components.target.switch_button"), key="switch_persona_btn"
        )

    target = profile.get("config", {})

    target_cols = st.columns(len(CATEGORY_OPTIONS))
    for i, cat in enumerate(CATEGORY_OPTIONS):
        with target_cols[i]:
            label = get_category_labels().get(cat, cat)
            pct = target.get(cat, 0)
            st.metric(label.split(" ")[0], f"{pct}%")

    # -- Switch Persona picker --
    if switch_clicked:
        _render_switch_picker(templates, profile)

    # -- Adjust percentages (toggle) --
    if st.button(t("components.target.adjust_button"), key="toggle_config_editor"):
        st.session_state["show_config_editor"] = not st.session_state.get(
            "show_config_editor", False
        )
    if st.session_state.get("show_config_editor", False):
        _render_config_editor(profile, target)


def _render_switch_picker(
    templates: list[dict], profile: dict
) -> None:
    """Render the persona switch picker."""
    st.markdown(t("components.target.switch_picker_title"))
    if templates:
        home_cur = profile.get("home_currency", "TWD")
        sw_cols = st.columns(3)
        for idx, tmpl in enumerate(templates):
            with sw_cols[idx % 3]:
                _render_template_card(
                    tmpl,
                    key_prefix="switch_tmpl",
                    home_currency=home_cur,
                    success_msg=t("components.target.switched", name=tmpl['name']),
                )
    else:
        st.warning(t("components.target.no_templates"))


def _render_config_editor(profile: dict, target: dict) -> None:
    """Render the target config percentage editor."""
    edit_cols = st.columns(len(CATEGORY_OPTIONS))
    new_config = {}
    for i, cat in enumerate(CATEGORY_OPTIONS):
        with edit_cols[i]:
            label = (
                get_category_labels().get(cat, cat)
                .split("(")[0]
                .strip()
            )
            new_config[cat] = st.number_input(
                label,
                min_value=0.0,
                max_value=100.0,
                value=float(target.get(cat, 0)),
                step=5.0,
                key=f"target_{cat}",
            )

    total_pct = sum(new_config.values())
    if abs(total_pct - 100) > 0.01:
        st.warning(t("components.target.total_warning", total=total_pct))
    else:
        if st.button(t("components.target.save_button"), key="save_profile"):
            result = api_put(
                f"/profiles/{profile['id']}",
                {"config": new_config},
            )
            if result:
                st.success(t("components.target.save_success"))
                invalidate_profile_caches()
                st.rerun()


def _render_initial_setup(templates: list[dict]) -> None:
    """Render UI for first-time profile setup."""
    st.info(t("components.target.initial_hint"))

    init_home_cur = st.selectbox(
        t("components.target.home_currency_label"),
        options=DISPLAY_CURRENCY_OPTIONS,
        index=(
            DISPLAY_CURRENCY_OPTIONS.index("TWD")
            if "TWD" in DISPLAY_CURRENCY_OPTIONS
            else 0
        ),
        key="init_home_currency",
        help=t("components.target.home_currency_help"),
    )

    if templates:
        template_cols = st.columns(3)
        for idx, tmpl in enumerate(templates):
            with template_cols[idx % 3]:
                _render_template_card(
                    tmpl,
                    key_prefix="pick_template",
                    home_currency=init_home_cur,
                    success_msg=t("components.target.template_applied", name=tmpl['name']),
                )
    else:
        st.warning(t("components.target.no_templates_backend"))
