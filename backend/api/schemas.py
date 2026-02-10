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


# ---------------------------------------------------------------------------
# Response Schemas
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


class ProfileUpdateRequest(BaseModel):
    """PUT /profiles/{id} 請求 Body。"""

    name: Optional[str] = None
    config: Optional[dict[str, float]] = None


class ProfileResponse(BaseModel):
    """GET /profiles 回傳的投資組合配置。"""

    id: int
    user_id: str
    name: str
    source_template_id: Optional[str] = None
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
# Webhook Schemas (for OpenClaw / AI agent)
# ---------------------------------------------------------------------------


class WebhookRequest(BaseModel):
    """POST /webhook 請求 Body — 統一入口供 AI agent 使用。"""

    action: str  # "summary", "signals", "scan", "moat", "alerts", "add_stock"
    ticker: str | None = None
    params: dict = {}


class WebhookResponse(BaseModel):
    """POST /webhook 回傳結構。"""

    success: bool
    message: str
    data: dict = {}
