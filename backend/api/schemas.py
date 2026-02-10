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
