"""
API — Signal Backtesting Schemas.
"""

from datetime import date, datetime

from pydantic import BaseModel


class SignalWindowMetrics(BaseModel):
    window_days: int
    hit_rate: float
    avg_return_pct: float
    median_return_pct: float
    sample_count: int


class SignalBacktestSummary(BaseModel):
    signal: str
    direction: str
    total_occurrences: int
    confidence: str
    windows: list[SignalWindowMetrics]
    false_positive_rate: float


class BacktestSummaryResponse(BaseModel):
    signals: list[SignalBacktestSummary]
    lookback_days: int
    computed_at: datetime
    total_signals_evaluated: int


class BacktestOccurrence(BaseModel):
    ticker: str
    signal_date: date
    market_status: str
    forward_returns: dict[str, float | None]


class BacktestDetailResponse(BaseModel):
    signal: str
    direction: str
    summary: SignalBacktestSummary
    total_occurrences: int
    occurrences: list[BacktestOccurrence]


class BackfillStatusResponse(BaseModel):
    is_backfilling: bool
    total: int
    completed: int
