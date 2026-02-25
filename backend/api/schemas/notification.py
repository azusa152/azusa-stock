"""
API — Notification / Telegram / Preferences / Persona / Snapshot / Webhook Schemas。
"""

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Telegram Settings Schemas
# ---------------------------------------------------------------------------


class TelegramSettingsRequest(BaseModel):
    """PUT /settings/telegram 請求 Body。"""

    telegram_chat_id: str = ""
    custom_bot_token: str | None = None
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

    language: str | None = None
    privacy_mode: bool
    notification_preferences: dict[str, bool] | None = None


class PreferencesResponse(BaseModel):
    """GET /settings/preferences 回應。"""

    language: str
    privacy_mode: bool
    notification_preferences: dict[str, bool]


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
    source_template_id: str | None = None
    config: dict[str, float]  # {"Bond": 50, "Trend_Setter": 30, ...}
    home_currency: str = "TWD"


class ProfileUpdateRequest(BaseModel):
    """PUT /profiles/{id} 請求 Body。"""

    name: str | None = None
    config: dict[str, float] | None = None
    home_currency: str | None = None


class ProfileResponse(BaseModel):
    """GET /profiles 回傳的投資組合配置。"""

    id: int
    user_id: str
    name: str
    source_template_id: str | None = None
    home_currency: str = "TWD"
    config: dict
    is_active: bool
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Portfolio Snapshot Schemas
# ---------------------------------------------------------------------------


class SnapshotResponse(BaseModel):
    """GET /snapshots 回傳的單日投資組合快照。"""

    snapshot_date: str  # ISO date string, e.g. "2025-02-19"
    total_value: float
    category_values: dict  # parsed from JSON storage
    display_currency: str = "USD"
    benchmark_value: float | None = None
    benchmark_values: dict[str, float | None] = {}  # {"^GSPC": 5000, "VT": 120, ...}


class TwrResponse(BaseModel):
    """GET /snapshots/twr 回傳的時間加權報酬率。"""

    twr_pct: float | None  # 百分比，例如 12.3 代表 +12.3%；None 表示資料不足
    start_date: str | None = None  # 計算起始日（快照中最早一筆）
    end_date: str | None = None  # 計算結束日（快照中最新一筆）
    snapshot_count: int = 0  # 用於計算的快照筆數


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
