"""
Domain — 資料庫實體 (SQLModel Tables)。
定義核心業務實體及資產配置相關資料表。
"""

import json as _json
from datetime import UTC, date, datetime

from sqlmodel import Column, Field, SQLModel, String

from domain.constants import (
    DEFAULT_LANGUAGE,
    DEFAULT_NOTIFICATION_PREFERENCES,
    DEFAULT_NOTIFICATION_RATE_LIMITS,
    DEFAULT_USER_ID,
)
from domain.enums import HoldingAction, ScanSignal, StockCategory


class Stock(SQLModel, table=True):
    """追蹤清單中的個股。"""

    ticker: str = Field(primary_key=True, description="股票代號")
    category: StockCategory = Field(description="分類")
    current_thesis: str = Field(default="", description="最新觀點")
    current_tags: str = Field(default="", description="最新標籤（逗號分隔）")
    display_order: int = Field(default=0, description="顯示順位（數字越小越前面）")
    last_scan_signal: str = Field(
        default=ScanSignal.NORMAL.value, description="上次掃描訊號"
    )
    signal_since: datetime | None = Field(default=None, description="目前訊號起始時間")
    is_active: bool = Field(default=True, description="是否追蹤中")
    is_etf: bool = Field(default=False, description="是否為 ETF（市場情緒排除用）")


class ThesisLog(SQLModel, table=True):
    """觀點版控紀錄。"""

    id: int | None = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    content: str = Field(description="觀點內容")
    tags: str = Field(default="", description="該版本的標籤快照（逗號分隔）")
    version: int = Field(description="版本號")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )


class RemovalLog(SQLModel, table=True):
    """移除紀錄（含版控，同一檔股票可多次移除）。"""

    id: int | None = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    reason: str = Field(description="移除原因")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="移除時間",
    )


class ScanLog(SQLModel, table=True):
    """掃描紀錄（每次掃描、每檔股票一筆）。"""

    id: int | None = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    signal: str = Field(description="掃描訊號（ScanSignal value）")
    market_status: str = Field(description="掃描時的市場情緒")
    market_status_details: str = Field(default="", description="市場情緒原因說明")
    details: str = Field(default="", description="警報詳情（JSON）")
    scanned_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="掃描時間",
    )


class PriceAlert(SQLModel, table=True):
    """自訂價格警報。"""

    id: int | None = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    metric: str = Field(description="指標名稱：rsi, price, bias")
    operator: str = Field(description="比較運算：lt, gt")
    threshold: float = Field(description="門檻值")
    is_active: bool = Field(default=True, description="是否啟用")
    last_triggered_at: datetime | None = Field(default=None, description="上次觸發時間")


# ---------------------------------------------------------------------------
# Asset Allocation — 投資組合配置相關
# ---------------------------------------------------------------------------


class SystemTemplate(SQLModel, table=True):
    """系統預設的投資組合人格範本（唯讀參考資料）。"""

    id: str = Field(
        primary_key=True, description="範本 ID（如 conservative, balanced）"
    )
    name: str = Field(description="範本名稱")
    description: str = Field(default="", description="範本說明")
    quote: str = Field(default="", description="引言")
    is_empty: bool = Field(default=False, description="是否為空白自訂範本")
    default_config: str = Field(default="{}", description="預設配置（JSON 字串）")


class UserInvestmentProfile(SQLModel, table=True):
    """使用者的投資組合目標配置。"""

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    name: str = Field(default="", description="配置名稱")
    source_template_id: str | None = Field(default=None, description="來源範本 ID")
    home_currency: str = Field(
        default="TWD", description="使用者的本幣（用於匯率曝險計算）"
    )
    config: str = Field(
        default="{}", description='配置（JSON 字串，如 {"Bond": 50, ...}）'
    )
    is_active: bool = Field(default=True, description="是否為啟用中的配置")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新時間",
    )


