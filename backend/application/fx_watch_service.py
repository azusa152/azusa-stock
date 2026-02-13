"""
Application — FX Watch Service：外匯換匯時機監控與警報。
提供 CRUD 操作與定期監控邏輯。
"""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from domain.constants import DEFAULT_USER_ID
from domain.entities import FXWatchConfig
from domain.fx_analysis import FXTimingResult, assess_exchange_timing
from infrastructure.market_data import get_forex_history_long
from infrastructure.notification import (
    is_notification_enabled,
    send_telegram_message_dual,
)
from infrastructure.repositories import (
    create_fx_watch,
    delete_fx_watch,
    find_active_fx_watches,
    find_all_fx_watches,
    find_fx_watch_by_id,
    update_fx_watch,
    update_fx_watch_last_alerted,
)
from logging_config import get_logger

logger = get_logger(__name__)


# ===========================================================================
# CRUD Operations
# ===========================================================================


def create_watch(
    session: Session,
    base_currency: str,
    quote_currency: str,
    recent_high_days: int = 30,
    consecutive_increase_days: int = 3,
    alert_on_recent_high: bool = True,
    alert_on_consecutive_increase: bool = True,
    reminder_interval_hours: int = 24,
    user_id: str = DEFAULT_USER_ID,
) -> FXWatchConfig:
    """
    新增一筆外匯監控配置。

    Args:
        session: Database session
        base_currency: 基礎貨幣（例如 USD）
        quote_currency: 報價貨幣（例如 TWD）
        recent_high_days: 回溯天數（近期高點判定）
        consecutive_increase_days: 連續上漲天數門檻
        alert_on_recent_high: 是否啟用近期高點警報
        alert_on_consecutive_increase: 是否啟用連續上漲警報
        reminder_interval_hours: 提醒間隔（小時）
        user_id: 使用者 ID

    Returns:
        新建的 FXWatchConfig 實體
    """
    watch = FXWatchConfig(
        user_id=user_id,
        base_currency=base_currency.upper(),
        quote_currency=quote_currency.upper(),
        recent_high_days=recent_high_days,
        consecutive_increase_days=consecutive_increase_days,
        alert_on_recent_high=alert_on_recent_high,
        alert_on_consecutive_increase=alert_on_consecutive_increase,
        reminder_interval_hours=reminder_interval_hours,
        is_active=True,
    )
    created = create_fx_watch(session, watch)
    logger.info(
        "新增外匯監控：%s/%s (recent_high=%dd, consecutive=%dd, flags=%s/%s, interval=%dh)",
        base_currency,
        quote_currency,
        recent_high_days,
        consecutive_increase_days,
        alert_on_recent_high,
        alert_on_consecutive_increase,
        reminder_interval_hours,
    )
    return created


def get_watch_by_id(session: Session, watch_id: int) -> FXWatchConfig | None:
    """根據 ID 查詢單一外匯監控配置。"""
    return find_fx_watch_by_id(session, watch_id)


def get_all_watches(
    session: Session, user_id: str = DEFAULT_USER_ID, active_only: bool = False
) -> list[FXWatchConfig]:
    """
    取得所有外匯監控配置。

    Args:
        session: Database session
        user_id: 使用者 ID
        active_only: 是否僅取啟用中的配置

    Returns:
        外匯監控配置列表
    """
    if active_only:
        return find_active_fx_watches(session, user_id)
    return find_all_fx_watches(session, user_id)


