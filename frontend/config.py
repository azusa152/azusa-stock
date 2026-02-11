"""
Frontend — 集中管理所有前端常數與設定。
避免散落在 app.py 中的 magic numbers / magic strings。
"""

import json
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
FX_HIGH_CONCENTRATION_PCT = 70.0  # matches backend constant
FX_MEDIUM_CONCENTRATION_PCT = 40.0  # matches backend constant

# ---------------------------------------------------------------------------
# Category Labels & Tags
# ---------------------------------------------------------------------------
CATEGORY_OPTIONS = ["Trend_Setter", "Moat", "Growth", "Bond", "Cash"]
CATEGORY_LABELS = {
    "Trend_Setter": "🌊 風向球 (Trend Setter)",
    "Moat": "🏰 護城河 (Moat)",
    "Growth": "🚀 成長夢想 (Growth)",
    "Bond": "🛡️ 債券 (Bond)",
    "Cash": "💵 現金 (Cash)",
}
# ---------------------------------------------------------------------------
# Category Colors (for pie chart visual grouping)
# ---------------------------------------------------------------------------
CATEGORY_COLOR_MAP = {
    "Trend_Setter": "#3B82F6",  # blue
    "Moat": "#22C55E",  # green
    "Growth": "#F97316",  # orange
    "Bond": "#8B5CF6",  # purple
    "Cash": "#EAB308",  # yellow
}
CATEGORY_ICON_SHORT = {
    "Trend_Setter": "🌊",
    "Moat": "🏰",
    "Growth": "🚀",
    "Bond": "🛡️",
    "Cash": "💵",
}
CATEGORY_COLOR_FALLBACK = "#9CA3AF"

SKIP_MOAT_CATEGORIES = ["Bond", "Cash"]  # 不顯示護城河檢測的分類
SKIP_SIGNALS_CATEGORIES = ["Cash"]  # 不取得技術訊號的分類
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
# Price Trend Chart
# ---------------------------------------------------------------------------
CACHE_TTL_PRICE_HISTORY = 300  # 5 minutes
API_PRICE_HISTORY_TIMEOUT = 15
PRICE_CHART_PERIODS = {
    "1W": 5,
    "1M": 21,
    "6M": 126,
    "1Y": 252,
}
PRICE_CHART_DEFAULT_PERIOD = "1M"
PRICE_CHART_HEIGHT = 200

# ---------------------------------------------------------------------------
# War Room / Asset Allocation
# ---------------------------------------------------------------------------
CACHE_TTL_TEMPLATES = 86400  # 24 hours (personas rarely change)
CACHE_TTL_PROFILE = 300  # 5 minutes
CACHE_TTL_HOLDINGS = 300  # 5 minutes
CACHE_TTL_REBALANCE = 60  # 1 minute (contains live prices)
API_REBALANCE_TIMEOUT = 30
DRIFT_CHART_HEIGHT = 300
ALLOCATION_CHART_HEIGHT = 400

# ---------------------------------------------------------------------------
# External URLs
# ---------------------------------------------------------------------------
WHALEWISDOM_STOCK_URL = "https://whalewisdom.com/stock/{ticker}"

# ---------------------------------------------------------------------------
# Radar Page — Category subset (excludes Cash)
# ---------------------------------------------------------------------------
RADAR_CATEGORY_OPTIONS = ["Trend_Setter", "Moat", "Growth", "Bond"]

# ---------------------------------------------------------------------------
# Stock Market Options (for multi-market support)
# ---------------------------------------------------------------------------
STOCK_MARKET_OPTIONS = {
    "US": {"label": "🇺🇸 美股", "suffix": "", "currency": "USD"},
    "TW": {"label": "🇹🇼 台股", "suffix": ".TW", "currency": "TWD"},
    "JP": {"label": "🇯🇵 日股", "suffix": ".T", "currency": "JPY"},
    "HK": {"label": "🇭🇰 港股", "suffix": ".HK", "currency": "HKD"},
}
STOCK_MARKET_PLACEHOLDERS = {
    "US": "AAPL",
    "TW": "2330",
    "JP": "7203",
    "HK": "0700",
}
# Reverse-lookup: ticker suffix -> market label (for display on stock cards)
TICKER_SUFFIX_TO_MARKET = {
    ".TW": "🇹🇼 台股",
    ".T": "🇯🇵 日股",
    ".HK": "🇭🇰 港股",
}
TICKER_DEFAULT_MARKET = "🇺🇸 美股"
STOCK_CATEGORY_OPTIONS = ["Trend_Setter", "Moat", "Growth"]

