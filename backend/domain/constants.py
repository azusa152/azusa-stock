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
ETF_MOAT_NA_MESSAGE = "ETF 不適用護城河分析"

# ---------------------------------------------------------------------------
# curl_cffi
# ---------------------------------------------------------------------------
CURL_CFFI_IMPERSONATE = "chrome"
