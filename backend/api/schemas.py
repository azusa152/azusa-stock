"""
API — Pydantic Request / Response Schemas。
僅用於 HTTP 層的資料驗證與序列化，不含業務邏輯。
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from domain.constants import (
    FX_WATCH_DEFAULT_ALERT_ON_CONSECUTIVE,
    FX_WATCH_DEFAULT_ALERT_ON_RECENT_HIGH,
    FX_WATCH_DEFAULT_CONSECUTIVE_DAYS,
    FX_WATCH_DEFAULT_RECENT_HIGH_DAYS,
    FX_WATCH_DEFAULT_REMINDER_HOURS,
)
from domain.enums import ScanSignal, StockCategory


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class TickerCreateRequest(BaseModel):
    """POST /ticker 請求 Body。"""

    ticker: str
    category: StockCategory
    thesis: str
    tags: list[str] = []
    is_etf: Optional[bool] = None


class ThesisCreateRequest(BaseModel):
    """POST /ticker/{ticker}/thesis 請求 Body。"""

    content: str
    tags: list[str] = []


class CategoryUpdateRequest(BaseModel):
    """PATCH /ticker/{ticker}/category 請求 Body。"""

    category: StockCategory


class DeactivateRequest(BaseModel):
    """POST /ticker/{ticker}/deactivate 請求 Body。"""

    reason: str


class ReorderRequest(BaseModel):
    """PUT /stocks/reorder 請求 Body。"""

    ordered_tickers: list[str]


class ReactivateRequest(BaseModel):
    """POST /ticker/{ticker}/reactivate 請求 Body。"""

    category: StockCategory | None = None
    thesis: str | None = None


class PriceAlertCreateRequest(BaseModel):
    """POST /ticker/{ticker}/alerts 請求 Body。"""

    metric: str = "rsi"
    operator: str = "lt"
    threshold: float = 30.0


class StockImportItem(BaseModel):
    """POST /stocks/import 單筆匯入資料。"""

    ticker: str = Field(..., min_length=1, max_length=20)
    category: str = Field(..., min_length=1, max_length=50)
    thesis: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    is_etf: Optional[bool] = None

    @field_validator("ticker")
    @classmethod
    def ticker_must_be_uppercase(cls, v: str) -> str:
        """Ticker must be uppercase."""
        return v.upper().strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Each tag must be non-empty and under 50 chars."""
        for tag in v:
            if not tag or len(tag) > 50:
                raise ValueError("Each tag must be non-empty and ≤50 chars")
        return v


class HoldingImportItem(BaseModel):
    """POST /holdings/import 單筆匯入資料。"""

    ticker: str = Field(..., min_length=1, max_length=20)
    category: str = Field(..., min_length=1, max_length=50)
    quantity: float = Field(..., gt=0)
    cost_basis: Optional[float] = Field(default=None, ge=0)
    broker: Optional[str] = Field(default=None, max_length=100)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    account_type: Optional[str] = Field(default=None, max_length=100)
    is_cash: bool = False

    @field_validator("ticker")
    @classmethod
    def ticker_must_be_uppercase(cls, v: str) -> str:
        """Ticker must be uppercase."""
        return v.upper().strip()

    @field_validator("currency")
    @classmethod
    def currency_must_be_uppercase(cls, v: str) -> str:
        """Currency must be uppercase."""
        return v.upper().strip()


# ---------------------------------------------------------------------------
# Response Schemas — Generic
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    """通用操作結果回應（刪除、停用、重新啟用、匯入等）。"""

    message: str


class ImportResponse(BaseModel):
    """匯入操作回應。"""

    message: str
    imported: int
    errors: list[str] = []


class HealthResponse(BaseModel):
    """GET /health 回應。"""

    status: str
    service: str


# ---------------------------------------------------------------------------
# Response Schemas — Stock
# ---------------------------------------------------------------------------


class StockResponse(BaseModel):
    """GET /stocks 回傳的單筆股票資料。"""

    ticker: str
    category: StockCategory
    current_thesis: str
    current_tags: list[str] = []
    display_order: int = 0
    last_scan_signal: ScanSignal = ScanSignal.NORMAL
    is_active: bool
    is_etf: bool = False
    signals: Optional[dict] = None


class RemovedStockResponse(BaseModel):
    """GET /stocks/removed 回傳的單筆已移除股票資料。"""

    ticker: str
    category: StockCategory
    current_thesis: str
    removal_reason: str
    removed_at: Optional[str] = None


