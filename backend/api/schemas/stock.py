"""
API — Stock / Ticker / Thesis / Import Schemas。
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

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


class ThesisLogResponse(BaseModel):
    """觀點歷史單一紀錄。"""

    version: int
    content: str
    tags: list[str] = []
    created_at: str


class StockExportItem(BaseModel):
    """匯出觀察名單單一紀錄。"""

    ticker: str
    category: str
    thesis: str = ""
    tags: list[str] = []
    is_etf: bool = False