def update_watch(
    session: Session,
    watch_id: int,
    recent_high_days: int | None = None,
    consecutive_increase_days: int | None = None,
    alert_on_recent_high: bool | None = None,
    alert_on_consecutive_increase: bool | None = None,
    reminder_interval_hours: int | None = None,
    is_active: bool | None = None,
) -> FXWatchConfig | None:
    """
    更新外匯監控配置。

    Args:
        session: Database session
        watch_id: 配置 ID
        recent_high_days: 回溯天數（可選）
        consecutive_increase_days: 連續上漲天數門檻（可選）
        alert_on_recent_high: 是否啟用近期高點警報（可選）
        alert_on_consecutive_increase: 是否啟用連續上漲警報（可選）
        reminder_interval_hours: 提醒間隔（可選）
        is_active: 是否啟用（可選）

    Returns:
        更新後的配置，若不存在則回傳 None
    """
    watch = find_fx_watch_by_id(session, watch_id)
    if not watch:
        return None

    if recent_high_days is not None:
        watch.recent_high_days = recent_high_days
    if consecutive_increase_days is not None:
        watch.consecutive_increase_days = consecutive_increase_days
    if alert_on_recent_high is not None:
        watch.alert_on_recent_high = alert_on_recent_high
    if alert_on_consecutive_increase is not None:
        watch.alert_on_consecutive_increase = alert_on_consecutive_increase
    if reminder_interval_hours is not None:
        watch.reminder_interval_hours = reminder_interval_hours
    if is_active is not None:
        watch.is_active = is_active

    watch = update_fx_watch(session, watch)

    logger.info(
        "更新外匯監控：ID=%d, is_active=%s, flags=%s/%s",
        watch_id,
        watch.is_active,
        watch.alert_on_recent_high,
        watch.alert_on_consecutive_increase,
    )
    return watch


def remove_watch(session: Session, watch_id: int) -> bool:
    """
    刪除外匯監控配置。

    Args:
        session: Database session
        watch_id: 配置 ID

    Returns:
        是否成功刪除
    """
    watch = find_fx_watch_by_id(session, watch_id)
    if not watch:
        return False

    delete_fx_watch(session, watch)
    logger.info(
        "刪除外匯監控：ID=%d, %s/%s",
        watch_id,
        watch.base_currency,
        watch.quote_currency,
    )
    return True


# ===========================================================================
# Forex History (Application-layer wrapper)
# ===========================================================================


def get_forex_history(base: str, quote: str) -> list[dict]:
    """
    取得 3 個月外匯歷史資料（供 API 路由使用）。

    Args:
        base: 基礎貨幣（例如 USD）
        quote: 報價貨幣（例如 TWD）

    Returns:
        日線歷史 [{"date": "YYYY-MM-DD", "close": float}, ...]
    """
    return get_forex_history_long(base.upper(), quote.upper())


# ===========================================================================
# Monitoring Logic
# ===========================================================================


def check_fx_watches(session: Session, user_id: str = DEFAULT_USER_ID) -> list[dict]:
    """
    檢查所有啟用中的外匯監控配置，產出分析結果（不發送通知）。

    Args:
        session: Database session
        user_id: 使用者 ID

    Returns:
        分析結果列表，格式：
        [
            {
                "watch_id": int,
                "pair": "USD/TWD",
                "result": FXTimingResult,
            },
            ...
        ]
    """
    watches = find_active_fx_watches(session, user_id)
    if not watches:
        logger.info("無啟用中的外匯監控配置")
        return []

    results = []
    for watch in watches:
        try:
            history = get_forex_history_long(watch.base_currency, watch.quote_currency)
            result = assess_exchange_timing(
                base_currency=watch.base_currency,
                quote_currency=watch.quote_currency,
                history=history,
                recent_high_days=watch.recent_high_days,
                consecutive_threshold=watch.consecutive_increase_days,
                alert_on_recent_high=watch.alert_on_recent_high,
                alert_on_consecutive_increase=watch.alert_on_consecutive_increase,
            )
            results.append(
                {
                    "watch_id": watch.id,
                    "pair": f"{watch.base_currency}/{watch.quote_currency}",
                    "result": result,
                }
            )
        except Exception as e:
            logger.warning(
                "外匯監控分析失敗：%s/%s - %s",
                watch.base_currency,
                watch.quote_currency,
                e,
            )
            continue

    return results