class ScanResult(BaseModel):
    """POST /scan 回傳的掃描結果（V2 三層漏斗）。"""

    ticker: str
    category: StockCategory
    signal: str
    alerts: list[str]
    moat: Optional[str] = None
    bias: Optional[float] = None
    volume_ratio: Optional[float] = None
    market_status: Optional[str] = None
    bias_percentile: Optional[float] = None
    is_rogue_wave: bool = False


class ScanResponse(BaseModel):
    """POST /scan 完整回傳結構（含整體市場情緒）。"""

    market_status: dict
    results: list[ScanResult]


class SignalsResponse(BaseModel):
    """GET /ticker/{ticker}/signals 技術訊號回應。"""

    ticker: Optional[str] = None
    price: Optional[float] = None
    previous_close: Optional[float] = None
    change_pct: Optional[float] = None
    rsi: Optional[float] = None
    ma200: Optional[float] = None
    ma60: Optional[float] = None
    bias: Optional[float] = None
    volume_ratio: Optional[float] = None
    status: list[str] = []
    error: Optional[str] = None
    bias_percentile: Optional[float] = None
    is_rogue_wave: bool = False


class PriceHistoryPoint(BaseModel):
    """價格歷史單一資料點。"""

    date: str
    close: float


class MoatResponse(BaseModel):
    """GET /ticker/{ticker}/moat 護城河分析回應。"""

    ticker: str = ""
    moat: Optional[str] = None
    details: Optional[str] = None
    margins: list[dict] = []
    yoy_change: Optional[float] = None


class EarningsResponse(BaseModel):
    """GET /ticker/{ticker}/earnings 財報日曆回應。"""

    ticker: str = ""
    next_earnings_date: Optional[str] = None
    days_until: Optional[int] = None
    error: Optional[str] = None


class DividendResponse(BaseModel):
    """GET /ticker/{ticker}/dividend 股息資訊回應。"""

    ticker: str = ""
    dividend_yield: Optional[float] = None
    ex_date: Optional[str] = None
    ytd_dividend_per_share: Optional[float] = None
    error: Optional[str] = None


class PriceAlertResponse(BaseModel):
    """價格警報回應。"""

    id: int
    ticker: str
    metric: str
    operator: str
    threshold: float
    is_active: bool


class LastScanResponse(BaseModel):
    """GET /scan/last 回應。"""

    last_scanned_at: Optional[str] = None
    epoch: Optional[int] = None
    market_status: Optional[str] = None
    market_status_details: Optional[str] = None
    fear_greed_level: Optional[str] = None
    fear_greed_score: Optional[int] = None


class AcceptedResponse(BaseModel):
    """非同步操作已接受回應。"""

    status: str = "accepted"
    message: str


class ScanStatusResponse(BaseModel):
    """GET /scan/status 回應。"""

    is_running: bool


class ThesisLogResponse(BaseModel):
    """觀點歷史單一紀錄。"""

    version: int
    content: str
    tags: list[str] = []
    created_at: str


class ScanLogResponse(BaseModel):
    """掃描歷史單一紀錄。"""

    ticker: str
    signal: str
    alerts: list[str] = []
    scanned_at: str


class StockExportItem(BaseModel):
    """匯出觀察名單單一紀錄。"""

    ticker: str
    category: str
    thesis: str = ""
    tags: list[str] = []
    is_etf: bool = False


class HoldingExportItem(BaseModel):
    """匯出持倉單一紀錄。"""

    ticker: str
    category: str
    quantity: float
    cost_basis: Optional[float] = None
    broker: Optional[str] = None
    currency: str = "USD"
    account_type: Optional[str] = None
    is_cash: bool = False


class XRayAlertResponse(BaseModel):
    """POST /rebalance/xray-alert 回應。"""

    message: str
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# Persona / Profile Schemas
# ---------------------------------------------------------------------------


class PersonaTemplateResponse(BaseModel):
    """GET /personas/templates 回傳的單一範本。"""

    id: str
    name: str
    description: str
    quote: str
    is_empty: bool
    default_config: dict


class ProfileCreateRequest(BaseModel):
    """POST /profiles 請求 Body。"""

    name: str = ""
    source_template_id: Optional[str] = None
    config: dict[str, float]  # {"Bond": 50, "Trend_Setter": 30, ...}
    home_currency: str = "TWD"


class ProfileUpdateRequest(BaseModel):
    """PUT /profiles/{id} 請求 Body。"""

    name: Optional[str] = None
    config: Optional[dict[str, float]] = None
    home_currency: Optional[str] = None


