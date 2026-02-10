"""
API — 股票管理路由。
薄控制器：僅負責解析請求、呼叫 Service、回傳回應。
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from api.schemas import (
    CategoryUpdateRequest,
    DeactivateRequest,
    ReactivateRequest,
    ReorderRequest,
    RemovedStockResponse,
    StockResponse,
    TickerCreateRequest,
    WebhookRequest,
    WebhookResponse,
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
    get_portfolio_summary,
    get_removal_history,
    import_stocks,
    list_active_stocks,
    list_removed_stocks,
    reactivate_stock,
    update_display_order,
    update_stock_category,
)
from domain.constants import (
    ETF_MOAT_NA_MESSAGE,
    LATEST_SCAN_LOGS_DEFAULT_LIMIT,
    SCAN_HISTORY_DEFAULT_LIMIT,
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
        return {"ticker": upper_ticker, "moat": "N/A", "details": ETF_MOAT_NA_MESSAGE}
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
    limit: int = SCAN_HISTORY_DEFAULT_LIMIT,
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
    limit: int = LATEST_SCAN_LOGS_DEFAULT_LIMIT,
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


# ===========================================================================
# OpenClaw / AI Agent Endpoints
# ===========================================================================


@router.get("/summary", response_class=PlainTextResponse)
def get_summary_route(session: Session = Depends(get_session)) -> str:
    """純文字投資組合摘要，專為 chat / AI agent 設計。"""
    return get_portfolio_summary(session)


@router.post("/webhook", response_model=WebhookResponse)
def webhook_route(
    payload: WebhookRequest,
    session: Session = Depends(get_session),
) -> WebhookResponse:
    """
    統一入口 — 供 OpenClaw 等 AI agent 使用。
    支援的 action: summary, signals, scan, moat, alerts, add_stock
    """
    import threading as _threading

    action = payload.action.lower().strip()
    ticker = payload.ticker.upper().strip() if payload.ticker else None

    try:
        if action == "summary":
            text = get_portfolio_summary(session)
            return WebhookResponse(success=True, message=text)

        if action == "signals":
            if not ticker:
                return WebhookResponse(success=False, message="請提供 ticker 參數。")
            result = get_technical_signals(ticker)
            if not result or "error" in result:
                return WebhookResponse(
                    success=False,
                    message=result.get("error", "無法取得技術訊號。") if result else "無法取得技術訊號。",
                )
            status_text = "\n".join(result.get("status", []))
            msg = (
                f"{ticker} — 現價 ${result.get('price')}, RSI={result.get('rsi')}, "
                f"Bias={result.get('bias')}%\n{status_text}"
            )
            return WebhookResponse(success=True, message=msg, data=result)

        if action == "scan":
            from application.services import run_scan as _run_scan
            from infrastructure.database import engine as _engine

            def _bg_scan() -> None:
                with Session(_engine) as s:
                    _run_scan(s)

            _threading.Thread(target=_bg_scan, daemon=True).start()
            return WebhookResponse(success=True, message="掃描已在背景啟動，結果將透過 Telegram 通知。")

        if action == "moat":
            if not ticker:
                return WebhookResponse(success=False, message="請提供 ticker 參數。")
            from infrastructure.market_data import analyze_moat_trend
            result = analyze_moat_trend(ticker)
            details = result.get("details", "N/A")
            return WebhookResponse(
                success=True,
                message=f"{ticker} 護城河：{result.get('moat', 'N/A')} — {details}",
                data=result,
            )

        if action == "alerts":
            if not ticker:
                return WebhookResponse(success=False, message="請提供 ticker 參數。")
            from application.services import list_price_alerts
            alerts = list_price_alerts(session, ticker)
            if not alerts:
                return WebhookResponse(success=True, message=f"{ticker} 目前沒有設定價格警報。")
            lines = [f"{ticker} 價格警報："]
            for a in alerts:
                op_str = "<" if a["operator"] == "lt" else ">"
                lines.append(f"  {a['metric']} {op_str} {a['threshold']} ({'啟用' if a['is_active'] else '停用'})")
            return WebhookResponse(success=True, message="\n".join(lines), data={"alerts": alerts})

        if action == "add_stock":
            params = payload.params
            t = params.get("ticker", ticker)
            if not t:
                return WebhookResponse(success=False, message="請提供 ticker 參數。")
            cat_str = params.get("category", "Growth")
            thesis = params.get("thesis", "由 AI agent 新增。")
            tags = params.get("tags", [])
            try:
                from domain.enums import StockCategory as _SC
                stock = create_stock(session, t, _SC(cat_str), thesis, tags)
                return WebhookResponse(
                    success=True,
                    message=f"✅ 已新增 {stock.ticker} 到 {cat_str} 分類。",
                )
            except StockAlreadyExistsError as e:
                return WebhookResponse(success=False, message=str(e))
            except ValueError:
                return WebhookResponse(success=False, message=f"無效的分類：{cat_str}")

        return WebhookResponse(
            success=False,
            message=f"不支援的 action: {action}。支援：summary, signals, scan, moat, alerts, add_stock",
        )

    except Exception as e:
        return WebhookResponse(success=False, message=f"錯誤：{e}")
