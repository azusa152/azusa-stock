"""
Application — 壓力測試服務。
提供組合壓力測試分析，評估市場崩盤情境下的預期損失。
"""

from sqlmodel import Session, select

from application.rebalance_service import _compute_holding_market_values
from application.stock_service import StockNotFoundError
from domain.constants import CATEGORY_FALLBACK_BETA, DEFAULT_USER_ID
from domain.entities import Holding
from domain.enums import StockCategory
from domain.stress_test import calculate_stress_test as _pure_stress_test
from infrastructure.market_data import (
    get_exchange_rates,
    get_stock_beta,
    prewarm_beta_batch,
)
from logging_config import get_logger

logger = get_logger(__name__)


def calculate_stress_test(
    session: Session, scenario_drop_pct: float, display_currency: str = "USD"
) -> dict:
    """
    計算組合壓力測試：評估市場崩盤情境下的預期損失。

    工作流程：
    1. 讀取所有持倉
    2. 取得匯率，將所有持倉轉換為 display_currency
    3. 計算持倉市值（複用 _compute_holding_market_values）
    4. 批次預熱 Beta 快取（並行取得）
    5. 為每個持倉取得 Beta（使用 category fallback 當 yfinance 未提供時）
    6. 委託 domain.stress_test 純函式計算壓力測試結果

    Args:
        session: DB session
        scenario_drop_pct: 市場崩盤情境 %（負數，如 -20.0 表示大盤跌 20%）
        display_currency: 顯示幣別（預設 USD）

    Returns:
        dict 含壓力測試結果（portfolio_beta, total_loss, pain_level, advice, breakdown）

    Raises:
        StockNotFoundError: 當無任何持倉時

    Privacy: 不記錄絕對金額日誌（僅記錄 portfolio beta 與 scenario %）
    """
    # 1) 取得所有持倉
    holdings = list(
        session.exec(select(Holding).where(Holding.user_id == DEFAULT_USER_ID)).all()
    )

    if not holdings:
        raise StockNotFoundError("尚未輸入任何持倉，請先新增資產。")

    # 2) 取得匯率：收集所有持倉幣別，批次取得相對 display_currency 的匯率
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(display_currency, holding_currencies)

    # 3) 計算持倉市值（複用再平衡服務邏輯）
    _currency_values, _cash_currency_values, ticker_agg = (
        _compute_holding_market_values(holdings, fx_rates)
    )

    # 4) 收集需要 Beta 的標的（排除現金）
    non_cash_tickers = [
        ticker
        for ticker, data in ticker_agg.items()
        if data["category"] != StockCategory.CASH.value
    ]

    # 批次預熱 Beta 快取（並行取得，避免串行呼叫）
    if non_cash_tickers:
        prewarm_beta_batch(non_cash_tickers)

    # 5) 組裝帶 Beta 的持倉清單
    holdings_with_beta: list[dict] = []

    # 計算組合總市值（避免在迴圈內重複計算）
    total_portfolio_value = sum(t["mv"] for t in ticker_agg.values())

    for ticker, data in ticker_agg.items():
        category = data["category"]
        market_value = data["mv"]

        # 取得 Beta（使用 category fallback）
        if category == StockCategory.CASH.value:
            beta = 0.0
        else:
            beta_from_yf = get_stock_beta(ticker)
            if beta_from_yf is not None:
                beta = beta_from_yf
            else:
                # yfinance 未提供，使用 category fallback
                beta = CATEGORY_FALLBACK_BETA.get(category, 1.0)
                logger.debug(
                    "%s Beta 未提供，使用 %s 分類預設值 %.2f",
                    ticker,
                    category,
                    beta,
                )

        # 計算權重百分比（用於組合 Beta 加權）
        weight_pct = (
            (market_value / total_portfolio_value * 100.0)
            if total_portfolio_value > 0
            else 0.0
        )

        holdings_with_beta.append(
            {
                "ticker": ticker,
                "category": category,
                "market_value": market_value,
                "beta": beta,
                "weight_pct": weight_pct,
            }
        )

    # 6) 呼叫 domain 純函式計算壓力測試
    result = _pure_stress_test(holdings_with_beta, scenario_drop_pct)

    # 加入 display_currency（前端需要）
    result["display_currency"] = display_currency

    # Privacy: 僅記錄組合 Beta 與情境參數（不記錄絕對金額）
    logger.info(
        "壓力測試完成：Beta=%.2f, 情境=%.1f%%, 痛苦等級=%s",
        result["portfolio_beta"],
        scenario_drop_pct,
        result["pain_level"]["level"],
    )

    return result