class ProfileResponse(BaseModel):
    """GET /profiles 回傳的投資組合配置。"""

    id: int
    user_id: str
    name: str
    source_template_id: Optional[str] = None
    home_currency: str = "TWD"
    config: dict
    is_active: bool
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Holdings Schemas
# ---------------------------------------------------------------------------


class HoldingRequest(BaseModel):
    """POST /holdings 請求 Body。"""

    ticker: str
    category: StockCategory
    quantity: float
    cost_basis: Optional[float] = None
    broker: Optional[str] = None
    currency: str = "USD"
    account_type: Optional[str] = None
    is_cash: bool = False


class CashHoldingRequest(BaseModel):
    """POST /holdings/cash 請求 Body。"""

    currency: str  # e.g. "USD", "TWD"
    amount: float
    broker: Optional[str] = None
    account_type: Optional[str] = None


class HoldingResponse(BaseModel):
    """GET /holdings 回傳的單一持倉。"""

    id: int
    ticker: str
    category: StockCategory
    quantity: float
    cost_basis: Optional[float] = None
    broker: Optional[str] = None
    currency: str = "USD"
    account_type: Optional[str] = None
    is_cash: bool
    updated_at: str


class CategoryAllocation(BaseModel):
    """單一分類的配置分析。"""

    target_pct: float
    current_pct: float
    drift_pct: float
    market_value: float


class HoldingDetail(BaseModel):
    """再平衡分析中的個股明細（同 ticker 跨券商合併）。"""

    ticker: str
    category: str
    currency: str = "USD"
    quantity: float
    market_value: float
    weight_pct: float
    avg_cost: Optional[float] = None
    cost_total: Optional[float] = (
        None  # avg_cost * quantity * fx，以 display_currency 計
    )
    current_price: Optional[float] = None
    change_pct: Optional[float] = None


class XRayEntry(BaseModel):
    """X-Ray: 單一標的真實曝險（直接持倉 + ETF 間接曝險）。"""

    symbol: str
    name: str = ""
    direct_value: float = 0.0
    direct_weight_pct: float = 0.0
    indirect_value: float = 0.0
    indirect_weight_pct: float = 0.0
    total_value: float = 0.0
    total_weight_pct: float = 0.0
    indirect_sources: list[str] = []  # e.g. ["VTI (5.2%)", "QQQ (8.1%)"]


class RebalanceResponse(BaseModel):
    """GET /rebalance 回傳的再平衡分析。"""

    total_value: float
    previous_total_value: Optional[float] = None
    total_value_change: Optional[float] = None
    total_value_change_pct: Optional[float] = None
    display_currency: str = "USD"
    categories: dict[str, CategoryAllocation]
    advice: list[str]
    holdings_detail: list[HoldingDetail] = []
    xray: list[XRayEntry] = []
    calculated_at: str = ""


# ---------------------------------------------------------------------------
# Currency Exposure Schemas
# ---------------------------------------------------------------------------


class CurrencyBreakdown(BaseModel):
    """幣別曝險分析：單一幣別的持倉分佈。"""

    currency: str
    value: float  # 以本幣計算的市值
    percentage: float  # 佔總投資組合的百分比
    is_home: bool


class FXMovement(BaseModel):
    """近期匯率變動。"""

    pair: str  # e.g. "USD/TWD"
    current_rate: float
    change_pct: float  # 期間內百分比變動
    direction: str  # "up" / "down" / "flat"


class FXRateAlertItem(BaseModel):
    """匯率變動警報項目（三層級偵測）。"""

    pair: str  # e.g. "USD/TWD"
    alert_type: str  # "daily_spike" / "short_term_swing" / "long_term_trend"
    change_pct: float  # signed percentage change
    direction: str  # "up" / "down"
    current_rate: float
    period_label: str  # "1 日" / "5 日" / "3 個月"


class CurrencyExposureResponse(BaseModel):
    """GET /currency-exposure 回傳的匯率曝險分析。"""

    home_currency: str
    total_value_home: float
    breakdown: list[CurrencyBreakdown]
    non_home_pct: float
    cash_breakdown: list[CurrencyBreakdown] = []
    cash_non_home_pct: float = 0.0
    total_cash_home: float = 0.0
    fx_movements: list[FXMovement]
    fx_rate_alerts: list[FXRateAlertItem] = []
    risk_level: str  # "low" / "medium" / "high"
    advice: list[str]
    calculated_at: str = ""


