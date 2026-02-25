"""
Folio — FastAPI 應用程式進入點。
負責建立 App、註冊路由、管理生命週期。
所有業務邏輯已移至 application/services.py。
"""

import os
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlmodel import Session

from api.dependencies import require_api_key
from api.rate_limit import limiter
from api.routes.forex_routes import router as forex_router
from api.routes.fx_watch_routes import router as fx_watch_router
from api.routes.guru_routes import resonance_router, router as guru_router
from api.routes.holding_routes import router as holding_router
from api.routes.persona_routes import router as persona_router
from api.routes.preferences_routes import router as preferences_router
from api.routes.scan_routes import router as scan_router
from api.routes.snapshot_routes import router as snapshot_router
from api.routes.stock_routes import router as stock_router
from api.routes.telegram_routes import router as telegram_router
from api.routes.thesis_routes import router as thesis_router
from api.schemas import HealthResponse
from infrastructure.database import create_db_and_tables
from config.settings import init_settings
from logging_config import get_logger

# Load environment variables from .env file
load_dotenv()
init_settings()

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: 啟動時建立資料表
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Folio 後端啟動中 — 初始化資料庫...")
    create_db_and_tables()
    logger.info("資料庫初始化完成，服務就緒。")

    # 種入系統預設大師（冪等）
    from application.guru.guru_service import seed_default_gurus
    from infrastructure.database import engine

    with Session(engine) as _session:
        seed_default_gurus(_session)

    # 背景快取預熱（非阻塞，daemon=True 確保不影響關閉）
    from application.scan.prewarm_service import prewarm_all_caches

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
    # Auth applied per-router, NOT globally (health must be exempt)
)

# Register rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGIN", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["X-API-Key", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, summary="Health check")
def health_check() -> dict:
    """Health check endpoint - NO auth (Docker healthcheck must access without key)."""
    return {"status": "ok", "service": "folio-backend"}


@app.post(
    "/admin/cache/clear",
    summary="Clear all backend caches (L1 + L2)",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("10/minute")
def clear_cache(request: Request) -> dict:
    """Admin endpoint - WITH auth and rate limiting."""
    from infrastructure.market_data import clear_all_caches

    result = clear_all_caches()
    return {"status": "ok", **result}


# ---------------------------------------------------------------------------
# 註冊路由
# ---------------------------------------------------------------------------

# Apply auth to all routers (health endpoint is exempt as it's not in a router)
auth_deps = [Depends(require_api_key)]

app.include_router(stock_router, dependencies=auth_deps)
app.include_router(thesis_router, dependencies=auth_deps)
app.include_router(scan_router, dependencies=auth_deps)
app.include_router(persona_router, dependencies=auth_deps)
app.include_router(holding_router, dependencies=auth_deps)
app.include_router(telegram_router, dependencies=auth_deps)
app.include_router(preferences_router, dependencies=auth_deps)
app.include_router(forex_router, dependencies=auth_deps)
app.include_router(fx_watch_router, dependencies=auth_deps)
app.include_router(guru_router, dependencies=auth_deps)
app.include_router(resonance_router, dependencies=auth_deps)
app.include_router(snapshot_router, dependencies=auth_deps)
