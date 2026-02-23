"""
Domain — 集中管理所有常數與閾值。
避免散落在各模組中的 magic numbers / magic strings。
"""

import os as _os

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
RSI_APPROACHING_BUY_THRESHOLD = 37
RSI_WEAKENING_THRESHOLD = 38
BIAS_OVERHEATED_THRESHOLD = 20
BIAS_OVERSOLD_THRESHOLD = -20
BIAS_WEAKENING_THRESHOLD = -15
# Same magnitude as BIAS_WEAKENING but measured against MA200 (not MA60); may diverge independently.
MA200_DEEP_DEVIATION_THRESHOLD = -15  # buy amplifier: price deeply below MA200
MA200_HIGH_DEVIATION_THRESHOLD = 20  # sell amplifier: price highly above MA200 (asymmetric due to positive market drift)
MOAT_MARGIN_DETERIORATION_THRESHOLD = -2  # percentage points YoY

# Category RSI offset — derived from CATEGORY_FALLBACK_BETA via round((beta - 1.0) * 4)
# Widens/narrows RSI bands symmetrically on both buy and sell sides per category
CATEGORY_RSI_OFFSET: dict[str, int] = {
    "Trend_Setter": 0,  # beta ~1.0
    "Moat": 1,  # beta ~1.2
    "Growth": 2,  # beta ~1.5
    "Bond": -3,  # beta ~0.3
    "Cash": 0,
}
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
# Persistent Data Directory — root for all app-written state files
# ---------------------------------------------------------------------------
DATA_DIR = _os.getenv("DATA_DIR", "/app/data")

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
REMOVAL_REASON_UNKNOWN = "constants.removal_reason_unknown"  # i18n key

# ---------------------------------------------------------------------------
# Default Parameter Values
# ---------------------------------------------------------------------------
DEFAULT_ALERT_METRIC = "rsi"
DEFAULT_ALERT_OPERATOR = "lt"
DEFAULT_ALERT_THRESHOLD = 30.0
DEFAULT_IMPORT_CATEGORY = "Growth"
DEFAULT_WEBHOOK_THESIS = "constants.default_webhook_thesis"  # i18n key

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
# i18n Language Support
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = ["zh-TW", "en", "ja", "zh-CN"]
DEFAULT_LANGUAGE = "zh-TW"
LANGUAGE_LABELS = {
    "zh-TW": "繁體中文",
    "en": "English",
    "ja": "日本語",
    "zh-CN": "简体中文",
}

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

# VIX → 0–100 分數的分段線性映射斷點（對齊 CNN 分級閾值）
VIX_SCORE_BREAKPOINTS: list[tuple[int, int]] = [
    (30, 25),  # VIX 30 → score 25（極度恐懼/恐懼 邊界）
    (20, 45),  # VIX 20 → score 45（恐懼/中性 邊界）
    (15, 55),  # VIX 15 → score 55（中性/貪婪 邊界）
    (10, 75),  # VIX 10 → score 75（貪婪/極度貪婪 邊界）
]
VIX_SCORE_FLOOR = 0  # VIX ≥ VIX_SCORE_FLOOR_VIX → score 0
VIX_SCORE_CEILING = 100  # VIX ≤ VIX_SCORE_CEILING_VIX → score 100
VIX_SCORE_FLOOR_VIX = 40  # 恐懼分數地板對應的 VIX 值
VIX_SCORE_CEILING_VIX = 8  # 貪婪分數天花板對應的 VIX 值

# CNN Fear & Greed Index 閾值（0–100 分）
CNN_FG_EXTREME_FEAR = 25  # 0–25 → 極度恐懼
CNN_FG_FEAR = 45  # 25–45 → 恐懼
CNN_FG_NEUTRAL_HIGH = 55  # 45–55 → 中性
CNN_FG_GREED = 75  # 55–75 → 貪婪
# 75–100 → 極度貪婪

CNN_FG_API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_FG_REQUEST_TIMEOUT = 10  # seconds

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
DISK_KEY_ROGUE_WAVE = "rogue_wave"

