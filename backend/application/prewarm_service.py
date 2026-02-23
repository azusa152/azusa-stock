"""
Application — 啟動快取預熱服務。
非阻塞式背景執行，在 FastAPI lifespan 啟動後填充 L1/L2 快取，
讓前端首次載入即可命中暖快取。
"""

import time

from sqlmodel import Session, select

from domain.constants import (
    EQUITY_CATEGORIES,
    GURU_BACKFILL_YEARS,
    SKIP_MOAT_CATEGORIES,
    SKIP_SIGNALS_CATEGORIES,
)
from domain.entities import Holding, Stock
from infrastructure.database import engine
from infrastructure.repositories import find_all_active_gurus
from infrastructure.market_data import (
    get_etf_sector_weights,
    get_fear_greed_index,
    get_ticker_sector,
    prewarm_beta_batch,
    prewarm_etf_holdings_batch,
    prewarm_moat_batch,
    prewarm_signals_batch,
)
from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 常數
# ---------------------------------------------------------------------------
_DEFAULT_USER_ID = "default"


def prewarm_all_caches() -> None:
    """非阻塞式啟動預熱 — 填充 L1/L2 快取。

    依序預熱：
    1. 技術訊號（signals + piggyback price history）
    2. 恐懼與貪婪指數（Fear & Greed）
    3. 護城河趨勢（moat）— 排除 Bond/Cash
    4. ETF 成分股（etf_holdings）— 僅 is_etf=True 的標的
    5. Beta 值（beta）— 壓力測試用，排除 Cash

    整個流程以 try/except 包裹，確保任何失敗都不會影響應用程式正常運作。
    """
    start = time.monotonic()
    logger.info("快取預熱啟動...")

    try:
        tickers = _collect_tickers()
    except Exception as exc:
        logger.error("快取預熱：無法讀取資料庫，中止預熱。%s", exc, exc_info=True)
        return

    if not tickers["all"]:
        logger.info("快取預熱：資料庫中無任何股票或持倉，跳過預熱。")
        return

    logger.info(
        "快取預熱：共 %d 檔標的（signals=%d, moat=%d, equity=%d, etf=%d, beta=%d, etf_sector_weights=%d）",
        len(tickers["all"]),
        len(tickers["signals"]),
        len(tickers["moat"]),
        len(tickers["equity"]),
        len(tickers["etf"]),
        len(tickers["beta"]),
        len(tickers["etf"]),
    )

    # Phase 1: 技術訊號（含 piggyback price history）
    _prewarm_phase("signals", lambda: prewarm_signals_batch(tickers["signals"]))

    # Phase 2: 恐懼與貪婪指數
    _prewarm_phase("fear_greed", get_fear_greed_index)

    # Phase 3: 護城河趨勢
    _prewarm_phase("moat", lambda: prewarm_moat_batch(tickers["moat"]))

    # Phase 4: ETF 成分股
    if tickers["etf"]:
        _prewarm_phase(
            "etf_holdings", lambda: prewarm_etf_holdings_batch(tickers["etf"])
        )

    # Phase 5: Beta 值（壓力測試用）
    if tickers["beta"]:
        _prewarm_phase("beta", lambda: prewarm_beta_batch(tickers["beta"]))

    # Phase 6: Smart Money 歷史 13F 回填（非阻塞、冪等）
    _prewarm_phase("guru_backfill", _backfill_all_gurus)

    # Phase 7: 行業板塊（sector）— 供 rebalance 端點快取讀取使用
    # 使用 equity 名單（EQUITY_CATEGORIES）填充磁碟快取，與 sector_exposure 邏輯完全對齊。
    if tickers["equity"]:
        _prewarm_phase("sector", lambda: _prewarm_sectors(tickers["equity"]))

    # Phase 8: ETF 行業板塊權重（etf_sector_weights）— ETF 穿透板塊計算的 Approach B
    # 僅針對 is_etf=True 的標的，填充 yfinance funds_data.sector_weightings 快取。
    if tickers["etf"]:
        _prewarm_phase(
            "etf_sector_weights",
            lambda: _prewarm_etf_sector_weights(tickers["etf"]),
        )

    elapsed = time.monotonic() - start
    logger.info("快取預熱完成，耗時 %.1f 秒。", elapsed)


# ---------------------------------------------------------------------------
# 內部 Helpers
# ---------------------------------------------------------------------------


