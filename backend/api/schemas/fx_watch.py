"""
API — FX Watch / Forex Monitoring Schemas。
"""

from typing import Optional

from pydantic import BaseModel

from domain.constants import (
    FX_WATCH_DEFAULT_ALERT_ON_CONSECUTIVE,
    FX_WATCH_DEFAULT_ALERT_ON_RECENT_HIGH,
    FX_WATCH_DEFAULT_CONSECUTIVE_DAYS,
    FX_WATCH_DEFAULT_RECENT_HIGH_DAYS,
    FX_WATCH_DEFAULT_REMINDER_HOURS,
)


# ---------------------------------------------------------------------------
# Request Schemas
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


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


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
