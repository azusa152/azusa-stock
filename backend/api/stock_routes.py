"""
API — 股票管理路由。
薄控制器：僅負責解析請求、呼叫 Service、回傳回應。
"""

from application.services import (
    CategoryUnchangedError,
    StockAlreadyActiveError,
    StockAlreadyExistsError,
    StockAlreadyInactiveError,
    StockNotFoundError,
    create_stock,
    deactivate_stock,
    export_stocks,
    get_moat_for_ticker,
    get_portfolio_summary,
    get_removal_history,
    handle_webhook,
    import_stocks,
    list_active_stocks,
    list_removed_stocks,
    reactivate_stock,
    update_display_order,
    update_stock_category,
)
from application.stock_service import get_enriched_stocks
from domain.analysis import compute_bias_percentile, detect_rogue_wave
from domain.constants import (
    ERROR_CATEGORY_UNCHANGED,
    ERROR_INVALID_INPUT,
    ERROR_STOCK_ALREADY_ACTIVE,
    ERROR_STOCK_ALREADY_EXISTS,
    ERROR_STOCK_ALREADY_INACTIVE,
    ERROR_STOCK_NOT_FOUND,
    GENERIC_VALIDATION_ERROR,
    GENERIC_WEBHOOK_ERROR,
    LATEST_SCAN_LOGS_DEFAULT_LIMIT,
    SCAN_HISTORY_DEFAULT_LIMIT,
)
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from i18n import get_user_language, t
from infrastructure.database import get_session
from infrastructure.market_data import (
    get_bias_distribution,
    get_dividend_info,
    get_earnings_date,
    get_price_history,
    get_technical_signals,
)
from logging_config import get_logger
from sqlmodel import Session

from api.rate_limit import limiter
from api.schemas import (
    CategoryUpdateRequest,
    DeactivateRequest,
    ImportResponse,
    MessageResponse,
    PriceAlertCreateRequest,
    ReactivateRequest,
    RemovedStockResponse,
    ReorderRequest,
    StockImportItem,
    StockResponse,
    TickerCreateRequest,
    WebhookRequest,
    WebhookResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/ticker", response_model=StockResponse, summary="Add a stock to the watchlist"
)
def create_ticker_route(
    payload: TickerCreateRequest,
    session: Session = Depends(get_session),
) -> StockResponse:
    """新增股票到追蹤清單。"""
    try:
        stock = create_stock(
            session,
            payload.ticker,
            payload.category,
            payload.thesis,
            payload.tags,
            is_etf=payload.is_etf,
        )
    except StockAlreadyExistsError as e:
        raise HTTPException(
            status_code=409,
            detail={"error_code": ERROR_STOCK_ALREADY_EXISTS, "detail": str(e)},
        )

    return StockResponse(
        ticker=stock.ticker,
        category=stock.category,
        current_thesis=stock.current_thesis,
        current_tags=payload.tags,
        is_active=stock.is_active,
        is_etf=stock.is_etf,
    )


@router.get(
    "/stocks", response_model=list[StockResponse], summary="List all active stocks"
)
def list_stocks_route(
    session: Session = Depends(get_session),
) -> list[StockResponse]:
    """取得所有追蹤中股票（僅 DB 資料，不含技術訊號）。"""
    results = list_active_stocks(session)
    return [StockResponse(**r) for r in results]


@router.get(
    "/stocks/enriched",
    summary="Get all active stocks with signals, earnings, and dividends",
)
def list_enriched_stocks_route(
    session: Session = Depends(get_session),
) -> list[dict]:
    """批次取得所有啟用中股票，附帶技術訊號、財報日期、股息資訊。"""
    return get_enriched_stocks(session)


@router.put(
    "/stocks/reorder",
    response_model=MessageResponse,
    summary="Reorder stock display positions",
)
def reorder_stocks_route(
    payload: ReorderRequest,
    session: Session = Depends(get_session),
) -> dict:
    """批次更新股票顯示順位。"""
    return update_display_order(session, payload.ordered_tickers)