def _collect_tickers() -> dict[str, list[str]]:
    """從 DB 收集需要預熱的 ticker 清單。

    回傳 dict:
        - all: 所有 unique tickers（watchlist + holdings，排除 Cash 類）
        - signals: 需要技術訊號的 tickers（排除 Cash）
        - moat: 需要護城河分析的 tickers（排除 Bond/Cash）
        - etf: 需要 ETF 成分股的 tickers（is_etf=True）
        - beta: 需要 Beta 值的 tickers（壓力測試用，排除 Cash）
    """
    with Session(engine) as session:
        # 活躍追蹤清單
        stocks = list(
            session.exec(select(Stock).where(Stock.is_active == True)).all()  # noqa: E712
        )
        # 持倉（排除現金）
        holdings = list(
            session.exec(
                select(Holding).where(
                    Holding.user_id == _DEFAULT_USER_ID,
                    Holding.is_cash == False,  # noqa: E712
                )
            ).all()
        )

    stock_map = {s.ticker: s for s in stocks}
    holding_tickers = {h.ticker for h in holdings}

    # Union of watchlist + holdings (unique)
    all_tickers = set(stock_map.keys()) | holding_tickers

    # Signals: 排除 Cash 類
    signals_tickers = [
        t
        for t in all_tickers
        if t not in stock_map
        or stock_map[t].category.value not in SKIP_SIGNALS_CATEGORIES
    ]

    # Moat: 排除 Bond/Cash
    moat_tickers = [
        t
        for t in all_tickers
        if t not in stock_map or stock_map[t].category.value not in SKIP_MOAT_CATEGORIES
    ]

    # ETF: 只有追蹤清單中 is_etf=True 的標的
    etf_tickers = [t for t, s in stock_map.items() if s.is_etf]

    # Beta: 與 signals 使用相同範圍（排除 Cash）
    # 若未來需要不同過濾邏輯（如包含 Bond），再拆分
    beta_tickers = signals_tickers

    # Equity: 與 rebalance 端點 sector_exposure 使用相同範圍（EQUITY_CATEGORIES）
    # 確保預熱涵蓋所有需要板塊資訊的標的，避免首次請求顯示 "Unknown"
    equity_tickers = [
        t
        for t in all_tickers
        if t not in stock_map or stock_map[t].category.value in EQUITY_CATEGORIES
    ]

    return {
        "all": sorted(all_tickers),
        "signals": sorted(signals_tickers),
        "moat": sorted(moat_tickers),
        "etf": sorted(etf_tickers),
        "beta": sorted(beta_tickers),
        "equity": sorted(equity_tickers),
    }


def _backfill_all_gurus() -> None:
    """對所有啟用中大師執行 5 年 13F 歷史回填。

    冪等：已同步的申報自動跳過，重複啟動安全。
    """
    # Late import to avoid circular dependency (prewarm → filing_service → repositories)
    from application.filing_service import backfill_guru_filings  # noqa: PLC0415

    with Session(engine) as session:
        gurus = find_all_active_gurus(session)

    if not gurus:
        logger.info("快取預熱 [guru_backfill] 無啟用中大師，跳過回填。")
        return

    logger.info("快取預熱 [guru_backfill] 開始回填 %d 位大師...", len(gurus))
    for guru in gurus:
        try:
            with Session(engine) as session:
                result = backfill_guru_filings(
                    session, guru.id, years=GURU_BACKFILL_YEARS
                )
            logger.info(
                "回填完成：%s，窗口內 %d 筆，已同步 %d，跳過 %d，錯誤 %d",
                guru.display_name,
                result["total_filings"],
                result["synced"],
                result["skipped"],
                result["errors"],
            )
        except Exception as exc:
            logger.warning(
                "快取預熱 [guru_backfill] 大師回填失敗：%s (ID=%d), error=%s",
                guru.display_name,
                guru.id,
                exc,
            )


def _prewarm_sectors(tickers: list[str]) -> None:
    """對股票類持倉逐一呼叫 get_ticker_sector()，填充磁碟快取。

    在背景執行緒中順序處理；失敗的單筆記錄警告後繼續，不中斷整個預熱流程。
    """
    total = len(tickers)
    ok = 0
    for i, ticker in enumerate(tickers, 1):
        try:
            sector = get_ticker_sector(ticker)
            ok += 1
            logger.debug(
                "快取預熱 [sector] (%d/%d) %s → %s", i, total, ticker, sector or "N/A"
            )
        except Exception as exc:
            logger.warning(
                "快取預熱 [sector] (%d/%d) %s 失敗：%s", i, total, ticker, exc
            )
    logger.info("快取預熱 [sector] 完成 %d/%d 筆。", ok, total)


def _prewarm_etf_sector_weights(tickers: list[str]) -> None:
    """對 ETF 標的逐一呼叫 get_etf_sector_weights()，填充磁碟快取。

    在背景執行緒中順序處理；失敗的單筆記錄警告後繼續，不中斷整個預熱流程。
    """
    total = len(tickers)
    ok = 0
    for i, ticker in enumerate(tickers, 1):
        try:
            weights = get_etf_sector_weights(ticker)
            ok += 1
            logger.debug(
                "快取預熱 [etf_sector_weights] (%d/%d) %s → %d 板塊",
                i,
                total,
                ticker,
                len(weights) if weights else 0,
            )
        except Exception as exc:
            logger.warning(
                "快取預熱 [etf_sector_weights] (%d/%d) %s 失敗：%s",
                i,
                total,
                ticker,
                exc,
            )
    logger.info("快取預熱 [etf_sector_weights] 完成 %d/%d 筆。", ok, total)


def _prewarm_phase(name: str, fn) -> None:
    """執行單一預熱階段，失敗時記錄警告但不中斷後續階段。"""
    try:
        phase_start = time.monotonic()
        fn()
        elapsed = time.monotonic() - phase_start
        logger.info("快取預熱 [%s] 完成，耗時 %.1f 秒。", name, elapsed)
    except Exception as exc:
        logger.warning("快取預熱 [%s] 失敗（非致命）：%s", name, exc, exc_info=True)
