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
MIN_CLOSE_PRICES_FOR_CHANGE = 2  # 計算日漲跌所需的最少收盤價數據點（前日 + 當日）

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
ENRICHED_THREAD_POOL_SIZE = 8  # 批次豐富資料用較大執行緒池
ENRICHED_PER_TICKER_TIMEOUT = 15  # 每檔股票豐富資料超時（秒）
SCAN_STALE_SECONDS = 1800  # 30 minutes — scanner skips if last scan is fresher
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
# Smart Withdrawal (聰明提款機)
# ---------------------------------------------------------------------------
# 流動性優先順序：最容易變現的排最前面，複利核心資產排最後
CATEGORY_LIQUIDITY_ORDER = ["Cash", "Bond", "Growth", "Moat", "Trend_Setter"]
WITHDRAWAL_MIN_SELL_VALUE = 10.0  # 最小賣出金額（避免灰塵交易）

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
# ETF Holdings Cache (for X-Ray analysis)
# ---------------------------------------------------------------------------
ETF_HOLDINGS_CACHE_MAXSIZE = 100
ETF_HOLDINGS_CACHE_TTL = 86400  # 24 hours (ETF holdings change slowly)
DISK_ETF_HOLDINGS_TTL = 604800  # 7 days
ETF_TOP_N = 10  # only resolve top N constituents per ETF

# ---------------------------------------------------------------------------
# Currency Exposure Monitor
# ---------------------------------------------------------------------------
FX_DAILY_SPIKE_PCT = 1.5  # 單日波動門檻
FX_SHORT_TERM_SWING_PCT = 2.0  # 5 日波段門檻
FX_LONG_TERM_TREND_PCT = 8.0  # 3 個月趨勢門檻
FX_HISTORY_PERIOD = "5d"  # yfinance period for short-term detection
FX_LONG_TERM_PERIOD = "3mo"  # yfinance period for long-term trend detection
DISK_KEY_FOREX_HISTORY = "forex_history"
DISK_FOREX_HISTORY_TTL = 3600  # 1 hour
FOREX_HISTORY_CACHE_MAXSIZE = 50
FOREX_HISTORY_CACHE_TTL = 3600  # 1 hour
DISK_KEY_FOREX_HISTORY_LONG = "forex_history_long"
DISK_FOREX_HISTORY_LONG_TTL = 14400  # 4 hours (long-term data changes slowly)
FOREX_HISTORY_LONG_CACHE_MAXSIZE = 50
FOREX_HISTORY_LONG_CACHE_TTL = 7200  # 2 hours L1

# ---------------------------------------------------------------------------
# FX Watch (Exchange Timing Alerts)
# ---------------------------------------------------------------------------
FX_WATCH_DEFAULT_RECENT_HIGH_DAYS = 30  # 30-day recent high window
FX_WATCH_DEFAULT_CONSECUTIVE_DAYS = 3  # 3-day consecutive increase threshold
FX_WATCH_DEFAULT_REMINDER_HOURS = 24  # 24-hour cooldown between alerts
FX_WATCH_DEFAULT_ALERT_ON_RECENT_HIGH = True  # Enable recent high alerts by default
FX_WATCH_DEFAULT_ALERT_ON_CONSECUTIVE = (
    True  # Enable consecutive increase alerts by default
)

# ---------------------------------------------------------------------------
# X-Ray (Portfolio Overlap Analysis)
# ---------------------------------------------------------------------------
XRAY_SINGLE_STOCK_WARN_PCT = 15.0  # Telegram warning threshold (%)
XRAY_SKIP_CATEGORIES = ["Cash", "Bond"]  # skip non-equity for X-Ray

# ---------------------------------------------------------------------------
# Fear & Greed Index
# ---------------------------------------------------------------------------
VIX_TICKER = "^VIX"
VIX_HISTORY_PERIOD = "5d"

# VIX 閾值（對應恐懼與貪婪等級）
VIX_EXTREME_FEAR = 30  # VIX > 30 → 極度恐懼
VIX_FEAR = 20  # VIX 20–30 → 恐懼
VIX_NEUTRAL_HIGH = 20  # VIX 15–20 → 中性
VIX_NEUTRAL_LOW = 15
VIX_GREED = 10  # VIX 10–15 → 貪婪
# VIX < 10 → 極度貪婪

# CNN Fear & Greed Index 閾值（0–100 分）
CNN_FG_EXTREME_FEAR = 25  # 0–25 → 極度恐懼
CNN_FG_FEAR = 45  # 25–45 → 恐懼
CNN_FG_NEUTRAL_HIGH = 55  # 45–55 → 中性
CNN_FG_GREED = 75  # 55–75 → 貪婪
# 75–100 → 極度貪婪

CNN_FG_API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_FG_REQUEST_TIMEOUT = 10  # seconds

# 綜合權重：VIX 40%, CNN 60%
FG_WEIGHT_VIX = 0.4
FG_WEIGHT_CNN = 0.6

# Fear & Greed Cache
FEAR_GREED_CACHE_MAXSIZE = 10
FEAR_GREED_CACHE_TTL = 1800  # L1: 30 minutes
DISK_FEAR_GREED_TTL = 7200  # L2: 2 hours