class FXAlertResponse(BaseModel):
    """POST /currency-exposure/alert 回應。"""

    message: str
    alerts: list[str] = []


# ---------------------------------------------------------------------------
# Smart Withdrawal Schemas (聰明提款機)
# ---------------------------------------------------------------------------


class WithdrawRequest(BaseModel):
    """POST /withdraw 請求 Body。"""

    target_amount: float
    display_currency: str = "USD"
    notify: bool = True


class SellRecommendationResponse(BaseModel):
    """單筆賣出建議。"""

    ticker: str
    category: str
    quantity_to_sell: float
    sell_value: float
    reason: str
    unrealized_pl: Optional[float] = None
    priority: int  # 1=再平衡, 2=節稅, 3=流動性


class WithdrawResponse(BaseModel):
    """POST /withdraw 回傳的提款計劃。"""

    recommendations: list[SellRecommendationResponse] = []
    total_sell_value: float = 0.0
    target_amount: float = 0.0
    shortfall: float = 0.0
    post_sell_drifts: dict[str, dict] = {}
    message: str = ""


# ---------------------------------------------------------------------------
# Fear & Greed Index Schemas
# ---------------------------------------------------------------------------


class VIXData(BaseModel):
    """VIX 指數資料。"""

    value: Optional[float] = None
    change_1d: Optional[float] = None
    level: str = "N/A"
    fetched_at: str = ""


class CNNFearGreedData(BaseModel):
    """CNN Fear & Greed Index 資料。"""

    score: Optional[int] = None
    label: str = ""
    level: str = "N/A"
    fetched_at: str = ""


class FearGreedResponse(BaseModel):
    """GET /market/fear-greed 回傳的恐懼與貪婪指數綜合分析。"""

    composite_score: int = 50
    composite_level: str = "N/A"
    composite_label: str = ""
    vix: Optional[VIXData] = None
    cnn: Optional[CNNFearGreedData] = None
    fetched_at: str = ""


# ---------------------------------------------------------------------------
# Telegram Settings Schemas
# ---------------------------------------------------------------------------


class TelegramSettingsRequest(BaseModel):
    """PUT /settings/telegram 請求 Body。"""

    telegram_chat_id: str = ""
    custom_bot_token: Optional[str] = None
    use_custom_bot: bool = False


class TelegramSettingsResponse(BaseModel):
    """GET /settings/telegram 回傳結構（token 遮蔽）。"""

    telegram_chat_id: str
    custom_bot_token_masked: str  # e.g. "123***xyz"
    use_custom_bot: bool


# ---------------------------------------------------------------------------
# User Preferences Schemas
# ---------------------------------------------------------------------------


class PreferencesRequest(BaseModel):
    """PUT /settings/preferences 請求 Body。"""

    language: Optional[str] = None
    privacy_mode: bool
    notification_preferences: Optional[dict[str, bool]] = None


class PreferencesResponse(BaseModel):
    """GET /settings/preferences 回應。"""

    language: str
    privacy_mode: bool
    notification_preferences: dict[str, bool]


# ---------------------------------------------------------------------------
# Webhook Schemas (for OpenClaw / AI agent)
# ---------------------------------------------------------------------------


class WebhookRequest(BaseModel):
    """POST /webhook 請求 Body — 統一入口供 AI agent 使用。"""

    action: str  # "help", "summary", "signals", "scan", "moat", "alerts", "add_stock"
    ticker: str | None = None
    params: dict = {}


class WebhookResponse(BaseModel):
    """POST /webhook 回傳結構。"""

    success: bool
    message: str
    data: dict = {}


# ---------------------------------------------------------------------------
# FX Watch Schemas
# ---------------------------------------------------------------------------


class FXWatchCreateRequest(BaseModel):
    """POST /fx-watch 請求 Body：新增外匯監控配置。"""

    base_currency: str
    quote_currency: str
    recent_high_days: int = FX_WATCH_DEFAULT_RECENT_HIGH_DAYS
    consecutive_increase_days: int = FX_WATCH_DEFAULT_CONSECUTIVE_DAYS
    alert_on_recent_high: bool = FX_WATCH_DEFAULT_ALERT_ON_RECENT_HIGH
    alert_on_consecutive_increase: bool = FX_WATCH_DEFAULT_ALERT_ON_CONSECUTIVE
    reminder_interval_hours: int = FX_WATCH_DEFAULT_REMINDER_HOURS


