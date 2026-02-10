"""
Folio — Streamlit Frontend Entry Point.
Uses st.navigation to switch between the Radar and Asset Allocation pages.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Page Config (must be the first Streamlit command)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Folio — 智能資產配置",
    page_icon="📡",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS — global styles shared across all pages
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
# Navigation — two-page app
# ---------------------------------------------------------------------------

radar_page = st.Page("views/radar.py", title="投資雷達", icon="📡", default=True)
allocation_page = st.Page("views/allocation.py", title="個人資產配置", icon="💼")

pg = st.navigation([radar_page, allocation_page])
pg.run()
