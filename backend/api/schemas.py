"""
API — Pydantic Request / Response Schemas。
僅用於 HTTP 層的資料驗證與序列化，不含業務邏輯。
"""

from typing import Optional

from pydantic import BaseModel

from domain.enums import StockCategory


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class TickerCreateRequest(BaseModel):
    """POST /ticker 請求 Body。"""

    ticker: str
    category: StockCategory
    thesis: str
    tags: list[str] = []


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

    ticker: str
    category: str
    thesis: str = ""
    tags: list[str] = []


class HoldingImportItem(BaseModel):
    """POST /holdings/import 單筆匯入資料。"""

    ticker: str
    category: str
    quantity: float
    cost_basis: Optional[float] = None
    broker: Optional[str] = None
    currency: str = "USD"
    account_type: Optional[str] = None
    is_cash: bool = False


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
    is_active: bool
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


class ScanResponse(BaseModel):
    """POST /scan 完整回傳結構（含整體市場情緒）。"""

    market_status: dict
    results: list[ScanResult]


class SignalsResponse(BaseModel):
    """GET /ticker/{ticker}/signals 技術訊號回應。"""

    ticker: Optional[str] = None
    price: Optional[float] = None
    rsi: Optional[float] = None
    ma200: Optional[float] = None
    ma60: Optional[float] = None
    bias: Optional[float] = None
    volume_ratio: Optional[float] = None
    status: list[str] = []
    error: Optional[str] = None


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
    current_price: Optional[float] = None


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
    risk_level: str  # "low" / "medium" / "high"
    advice: list[str]
    calculated_at: str = ""


class FXAlertResponse(BaseModel):
    """POST /currency-exposure/alert 回應。"""

    message: str
    alerts: list[str] = []


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

    privacy_mode: bool
    notification_preferences: Optional[dict[str, bool]] = None


class PreferencesResponse(BaseModel):
    """GET /settings/preferences 回應。"""

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
