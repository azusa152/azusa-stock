"""
API — 掃描路由（非同步 fire-and-forget）。
掃描在背景執行緒執行，結果透過 Telegram 通知。
"""

import threading

from fastapi import APIRouter
from sqlmodel import Session

from application.services import run_scan
from infrastructure.database import engine
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _run_scan_background() -> None:
    """在背景執行緒中執行掃描（自建 DB Session）。"""
    try:
        with Session(engine) as session:
            run_scan(session)
    except Exception as e:
        logger.error("背景掃描失敗：%s", e, exc_info=True)


@router.post("/scan")
def run_scan_route() -> dict:
    """觸發 V2 三層漏斗掃描（非同步），結果透過 Telegram 通知。"""
    thread = threading.Thread(target=_run_scan_background, daemon=True)
    thread.start()
    logger.info("掃描已在背景執行緒啟動。")
    return {"status": "accepted", "message": "掃描已啟動，結果將透過 Telegram 通知。"}
