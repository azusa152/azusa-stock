"""
Frontend — 集中管理所有前端常數與設定。
避免散落在 app.py 中的 magic numbers / magic strings。
"""

import json
import os

from i18n import t

# ---------------------------------------------------------------------------
# Backend Connection
# ---------------------------------------------------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
FOLIO_API_KEY = os.getenv("FOLIO_API_KEY", "")

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


def get_fx_chart_periods() -> dict[str, int]:
    """Get localized FX chart period options."""
    return {
        t("config.fx_period.1month"): 30,
        t("config.fx_period.2months"): 60,
        t("config.fx_period.3months"): 90,
    }


FX_CHART_DEFAULT_PERIOD_KEY = "config.fx_period.3months"  # Key for default period

# Cache TTL for FX history (align with backend L1 cache)
CACHE_TTL_FX_HISTORY = 7200  # 2 hours
API_FX_HISTORY_TIMEOUT = 20  # Longer timeout for potential yfinance delays

# ---------------------------------------------------------------------------
# UI Thresholds & Display
# ---------------------------------------------------------------------------
BIAS_OVERHEATED_UI = 20
BIAS_OVERSOLD_UI = -20
ROGUE_WAVE_PERCENTILE_UI = 95
ROGUE_WAVE_WARNING_PERCENTILE_UI = 90
PRICE_WEAK_BIAS_THRESHOLD = -5
MARGIN_BAD_CHANGE_THRESHOLD = -2
EARNINGS_BADGE_DAYS_THRESHOLD = 14
SCAN_HISTORY_CARD_LIMIT = 10
DEFAULT_ALERT_THRESHOLD = 30.0

# ---------------------------------------------------------------------------
# Category Labels & Tags
# ---------------------------------------------------------------------------
CATEGORY_OPTIONS = ["Trend_Setter", "Moat", "Growth", "Bond", "Cash"]


def get_category_label(category: str) -> str:
    """Get localized category label for a single category key."""
    return t(f"config.category.{category.lower()}")


def get_category_labels() -> dict[str, str]:
    """Get all localized category labels as a dict (evaluated at call time)."""
    return {k: get_category_label(k) for k in CATEGORY_OPTIONS}


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


def get_withdraw_priority_label(priority: int) -> str:
    """Get localized withdrawal priority label."""
    labels = {
        1: t("config.priority.rebalance"),
        2: t("config.priority.tax"),
        3: t("config.priority.liquidity"),
    }
    return labels.get(priority, str(priority))


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
def get_stock_market_options() -> dict:
    """Get localized stock market options."""
    return {
        "US": {"label": t("config.market.us"), "suffix": "", "currency": "USD"},
        "TW": {"label": t("config.market.tw"), "suffix": ".TW", "currency": "TWD"},
        "JP": {"label": t("config.market.jp"), "suffix": ".T", "currency": "JPY"},
        "HK": {"label": t("config.market.hk"), "suffix": ".HK", "currency": "HKD"},
    }


STOCK_MARKET_PLACEHOLDERS = {
    "US": "AAPL",
    "TW": "2330",
    "JP": "7203",
    "HK": "0700",
}


def get_ticker_market_label(ticker: str) -> str:
    """Get market label from ticker suffix."""
    if ".TW" in ticker:
        return t("config.market.tw")
    elif ".T" in ticker:
        return t("config.market.jp")
    elif ".HK" in ticker:
        return t("config.market.hk")
    else:
        return t("config.market.us")


STOCK_CATEGORY_OPTIONS = ["Trend_Setter", "Moat", "Growth"]

# ---------------------------------------------------------------------------
# Cash Form Options
# ---------------------------------------------------------------------------
CASH_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "EUR", "GBP", "CNY", "HKD", "SGD", "THB"]


def get_cash_account_type_options() -> list[str]:
    """Get localized cash account type options."""
    return [
        t("config.account_type.savings"),
        t("config.account_type.fixed_deposit"),
        t("config.account_type.money_market"),
        t("config.account_type.other"),
    ]


# ---------------------------------------------------------------------------
# Display Currency Options (for rebalance analysis)
# ---------------------------------------------------------------------------
DISPLAY_CURRENCY_OPTIONS = [
    "USD",
    "TWD",
    "JPY",
    "EUR",
    "GBP",
    "CNY",
    "HKD",
    "SGD",
    "THB",
]

