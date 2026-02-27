"""
Application — 啟動快取預熱服務。
非阻塞式背景執行，在 FastAPI lifespan 啟動後填充 L1/L2 快取，
讓前端首次載入即可命中暖快取。
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlmodel import Session, select

from domain.constants import (
    DEFAULT_USER_ID,
    EQUITY_CATEGORIES,
    GURU_BACKFILL_YEARS,
    SCAN_THREAD_POOL_SIZE,
    SKIP_MOAT_CATEGORIES,
    SKIP_SIGNALS_CATEGORIES,
)
from domain.entities import Holding, Stock
from infrastructure.database import engine
from infrastructure.market_data import (
    batch_download_history,
    get_etf_sector_weights,
    get_fear_greed_index,
    get_ticker_sector,
    prewarm_beta_batch,
    prewarm_etf_holdings_batch,
    prewarm_moat_batch,
    prewarm_signals_batch,
    prime_signals_cache_batch,
)
from infrastructure.repositories import find_all_active_gurus
from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 預熱就緒旗標（供 /prewarm-status 端點查詢）
# ---------------------------------------------------------------------------
_prewarm_ready = False
_prewarm_lock = threading.Lock()


def is_prewarm_ready() -> bool:
    """回傳快取預熱是否已完成。"""
    return _prewarm_ready


def _set_prewarm_ready(value: bool) -> None:
    global _prewarm_ready
    with _prewarm_lock:
        _prewarm_ready = value


def prewarm_all_caches() -> None:
    """非阻塞式啟動預熱 — 填充 L1/L2 快取。

    流程：
    1. 技術訊號（batch_download_history + prime_signals_cache_batch，一次 HTTP 請求）
    2. 其餘各階段並行執行：moat、fear_greed、etf_holdings、beta、
       guru_backfill、sector、etf_sector_weights

    整個流程以 try/except 包裹，確保任何失敗都不會影響應用程式正常運作。
    """
    start = time.monotonic()
    logger.info("快取預熱啟動...")

    try:
        tickers = _collect_tickers()
    except Exception as exc:
        logger.error("快取預熱：無法讀取資料庫，中止預熱。%s", exc, exc_info=True)
        _set_prewarm_ready(True)  # 服務仍可運作，只是快取為冷啟動狀態
        return

    if not tickers["all"]:
        logger.info("快取預熱：資料庫中無任何股票或持倉，跳過預熱。")
        _set_prewarm_ready(True)
        return

    logger.info(
        "快取預熱：共 %d 檔標的（signals=%d, moat=%d, sector=%d, etf=%d, beta=%d, etf_sector_weights=%d）",
        len(tickers["all"]),
        len(tickers["signals"]),
        len(tickers["moat"]),
        len(tickers["sector"]),
        len(tickers["etf"]),
        len(tickers["beta"]),
        len(tickers["etf"]),
    )

    # Phase 1: 技術訊號（批次下載，大幅減少 HTTP 請求數量）
    _prewarm_phase("signals", lambda: _batch_prewarm_signals(tickers["signals"]))

    # Phase 2+: 其餘階段並行執行（互相獨立，不依賴 Phase 1 結果）
    # moat 預熱使用 4 個工作執行緒（預設 SCAN_THREAD_POOL_SIZE=2 限制吞吐量；
    # 提高並行度讓執行緒在全域限流器釋放時立即接手，縮短整體等待時間）
    _MOAT_PREWARM_WORKERS = 4
    parallel_phases: list[tuple[str, object]] = [
        ("fear_greed", get_fear_greed_index),
        (
            "moat",
            lambda: prewarm_moat_batch(
                tickers["moat"], max_workers=_MOAT_PREWARM_WORKERS
            ),
        ),
        ("guru_backfill", _backfill_all_gurus),
    ]
    if tickers["etf"]:
        parallel_phases.append(
            ("etf_holdings", lambda: prewarm_etf_holdings_batch(tickers["etf"]))
        )
        parallel_phases.append(
            ("etf_sector_weights", lambda: _prewarm_etf_sector_weights(tickers["etf"]))
        )
    if tickers["beta"]:
        parallel_phases.append(("beta", lambda: prewarm_beta_batch(tickers["beta"])))
    if tickers["sector"]:
        parallel_phases.append(("sector", lambda: _prewarm_sectors(tickers["sector"])))

    with ThreadPoolExecutor(max_workers=min(len(parallel_phases), 4)) as pool:
        phase_futures = {
            pool.submit(_prewarm_phase, name, fn): name for name, fn in parallel_phases
        }
        for future in as_completed(phase_futures):
            phase_name = phase_futures[future]
            try:
                future.result()
            except Exception as exc:
                logger.warning(
                    "快取預熱並行階段 [%s] 發生未預期錯誤：%s", phase_name, exc
                )

    elapsed = time.monotonic() - start
    logger.info("快取預熱完成，耗時 %.1f 秒。", elapsed)
    _set_prewarm_ready(True)


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
                    Holding.user_id == DEFAULT_USER_ID,
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

    # Moat: 排除 Bond/Cash 及 ETF（ETF 無損益表，moat 分析必定失敗）
    moat_tickers = [
        t
        for t in all_tickers
        if t not in stock_map
        or (
            stock_map[t].category.value not in SKIP_MOAT_CATEGORIES
            and not stock_map[t].is_etf
        )
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

    # Sector: 熱力圖需要包含 Bond 類標的（Bond 有 GICS 板塊，只是不做訊號/護城河）
    # SKIP_SIGNALS_CATEGORIES（僅 Cash）排除的標的，其餘均需板塊資訊
    sector_tickers = [
        t
        for t in all_tickers
        if t not in stock_map
        or stock_map[t].category.value not in SKIP_SIGNALS_CATEGORIES
    ]

    return {
        "all": sorted(all_tickers),
        "signals": sorted(signals_tickers),
        "moat": sorted(moat_tickers),
        "etf": sorted(etf_tickers),
        "beta": sorted(beta_tickers),
        "equity": sorted(equity_tickers),
        "sector": sorted(sector_tickers),
    }


def _batch_prewarm_signals(signal_tickers: list[str]) -> None:
    """批次下載所有標的歷史資料（一次 HTTP 請求），再並行計算訊號填充快取。
    若批次下載失敗或部分標的缺資料，回退至逐一呼叫。
    """
    if not signal_tickers:
        return

    hist_batch = batch_download_history(signal_tickers)
    if hist_batch:
        primed = prime_signals_cache_batch(hist_batch)
        logger.info(
            "快取預熱 [signals] 批次預熱 %d/%d 檔。", primed, len(signal_tickers)
        )
        # 回退：批次下載中缺失的標的（非 US 市場、資料不足等）
        missed = [t for t in signal_tickers if t not in hist_batch]
        if missed:
            logger.info(
                "快取預熱 [signals] 回退至個別呼叫：%d 檔（%s）。",
                len(missed),
                ", ".join(missed),
            )
            prewarm_signals_batch(missed)
    else:
        # 批次下載完全失敗，回退至個別呼叫
        logger.warning("快取預熱 [signals] 批次下載失敗，回退至個別呼叫。")
        prewarm_signals_batch(signal_tickers)


def _backfill_all_gurus() -> None:
    """對所有啟用中大師執行 5 年 13F 歷史回填。

    冪等：已同步的申報自動跳過，重複啟動安全。
    """
    # Late import to avoid circular dependency (prewarm → filing_service → repositories)
    from application.stock.filing_service import backfill_guru_filings

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
    """對股票類持倉並行呼叫 get_ticker_sector()，填充磁碟快取。

    以 ThreadPoolExecutor 並行處理；失敗的單筆記錄警告後繼續，不中斷整個預熱流程。
    """
    total = len(tickers)
    ok_count = 0

    def _fetch_one(ticker: str) -> tuple[str, bool]:
        sector = get_ticker_sector(ticker)
        logger.debug("快取預熱 [sector] %s → %s", ticker, sector or "N/A")
        return ticker, True

    with ThreadPoolExecutor(max_workers=SCAN_THREAD_POOL_SIZE) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                future.result()
                ok_count += 1
            except Exception as exc:
                logger.warning("快取預熱 [sector] %s 失敗：%s", ticker, exc)
    logger.info("快取預熱 [sector] 完成 %d/%d 筆。", ok_count, total)


def _prewarm_etf_sector_weights(tickers: list[str]) -> None:
    """對 ETF 標的並行呼叫 get_etf_sector_weights()，填充磁碟快取。

    以 ThreadPoolExecutor 並行處理；失敗的單筆記錄警告後繼續，不中斷整個預熱流程。
    """
    total = len(tickers)
    ok_count = 0

    def _fetch_one(ticker: str) -> tuple[str, int]:
        weights = get_etf_sector_weights(ticker)
        sector_count = len(weights) if weights else 0
        logger.debug("快取預熱 [etf_sector_weights] %s → %d 板塊", ticker, sector_count)
        return ticker, sector_count

    with ThreadPoolExecutor(max_workers=SCAN_THREAD_POOL_SIZE) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                future.result()
                ok_count += 1
            except Exception as exc:
                logger.warning("快取預熱 [etf_sector_weights] %s 失敗：%s", ticker, exc)
    logger.info("快取預熱 [etf_sector_weights] 完成 %d/%d 筆。", ok_count, total)


def _prewarm_phase(name: str, fn) -> None:
    """執行單一預熱階段，失敗時記錄警告但不中斷後續階段。"""
    try:
        phase_start = time.monotonic()
        fn()
        elapsed = time.monotonic() - phase_start
        logger.info("快取預熱 [%s] 完成，耗時 %.1f 秒。", name, elapsed)
    except Exception as exc:
        logger.warning("快取預熱 [%s] 失敗（非致命）：%s", name, exc, exc_info=True)
