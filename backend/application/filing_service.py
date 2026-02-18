"""
Application — Filing Service：13F 季報同步與持倉差異分析。

主要工作流程：
1. 從 EDGAR 取得最新兩筆 13F-HR 申報（latest + previous）
2. 若 latest 已同步則跳過（冪等）
3. 解析 13F XML 持倉明細
4. 對每筆持倉呼叫 classify_holding_change()，與前季進行比較
5. 對前季有但本季完全消失的 CUSIP 建立 SOLD_OUT 記錄
6. 計算 weight_pct
7. 批次儲存 GuruFiling + GuruHolding
8. 回傳摘要 dict
"""

from datetime import date, timedelta

from sqlmodel import Session

from domain.constants import (
    GURU_BACKFILL_FILING_COUNT,
    GURU_BACKFILL_YEARS,
    GURU_TOP_HOLDINGS_COUNT,
)
from domain.entities import Guru, GuruFiling, GuruHolding
from domain.enums import HoldingAction
from domain.smart_money import (
    classify_holding_change,
    compute_change_pct,
    compute_holding_weight,
)
from infrastructure.repositories import (
    find_all_active_gurus,
    find_filing_by_accession,
    find_guru_by_id,
    find_holdings_by_filing,
    find_latest_filing_by_guru,
    save_filing,
    save_holdings_batch,
)
from infrastructure.sec_edgar import (
    fetch_13f_filing_detail,
    get_latest_13f_filings,
    map_cusip_to_ticker,
)
from logging_config import get_logger

logger = get_logger(__name__)


def sync_guru_filing(session: Session, guru_id: int) -> dict:
    """
    同步指定大師的最新 13F 季報。

    流程：
    1. 取得大師資料與 EDGAR 最新兩筆申報
    2. 若最新申報已存在資料庫則跳過（冪等）
    3. 委派給 _sync_single_filing() 執行實際同步

    Args:
        session: Database session
        guru_id: Guru.id

    Returns:
        dict with keys:
            guru_id, guru_display_name, status ("synced" | "skipped" | "error"),
            accession_number, report_date, filing_date,
            total_holdings, new_positions, sold_out, increased, decreased,
            top_holdings (list of top-N holdings by weight)
    """
    guru = find_guru_by_id(session, guru_id)
    if guru is None:
        logger.warning("sync_guru_filing 找不到大師：ID=%d", guru_id)
        return {"guru_id": guru_id, "status": "error", "error": "guru not found"}

    edgar_filings = get_latest_13f_filings(guru.cik, count=2)
    if not edgar_filings:
        logger.warning("EDGAR 無 13F 申報：%s (%s)", guru.display_name, guru.cik)
        return {
            "guru_id": guru_id,
            "guru_display_name": guru.display_name,
            "status": "error",
            "error": "no 13F filings found on EDGAR",
        }

    return _sync_single_filing(session, guru, edgar_filings[0])


