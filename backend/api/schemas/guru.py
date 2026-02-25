"""
API — Guru / Resonance / Dashboard / Filing Schemas。
"""

from typing import Literal

from pydantic import BaseModel, Field

GuruStyleLiteral = Literal[
    "VALUE", "GROWTH", "MACRO", "QUANT", "ACTIVIST", "MULTI_STRATEGY"
]
GuruTierLiteral = Literal["TIER_1", "TIER_2", "TIER_3"]

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class GuruCreate(BaseModel):
    """POST /gurus 請求 Body。"""

    name: str = Field(..., min_length=1, max_length=200)
    cik: str = Field(..., min_length=1, max_length=20, description="SEC CIK 代碼")
    display_name: str = Field(..., min_length=1, max_length=100)
    style: GuruStyleLiteral | None = Field(default=None, description="投資風格")
    tier: GuruTierLiteral | None = Field(default=None, description="等級排名")


# ---------------------------------------------------------------------------
# Response Schemas — Guru / Smart Money
# ---------------------------------------------------------------------------


class GuruResponse(BaseModel):
    """GET /gurus 回傳的單一大師資料。"""

    id: int
    name: str
    cik: str
    display_name: str
    is_active: bool
    is_default: bool
    style: str | None = None
    tier: str | None = None


class GuruFilingResponse(BaseModel):
    """GET /gurus/{guru_id}/filing 回傳的最新申報摘要。"""

    guru_id: int
    guru_display_name: str
    report_date: str | None = None
    filing_date: str | None = None
    total_value: float | None = None
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
    ticker: str | None = None
    company_name: str
    value: float
    shares: float
    action: str
    change_pct: float | None = None
    weight_pct: float | None = None
    report_date: str | None = None
    filing_date: str | None = None


class SyncResponse(BaseModel):
    """POST /gurus/{guru_id}/sync 回傳的同步結果。"""

    status: str
    guru_id: int | None = None
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


# ---------------------------------------------------------------------------
# Response Schemas — Resonance
# ---------------------------------------------------------------------------


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
# Response Schemas — Dashboard
# ---------------------------------------------------------------------------


class GuruSummaryItem(BaseModel):
    """GET /gurus/dashboard 中單一大師的摘要卡片。"""

    id: int
    display_name: str
    latest_report_date: str | None = None
    latest_filing_date: str | None = None
    total_value: float | None = None
    holdings_count: int = 0
    filing_count: int = 0
    style: str | None = None
    tier: str | None = None


class SeasonHighlightItem(BaseModel):
    """本季重點變動（新建倉或清倉）的單筆記錄。"""

    ticker: str | None = None
    company_name: str = ""
    guru_id: int
    guru_display_name: str
    value: float = 0.0
    weight_pct: float | None = None
    change_pct: float | None = None


class SeasonHighlights(BaseModel):
    """本季新建倉與清倉彙總。"""

    new_positions: list[SeasonHighlightItem] = []
    sold_outs: list[SeasonHighlightItem] = []


class ConsensusGuruDetail(BaseModel):
    """共識股票中單一大師的持倉細節。"""

    display_name: str
    action: str
    weight_pct: float | None = None


class ConsensusStockItem(BaseModel):
    """被多位大師同時持有的共識股票。"""

    ticker: str
    company_name: str = ""
    guru_count: int
    gurus: list[ConsensusGuruDetail] = []
    total_value: float = 0.0
    avg_weight_pct: float | None = None
    sector: str | None = None


class SectorBreakdownItem(BaseModel):
    """依行業板塊彙總的持倉分佈單筆。"""

    sector: str
    total_value: float
    holding_count: int
    weight_pct: float


class ActivityFeedItem(BaseModel):
    """單一股票的買入或賣出活動摘要。"""

    ticker: str
    company_name: str
    guru_count: int
    gurus: list[str] = []
    total_value: float = 0.0


class ActivityFeed(BaseModel):
    """本季最多買入與最多賣出股票排行。"""

    most_bought: list[ActivityFeedItem] = []
    most_sold: list[ActivityFeedItem] = []


class DashboardResponse(BaseModel):
    """GET /gurus/dashboard 完整回應。"""

    gurus: list[GuruSummaryItem] = []
    season_highlights: SeasonHighlights = SeasonHighlights()
    consensus: list[ConsensusStockItem] = []
    sector_breakdown: list[SectorBreakdownItem] = []
    activity_feed: ActivityFeed = ActivityFeed()


class FilingHistoryItem(BaseModel):
    """GET /gurus/{guru_id}/filings 中的單筆申報摘要。"""

    id: int
    report_date: str
    filing_date: str
    total_value: float | None = None
    holdings_count: int = 0
    filing_url: str = ""


class FilingHistoryResponse(BaseModel):
    """GET /gurus/{guru_id}/filings 完整回應。"""

    filings: list[FilingHistoryItem] = []
