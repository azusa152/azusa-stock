"""
API — Guru analytics schemas (13F heat map + guru backtest).
"""

from pydantic import BaseModel, Field

from api.schemas.guru import SectorBreakdownItem


class HeatmapGuruDetail(BaseModel):
    """Per-guru detail for a heat map ticker entry."""

    guru_id: int
    guru_display_name: str
    weight_pct: float | None = None
    action: str
    value: float


class HeatmapItem(BaseModel):
    """Single ticker aggregation for 13F heat map."""

    ticker: str
    company_name: str
    sector: str | None = None
    guru_count: int
    gurus: list[HeatmapGuruDetail] = Field(default_factory=list)
    combined_value: float
    combined_weight_pct: float
    dominant_action: str
    action_breakdown: dict[str, int] = Field(default_factory=dict)


class HeatmapResponse(BaseModel):
    """Response payload for `/gurus/heatmap`."""

    items: list[HeatmapItem] = Field(default_factory=list)
    sectors: list[SectorBreakdownItem] = Field(default_factory=list)
    report_date: str | None = None
    filing_delay_note: str = ""
    generated_at: str


class QuarterResult(BaseModel):
    """Per-quarter return result in guru backtest."""

    report_date: str
    filing_date: str
    clone_return_pct: float
    benchmark_return_pct: float
    alpha_pct: float
    holdings_count: int
    top5_holdings: list[str] = Field(default_factory=list)


class CumulativeSeries(BaseModel):
    """Compact chart series for cumulative return lines."""

    dates: list[str] = Field(default_factory=list)
    clone_returns: list[float] = Field(default_factory=list)
    benchmark_returns: list[float] = Field(default_factory=list)


class GuruBacktestResponse(BaseModel):
    """Response payload for `/gurus/{guru_id}/backtest`."""

    guru_id: int
    guru_display_name: str
    benchmark: str = Field(description="Benchmark ticker symbol (e.g. SPY, VT)")
    quarters: list[QuarterResult] = Field(default_factory=list)
    cumulative_series: CumulativeSeries = Field(default_factory=CumulativeSeries)
    cumulative_clone_return: float
    cumulative_benchmark_return: float
    alpha: float
    computed_at: str
    disclaimer: str = ""
