"""
Application — Resonance Service：計算使用者投資組合與大師持倉的重疊分析。

主要功能：
1. compute_portfolio_resonance  — 全大師 × 全使用者持倉的重疊矩陣
2. get_resonance_for_ticker     — 查詢哪些大師持有指定股票（用於 Radar 徽章）
3. get_great_minds_list         — 「英雄所見略同」清單（使用者 + 大師雙重持有的股票）
"""

from sqlmodel import Session, select

from domain.entities import Holding, Stock
from domain.smart_money import compute_resonance_matches
from infrastructure.repositories import (
    find_all_active_gurus,
    find_holdings_by_guru_latest,
    find_holdings_by_ticker_across_gurus,
    find_latest_filing_by_guru,
)
from logging_config import get_logger

logger = get_logger(__name__)


def compute_portfolio_resonance(session: Session) -> list[dict]:
    """
    計算所有大師的最新持倉與使用者關注清單／實際持倉的重疊。

    流程：
    1. 載入所有啟用中大師的最新持倉（tickers）
    2. 載入使用者的 Stock 關注清單 tickers
    3. 載入使用者的 Holding 實際持倉 tickers
    4. 合併使用者 tickers，對每位大師呼叫 compute_resonance_matches()
    5. 回傳帶有 overlapping_tickers 與各股票最新動作的列表

    Args:
        session: Database session

    Returns:
        list of dicts，每筆代表一位大師的共鳴結果：
            guru_id, guru_display_name,
            overlapping_tickers (list[str]),
            overlap_count (int),
            holdings (list[dict]: ticker, action, weight_pct, change_pct)
    """
    gurus = find_all_active_gurus(session)
    if not gurus:
        logger.info("無啟用中大師，跳過共鳴計算。")
        return []

    # 使用者關注清單（Stock 表，is_active=True）
    watchlist_tickers: set[str] = {
        s.ticker
        for s in session.exec(
            select(Stock).where(Stock.is_active == True)  # noqa: E712
        ).all()
    }

    # 使用者實際持倉（Holding 表）
    holding_tickers: set[str] = {h.ticker for h in session.exec(select(Holding)).all()}

    user_tickers = watchlist_tickers | holding_tickers

    results: list[dict] = []
    for guru in gurus:
        holdings = find_holdings_by_guru_latest(session, guru.id)
        guru_ticker_map: dict[str, dict] = {}
        for h in holdings:
            if h.ticker:
                guru_ticker_map[h.ticker] = {
                    "ticker": h.ticker,
                    "action": h.action,
                    "weight_pct": h.weight_pct,
                    "change_pct": h.change_pct,
                }

        guru_tickers = set(guru_ticker_map.keys())
        overlapping = compute_resonance_matches(guru_tickers, user_tickers)

        results.append(
            {
                "guru_id": guru.id,
                "guru_display_name": guru.display_name,
                "overlapping_tickers": sorted(overlapping),
                "overlap_count": len(overlapping),
                "holdings": [guru_ticker_map[t] for t in sorted(overlapping)],
            }
        )

    # Sort by overlap_count descending so most relevant gurus appear first
    results.sort(key=lambda x: x["overlap_count"], reverse=True)
    logger.info(
        "共鳴計算完成，%d 位大師，共有 %d 位有重疊持倉。",
        len(results),
        sum(1 for r in results if r["overlap_count"] > 0),
    )
    return results


def get_resonance_for_ticker(session: Session, ticker: str) -> list[dict]:
    """
    查詢哪些大師的最新申報中持有指定股票（用於 Radar 頁面徽章顯示）。

    Pre-loads all active gurus and their latest filings in bulk to avoid N+1 queries.

    Args:
        session: Database session
        ticker: 股票代號

    Returns:
        list of dicts，每筆代表一位持有此股票的大師：
            guru_id, guru_display_name,
            action, weight_pct, change_pct,
            report_date, filing_date
    """
    holdings = find_holdings_by_ticker_across_gurus(session, ticker)
    if not holdings:
        return []

    # Pre-load all active gurus and latest filings to avoid N+1 queries
    all_gurus = find_all_active_gurus(session)
    guru_map: dict[int, str] = {g.id: g.display_name for g in all_gurus}
    filing_map: dict[int, object] = {
        g.id: find_latest_filing_by_guru(session, g.id) for g in all_gurus
    }

    results: list[dict] = []
    for holding in holdings:
        filing = filing_map.get(holding.guru_id)
        results.append(
            {
                "guru_id": holding.guru_id,
                "guru_display_name": guru_map.get(holding.guru_id, ""),
                "action": holding.action,
                "weight_pct": holding.weight_pct,
                "change_pct": holding.change_pct,
                "report_date": filing.report_date if filing else None,  # type: ignore[union-attr]
                "filing_date": filing.filing_date if filing else None,  # type: ignore[union-attr]
            }
        )

    return results


def get_great_minds_list(session: Session) -> list[dict]:
    """
    回傳「英雄所見略同」清單：使用者（關注清單或持倉）＋至少一位大師同時持有的股票。

    按持有該股票的大師數量降序排列（大師共識越高越靠前）。

    Args:
        session: Database session

    Returns:
        list of dicts，每筆代表一支共鳴股票：
            ticker,
            guru_count (int),
            gurus (list[dict]: guru_id, guru_display_name, action, weight_pct)
    """
    resonance_results = compute_portfolio_resonance(session)
    if not resonance_results:
        return []

    # Aggregate: ticker → list of guru dicts
    ticker_gurus: dict[str, list[dict]] = {}
    for entry in resonance_results:
        for holding in entry["holdings"]:
            tk = holding["ticker"]
            if tk not in ticker_gurus:
                ticker_gurus[tk] = []
            ticker_gurus[tk].append(
                {
                    "guru_id": entry["guru_id"],
                    "guru_display_name": entry["guru_display_name"],
                    "action": holding["action"],
                    "weight_pct": holding["weight_pct"],
                }
            )

    great_minds = [
        {
            "ticker": ticker,
            "guru_count": len(gurus),
            "gurus": gurus,
        }
        for ticker, gurus in ticker_gurus.items()
    ]
    great_minds.sort(key=lambda x: x["guru_count"], reverse=True)
    return great_minds