# ---------------------------------------------------------------------------
# Cash Form Options
# ---------------------------------------------------------------------------
CASH_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "EUR", "GBP", "CNY", "HKD", "SGD", "THB"]
CASH_ACCOUNT_TYPE_OPTIONS = ["活存", "定存", "貨幣市場基金", "其他"]

# ---------------------------------------------------------------------------
# Display Currency Options (for rebalance analysis)
# ---------------------------------------------------------------------------
DISPLAY_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "EUR", "GBP", "CNY", "HKD", "SGD", "THB"]

# ---------------------------------------------------------------------------
# UI Constants (shared across pages)
# ---------------------------------------------------------------------------
ALERT_METRIC_OPTIONS = ["rsi", "price", "bias"]
ALERT_OPERATOR_OPTIONS = ["lt", "gt"]
SCAN_SIGNAL_ICONS = {
    "THESIS_BROKEN": "🔴",
    "CONTRARIAN_BUY": "🟢",
    "OVERHEATED": "🟠",
    "NORMAL": "⚪",
}
REORDER_MIN_STOCKS = 2
PRIVACY_MASK = "***"
PRIVACY_TOGGLE_LABEL = "🙈 隱私模式"

# ---------------------------------------------------------------------------
# Dashboard Page
# ---------------------------------------------------------------------------
DASHBOARD_TOP_HOLDINGS_LIMIT = 10
CACHE_TTL_LAST_SCAN = 60  # 1 minute
CACHE_TTL_PREFERENCES = 300  # 5 minutes
HEALTH_SCORE_GOOD_THRESHOLD = 80
HEALTH_SCORE_WARN_THRESHOLD = 50
MARKET_SENTIMENT_LABELS = {
    "POSITIVE": {"label": "☀️ 晴天", "color": "green"},
    "CAUTION": {"label": "🌧️ 雨天", "color": "red"},
}
MARKET_SENTIMENT_DEFAULT_LABEL = "⏳ 尚未掃描"
DASHBOARD_DRIFT_CHART_HEIGHT = 250
DASHBOARD_ALLOCATION_CHART_HEIGHT = 300

# ---------------------------------------------------------------------------
# X-Ray (Portfolio Overlap Analysis)
# ---------------------------------------------------------------------------
XRAY_WARN_THRESHOLD_PCT = 15.0
XRAY_TOP_N_DISPLAY = 15

# ---------------------------------------------------------------------------
# File Names
# ---------------------------------------------------------------------------
EXPORT_FILENAME = "folio_watchlist.json"
HOLDINGS_EXPORT_FILENAME = "folio_holdings.json"

# ---------------------------------------------------------------------------
# Import Templates (embedded as JSON strings for frontend download)
# ---------------------------------------------------------------------------
STOCK_IMPORT_TEMPLATE = json.dumps(
    [
        {
            "ticker": "NVDA",
            "category": "Moat",
            "thesis": "Your investment thesis here.",
            "tags": ["AI", "Semiconductor"],
        },
        {
            "ticker": "TLT",
            "category": "Bond",
            "thesis": "Long-term treasury bond ETF.",
            "tags": ["Bond"],
        },
    ],
    ensure_ascii=False,
    indent=2,
)

HOLDING_IMPORT_TEMPLATE = json.dumps(
    [
        {
            "ticker": "NVDA",
            "category": "Moat",
            "quantity": 10,
            "cost_basis": 120.50,
            "broker": "Firstrade",
            "currency": "USD",
        },
        {
            "ticker": "2330.TW",
            "category": "Moat",
            "quantity": 100,
            "cost_basis": 580.00,
            "broker": "永豐金",
            "currency": "TWD",
        },
        {
            "ticker": "TLT",
            "category": "Bond",
            "quantity": 50,
            "cost_basis": 92.00,
            "broker": "永豐金",
            "currency": "USD",
        },
        {
            "ticker": "USD",
            "category": "Cash",
            "quantity": 50000,
            "cost_basis": None,
            "broker": "台新銀行",
            "account_type": "活存",
            "currency": "USD",
            "is_cash": True,
        },
        {
            "ticker": "TWD",
            "category": "Cash",
            "quantity": 100000,
            "cost_basis": None,
            "broker": "中國信託",
            "account_type": "定存",
            "currency": "TWD",
            "is_cash": True,
        },
    ],
    ensure_ascii=False,
    indent=2,
)
