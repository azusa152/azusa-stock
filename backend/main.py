"""
Folio — FastAPI 應用程式進入點。
負責建立 App、註冊路由、管理生命週期。
所有業務邏輯已移至 application/services.py。
"""

import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.forex_routes import router as forex_router
from api.fx_watch_routes import router as fx_watch_router
from api.holding_routes import router as holding_router
from api.persona_routes import router as persona_router
from api.preferences_routes import router as preferences_router
from api.scan_routes import router as scan_router
from api.schemas import HealthResponse
from api.stock_routes import router as stock_router
from api.telegram_routes import router as telegram_router
from api.thesis_routes import router as thesis_router
from infrastructure.database import create_db_and_tables
from logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: 啟動時建立資料表
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Folio 後端啟動中 — 初始化資料庫...")
    create_db_and_tables()
    logger.info("資料庫初始化完成，服務就緒。")

    # 背景快取預熱（非阻塞，daemon=True 確保不影響關閉）
    from application.prewarm_service import prewarm_all_caches

    threading.Thread(target=prewarm_all_caches, daemon=True).start()
    logger.info("背景快取預熱已啟動。")

    yield
    logger.info("Folio 後端關閉中...")


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Folio API",
    description="Folio — 智能資產配置",
    version="2.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, summary="Health check")
def health_check() -> dict:
    return {"status": "ok", "service": "folio-backend"}


@app.post("/admin/cache/clear", summary="Clear all backend caches (L1 + L2)")
def clear_cache() -> dict:
    from infrastructure.market_data import clear_all_caches

    result = clear_all_caches()
    return {"status": "ok", **result}


# ---------------------------------------------------------------------------
# 註冊路由
# ---------------------------------------------------------------------------

app.include_router(stock_router)
app.include_router(thesis_router)
app.include_router(scan_router)
app.include_router(persona_router)
app.include_router(holding_router)
app.include_router(telegram_router)
app.include_router(preferences_router)
app.include_router(forex_router)
app.include_router(fx_watch_router)