# ---------------------------------------------------------------------------
# Webhook Messages (use t("webhook.missing_ticker") at call sites)
# ---------------------------------------------------------------------------
WEBHOOK_MISSING_TICKER = "webhook.missing_ticker"  # i18n key

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
    "guru_sync": {
        "description": "Trigger 13F filing sync for all tracked gurus (EDGAR fetch)",
        "requires_ticker": False,
    },
    "guru_summary": {
        "description": "Send latest guru holding changes digest via Telegram",
        "requires_ticker": False,
    },
}

# ---------------------------------------------------------------------------
# Notification Preferences — toggleable notification types
# ---------------------------------------------------------------------------
NOTIFICATION_TYPES = {
    "scan_alerts": "constants.notification_scan_alerts",
    "price_alerts": "constants.notification_price_alerts",
    "weekly_digest": "constants.notification_weekly_digest",
    "xray_alerts": "constants.notification_xray_alerts",
    "fx_alerts": "constants.notification_fx_alerts",
    "fx_watch_alerts": "constants.notification_fx_watch_alerts",
    "guru_alerts": "constants.notification_guru_alerts",
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
ERROR_INVALID_INPUT = "INVALID_INPUT"
ERROR_INTERNAL_ERROR = "INTERNAL_ERROR"

# ---------------------------------------------------------------------------
# Generic Error Messages — i18n keys, resolve with t() at call sites
# ---------------------------------------------------------------------------
GENERIC_ERROR_MESSAGE = "constants.generic_error"
GENERIC_VALIDATION_ERROR = "constants.generic_validation_error"
GENERIC_TELEGRAM_ERROR = "constants.generic_telegram_error"
GENERIC_PREFERENCES_ERROR = "constants.generic_preferences_error"
GENERIC_WEBHOOK_ERROR = "constants.generic_webhook_error"

# ---------------------------------------------------------------------------
# curl_cffi
# ---------------------------------------------------------------------------
CURL_CFFI_IMPERSONATE = "chrome"

# ---------------------------------------------------------------------------
# Rogue Wave (瘋狗浪) — Historical Bias Percentile Alert
# ---------------------------------------------------------------------------
ROGUE_WAVE_HISTORY_PERIOD = "3y"
ROGUE_WAVE_MIN_HISTORY_DAYS = 200
ROGUE_WAVE_BIAS_PERCENTILE = 95  # 95th percentile = extreme overheating
ROGUE_WAVE_VOLUME_RATIO_THRESHOLD = 1.5  # 50% above normal volume
VOLUME_SURGE_THRESHOLD = 1.5  # volume confidence qualifier: surge
VOLUME_THIN_THRESHOLD = 0.5  # volume confidence qualifier: thin volume

ROGUE_WAVE_CACHE_MAXSIZE = 200
ROGUE_WAVE_CACHE_TTL = 86400  # L1: 24 hours
DISK_ROGUE_WAVE_TTL = 172800  # L2: 48 hours

# ---------------------------------------------------------------------------
# Retry Configuration (yfinance transient network failures)
# ---------------------------------------------------------------------------
YFINANCE_RETRY_ATTEMPTS = 3
YFINANCE_RETRY_WAIT_MIN = 2  # seconds (exponential backoff minimum)
YFINANCE_RETRY_WAIT_MAX = 10  # seconds (exponential backoff maximum)

# ---------------------------------------------------------------------------
# Beta Cache Configuration (Stress Test)
# ---------------------------------------------------------------------------
BETA_CACHE_MAXSIZE = 200
BETA_CACHE_TTL = 86400  # 24 hours (L1)
DISK_BETA_TTL = 604800  # 7 days (L2)
DISK_KEY_BETA = "beta"

# Category Fallback Beta (when yfinance returns None)
CATEGORY_FALLBACK_BETA: dict[str, float] = {
    "Trend_Setter": 1.0,
    "Moat": 1.2,
    "Growth": 1.5,
    "Bond": 0.3,
    "Cash": 0.0,
}

# ---------------------------------------------------------------------------
# Stress Test Pain Levels
# ---------------------------------------------------------------------------
# threshold 表示該等級的最低損失門檻（含）
# loss_pct < 10% → low, 10% <= loss < 20% → moderate, 20% <= loss < 30% → high, loss >= 30% → panic
STRESS_PAIN_LEVELS = [
    {
        "threshold": 0,
        "level": "low",
        "label": "constants.stress_pain_low",
        "emoji": "green",
    },
    {
        "threshold": 10,
        "level": "moderate",
        "label": "constants.stress_pain_moderate",
        "emoji": "yellow",
    },
    {
        "threshold": 20,
        "level": "high",
        "label": "constants.stress_pain_high",
        "emoji": "orange",
    },
    {
        "threshold": 30,
        "level": "panic",
        "label": "constants.stress_pain_panic",
        "emoji": "red",
    },
]

STRESS_DISCLAIMER = "constants.stress_disclaimer"  # i18n key
STRESS_EMPTY_PAIN_LABEL = "stress_test.no_holdings"  # i18n key (when no holdings)

# ---------------------------------------------------------------------------
# Smart Money Tracker (大師足跡追蹤)
# ---------------------------------------------------------------------------
GURU_HOLDING_CHANGE_THRESHOLD_PCT = 20.0  # +/-20% = significant change
GURU_TOP_HOLDINGS_COUNT = 10
GURU_HOLDING_CHANGES_DISPLAY_LIMIT = 20  # default limit for per-guru holding changes
GURU_FILING_DEADLINES = ["02-14", "05-15", "08-14", "11-14"]
SEC_EDGAR_BASE_URL = "https://data.sec.gov"
SEC_EDGAR_ARCHIVES_BASE_URL = "https://www.sec.gov"
# TODO(Phase 2): override with env var SEC_EDGAR_USER_AGENT in sec_edgar.py;
# SEC policy requires a real contact email in the User-Agent header.
SEC_EDGAR_USER_AGENT = "Folio/1.0 (folio@example.com)"
SEC_EDGAR_RATE_LIMIT_CPS = 10.0  # SEC allows 10 req/sec
SEC_EDGAR_REQUEST_TIMEOUT = 15

# Default Gurus (CIK codes)
DEFAULT_GURUS = [
    {
        "name": "Berkshire Hathaway Inc",
        "cik": "0001067983",
        "display_name": "Warren Buffett",
    },
    {
        "name": "Bridgewater Associates, LP",
        "cik": "0001350694",
        "display_name": "Ray Dalio",
    },
    {
        "name": "Oaktree Capital Management, L.P.",
        "cik": "0001535581",
        "display_name": "Howard Marks",
    },
    {
        "name": "ARK Investment Management LLC",
        "cik": "0001603466",
        "display_name": "Cathie Wood",
    },
    {
        "name": "Pershing Square Capital Management",
        "cik": "0001336528",
        "display_name": "Bill Ackman",
    },
    {
        "name": "Scion Asset Management, LLC",
        "cik": "0001649339",
        "display_name": "Michael Burry",
    },
]

# Notification
NOTIFICATION_TYPE_GURU_ALERTS = "guru_alerts"

GURU_BACKFILL_YEARS = 5  # 回填歷史 13F 資料的年數
GURU_BACKFILL_FILING_COUNT = 20  # 每位大師最多取回 20 筆申報（約 5 年）

# Cache
GURU_FILING_CACHE_MAXSIZE = 50
GURU_FILING_CACHE_TTL = 86400  # 24h (13F data is quarterly)
DISK_GURU_FILING_TTL = 604800  # 7 days
DISK_KEY_GURU_FILING = "guru_filing"
DISK_SECTOR_TTL = 2592000  # 30 days (sectors change very rarely)
DISK_KEY_SECTOR = "sector"

# ---------------------------------------------------------------------------
# Equity Categories (used by sector exposure, X-Ray, etc.)
# ---------------------------------------------------------------------------
EQUITY_CATEGORIES: frozenset[str] = frozenset({"Trend_Setter", "Moat", "Growth"})
