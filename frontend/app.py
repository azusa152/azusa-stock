"""
Folio — Streamlit Frontend Entry Point.
Uses st.navigation to switch between Dashboard, Radar, and Asset Allocation pages.
"""

import requests
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from config import BACKEND_URL, FOLIO_API_KEY
from i18n import t
from utils import fetch_preferences

# ---------------------------------------------------------------------------
# Page Config (must be the first Streamlit command)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Folio",
    page_icon="📡",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Load Persisted Preferences EARLY — language must be set before navigation
# titles are rendered; privacy mode also loaded here to avoid a second fetch.
# ---------------------------------------------------------------------------

if "_prefs_loaded" not in st.session_state:
    st.session_state["_prefs_loaded"] = True
    st.session_state["_privacy_mode_value"] = False
    st.session_state["language"] = "zh-TW"
    try:
        prefs = fetch_preferences()
        if prefs:
            if "privacy_mode" in prefs:
                st.session_state["_privacy_mode_value"] = prefs["privacy_mode"]
            if "language" in prefs:
                st.session_state["language"] = prefs["language"]
    except Exception:
        pass

st.session_state["privacy_mode"] = st.session_state["_privacy_mode_value"]

# ---------------------------------------------------------------------------
# Navigation — MUST be registered before any widgets that may trigger a rerun,
# otherwise Streamlit falls back to legacy pages/ routing
# ---------------------------------------------------------------------------

dashboard_page = st.Page("views/dashboard.py", title=t("nav.dashboard"), icon="📊", default=True, url_path="dashboard")
radar_page = st.Page("views/radar.py", title=t("nav.radar"), icon="📡", url_path="radar")
allocation_page = st.Page("views/allocation.py", title=t("nav.allocation"), icon="💼", url_path="allocation")
fx_watch_page = st.Page("views/fx_watch.py", title=t("nav.fx_watch"), icon="💱", url_path="fx_watch")

pg = st.navigation([dashboard_page, radar_page, allocation_page, fx_watch_page])

# ---------------------------------------------------------------------------
# Custom CSS — global styles shared across all pages (safe after navigation)
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
/* Hide default Streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Tab bar */
.stTabs [data-baseweb="tab-list"] {gap: 2px;}
.stTabs [data-baseweb="tab"] {padding: 8px 16px; border-radius: 6px 6px 0 0;}

/* Metrics — tighter, cleaner */
[data-testid="stMetricValue"] {font-size: 1.15rem;}
[data-testid="stMetricLabel"] {font-size: 0.72rem; opacity: 0.8;}

/* Expander rounded */
div[data-testid="stExpander"] details {border-radius: 8px;}

/* Card container rounded */
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 12px;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Browser Timezone Detection (once per session, safe after navigation)
# ---------------------------------------------------------------------------

if "browser_tz" not in st.session_state:
    try:
        tz = streamlit_js_eval(
            js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone",
            key="browser_tz",
        )
        if tz:
            st.session_state["browser_tz"] = tz
    except Exception:
        pass  # Safari may block JS eval iframe; gracefully fall back to UTC


# ---------------------------------------------------------------------------
# Language Selector (in sidebar, persists across pages)
# ---------------------------------------------------------------------------

_LANGUAGE_OPTIONS = {
    "zh-TW": "🇹🇼 繁體中文",
    "en": "🇺🇸 English",
    "ja": "🇯🇵 日本語",
    "zh-CN": "🇨🇳 简体中文",
}


def _on_language_change():
    """Save language preference to backend when selector changes."""
    new_lang = st.session_state.get("language_selector", "zh-TW")
    st.session_state["language"] = new_lang
    
    # Save to backend
    try:
        response = requests.put(
            f"{BACKEND_URL}/settings/preferences",
            json={
                "language": new_lang,
                "privacy_mode": st.session_state["_privacy_mode_value"],
            },
            headers={"X-API-Key": FOLIO_API_KEY},
            timeout=5,
        )
        if response.status_code == 200:
            pass  # Success, silently update
    except Exception:
        pass  # Fail silently, user will see next time they load


with st.sidebar:
    st.selectbox(
        "🌐 Language",
        options=list(_LANGUAGE_OPTIONS.keys()),
        format_func=lambda x: _LANGUAGE_OPTIONS[x],
        key="language_selector",
        index=list(_LANGUAGE_OPTIONS.keys()).index(
            st.session_state.get("language", "zh-TW")
        ),
        on_change=_on_language_change,
    )

# ---------------------------------------------------------------------------
# Run the selected page
# ---------------------------------------------------------------------------

pg.run()
