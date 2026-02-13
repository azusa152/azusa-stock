"""
Folio — FastAPI 應用程式進入點。
負責建立 App、註冊路由、管理生命週期。
所有業務邏輯已移至 application/services.py。
"""

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
