"""
Domain — 集中管理所有常數與閾值。
避免散落在各模組中的 magic numbers / magic strings。
"""

# ---------------------------------------------------------------------------
# Technical Indicator Parameters
# ---------------------------------------------------------------------------
RSI_PERIOD = 14
MA200_WINDOW = 200
MA60_WINDOW = 60
VOLUME_RATIO_SHORT_DAYS = 5
VOLUME_RATIO_LONG_DAYS = 20
YFINANCE_HISTORY_PERIOD = "1y"
MIN_HISTORY_DAYS_FOR_SIGNALS = 60

# ---------------------------------------------------------------------------
# Decision Engine Thresholds
# ---------------------------------------------------------------------------
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_CONTRARIAN_BUY_THRESHOLD = 35
BIAS_OVERHEATED_THRESHOLD = 20
BIAS_OVERSOLD_THRESHOLD = -20
MOAT_MARGIN_DETERIORATION_THRESHOLD = -2  # percentage points YoY
MARKET_CAUTION_BELOW_60MA_PCT = 50  # % of trend stocks below 60MA

# ---------------------------------------------------------------------------
# Cache Configuration
# ---------------------------------------------------------------------------
SIGNALS_CACHE_MAXSIZE = 200
SIGNALS_CACHE_TTL = 300  # 5 minutes
MOAT_CACHE_MAXSIZE = 200
MOAT_CACHE_TTL = 3600  # 1 hour
EARNINGS_CACHE_MAXSIZE = 200
EARNINGS_CACHE_TTL = 86400  # 24 hours
DIVIDEND_CACHE_MAXSIZE = 200
DIVIDEND_CACHE_TTL = 3600  # 1 hour

# ---------------------------------------------------------------------------
# Disk Cache (L2) — 持久化快取，容器重啟後仍可使用
# ---------------------------------------------------------------------------
DISK_CACHE_DIR = "/app/data/yf_cache"
DISK_CACHE_SIZE_LIMIT = 100 * 1024 * 1024  # 100 MB

# Disk Cache TTLs（比 L1 更長，作為冷啟動 fallback）
DISK_SIGNALS_TTL = 1800  # 30 minutes
DISK_MOAT_TTL = 86400  # 24 hours
DISK_EARNINGS_TTL = 604800  # 7 days
DISK_DIVIDEND_TTL = 86400  # 24 hours

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
YFINANCE_RATE_LIMIT_CPS = 2.0  # calls per second

# ---------------------------------------------------------------------------
# Scan & Alerts
# ---------------------------------------------------------------------------
SCAN_THREAD_POOL_SIZE = 4
PRICE_ALERT_COOLDOWN_HOURS = 4
WEEKLY_DIGEST_LOOKBACK_DAYS = 7
SCAN_HISTORY_DEFAULT_LIMIT = 20
LATEST_SCAN_LOGS_DEFAULT_LIMIT = 50
INSTITUTIONAL_HOLDERS_TOP_N = 5
MARGIN_TREND_QUARTERS = 5

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_REQUEST_TIMEOUT = 10

# ---------------------------------------------------------------------------
# Shared Messages
# ---------------------------------------------------------------------------
SKIP_SIGNALS_CATEGORIES = ["Cash"]  # Cash 類不進行 yfinance 訊號掃描
SKIP_MOAT_CATEGORIES = ["Bond", "Cash"]  # 債券與現金不適用護城河分析
REMOVAL_REASON_UNKNOWN = "未知"

# ---------------------------------------------------------------------------
# Default Parameter Values
# ---------------------------------------------------------------------------
DEFAULT_ALERT_METRIC = "rsi"
DEFAULT_ALERT_OPERATOR = "lt"
DEFAULT_ALERT_THRESHOLD = 30.0
DEFAULT_IMPORT_CATEGORY = "Growth"
DEFAULT_WEBHOOK_THESIS = "由 AI agent 新增。"

# ---------------------------------------------------------------------------
# Category Display Order & Icons
# ---------------------------------------------------------------------------
CATEGORY_DISPLAY_ORDER = ["Trend_Setter", "Moat", "Growth", "Bond", "Cash"]

CATEGORY_ICON: dict[str, str] = {
    "Trend_Setter": "🌊",
    "Moat": "🏰",
    "Growth": "🚀",
    "Bond": "🛡️",
    "Cash": "💵",
}

# ---------------------------------------------------------------------------
# User & Profile
# ---------------------------------------------------------------------------
DEFAULT_USER_ID = "default"
DRIFT_THRESHOLD_PCT = 5.0  # rebalancing drift threshold (percentage points)

# ---------------------------------------------------------------------------
# Forex Cache
# ---------------------------------------------------------------------------
FOREX_CACHE_MAXSIZE = 50
FOREX_CACHE_TTL = 3600  # 1 hour
DISK_FOREX_TTL = 86400  # 24 hours

# ---------------------------------------------------------------------------
# Supported Currencies
# ---------------------------------------------------------------------------
SUPPORTED_CURRENCIES = ["USD", "TWD", "JPY", "EUR", "GBP", "CNY", "HKD", "SGD", "THB"]

# ---------------------------------------------------------------------------
# Price History Cache
# ---------------------------------------------------------------------------
PRICE_HISTORY_CACHE_MAXSIZE = 200
PRICE_HISTORY_CACHE_TTL = 300  # L1: 5 minutes (same as signals)
DISK_PRICE_HISTORY_TTL = 1800  # L2: 30 minutes

# ---------------------------------------------------------------------------
# Disk Cache Key Prefixes
# ---------------------------------------------------------------------------
DISK_KEY_SIGNALS = "signals"
DISK_KEY_MOAT = "moat"
DISK_KEY_EARNINGS = "earnings"
DISK_KEY_DIVIDEND = "dividend"
DISK_KEY_PRICE_HISTORY = "price_history"
DISK_KEY_FOREX = "forex"

# ---------------------------------------------------------------------------
# Webhook Messages
# ---------------------------------------------------------------------------
WEBHOOK_MISSING_TICKER = "請提供 ticker 參數。"
WEBHOOK_UNKNOWN_ACTION_TEMPLATE = "不支援的 action: {action}。支援：summary, signals, scan, moat, alerts, add_stock"

# ---------------------------------------------------------------------------
# curl_cffi
# ---------------------------------------------------------------------------
CURL_CFFI_IMPERSONATE = "chrome"