class FXWatchUpdateRequest(BaseModel):
    """PATCH /fx-watch/{id} 請求 Body：更新外匯監控配置。"""

    recent_high_days: Optional[int] = None
    consecutive_increase_days: Optional[int] = None
    alert_on_recent_high: Optional[bool] = None
    alert_on_consecutive_increase: Optional[bool] = None
    reminder_interval_hours: Optional[int] = None
    is_active: Optional[bool] = None


class FXWatchResponse(BaseModel):
    """GET /fx-watch 回傳單筆配置。"""

    id: int
    user_id: str
    base_currency: str
    quote_currency: str
    recent_high_days: int
    consecutive_increase_days: int
    alert_on_recent_high: bool
    alert_on_consecutive_increase: bool
    reminder_interval_hours: int
    is_active: bool
    last_alerted_at: Optional[str] = None
    created_at: str
    updated_at: str


class FXTimingResultResponse(BaseModel):
    """換匯時機分析結果。"""

    base_currency: str
    quote_currency: str
    current_rate: float
    is_recent_high: bool
    lookback_high: float
    lookback_days: int
    consecutive_increases: int
    consecutive_threshold: int
    alert_on_recent_high: bool
    alert_on_consecutive_increase: bool
    should_alert: bool
    recommendation_zh: str
    reasoning_zh: str


class FXWatchCheckResultItem(BaseModel):
    """單筆外匯監控分析結果。"""

    watch_id: int
    pair: str
    result: FXTimingResultResponse


class FXWatchCheckResponse(BaseModel):
    """POST /fx-watch/check 回傳結構：分析結果（不發送通知）。"""

    total_watches: int
    results: list[FXWatchCheckResultItem]


class FXWatchAlertResponse(BaseModel):
    """POST /fx-watch/alert 回傳結構：警報發送結果。"""

    total_watches: int
    triggered_alerts: int
    sent_alerts: int
    alerts: list[FXWatchCheckResultItem]


# ---------------------------------------------------------------------------
# Smart Money Schemas (大師足跡追踪)
# ---------------------------------------------------------------------------


class GuruCreate(BaseModel):
    """POST /gurus 請求 Body。"""

    name: str = Field(..., min_length=1, max_length=200)
    cik: str = Field(..., min_length=1, max_length=20, description="SEC CIK 代碼")
    display_name: str = Field(..., min_length=1, max_length=100)


class GuruResponse(BaseModel):
    """GET /gurus 回傳的單一大師資料。"""

    id: int
    name: str
    cik: str
    display_name: str
    is_active: bool
    is_default: bool


class GuruFilingResponse(BaseModel):
    """GET /gurus/{guru_id}/filing 回傳的最新申報摘要。"""

    guru_id: int
    guru_display_name: str
    report_date: Optional[str] = None
    filing_date: Optional[str] = None
    total_value: Optional[float] = None
    holdings_count: int = 0
    filing_url: str = ""
    new_positions: int = 0
    sold_out: int = 0
    increased: int = 0
    decreased: int = 0
    top_holdings: list[dict] = []


class GuruHoldingResponse(BaseModel):
    """GET /gurus/{guru_id}/holdings 回傳的單一持倉記錄。"""

    guru_id: int
    cusip: str
    ticker: Optional[str] = None
    company_name: str
    value: float
    shares: float
    action: str
    change_pct: Optional[float] = None
    weight_pct: Optional[float] = None
    report_date: Optional[str] = None
    filing_date: Optional[str] = None


class SyncResponse(BaseModel):
    """POST /gurus/{guru_id}/sync 回傳的同步結果。"""

    status: str
    guru_id: Optional[int] = None
    message: str = ""
    new_positions: int = 0
    sold_out: int = 0
    increased: int = 0
    decreased: int = 0


class SyncAllResponse(BaseModel):
    """POST /gurus/sync 回傳的全大師同步結果。"""

    synced: int
    skipped: int
    errors: int
    results: list[SyncResponse] = []


class ResonanceEntryResponse(BaseModel):
    """GET /resonance 回傳的單一大師共鳴記錄。"""

    guru_id: int
    guru_display_name: str
    overlapping_tickers: list[str] = []
    overlap_count: int
    holdings: list[dict] = []


class ResonanceResponse(BaseModel):
    """GET /resonance 完整回應。"""

    results: list[ResonanceEntryResponse]
    total_gurus: int
    gurus_with_overlap: int


