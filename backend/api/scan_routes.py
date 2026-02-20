"""
API — 掃描路由（非同步 fire-and-forget）。
掃描在背景執行緒執行，結果透過 Telegram 通知。
包含 mutex 防止同時多個掃描 / 摘要執行。
"""

import threading

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from api.rate_limit import limiter
from api.schemas import (
    AcceptedResponse,
    CNNFearGreedData,
    FearGreedResponse,
    LastScanResponse,
    ScanStatusResponse,
    VIXData,
)
from application.formatters import format_fear_greed_label
from application.services import run_scan, send_weekly_digest
from domain.constants import ERROR_DIGEST_IN_PROGRESS, ERROR_SCAN_IN_PROGRESS
from i18n import get_user_language, t
from infrastructure import repositories as repo
from infrastructure.database import engine, get_session
from infrastructure.market_data import get_fear_greed_index
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Mutex：防止並行掃描 / 摘要造成 yfinance 過載或資料競爭
_scan_lock = threading.Lock()
_digest_lock = threading.Lock()


def _run_scan_background() -> None:
    """在背景執行緒中執行掃描（自建 DB Session）。"""
    try:
        with Session(engine) as session:
            run_scan(session)
    except Exception as e:
        logger.error("背景掃描失敗：%s", e, exc_info=True)


def _run_digest_background() -> None:
    """在背景執行緒中生成每週摘要（自建 DB Session）。"""
    try:
        with Session(engine) as session:
            send_weekly_digest(session)
    except Exception as e:
        logger.error("每週摘要生成失敗：%s", e, exc_info=True)


@router.get(
    "/scan/last", response_model=LastScanResponse, summary="Get last scan timestamp"
)
def get_last_scan_time(session: Session = Depends(get_session)) -> LastScanResponse:
    """取得最近一次掃描的時間戳與市場情緒，用於判斷資料新鮮度。"""
    logs = repo.find_latest_scan_logs(session, limit=1)
    if not logs:
        return LastScanResponse(last_scanned_at=None, epoch=None)
    log = logs[0]
    ts = log.scanned_at

    # 取得最新 Fear & Greed 資料（快取，不額外呼叫 yfinance）
    fg = get_fear_greed_index()
    fg_level = fg.get("composite_level")
    fg_score = fg.get("composite_score")

    return LastScanResponse(
        last_scanned_at=ts.isoformat(),
        epoch=int(ts.timestamp()),
        market_status=log.market_status,
        market_status_details=getattr(log, "market_status_details", ""),
        fear_greed_level=fg_level,
        fear_greed_score=fg_score,
    )


@router.get(
    "/scan/status",
    response_model=ScanStatusResponse,
    summary="Check if scan is running",
)
def get_scan_status() -> ScanStatusResponse:
    """回傳目前掃描是否正在執行中（用於前端 UI 狀態顯示）。"""
    return ScanStatusResponse(is_running=_scan_lock.locked())


@router.get(
    "/market/fear-greed", response_model=FearGreedResponse, summary="Fear & Greed Index"
)
def get_fear_greed(session: Session = Depends(get_session)) -> FearGreedResponse:
    """取得恐懼與貪婪指數（VIX + CNN Fear & Greed 綜合分析）。"""
    fg = get_fear_greed_index()
    composite_level = fg.get("composite_level", "N/A")
    composite_score = fg.get("composite_score", 50)

    vix_raw = fg.get("vix")
    cnn_raw = fg.get("cnn")

    lang = get_user_language(session)

    return FearGreedResponse(
        composite_score=composite_score,
        composite_level=composite_level,
        composite_label=format_fear_greed_label(
            composite_level, composite_score, lang=lang
        ),
        vix=VIXData(**vix_raw) if vix_raw else None,
        cnn=CNNFearGreedData(**cnn_raw) if cnn_raw else None,
        fetched_at=fg.get("fetched_at", ""),
    )


@router.post(
    "/scan", response_model=AcceptedResponse, summary="Trigger background scan"
)
@limiter.limit("5/minute")
async def run_scan_route(
    request: Request, session: Session = Depends(get_session)
) -> AcceptedResponse:
    """
    觸發 V2 三層漏斗掃描（非同步），結果透過 Telegram 通知。

    Rate limited: 5/minute per IP (prevents scan abuse & yfinance overload).
    """
    if not _scan_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": ERROR_SCAN_IN_PROGRESS,
                "detail": t("api.scan_in_progress", lang=get_user_language(session)),
            },
        )

    def _run_with_lock() -> None:
        try:
            _run_scan_background()
        finally:
            _scan_lock.release()

    thread = threading.Thread(target=_run_with_lock, daemon=True)
    thread.start()
    logger.info("掃描已在背景執行緒啟動。")
    return AcceptedResponse(
        status="accepted",
        message=t("api.scan_started", lang=get_user_language(session)),
    )


@router.post(
    "/digest", response_model=AcceptedResponse, summary="Trigger weekly digest"
)
@limiter.limit("5/minute")
async def run_digest_route(
    request: Request, session: Session = Depends(get_session)
) -> AcceptedResponse:
    """
    觸發每週摘要（非同步），結果透過 Telegram 通知。

    Rate limited: 5/minute per IP (prevents digest abuse).
    """
    if not _digest_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": ERROR_DIGEST_IN_PROGRESS,
                "detail": t("api.digest_in_progress", lang=get_user_language(session)),
            },
        )

    def _run_with_lock() -> None:
        try:
            _run_digest_background()
        finally:
            _digest_lock.release()

    thread = threading.Thread(target=_run_with_lock, daemon=True)
    thread.start()
    logger.info("每週摘要已在背景執行緒啟動。")
    return AcceptedResponse(
        status="accepted",
        message=t("api.digest_started", lang=get_user_language(session)),
    )