@router.get("/ticker/{ticker}/signals", summary="Get technical signals for a stock")
def get_signals_route(ticker: str) -> dict:
    """取得指定股票的技術訊號（yfinance，含快取）。"""
    ticker_upper = ticker.upper()
    signals = get_technical_signals(ticker_upper) or {}
    if signals and "error" not in signals:
        bias = signals.get("bias")
        volume_ratio = signals.get("volume_ratio")
        dist = get_bias_distribution(ticker_upper)
        bias_percentile: float | None = None
        if dist and bias is not None:
            bias_percentile = compute_bias_percentile(bias, dist["historical_biases"])
        signals["bias_percentile"] = bias_percentile
        signals["is_rogue_wave"] = detect_rogue_wave(bias_percentile, volume_ratio)
    return signals


@router.get(
    "/ticker/{ticker}/price-history", summary="Get 1-year price history for a stock"
)
def get_price_history_route(ticker: str) -> list[dict]:
    """取得指定股票的收盤價歷史（1 年），用於價格趨勢圖。"""
    return get_price_history(ticker.upper()) or []


@router.get("/stocks/export", summary="Export watchlist as JSON")
def export_stocks_route(
    session: Session = Depends(get_session),
) -> list[dict]:
    """匯出所有追蹤中股票（精簡格式，適用於 JSON 下載與匯入）。"""
    return export_stocks(session)


@router.get("/ticker/{ticker}/moat", summary="Get moat analysis (gross margin YoY)")
def get_moat_route(ticker: str, session: Session = Depends(get_session)) -> dict:
    """取得指定股票的護城河趨勢（毛利率 5 季走勢 + YoY 診斷）。Bond / Cash 不適用。"""
    return get_moat_for_ticker(session, ticker)


@router.patch(
    "/ticker/{ticker}/category",
    response_model=MessageResponse,
    summary="Update stock category",
)
def update_category_route(
    ticker: str,
    payload: CategoryUpdateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """切換股票分類。"""
    try:
        return update_stock_category(session, ticker, payload.category)
    except StockNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_STOCK_NOT_FOUND, "detail": str(e)},
        )
    except CategoryUnchangedError as e:
        raise HTTPException(
            status_code=409,
            detail={"error_code": ERROR_CATEGORY_UNCHANGED, "detail": str(e)},
        )


@router.post(
    "/ticker/{ticker}/deactivate",
    response_model=MessageResponse,
    summary="Deactivate a tracked stock",
)
def deactivate_ticker_route(
    ticker: str,
    payload: DeactivateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """移除追蹤股票。"""
    try:
        return deactivate_stock(session, ticker, payload.reason)
    except StockNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_STOCK_NOT_FOUND, "detail": str(e)},
        )
    except StockAlreadyInactiveError as e:
        raise HTTPException(
            status_code=409,
            detail={"error_code": ERROR_STOCK_ALREADY_INACTIVE, "detail": str(e)},
        )


@router.get(
    "/stocks/removed",
    response_model=list[RemovedStockResponse],
    summary="List all removed stocks",
)
def list_removed_stocks_route(
    session: Session = Depends(get_session),
) -> list[RemovedStockResponse]:
    """取得所有已移除股票。"""
    results = list_removed_stocks(session)
    return [RemovedStockResponse(**r) for r in results]


@router.get("/ticker/{ticker}/removals", summary="Get removal history for a stock")
def get_removal_history_route(
    ticker: str,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的移除歷史。"""
    try:
        return get_removal_history(session, ticker)
    except StockNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_STOCK_NOT_FOUND, "detail": str(e)},
        )


@router.post(
    "/ticker/{ticker}/reactivate",
    response_model=MessageResponse,
    summary="Reactivate a removed stock",
)
def reactivate_ticker_route(
    ticker: str,
    payload: ReactivateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """重新啟用已移除的股票。"""
    try:
        return reactivate_stock(session, ticker, payload.category, payload.thesis)
    except StockNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_STOCK_NOT_FOUND, "detail": str(e)},
        )
    except StockAlreadyActiveError as e:
        raise HTTPException(
            status_code=409,
            detail={"error_code": ERROR_STOCK_ALREADY_ACTIVE, "detail": str(e)},
        )


@router.get("/ticker/{ticker}/earnings", summary="Get next earnings date for a stock")
def get_earnings_route(ticker: str) -> dict:
    """取得指定股票的下次財報日期。"""
    return get_earnings_date(ticker.upper())


@router.get("/ticker/{ticker}/dividend", summary="Get dividend info for a stock")
def get_dividend_route(ticker: str) -> dict:
    """取得指定股票的股息資訊。"""
    return get_dividend_info(ticker.upper())


@router.get("/ticker/{ticker}/scan-history", summary="Get scan history for a stock")
def get_scan_history_route(
    ticker: str,
    limit: int = SCAN_HISTORY_DEFAULT_LIMIT,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的掃描歷史。"""
    from application.services import get_scan_history

    try:
        return get_scan_history(session, ticker, limit)
    except StockNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_STOCK_NOT_FOUND, "detail": str(e)},
        )


