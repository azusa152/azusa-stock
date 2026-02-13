"""
Folio — Streamlit Frontend Entry Point.
Uses st.navigation to switch between Dashboard, Radar, and Asset Allocation pages.
"""

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from utils import fetch_preferences

# ---------------------------------------------------------------------------
# Page Config (must be the first Streamlit command)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Folio — 智能資產配置",
    page_icon="📡",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Navigation — MUST be registered before any widgets that may trigger a rerun,
# otherwise Streamlit falls back to legacy pages/ routing
# ---------------------------------------------------------------------------

dashboard_page = st.Page("views/dashboard.py", title="投資組合總覽", icon="📊", default=True, url_path="dashboard")
radar_page = st.Page("views/radar.py", title="投資雷達", icon="📡", url_path="radar")
allocation_page = st.Page("views/allocation.py", title="個人資產配置", icon="💼", url_path="allocation")
fx_watch_page = st.Page("views/fx_watch.py", title="外匯監控", icon="💱", url_path="fx_watch")

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
# Load Persisted Privacy Mode (once per session, then re-hydrate every rerun)
# Safe after navigation setup
# ---------------------------------------------------------------------------

if "_privacy_mode_value" not in st.session_state:
    st.session_state["_privacy_mode_value"] = False
    try:
        prefs = fetch_preferences()
        if prefs and "privacy_mode" in prefs:
            st.session_state["_privacy_mode_value"] = prefs["privacy_mode"]
    except Exception:
        pass  # Backend unreachable — default to False

# Re-hydrate widget key before page renders (survives page switches)
st.session_state["privacy_mode"] = st.session_state["_privacy_mode_value"]

# ---------------------------------------------------------------------------
# Run the selected page
# ---------------------------------------------------------------------------

pg.run()