class Holding(SQLModel, table=True):
    """使用者的實際持倉（用於資產配置計算）。"""

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    ticker: str = Field(description="資產代號（股票代號或幣別如 USD）")
    category: StockCategory = Field(description="資產分類")
    quantity: float = Field(description="持有數量（股數或金額）")
    cost_basis: float | None = Field(default=None, description="成本基礎（每單位）")
    broker: str | None = Field(default=None, description="券商名稱")
    currency: str = Field(default="USD", description="持倉幣別（如 USD, TWD, JPY）")
    account_type: str | None = Field(
        default=None, description="帳戶類型（活存/定存/貨幣市場基金）"
    )
    is_cash: bool = Field(default=False, description="是否為現金類資產")
    purchase_fx_rate: float | None = Field(
        default=None, description="購入時匯率（1 單位持倉幣別 = ? 單位 USD）"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="更新時間",
    )


class UserTelegramSettings(SQLModel, table=True):
    """使用者的 Telegram 通知設定（支援自訂 Bot）。"""

    user_id: str = Field(
        default=DEFAULT_USER_ID, primary_key=True, description="使用者 ID"
    )
    telegram_chat_id: str = Field(default="", description="Telegram Chat ID")
    custom_bot_token: str | None = Field(default=None, description="自訂 Bot Token")
    use_custom_bot: bool = Field(default=False, description="是否使用自訂 Bot")


