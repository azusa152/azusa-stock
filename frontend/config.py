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
API_GET_ENRICHED_TIMEOUT = 10  # short: page loads fast; warm cache responds in time

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
# FX Watch Configuration
# ---------------------------------------------------------------------------
CACHE_TTL_FX_WATCH = 60  # 1 minute (watches update frequently)
API_FX_WATCH_TIMEOUT = 15  # FX watch API timeout

# Currency options for FX Watch (align with backend SUPPORTED_CURRENCIES)
FX_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "EUR", "GBP", "CNY", "HKD", "SGD", "THB"]

# ---------------------------------------------------------------------------
# FX Chart Configuration
# ---------------------------------------------------------------------------
FX_CHART_HEIGHT = 280  # Matches price chart height for consistency
FX_CHART_PERIODS = {
    "1 個月": 30,
    "2 個月": 60,
    "3 個月": 90,
}
FX_CHART_DEFAULT_PERIOD = "3 個月"  # Show full available data by default

# Cache TTL for FX history (align with backend L1 cache)
CACHE_TTL_FX_HISTORY = 7200  # 2 hours
API_FX_HISTORY_TIMEOUT = 20  # Longer timeout for potential yfinance delays

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
API_WITHDRAW_TIMEOUT = 30
DRIFT_CHART_HEIGHT = 300
ALLOCATION_CHART_HEIGHT = 400
WITHDRAW_PRIORITY_LABELS = {
    1: "🔄 再平衡",
    2: "📉 節稅",
    3: "💧 流動性",
}

# ---------------------------------------------------------------------------
# Stress Test (Portfolio Stress Testing)
# ---------------------------------------------------------------------------
CACHE_TTL_STRESS_TEST = 60  # 1 minute (same as rebalance)
API_STRESS_TEST_TIMEOUT = 60  # Increased to allow Beta fetching for multiple holdings
STRESS_SLIDER_MIN = -50
STRESS_SLIDER_MAX = 0
STRESS_SLIDER_STEP = 5
STRESS_SLIDER_DEFAULT = -20
PAIN_LEVEL_COLORS = {
    "low": "#22c55e",  # green
    "moderate": "#eab308",  # yellow
    "high": "#f97316",  # orange
    "panic": "#ef4444",  # red
}

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

# Fear & Greed Index
FEAR_GREED_LABELS = {
    "EXTREME_FEAR": {"label": "😱 極度恐懼", "color": "inverse"},
    "FEAR": {"label": "😨 恐懼", "color": "off"},
    "NEUTRAL": {"label": "😐 中性", "color": "normal"},
    "GREED": {"label": "🤑 貪婪", "color": "normal"},
    "EXTREME_GREED": {"label": "🤯 極度貪婪", "color": "off"},
    "N/A": {"label": "⏳ 無資料", "color": "off"},
}
FEAR_GREED_DEFAULT_LABEL = "⏳ 無資料"
CACHE_TTL_FEAR_GREED = 1800  # 30 minutes
API_FEAR_GREED_TIMEOUT = 15

# Fear & Greed Gauge Chart (CNN-style semicircle)
FEAR_GREED_GAUGE_HEIGHT = 200
FEAR_GREED_GAUGE_BANDS: list[dict] = [
    {"range": [0, 25], "color": "#d32f2f"},  # 極度恐懼 — dark red
    {"range": [25, 45], "color": "#ff9800"},  # 恐懼 — orange
    {"range": [45, 55], "color": "#fdd835"},  # 中性 — yellow
    {"range": [55, 75], "color": "#66bb6a"},  # 貪婪 — light green
    {"range": [75, 100], "color": "#2e7d32"},  # 極度貪婪 — dark green
]
FEAR_GREED_CNN_UNAVAILABLE_MSG = "⚠️ CNN 資料不可用，僅使用 VIX"

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
