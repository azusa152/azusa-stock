"""
Application — Guru Service：大師 CRUD 與預設種子資料管理。
"""

from sqlmodel import Session

from domain.constants import DEFAULT_GURUS
from domain.entities import Guru
from infrastructure.repositories import (
    deactivate_guru,
    find_all_active_gurus,
    find_guru_by_cik,
    find_guru_by_id,
    save_guru,
    update_guru,
)
from logging_config import get_logger

logger = get_logger(__name__)


def seed_default_gurus(session: Session) -> int:
    """
    冪等地插入系統預設大師清單（DEFAULT_GURUS 中未存在者才新增）。
    供 app 啟動時呼叫。

    Args:
        session: Database session

    Returns:
        本次新增的筆數
    """
    added = 0
    for entry in DEFAULT_GURUS:
        existing = find_guru_by_cik(session, entry["cik"])
        if existing is None:
            guru = Guru(
                name=entry["name"],
                cik=entry["cik"],
                display_name=entry["display_name"],
                is_default=True,
            )
            save_guru(session, guru)
            added += 1
            logger.info("種子大師新增：%s (%s)", entry["display_name"], entry["cik"])

    logger.info(
        "大師種子資料完成：本次新增 %d 筆，共 %d 筆預設大師", added, len(DEFAULT_GURUS)
    )
    return added


def list_gurus(session: Session) -> list[Guru]:
    """
    取得所有啟用中的大師清單。

    Args:
        session: Database session

    Returns:
        啟用中的 Guru 列表
    """
    return find_all_active_gurus(session)


def add_guru(
    session: Session,
    name: str,
    cik: str,
    display_name: str,
) -> Guru:
    """
    新增自訂大師（以 CIK 為唯一鍵）。
    若 CIK 已存在且為停用狀態，則重新啟用並更新資訊。

    Args:
        session: Database session
        name: 機構正式名稱
        cik: SEC CIK（10 碼補零）
        display_name: 顯示名稱

    Returns:
        新增或重新啟用的 Guru 實體
    """
    existing = find_guru_by_cik(session, cik)
    if existing is not None:
        # 若已停用，重新啟用並更新顯示資訊
        existing.is_active = True
        existing.name = name
        existing.display_name = display_name
        guru = update_guru(session, existing)
        logger.info("大師重新啟用：%s (%s)", display_name, cik)
        return guru

    guru = Guru(name=name, cik=cik, display_name=display_name)
    saved = save_guru(session, guru)
    logger.info("新增大師：%s (%s)", display_name, cik)
    return saved


def remove_guru(session: Session, guru_id: int) -> bool:
    """
    停用大師（軟刪除）。

    Args:
        session: Database session
        guru_id: 大師 ID

    Returns:
        True 表示成功停用，False 表示找不到
    """
    guru = find_guru_by_id(session, guru_id)
    if guru is None:
        return False

    deactivate_guru(session, guru)
    logger.info("停用大師：%s (ID=%d)", guru.display_name, guru_id)
    return True