def backfill_guru_filings(
    session: Session,
    guru_id: int,
    years: int = GURU_BACKFILL_YEARS,
    _today: date | None = None,
) -> dict:
    """
    回填指定大師最近 N 年的 13F 歷史申報。

    流程：
    1. 從 EDGAR 取回最多 GURU_BACKFILL_FILING_COUNT 筆申報
    2. 過濾出在 years 年窗口內的申報
    3. 依 report_date 升冪排序（舊→新），確保 diff 鏈正確
    4. 逐筆呼叫 _sync_single_filing()（冪等：已同步者自動跳過）
    5. 回傳摘要 dict

    Args:
        session: Database session
        guru_id: Guru.id
        years: 回填年數（預設 GURU_BACKFILL_YEARS）
        _today: 參考日期（測試注入用；正常呼叫留 None 使用 date.today()）

    Returns:
        dict with keys: guru_id, guru_display_name, total_filings, synced, skipped, errors
    """
    guru = find_guru_by_id(session, guru_id)
    if guru is None:
        logger.warning("backfill_guru_filings 找不到大師：ID=%d", guru_id)
        return {
            "guru_id": guru_id,
            "status": "error",
            "error": "guru not found",
            "total_filings": 0,
            "synced": 0,
            "skipped": 0,
            "errors": 0,
        }

    edgar_filings = get_latest_13f_filings(guru.cik, count=GURU_BACKFILL_FILING_COUNT)
    if not edgar_filings:
        logger.info("EDGAR 無 13F 申報可回填：%s (%s)", guru.display_name, guru.cik)
        return {
            "guru_id": guru_id,
            "guru_display_name": guru.display_name,
            "total_filings": 0,
            "synced": 0,
            "skipped": 0,
            "errors": 0,
        }

    cutoff = (_today or date.today()) - timedelta(days=years * 365)
    in_window = [
        f
        for f in edgar_filings
        if date.fromisoformat(f["report_date"]) >= cutoff
    ]
    # 升冪排序，讓舊季先同步，diff 鏈方向正確
    in_window.sort(key=lambda f: f["report_date"])

    synced = skipped = errors = 0
    for edgar_filing in in_window:
        try:
            result = _sync_single_filing(session, guru, edgar_filing)
            if result["status"] == "synced":
                synced += 1
            elif result["status"] == "skipped":
                skipped += 1
            else:
                errors += 1
        except Exception as exc:
            logger.warning(
                "回填申報失敗：%s %s, error=%s",
                guru.display_name,
                edgar_filing.get("accession_number"),
                exc,
            )
            errors += 1

    logger.info(
        "13F 回填完成：%s，窗口內 %d 筆，已同步 %d，跳過 %d，錯誤 %d",
        guru.display_name,
        len(in_window),
        synced,
        skipped,
        errors,
    )
    return {
        "guru_id": guru_id,
        "guru_display_name": guru.display_name,
        "total_filings": len(in_window),
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
    }


def sync_all_gurus(session: Session) -> list[dict]:
    """
    批次同步所有啟用中大師的最新 13F 季報。

    Args:
        session: Database session

    Returns:
        每位大師的 sync_guru_filing() 結果列表
    """
    gurus = find_all_active_gurus(session)
    if not gurus:
        logger.info("無啟用中的大師，跳過同步")
        return []

    results = []
    for guru in gurus:
        try:
            result = sync_guru_filing(session, guru.id)
            results.append(result)
        except Exception as exc:
            logger.warning(
                "大師同步失敗：%s (ID=%d), error=%s", guru.display_name, guru.id, exc
            )
            results.append(
                {
                    "guru_id": guru.id,
                    "guru_display_name": guru.display_name,
                    "status": "error",
                    "error": str(exc),
                }
            )

    return results


def get_filing_summary(session: Session, guru_id: int) -> dict | None:
    """
    取得指定大師最新申報摘要（含分類持倉）。

    Args:
        session: Database session
        guru_id: Guru.id

    Returns:
        摘要 dict（參考 _build_summary），若無申報則回傳 None
    """
    guru = find_guru_by_id(session, guru_id)
    if guru is None:
        return None

    filing = find_latest_filing_by_guru(session, guru_id)
    if filing is None:
        return None

    holdings = find_holdings_by_filing(session, filing.id)
    return _build_summary(guru, filing, holdings)