class ResonanceTickerResponse(BaseModel):
    """GET /resonance/{ticker} 回傳的大師共鳴資料。"""

    ticker: str
    gurus: list[dict] = []
    guru_count: int = 0


class GreatMindsEntryResponse(BaseModel):
    """英雄所見略同清單單筆資料。"""

    ticker: str
    guru_count: int
    gurus: list[dict] = []


class GreatMindsResponse(BaseModel):
    """GET /resonance/great-minds 完整回應。"""

    stocks: list[GreatMindsEntryResponse]
    total_count: int


# ---------------------------------------------------------------------------
# Dashboard Schemas (大師儀表板聚合)
# ---------------------------------------------------------------------------


class GuruSummaryItem(BaseModel):
    """GET /gurus/dashboard 中單一大師的摘要卡片。"""

    id: int
    display_name: str
    latest_report_date: Optional[str] = None
    latest_filing_date: Optional[str] = None
    total_value: Optional[float] = None
    holdings_count: int = 0
    filing_count: int = 0


class SeasonHighlightItem(BaseModel):
    """本季重點變動（新建倉或清倉）的單筆記錄。"""

    ticker: Optional[str] = None
    company_name: str = ""
    guru_id: int
    guru_display_name: str
    value: float = 0.0
    weight_pct: Optional[float] = None
    change_pct: Optional[float] = None


class SeasonHighlights(BaseModel):
    """本季新建倉與清倉彙總。"""

    new_positions: list[SeasonHighlightItem] = []
    sold_outs: list[SeasonHighlightItem] = []


class ConsensusStockItem(BaseModel):
    """被多位大師同時持有的共識股票。"""

    ticker: str
    guru_count: int
    gurus: list[str] = []
    total_value: float = 0.0


class SectorBreakdownItem(BaseModel):
    """依行業板塊彙總的持倉分佈單筆。"""

    sector: str
    total_value: float
    holding_count: int
    weight_pct: float


class DashboardResponse(BaseModel):
    """GET /gurus/dashboard 完整回應。"""

    gurus: list[GuruSummaryItem] = []
    season_highlights: SeasonHighlights = SeasonHighlights()
    consensus: list[ConsensusStockItem] = []
    sector_breakdown: list[SectorBreakdownItem] = []


class FilingHistoryItem(BaseModel):
    """GET /gurus/{guru_id}/filings 中的單筆申報摘要。"""

    id: int
    report_date: str
    filing_date: str
    total_value: Optional[float] = None
    holdings_count: int = 0
    filing_url: str = ""


class FilingHistoryResponse(BaseModel):
    """GET /gurus/{guru_id}/filings 完整回應。"""

    filings: list[FilingHistoryItem] = []


# ---------------------------------------------------------------------------
# Portfolio Snapshot Schemas
# ---------------------------------------------------------------------------


class SnapshotResponse(BaseModel):
    """GET /snapshots 回傳的單日投資組合快照。"""

    snapshot_date: str  # ISO date string, e.g. "2025-02-19"
    total_value: float
    category_values: dict  # parsed from JSON storage
    display_currency: str = "USD"
    benchmark_value: Optional[float] = None


class TwrResponse(BaseModel):
    """GET /snapshots/twr 回傳的時間加權報酬率。"""

    twr_pct: Optional[float]  # 百分比，例如 12.3 代表 +12.3%；None 表示資料不足
    start_date: Optional[str] = None  # 計算起始日（快照中最早一筆）
    end_date: Optional[str] = None  # 計算結束日（快照中最新一筆）
    snapshot_count: int = 0  # 用於計算的快照筆數


# ---------------------------------------------------------------------------
# Stress Test Schemas
# ---------------------------------------------------------------------------


class StressTestHoldingBreakdown(BaseModel):
    """壓力測試：單檔持倉損失細項。"""

    ticker: str
    category: str
    beta: float
    market_value: float
    expected_drop_pct: float
    expected_loss: float


class StressTestPainLevel(BaseModel):
    """壓力測試：痛苦等級分類。"""

    level: str
    label: str
    emoji: str


class StressTestResponse(BaseModel):
    """GET /stress-test 回傳結構：組合壓力測試結果。"""

    portfolio_beta: float
    scenario_drop_pct: float
    total_value: float
    total_loss: float
    total_loss_pct: float
    display_currency: str
    pain_level: StressTestPainLevel
    advice: list[str]
    disclaimer: str
    holdings_breakdown: list[StressTestHoldingBreakdown]