def send_fx_watch_alerts(session: Session, user_id: str = DEFAULT_USER_ID) -> dict:
    """
    檢查所有啟用中的外匯監控配置，發送 Telegram 警報（帶冷卻機制）。

    Args:
        session: Database session
        user_id: 使用者 ID

    Returns:
        執行結果，格式：
        {
            "total_watches": int,
            "triggered_alerts": int,
            "sent_alerts": int,
            "alerts": [
                {
                    "watch_id": int,
                    "pair": "USD/TWD",
                    "result": FXTimingResult,
                },
                ...
            ],
        }
    """
    watches = find_active_fx_watches(session, user_id)
    if not watches:
        logger.info("無啟用中的外匯監控配置")
        return {
            "total_watches": 0,
            "triggered_alerts": 0,
            "sent_alerts": 0,
            "alerts": [],
        }

    triggered_alerts: list[dict] = []
    now = datetime.now(timezone.utc)

    for watch in watches:
        # 檢查冷卻時間
        if watch.last_alerted_at:
            cooldown_until = watch.last_alerted_at + timedelta(
                hours=watch.reminder_interval_hours
            )
            if now < cooldown_until:
                logger.debug(
                    "外匯監控冷卻中：%s/%s (ID=%d)，下次警報時間：%s",
                    watch.base_currency,
                    watch.quote_currency,
                    watch.id,
                    cooldown_until.isoformat(),
                )
                continue

        # 取得歷史資料並分析
        try:
            history = get_forex_history_long(watch.base_currency, watch.quote_currency)
            result = assess_exchange_timing(
                base_currency=watch.base_currency,
                quote_currency=watch.quote_currency,
                history=history,
                recent_high_days=watch.recent_high_days,
                consecutive_threshold=watch.consecutive_increase_days,
                alert_on_recent_high=watch.alert_on_recent_high,
                alert_on_consecutive_increase=watch.alert_on_consecutive_increase,
            )

            # 若應發出警報，加入列表並更新時間戳
            if result.should_alert:
                triggered_alerts.append(
                    {
                        "watch_id": watch.id,
                        "pair": f"{watch.base_currency}/{watch.quote_currency}",
                        "result": result,
                    }
                )
                update_fx_watch_last_alerted(session, watch.id, now)
                logger.info(
                    "觸發外匯監控警報：%s/%s (ID=%d)",
                    watch.base_currency,
                    watch.quote_currency,
                    watch.id,
                )

        except Exception as e:
            logger.warning(
                "外匯監控分析失敗：%s/%s - %s",
                watch.base_currency,
                watch.quote_currency,
                e,
            )
            continue

    # 若有觸發警報，發送 Telegram 通知
    sent_alerts = 0
    if triggered_alerts:
        if is_notification_enabled(session, "fx_watch_alerts"):
            alert_lines = []
            for alert in triggered_alerts:
                res: FXTimingResult = alert["result"]
                alert_lines.append(
                    f"📈 {alert['pair']}\n"
                    f"💡 {res.recommendation_zh}\n"
                    f"📊 {res.reasoning_zh}\n"
                    f"💱 現價：{res.current_rate:.4f}"
                )

            full_msg = "💱 外匯換匯時機警報\n\n" + "\n\n".join(alert_lines)
            try:
                send_telegram_message_dual(full_msg, session)
                sent_alerts = len(triggered_alerts)
                logger.info("已發送外匯換匯警報（%d 筆）", sent_alerts)
            except Exception as e:
                logger.warning("外匯換匯 Telegram 警報發送失敗：%s", e)
        else:
            logger.info("外匯換匯警報通知已關閉，跳過發送")

    return {
        "total_watches": len(watches),
        "triggered_alerts": len(triggered_alerts),
        "sent_alerts": sent_alerts,
        "alerts": triggered_alerts,
    }