def get_holding_changes(session: Session, guru_id: int) -> list[dict]:
    """
    取得指定大師最新申報中有動作的持倉（action != UNCHANGED）。

    Args:
        session: Database session
        guru_id: Guru.id

    Returns:
        持倉變動列表，每筆含 report_date, filing_date, ticker, company_name,
        action, change_pct, value, shares, weight_pct
    """
    filing = find_latest_filing_by_guru(session, guru_id)
    if filing is None:
        return []

    holdings = find_holdings_by_filing(session, filing.id)
    changes = [h for h in holdings if h.action != HoldingAction.UNCHANGED.value]

    return [_holding_to_dict(h, filing) for h in changes]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _sync_single_filing(
    session: Session, guru: Guru, edgar_filing_dict: dict
) -> dict:
    """
    同步單筆 EDGAR 申報至資料庫（由 sync_guru_filing 與 backfill_guru_filings 共用）。

    流程：
    1. 冪等檢查（accession_number 已存在則回傳 skipped）
    2. 下載並解析 13F XML
    3. 載入前季持倉快照（在 save_filing 之前呼叫，確保取得舊季資料）
    4. 組裝 GuruFiling + GuruHolding，儲存至 DB
    5. 回傳摘要 dict

    Args:
        session: Database session
        guru: Guru entity
        edgar_filing_dict: 單筆 EDGAR 申報 dict（含 accession_number, report_date 等）

    Returns:
        dict with status "synced" | "skipped" | "error"
    """
    accession_number = edgar_filing_dict["accession_number"]

    # 冪等檢查
    if find_filing_by_accession(session, accession_number) is not None:
        logger.info(
            "13F 申報已存在，跳過同步：%s %s", guru.display_name, accession_number
        )
        return {
            "guru_id": guru.id,
            "guru_display_name": guru.display_name,
            "status": "skipped",
            "accession_number": accession_number,
            "report_date": edgar_filing_dict["report_date"],
            "filing_date": edgar_filing_dict["filing_date"],
        }

    # 下載並解析持倉明細
    raw_holdings = fetch_13f_filing_detail(accession_number, guru.cik)
    if not raw_holdings:
        logger.warning(
            "13F 持倉明細解析失敗：%s %s", guru.display_name, accession_number
        )
        return {
            "guru_id": guru.id,
            "guru_display_name": guru.display_name,
            "status": "error",
            "error": "failed to fetch or parse infotable XML",
        }

    # 載入前季持倉快照（必須在 save_filing 之前呼叫，此時 DB 中最新申報即為前季）
    prev_holdings_map = _snapshot_prev_holdings(session, guru.id)

    # 計算總持倉市值（用於 weight_pct）
    total_value = sum(h["value"] for h in raw_holdings)

    # 組裝 GuruFiling
    filing = save_filing(
        session,
        GuruFiling(
            guru_id=guru.id,
            accession_number=accession_number,
            report_date=edgar_filing_dict["report_date"],
            filing_date=edgar_filing_dict["filing_date"],
            total_value=total_value,
            holdings_count=len(raw_holdings),
            filing_url=edgar_filing_dict.get("filing_url", ""),
        ),
    )

    # 組裝並分類 GuruHolding 列表（含前季完全消失的 SOLD_OUT）
    holdings = _build_holdings(
        raw_holdings, filing, guru, prev_holdings_map, total_value
    )
    save_holdings_batch(session, holdings)

    summary = _build_summary(guru, filing, holdings)
    logger.info(
        "13F 同步完成：%s %s，持倉 %d 筆，新建倉 %d，清倉 %d",
        guru.display_name,
        accession_number,
        len(holdings),
        summary["new_positions"],
        summary["sold_out"],
    )
    return summary


def _snapshot_prev_holdings(session: Session, guru_id: int) -> dict[str, float]:
    """
    載入資料庫中現有最新申報的 cusip → shares 快照，作為本次 diff 的基準。

    重要：此函式必須在 save_filing（新申報）之前呼叫，否則會取到剛存入的
    本季資料而非前季資料。

    Args:
        session: Database session
        guru_id: Guru.id

    Returns:
        cusip → shares 映射；若無前季申報則回傳空 dict
    """
    prev_filing = find_latest_filing_by_guru(session, guru_id)
    if prev_filing is None:
        return {}

    prev_holdings = find_holdings_by_filing(session, prev_filing.id)
    return {h.cusip: h.shares for h in prev_holdings}


