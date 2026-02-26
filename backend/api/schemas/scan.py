"""
API — Scan / PriceAlert / FearGreed Schemas。
"""

from pydantic import BaseModel

from domain.enums import StockCategory

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class PriceAlertCreateRequest(BaseModel):
    """POST /ticker/{ticker}/alerts 請求 Body。"""

    metric: str = "rsi"
    operator: str = "lt"
    threshold: float = 30.0


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


class ScanResult(BaseModel):
    """POST /scan 回傳的掃描結果（V2 三層漏斗）。"""

    ticker: str
    category: StockCategory
    signal: str
    alerts: list[str]
    moat: str | None = None
    bias: float | None = None
    volume_ratio: float | None = None
    market_status: str | None = None
    bias_percentile: float | None = None
    is_rogue_wave: bool = False


class ScanResponse(BaseModel):
    """POST /scan 完整回傳結構（含整體市場情緒）。"""

    market_status: dict
    results: list[ScanResult]


class SignalsResponse(BaseModel):
    """GET /ticker/{ticker}/signals 技術訊號回應。"""

    ticker: str | None = None
    price: float | None = None
    previous_close: float | None = None
    change_pct: float | None = None
    rsi: float | None = None
    ma200: float | None = None
    ma60: float | None = None
    bias: float | None = None
    bias_200: float | None = None
    volume_ratio: float | None = None
    status: list[str] = []
    error: str | None = None
    bias_percentile: float | None = None
    is_rogue_wave: bool = False


class PriceHistoryPoint(BaseModel):
    """價格歷史單一資料點。"""

    date: str
    close: float


class MoatResponse(BaseModel):
    """GET /ticker/{ticker}/moat 護城河分析回應。"""

    ticker: str = ""
    moat: str | None = None
    details: str | None = None
    margins: list[dict] = []
    yoy_change: float | None = None


class EarningsResponse(BaseModel):
    """GET /ticker/{ticker}/earnings 財報日曆回應。"""

    ticker: str = ""
    next_earnings_date: str | None = None
    days_until: int | None = None
    error: str | None = None


class DividendResponse(BaseModel):
    """GET /ticker/{ticker}/dividend 股息資訊回應。"""

    ticker: str = ""
    dividend_yield: float | None = None
    ex_date: str | None = None
    ytd_dividend_per_share: float | None = None
    error: str | None = None


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

    last_scanned_at: str | None = None
    epoch: int | None = None
    market_status: str | None = None
    market_status_details: str | None = None
    fear_greed_level: str | None = None
    fear_greed_score: int | None = None


class ScanStatusResponse(BaseModel):
    """GET /scan/status 回應。"""

    is_running: bool


class PrewarmStatusResponse(BaseModel):
    """GET /prewarm-status 回應。"""

    ready: bool


class ScanLogResponse(BaseModel):
    """掃描歷史單一紀錄。"""

    ticker: str
    signal: str
    alerts: list[str] = []
    scanned_at: str


class VIXData(BaseModel):
    """VIX 指數資料。"""

    value: float | None = None
    change_1d: float | None = None
    level: str = "N/A"
    fetched_at: str = ""


class CNNFearGreedData(BaseModel):
    """CNN Fear & Greed Index 資料。"""

    score: int | None = None
    label: str = ""
    level: str = "N/A"
    fetched_at: str = ""


class FearGreedComponent(BaseModel):
    """Self-calculated Fear & Greed component score."""

    name: str
    score: int | None = None
    weight: float


class FearGreedResponse(BaseModel):
    """GET /market/fear-greed 回傳的恐懼與貪婪指數綜合分析。"""

    composite_score: int = 50
    composite_level: str = "N/A"
    composite_label: str = ""
    self_calculated_score: int | None = None
    components: list[FearGreedComponent] = []
    vix: VIXData | None = None
    cnn: CNNFearGreedData | None = None
    fetched_at: str = ""