class UserPreferences(SQLModel, table=True):
    """使用者偏好設定（跨裝置同步）。"""

    user_id: str = Field(
        default=DEFAULT_USER_ID, primary_key=True, description="使用者 ID"
    )
    language: str = Field(default=DEFAULT_LANGUAGE, description="偏好語言")
    privacy_mode: bool = Field(default=False, description="是否啟用隱私模式")
    notification_preferences: str = Field(
        default=_json.dumps(DEFAULT_NOTIFICATION_PREFERENCES),
        sa_column=Column(String, default=_json.dumps(DEFAULT_NOTIFICATION_PREFERENCES)),
        description="通知偏好 JSON（各類通知的啟用/停用）",
    )
    notification_rate_limits: str = Field(
        default=_json.dumps(DEFAULT_NOTIFICATION_RATE_LIMITS),
        sa_column=Column(String, default=_json.dumps(DEFAULT_NOTIFICATION_RATE_LIMITS)),
        description='通知頻率限制 JSON，格式：{"fx_alerts": {"max_count": 2, "window_hours": 24}}，空 dict 表示無限制',
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

    def get_notification_rate_limits(self) -> dict[str, dict[str, int]]:
        """解析通知頻率限制 JSON。空 dict 表示全部無限制。"""
        try:
            stored = _json.loads(self.notification_rate_limits)
        except (TypeError, _json.JSONDecodeError):
            stored = {}
        return {**DEFAULT_NOTIFICATION_RATE_LIMITS, **stored}

    def set_notification_rate_limits(self, limits: dict[str, dict[str, int]]) -> None:
        """合併並序列化通知頻率限制（保留既有的其他類型設定）。"""
        existing = self.get_notification_rate_limits()
        merged = {**existing, **limits}
        self.notification_rate_limits = _json.dumps(merged)


# ---------------------------------------------------------------------------
# Smart Money Tracker (大師足跡追蹤)
# ---------------------------------------------------------------------------


class Guru(SQLModel, table=True):
    """追蹤的機構投資人（大師）。"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(description="機構名稱 (e.g. Berkshire Hathaway)")
    cik: str = Field(unique=True, description="SEC CIK 代碼 (10-digit zero-padded)")
    display_name: str = Field(description="顯示名稱 (e.g. Warren Buffett)")
    is_active: bool = Field(default=True, description="是否追蹤中")
    is_default: bool = Field(default=False, description="是否為系統預設大師")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )
    style: str | None = Field(
        default=None,
        description="投資風格 (VALUE, GROWTH, MACRO, QUANT, ACTIVIST, MULTI_STRATEGY)",
    )
    tier: str | None = Field(
        default=None,
        description="等級排名 (TIER_1, TIER_2, TIER_3)",
    )


class GuruFiling(SQLModel, table=True):
    """大師的 13F 季度申報記錄。"""

    id: int | None = Field(default=None, primary_key=True)
    guru_id: int = Field(foreign_key="guru.id", description="對應大師 ID")
    accession_number: str = Field(unique=True, description="SEC 文件編號")
    report_date: str = Field(description="持倉基準日 (e.g. 2024-12-31)")
    filing_date: str = Field(description="SEC 公告日 (e.g. 2025-02-14)")
    total_value: float | None = Field(default=None, description="總持倉市值 (千美元)")
    holdings_count: int = Field(default=0, description="持倉數量")
    filing_url: str = Field(default="", description="SEC EDGAR 原始文件連結")
    synced_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="同步時間",
    )


class GuruHolding(SQLModel, table=True):
    """大師某次申報中的個別持倉。"""

    id: int | None = Field(default=None, primary_key=True)
    filing_id: int = Field(foreign_key="gurufiling.id", description="對應申報 ID")
    guru_id: int = Field(foreign_key="guru.id", description="對應大師 ID")
    cusip: str = Field(description="CUSIP 代碼")
    ticker: str | None = Field(default=None, description="對應的股票代號")
    company_name: str = Field(description="13F 中的公司名稱")
    value: float = Field(description="持倉市值 (千美元)")
    shares: float = Field(description="持股數量")
    action: str = Field(
        default=HoldingAction.UNCHANGED.value, description="與前季比較的動作"
    )
    change_pct: float | None = Field(default=None, description="持股數量變動百分比")
    weight_pct: float | None = Field(default=None, description="佔該大師總持倉比例")
    sector: str | None = Field(default=None, description="GICS 行業板塊（yfinance）")


# ---------------------------------------------------------------------------
# Portfolio Snapshots — 投資組合每日快照（供績效圖表使用）
# ---------------------------------------------------------------------------


class PortfolioSnapshot(SQLModel, table=True):
    """每日投資組合總市值快照（用於歷史績效追蹤）。"""

    id: int | None = Field(default=None, primary_key=True)
    snapshot_date: date = Field(
        index=True, unique=True, description="快照日期（每日唯一）"
    )
    total_value: float = Field(description="投資組合總市值")
    category_values: str = Field(
        default="{}", description="各類別市值 JSON（如 {'Trend_Setter': 45000, ...}）"
    )
    display_currency: str = Field(default="USD", description="顯示幣別")
    benchmark_value: float | None = Field(
        default=None, description="同日 S&P 500 收盤價（基準比較用，向下相容）"
    )
    benchmark_values: str = Field(
        default="{}",
        description='多基準指數收盤價 JSON，如 {"^GSPC": 5000, "VT": 120, "^N225": 38000, "^TWII": 18000}',
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="建立時間",
    )


class FXWatchConfig(SQLModel, table=True):
    """外匯換匯時機監控配置。"""

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(default=DEFAULT_USER_ID, description="使用者 ID")
    base_currency: str = Field(description="基礎貨幣，例如 USD")
    quote_currency: str = Field(description="報價貨幣，例如 TWD")
    recent_high_days: int = Field(default=30, description="回溯天數（近期高點判定）")
    consecutive_increase_days: int = Field(default=3, description="連續上漲天數門檻")
    alert_on_recent_high: bool = Field(default=True, description="是否啟用近期高點警報")
    alert_on_consecutive_increase: bool = Field(
        default=True, description="是否啟用連續上漲警報"
    )
    reminder_interval_hours: int = Field(
        default=24, description="提醒間隔（小時），避免重複通知"
    )
    is_active: bool = Field(default=True, description="是否啟用")
    last_alerted_at: datetime | None = Field(default=None, description="上次警報時間")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="建立時間"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="更新時間"
    )


# ---------------------------------------------------------------------------
# Notification Log (rate-limit tracking)
# ---------------------------------------------------------------------------


class NotificationLog(SQLModel, table=True):
    """通知發送日誌，用於頻率限制（每段時間最多 N 次）。"""

    id: int | None = Field(default=None, primary_key=True)
    notification_type: str = Field(
        index=True, description="通知類型，例如 'fx_alerts'、'fx_watch_alerts'"
    )
    sent_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        index=True,
        description="發送時間（naive UTC，與 SQLite 相容）",
    )