def _build_holdings(
    raw_holdings: list[dict],
    filing: GuruFiling,
    guru: Guru,
    prev_map: dict[str, float],
    total_value: float,
) -> list[GuruHolding]:
    """
    將 EDGAR 原始持倉列表轉換為 GuruHolding 物件，含分類與計算。

    同時處理前季有但本季完全消失的 CUSIP（SOLD_OUT），
    這類倉位不出現在 EDGAR XML 中，需從 prev_map 補充建立。
    """
    holdings = []
    current_cusips: set[str] = set()

    for raw in raw_holdings:
        cusip = raw["cusip"]
        current_cusips.add(cusip)
        current_shares = raw["shares"]
        previous_shares = prev_map.get(cusip)

        action = classify_holding_change(current_shares, previous_shares)
        change_pct = (
            compute_change_pct(current_shares, previous_shares)
            if previous_shares is not None
            else None
        )
        weight_pct = compute_holding_weight(raw["value"], total_value)
        ticker = map_cusip_to_ticker(cusip, raw["company_name"])

        holdings.append(
            GuruHolding(
                filing_id=filing.id,
                guru_id=guru.id,
                cusip=cusip,
                ticker=ticker,
                company_name=raw["company_name"],
                value=raw["value"],
                shares=current_shares,
                action=action.value,
                change_pct=change_pct,
                weight_pct=weight_pct,
            )
        )

    # 前季存在但本季完全消失 → SOLD_OUT
    for cusip, prev_shares in prev_map.items():
        if cusip not in current_cusips:
            ticker = map_cusip_to_ticker(cusip, "")
            holdings.append(
                GuruHolding(
                    filing_id=filing.id,
                    guru_id=guru.id,
                    cusip=cusip,
                    ticker=ticker,
                    company_name="",
                    value=0.0,
                    shares=0.0,
                    action=HoldingAction.SOLD_OUT.value,
                    change_pct=-100.0,
                    weight_pct=0.0,
                )
            )

    return holdings


def _build_summary(guru: Guru, filing: GuruFiling, holdings: list[GuruHolding]) -> dict:
    """組裝 sync/summary 回傳 dict。"""
    action_counts: dict[str, int] = {
        HoldingAction.NEW_POSITION.value: 0,
        HoldingAction.SOLD_OUT.value: 0,
        HoldingAction.INCREASED.value: 0,
        HoldingAction.DECREASED.value: 0,
    }
    for h in holdings:
        if h.action in action_counts:
            action_counts[h.action] += 1

    top_holdings = sorted(
        [_holding_to_dict(h, filing) for h in holdings if h.weight_pct is not None],
        key=lambda x: x["weight_pct"] or 0,
        reverse=True,
    )[:GURU_TOP_HOLDINGS_COUNT]

    return {
        "guru_id": guru.id,
        "guru_display_name": guru.display_name,
        "status": "synced",
        "accession_number": filing.accession_number,
        "report_date": filing.report_date,
        "filing_date": filing.filing_date,
        "total_value": filing.total_value,
        "holdings_count": len(holdings),
        "filing_url": filing.filing_url,
        "new_positions": action_counts[HoldingAction.NEW_POSITION.value],
        "sold_out": action_counts[HoldingAction.SOLD_OUT.value],
        "increased": action_counts[HoldingAction.INCREASED.value],
        "decreased": action_counts[HoldingAction.DECREASED.value],
        "top_holdings": top_holdings,
    }


def _holding_to_dict(h: GuruHolding, filing: GuruFiling) -> dict:
    """GuruHolding → serializable dict，含所屬申報的日期資訊。"""
    return {
        "id": h.id,
        "guru_id": h.guru_id,
        "cusip": h.cusip,
        "ticker": h.ticker,
        "company_name": h.company_name,
        "value": h.value,
        "shares": h.shares,
        "action": h.action,
        "change_pct": h.change_pct,
        "weight_pct": h.weight_pct,
        "report_date": filing.report_date,
        "filing_date": filing.filing_date,
    }