# ---------------------------------------------------------------------------
# UI Constants (shared across pages)
# ---------------------------------------------------------------------------
ALERT_METRIC_OPTIONS = ["rsi", "price", "bias"]
ALERT_OPERATOR_OPTIONS = ["lt", "gt"]
SCAN_SIGNAL_ICONS = {
    "THESIS_BROKEN": "🔴",
    "DEEP_VALUE": "🔵",
    "OVERSOLD": "🟣",
    "CONTRARIAN_BUY": "🟢",
    "OVERHEATED": "🟠",
    "CAUTION_HIGH": "🟡",
    "WEAKENING": "🟤",
    "NORMAL": "⚪",
}
REORDER_MIN_STOCKS = 2
PRIVACY_MASK = "***"


def get_privacy_toggle_label() -> str:
    """Get localized privacy toggle label."""
    return t("config.privacy_mode")


# ---------------------------------------------------------------------------
# Dashboard Page
# ---------------------------------------------------------------------------
DASHBOARD_TOP_HOLDINGS_LIMIT = 10
CACHE_TTL_LAST_SCAN = 60  # 1 minute
CACHE_TTL_PREFERENCES = 300  # 5 minutes
HEALTH_SCORE_GOOD_THRESHOLD = 80
HEALTH_SCORE_WARN_THRESHOLD = 50


def get_market_sentiment_label(sentiment: str) -> dict:
    """Get localized market sentiment label and color."""
    labels = {
        "POSITIVE": {"label": t("config.sentiment.positive"), "color": "green"},
        "CAUTION": {"label": t("config.sentiment.caution"), "color": "red"},
    }
    return labels.get(
        sentiment, {"label": t("config.sentiment.not_scanned"), "color": "off"}
    )


# Fear & Greed Index
def get_fear_greed_label(level: str) -> dict:
    """Get localized fear & greed label and color."""
    labels = {
        "EXTREME_FEAR": {
            "label": t("config.fear_greed.extreme_fear"),
            "color": "inverse",
        },
        "FEAR": {"label": t("config.fear_greed.fear"), "color": "off"},
        "NEUTRAL": {"label": t("config.fear_greed.neutral"), "color": "normal"},
        "GREED": {"label": t("config.fear_greed.greed"), "color": "normal"},
        "EXTREME_GREED": {
            "label": t("config.fear_greed.extreme_greed"),
            "color": "off",
        },
        "N/A": {"label": t("config.fear_greed.na"), "color": "off"},
    }
    return labels.get(level, {"label": t("config.fear_greed.na"), "color": "off"})


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


def get_cnn_unavailable_msg() -> str:
    """Get localized CNN unavailable message."""
    return t("config.cnn_unavailable")


DASHBOARD_DRIFT_CHART_HEIGHT = 250
DASHBOARD_ALLOCATION_CHART_HEIGHT = 300

# ---------------------------------------------------------------------------
# X-Ray (Portfolio Overlap Analysis)
# ---------------------------------------------------------------------------
XRAY_WARN_THRESHOLD_PCT = 15.0
XRAY_TOP_N_DISPLAY = 15

# ---------------------------------------------------------------------------
# Smart Money (大師足跡)
# ---------------------------------------------------------------------------
CACHE_TTL_GURU_LIST = 300           # 5 minutes (guru list rarely changes)
CACHE_TTL_GURU_FILING = 86400       # 24 hours (13F data is quarterly)
CACHE_TTL_GURU_DASHBOARD = 3600     # 1 hour (aggregated dashboard data)
CACHE_TTL_RESONANCE = 86400         # 24 hours (derived from 13F data)
API_GURU_SYNC_TIMEOUT = 120         # EDGAR fetch can be slow
API_GURU_GET_TIMEOUT = 20
API_GURU_DASHBOARD_TIMEOUT = 30     # dashboard aggregation can be slow on first call

SMART_MONEY_TOP_N = 20  # increased from 10 to show more meaningful holdings
SMART_MONEY_STALE_DAYS = 120  # report date older than this shown as stale on guru cards
SEASON_HIGHLIGHTS_DISPLAY_LIMIT = 10  # limit season highlights to top N per category

# Action color coding (PRD section 4.2: green=buy/new, red=sell/out, gray=hold)
HOLDING_ACTION_COLORS: dict[str, str] = {
    "NEW_POSITION": "#22C55E",   # green
    "INCREASED": "#86EFAC",      # light green
    "DECREASED": "#FCA5A5",      # light red
    "SOLD_OUT": "#EF4444",       # red
    "UNCHANGED": "#9CA3AF",      # gray
}

HOLDING_ACTION_ICONS: dict[str, str] = {
    "NEW_POSITION": "🟢",
    "INCREASED": "📈",
    "DECREASED": "📉",
    "SOLD_OUT": "🔴",
    "UNCHANGED": "⚪",
}


def get_holding_action_label(action: str) -> str:
    """Get localized holding action label."""
    return t(f"smart_money.action.{action.lower()}")


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