@router.get("/scan/history", summary="Get latest scan logs across all stocks")
def get_all_scan_history_route(
    limit: int = LATEST_SCAN_LOGS_DEFAULT_LIMIT,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得最近掃描紀錄。"""
    from application.services import get_latest_scan_logs

    return get_latest_scan_logs(session, limit)


@router.post(
    "/ticker/{ticker}/alerts",
    response_model=MessageResponse,
    summary="Create a price alert",
)
def create_price_alert_route(
    ticker: str,
    payload: PriceAlertCreateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """建立價格警報。"""
    from application.services import create_price_alert

    try:
        return create_price_alert(
            session,
            ticker,
            payload.metric,
            payload.operator,
            payload.threshold,
        )
    except StockNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_STOCK_NOT_FOUND, "detail": str(e)},
        )


@router.get("/ticker/{ticker}/alerts", summary="List price alerts for a stock")
def get_price_alerts_route(
    ticker: str,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的價格警報列表。"""
    from application.services import list_price_alerts

    return list_price_alerts(session, ticker)


@router.delete(
    "/alerts/{alert_id}", response_model=MessageResponse, summary="Delete a price alert"
)
def delete_price_alert_route(
    alert_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """刪除價格警報。"""
    from application.services import delete_price_alert

    return delete_price_alert(session, alert_id)


@router.patch(
    "/alerts/{alert_id}/toggle",
    response_model=MessageResponse,
    summary="Toggle a price alert on/off",
)
def toggle_price_alert_route(
    alert_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """切換價格警報啟用狀態。"""
    from application.scan_service import toggle_price_alert

    return toggle_price_alert(session, alert_id)


@router.post(
    "/stocks/import",
    response_model=ImportResponse,
    summary="Bulk import stocks (upsert)",
)
def import_stocks_route(
    payload: list[StockImportItem],
    session: Session = Depends(get_session),
) -> dict:
    """
    批次匯入股票（upsert 邏輯）。

    限制：
    - 最多一次匯入 1000 筆
    - ticker 長度限制 20 字元
    - thesis 長度限制 5000 字元
    """
    if len(payload) > 1000:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=get_user_language(session)),
            },
        )

    # Convert Pydantic models to dicts for the service layer
    payload_dicts = [item.model_dump() for item in payload]
    result = import_stocks(session, payload_dicts)

    # Transform service response to match ImportResponse schema
    return {
        "message": result["message"],
        "imported": result["created"] + result["updated"],
        "errors": result["errors"],
    }


# ===========================================================================
# OpenClaw / AI Agent Endpoints
# ===========================================================================


@router.get(
    "/summary",
    response_class=PlainTextResponse,
    summary="Plain-text portfolio summary for AI agents",
)
def get_summary_route(session: Session = Depends(get_session)) -> str:
    """純文字投資組合摘要，專為 chat / AI agent 設計。"""
    return get_portfolio_summary(session)


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Unified webhook for AI agent actions",
)
@limiter.limit("5/minute")
async def webhook_route(
    request: Request,
    payload: WebhookRequest,
    session: Session = Depends(get_session),
) -> WebhookResponse:
    """
    統一入口 — 供 OpenClaw 等 AI agent 使用。
    支援的 action: help, summary, signals, scan, moat, alerts, add_stock

    Rate limited: 5/minute per IP (prevents webhook abuse).
    """
    try:
        result = handle_webhook(session, payload.action, payload.ticker, payload.params)
        return WebhookResponse(**result)
    except Exception as e:
        logger.error("Webhook 處理失敗：%s", e, exc_info=True)
        return WebhookResponse(
            success=False,
            message=t(GENERIC_WEBHOOK_ERROR, lang=get_user_language(session)),
        )
