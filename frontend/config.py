"""
Frontend — 集中管理所有前端常數與設定。
避免散落在 app.py 中的 magic numbers / magic strings。
"""

import os

# ---------------------------------------------------------------------------
# Backend Connection
# ---------------------------------------------------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# ---------------------------------------------------------------------------
# API Timeouts (seconds)
# ---------------------------------------------------------------------------
API_GET_TIMEOUT = 30
API_POST_TIMEOUT = 60
API_PATCH_TIMEOUT = 30
API_PUT_TIMEOUT = 30
API_DELETE_TIMEOUT = 30
API_SIGNALS_TIMEOUT = 15
API_EARNINGS_TIMEOUT = 15
API_DIVIDEND_TIMEOUT = 15

# ---------------------------------------------------------------------------
# Streamlit Cache TTLs (seconds)
# ---------------------------------------------------------------------------
CACHE_TTL_STOCKS = 300  # 5 minutes
CACHE_TTL_SIGNALS = 300  # 5 minutes
CACHE_TTL_REMOVED = 300  # 5 minutes
CACHE_TTL_MOAT = 3600  # 1 hour
CACHE_TTL_EARNINGS = 86400  # 24 hours
CACHE_TTL_DIVIDEND = 3600  # 1 hour
CACHE_TTL_SCAN_HISTORY = 300  # 5 minutes
CACHE_TTL_ALERTS = 300  # 5 minutes
CACHE_TTL_THESIS = 300  # 5 minutes

# ---------------------------------------------------------------------------
# UI Thresholds & Display
# ---------------------------------------------------------------------------
BIAS_OVERHEATED_UI = 20
BIAS_OVERSOLD_UI = -20
PRICE_WEAK_BIAS_THRESHOLD = -5
MARGIN_BAD_CHANGE_THRESHOLD = -2
EARNINGS_BADGE_DAYS_THRESHOLD = 14
SCAN_HISTORY_CARD_LIMIT = 10
DEFAULT_ALERT_THRESHOLD = 30.0

# ---------------------------------------------------------------------------
# Category Labels & Tags
# ---------------------------------------------------------------------------
CATEGORY_OPTIONS = ["Trend_Setter", "Moat", "Growth", "ETF"]
CATEGORY_LABELS = {
    "Trend_Setter": "🌊 風向球 (Trend Setter)",
    "Moat": "🏰 護城河 (Moat)",
    "Growth": "🚀 成長夢想 (Growth)",
    "ETF": "🧺 ETF",
}
DEFAULT_TAG_OPTIONS = [
    "AI",
    "Semiconductor",
    "Cloud",
    "SaaS",
    "Hardware",
    "EC",
    "Energy",
    "Crypto",
]

# ---------------------------------------------------------------------------
# External URLs
# ---------------------------------------------------------------------------
WHALEWISDOM_STOCK_URL = "https://whalewisdom.com/stock/{ticker}"

# ---------------------------------------------------------------------------
# File Names
# ---------------------------------------------------------------------------
EXPORT_FILENAME = "azusa_watchlist.json"
