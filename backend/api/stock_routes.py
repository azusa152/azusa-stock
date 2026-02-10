"""
API — 股票管理路由。
薄控制器：僅負責解析請求、呼叫 Service、回傳回應。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.schemas import (
    CategoryUpdateRequest,
    DeactivateRequest,
    ReactivateRequest,
    ReorderRequest,
    RemovedStockResponse,
    StockResponse,
    TickerCreateRequest,
)
from application.services import (
    CategoryUnchangedError,
    StockAlreadyActiveError,
    StockAlreadyExistsError,
    StockAlreadyInactiveError,
    StockNotFoundError,
    create_stock,
    deactivate_stock,
    export_stocks,
    get_removal_history,
    import_stocks,
    list_active_stocks,
    list_removed_stocks,
    reactivate_stock,
    update_display_order,
    update_stock_category,
)
from domain.enums import StockCategory
from infrastructure import repositories as repo
from infrastructure.database import get_session
from infrastructure.market_data import (
    analyze_moat_trend,
    get_dividend_info,
    get_earnings_date,
    get_technical_signals,
)

router = APIRouter()


@router.post("/ticker", response_model=StockResponse)
def create_ticker_route(
    payload: TickerCreateRequest,
    session: Session = Depends(get_session),
) -> StockResponse:
    """新增股票到追蹤清單。"""
    try:
        stock = create_stock(
            session, payload.ticker, payload.category, payload.thesis, payload.tags
        )
    except StockAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return StockResponse(
        ticker=stock.ticker,
        category=stock.category,
        current_thesis=stock.current_thesis,
        current_tags=payload.tags,
        is_active=stock.is_active,
    )


@router.get("/stocks", response_model=list[StockResponse])
def list_stocks_route(
    session: Session = Depends(get_session),
) -> list[StockResponse]:
    """取得所有追蹤中股票（僅 DB 資料，不含技術訊號）。"""
    results = list_active_stocks(session)
    return [StockResponse(**r) for r in results]


@router.put("/stocks/reorder")
def reorder_stocks_route(
    payload: ReorderRequest,
    session: Session = Depends(get_session),
) -> dict:
    """批次更新股票顯示順位。"""
    return update_display_order(session, payload.ordered_tickers)


@router.get("/ticker/{ticker}/signals")
def get_signals_route(ticker: str) -> dict:
    """取得指定股票的技術訊號（yfinance，含快取）。"""
    return get_technical_signals(ticker.upper()) or {}


@router.get("/stocks/export")
def export_stocks_route(
    session: Session = Depends(get_session),
) -> list[dict]:
    """匯出所有追蹤中股票（精簡格式，適用於 JSON 下載與匯入）。"""
    return export_stocks(session)


@router.get("/ticker/{ticker}/moat")
def get_moat_route(ticker: str, session: Session = Depends(get_session)) -> dict:
    """取得指定股票的護城河趨勢（毛利率 5 季走勢 + YoY 診斷）。ETF 不適用。"""
    upper_ticker = ticker.upper()
    stock = repo.find_stock_by_ticker(session, upper_ticker)
    if stock and stock.category == StockCategory.ETF:
        return {"ticker": upper_ticker, "moat": "N/A", "details": "ETF 不適用護城河分析"}
    return analyze_moat_trend(upper_ticker)


@router.patch("/ticker/{ticker}/category")
def update_category_route(
    ticker: str,
    payload: CategoryUpdateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """切換股票分類。"""
    try:
        return update_stock_category(session, ticker, payload.category)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CategoryUnchangedError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/ticker/{ticker}/deactivate")
def deactivate_ticker_route(
    ticker: str,
    payload: DeactivateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """移除追蹤股票。"""
    try:
        return deactivate_stock(session, ticker, payload.reason)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StockAlreadyInactiveError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/stocks/removed", response_model=list[RemovedStockResponse])
def list_removed_stocks_route(
    session: Session = Depends(get_session),
) -> list[RemovedStockResponse]:
    """取得所有已移除股票。"""
    results = list_removed_stocks(session)
    return [RemovedStockResponse(**r) for r in results]


@router.get("/ticker/{ticker}/removals")
def get_removal_history_route(
    ticker: str,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的移除歷史。"""
    try:
        return get_removal_history(session, ticker)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ticker/{ticker}/reactivate")
def reactivate_ticker_route(
    ticker: str,
    payload: ReactivateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """重新啟用已移除的股票。"""
    try:
        return reactivate_stock(session, ticker, payload.category, payload.thesis)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StockAlreadyActiveError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/ticker/{ticker}/earnings")
def get_earnings_route(ticker: str) -> dict:
    """取得指定股票的下次財報日期。"""
    return get_earnings_date(ticker.upper())


@router.get("/ticker/{ticker}/dividend")
def get_dividend_route(ticker: str) -> dict:
    """取得指定股票的股息資訊。"""
    return get_dividend_info(ticker.upper())


@router.get("/ticker/{ticker}/scan-history")
def get_scan_history_route(
    ticker: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的掃描歷史。"""
    from application.services import get_scan_history
    try:
        return get_scan_history(session, ticker, limit)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scan/history")
def get_all_scan_history_route(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得最近掃描紀錄。"""
    from application.services import get_latest_scan_logs
    return get_latest_scan_logs(session, limit)


@router.post("/ticker/{ticker}/alerts")
def create_price_alert_route(
    ticker: str,
    payload: dict,
    session: Session = Depends(get_session),
) -> dict:
    """建立價格警報。"""
    from application.services import create_price_alert
    try:
        return create_price_alert(
            session,
            ticker,
            payload.get("metric", "rsi"),
            payload.get("operator", "lt"),
            payload.get("threshold", 30.0),
        )
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/ticker/{ticker}/alerts")
def get_price_alerts_route(
    ticker: str,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的價格警報列表。"""
    from application.services import list_price_alerts
    return list_price_alerts(session, ticker)


@router.delete("/alerts/{alert_id}")
def delete_price_alert_route(
    alert_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """刪除價格警報。"""
    from application.services import delete_price_alert
    return delete_price_alert(session, alert_id)


@router.post("/stocks/import")
def import_stocks_route(
    payload: list[dict],
    session: Session = Depends(get_session),
) -> dict:
    """批次匯入股票（upsert 邏輯）。"""
    return import_stocks(session, payload)
