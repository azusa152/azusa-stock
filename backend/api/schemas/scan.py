"""
API — Scan / PriceAlert / FearGreed Schemas。
"""

from typing import Optional

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
    bias_200: Optional[float] = None
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