# ---------------------------------------------------------------------------
# Disk Cache Key Prefixes
# ---------------------------------------------------------------------------
DISK_KEY_SIGNALS = "signals"
DISK_KEY_MOAT = "moat"
DISK_KEY_EARNINGS = "earnings"
DISK_KEY_DIVIDEND = "dividend"
DISK_KEY_PRICE_HISTORY = "price_history"
DISK_KEY_FOREX = "forex"
DISK_KEY_ETF_HOLDINGS = "etf_holdings"
DISK_KEY_FEAR_GREED = "fear_greed"

# ---------------------------------------------------------------------------
# Webhook Messages
# ---------------------------------------------------------------------------
WEBHOOK_MISSING_TICKER = "請提供 ticker 參數。"

# ---------------------------------------------------------------------------
# Webhook Action Registry — single source of truth for AI agent actions
# ---------------------------------------------------------------------------
WEBHOOK_ACTION_REGISTRY: dict[str, dict] = {
    "help": {
        "description": "List all supported webhook actions and their parameters",
        "requires_ticker": False,
    },
    "summary": {
        "description": "Portfolio health overview (plain text)",
        "requires_ticker": False,
    },
    "signals": {
        "description": "Technical indicators for a ticker (RSI, MA, Bias)",
        "requires_ticker": True,
    },
    "scan": {
        "description": "Trigger background full scan (results via Telegram)",
        "requires_ticker": False,
    },
    "moat": {
        "description": "Gross margin YoY analysis for a ticker",
        "requires_ticker": True,
    },
    "alerts": {
        "description": "List price alerts for a ticker",
        "requires_ticker": True,
    },
    "add_stock": {
        "description": "Add a stock to the watchlist",
        "requires_ticker": True,
        "params": {
            "ticker": "str (required)",
            "category": "StockCategory (Trend_Setter|Moat|Growth|Bond|Cash)",
            "thesis": "str (investment thesis)",
            "tags": "list[str] (e.g. ['AI', 'Semiconductor'])",
        },
    },
    "fear_greed": {
        "description": "Current Fear & Greed Index (VIX + CNN composite)",
        "requires_ticker": False,
    },
    "withdraw": {
        "description": "Smart withdrawal plan (Liquidity Waterfall)",
        "requires_ticker": False,
        "params": {
            "amount": "float (required, target withdrawal amount)",
            "currency": "str (display currency, default USD)",
        },
    },
    "fx_watch": {
        "description": "Check FX watch configs & send Telegram alerts (with cooldown)",
        "requires_ticker": False,
    },
}

# ---------------------------------------------------------------------------
# Notification Preferences — toggleable notification types
# ---------------------------------------------------------------------------
NOTIFICATION_TYPES = {
    "scan_alerts": "掃描訊號通知（THESIS_BROKEN / OVERHEATED / CONTRARIAN_BUY）",
    "price_alerts": "自訂價格警報觸發通知",
    "weekly_digest": "每週投資摘要",
    "xray_alerts": "X-Ray 集中度警告",
    "fx_alerts": "匯率曝險警報",
    "fx_watch_alerts": "外匯換匯時機警報",
}
DEFAULT_NOTIFICATION_PREFERENCES: dict[str, bool] = {
    k: True for k in NOTIFICATION_TYPES
}

# ---------------------------------------------------------------------------
# Error Codes — machine-readable slugs for AI agent error handling
# ---------------------------------------------------------------------------
ERROR_STOCK_NOT_FOUND = "STOCK_NOT_FOUND"
ERROR_STOCK_ALREADY_EXISTS = "STOCK_ALREADY_EXISTS"
ERROR_STOCK_ALREADY_INACTIVE = "STOCK_ALREADY_INACTIVE"
ERROR_STOCK_ALREADY_ACTIVE = "STOCK_ALREADY_ACTIVE"
ERROR_CATEGORY_UNCHANGED = "CATEGORY_UNCHANGED"
ERROR_HOLDING_NOT_FOUND = "HOLDING_NOT_FOUND"
ERROR_PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
ERROR_SCAN_IN_PROGRESS = "SCAN_IN_PROGRESS"
ERROR_DIGEST_IN_PROGRESS = "DIGEST_IN_PROGRESS"
ERROR_TELEGRAM_NOT_CONFIGURED = "TELEGRAM_NOT_CONFIGURED"
ERROR_TELEGRAM_SEND_FAILED = "TELEGRAM_SEND_FAILED"
ERROR_PREFERENCES_UPDATE_FAILED = "PREFERENCES_UPDATE_FAILED"

# ---------------------------------------------------------------------------
# curl_cffi
# ---------------------------------------------------------------------------
CURL_CFFI_IMPERSONATE = "chrome"

# ---------------------------------------------------------------------------
# Retry Configuration (yfinance transient network failures)
# ---------------------------------------------------------------------------
YFINANCE_RETRY_ATTEMPTS = 3
YFINANCE_RETRY_WAIT_MIN = 2  # seconds (exponential backoff minimum)
YFINANCE_RETRY_WAIT_MAX = 10  # seconds (exponential backoff maximum)
