"""
Domain — 資料庫實體 (SQLModel Tables)。
定義核心業務實體及資產配置相關資料表。
"""

import json as _json
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Column, Field, SQLModel, String

from domain.constants import DEFAULT_NOTIFICATION_PREFERENCES, DEFAULT_USER_ID
from domain.enums import ScanSignal, StockCategory


class Stock(SQLModel, table=True):
    """追蹤清單中的個股。"""

    ticker: str = Field(primary_key=True, description="股票代號")
    category: StockCategory = Field(description="分類")
    current_thesis: str = Field(default="", description="最新觀點")
    current_tags: str = Field(default="", description="最新標籤（逗號分隔）")
    display_order: int = Field(default=0, description="顯示順位（數字越小越前面）")
    last_scan_signal: str = Field(default=ScanSignal.NORMAL.value, description="上次掃描訊號")
    is_active: bool = Field(default=True, description="是否追蹤中")


class ThesisLog(SQLModel, table=True):
    """觀點版控紀錄。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    content: str = Field(description="觀點內容")
    tags: str = Field(default="", description="該版本的標籤快照（逗號分隔）")
    version: int = Field(description="版本號")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="建立時間",
    )


class RemovalLog(SQLModel, table=True):
    """移除紀錄（含版控，同一檔股票可多次移除）。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    reason: str = Field(description="移除原因")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="移除時間",
    )


class ScanLog(SQLModel, table=True):
    """掃描紀錄（每次掃描、每檔股票一筆）。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    signal: str = Field(description="掃描訊號（ScanSignal value）")
    market_status: str = Field(description="掃描時的市場情緒")
    market_status_details: str = Field(default="", description="市場情緒原因說明")
    details: str = Field(default="", description="警報詳情（JSON）")
    scanned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="掃描時間",
    )


class PriceAlert(SQLModel, table=True):
    """自訂價格警報。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    metric: str = Field(description="指標名稱：rsi, price, bias")
    operator: str = Field(description="比較運算：lt, gt")
    threshold: float = Field(description="門檻值")
    is_active: bool = Field(default=True, description="是否啟用")
    last_triggered_at: Optional[datetime] = Field(
        default=None, description="上次觸發時間"
    )


# ---------------------------------------------------------------------------
# Asset Allocation — 投資組合配置相關
# ---------------------------------------------------------------------------


class SystemTemplate(SQLModel, table=True):
    """系統預設的投資組合人格範本（唯讀參考資料）。"""

    id: str = Field(primary_key=True, description="範本 ID（如 conservative, balanced）")
    name: str = Field(description="範本名稱")
    description: str = Field(default="", description="範本說明")
    quote: str = Field(default="", description="引言")
    is_empty: bool = Field(default=False, description="是否為空白自訂範本")
    default_config: str = Field(default="{}", description="預設配置（JSON 字串）")


class UserInvestmentProfile(SQLModel, table=True):
    """使用者的投資組合目標配置。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    name: str = Field(default="", description="配置名稱")
    source_template_id: Optional[str] = Field(default=None, description="來源範本 ID")
    home_currency: str = Field(default="TWD", description="使用者的本幣（用於匯率曝險計算）")
    config: str = Field(default="{}", description="配置（JSON 字串，如 {\"Bond\": 50, ...}）")
    is_active: bool = Field(default=True, description="是否為啟用中的配置")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="建立時間",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="更新時間",
    )


class Holding(SQLModel, table=True):
    """使用者的實際持倉（用於資產配置計算）。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    ticker: str = Field(description="資產代號（股票代號或幣別如 USD）")
    category: StockCategory = Field(description="資產分類")
    quantity: float = Field(description="持有數量（股數或金額）")
    cost_basis: Optional[float] = Field(default=None, description="成本基礎（每單位）")
    broker: Optional[str] = Field(default=None, description="券商名稱")
    currency: str = Field(default="USD", description="持倉幣別（如 USD, TWD, JPY）")
    account_type: Optional[str] = Field(default=None, description="帳戶類型（活存/定存/貨幣市場基金）")
    is_cash: bool = Field(default=False, description="是否為現金類資產")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="更新時間",
    )


class UserTelegramSettings(SQLModel, table=True):
    """使用者的 Telegram 通知設定（支援自訂 Bot）。"""

    user_id: str = Field(default=DEFAULT_USER_ID, primary_key=True, description="使用者 ID")
    telegram_chat_id: str = Field(default="", description="Telegram Chat ID")
    custom_bot_token: Optional[str] = Field(default=None, description="自訂 Bot Token")
    use_custom_bot: bool = Field(default=False, description="是否使用自訂 Bot")


class UserPreferences(SQLModel, table=True):
    """使用者偏好設定（跨裝置同步）。"""

    user_id: str = Field(default=DEFAULT_USER_ID, primary_key=True, description="使用者 ID")
    privacy_mode: bool = Field(default=False, description="是否啟用隱私模式")
    notification_preferences: str = Field(
        default=_json.dumps(DEFAULT_NOTIFICATION_PREFERENCES),
        sa_column=Column(String, default=_json.dumps(DEFAULT_NOTIFICATION_PREFERENCES)),
        description="通知偏好 JSON（各類通知的啟用/停用）",
    )

    def get_notification_prefs(self) -> dict[str, bool]:
        """解析通知偏好 JSON，缺少的 key 以預設值填補。"""
        try:
            stored = _json.loads(self.notification_preferences)
        except (TypeError, _json.JSONDecodeError):
            stored = {}
        return {**DEFAULT_NOTIFICATION_PREFERENCES, **stored}

    def set_notification_prefs(self, prefs: dict[str, bool]) -> None:
        """合併並序列化通知偏好。"""
        merged = {**DEFAULT_NOTIFICATION_PREFERENCES, **prefs}
        self.notification_preferences = _json.dumps(merged)
