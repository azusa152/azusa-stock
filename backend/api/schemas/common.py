"""
API — 共用/通用 Response Schemas。
"""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """通用操作結果回應（刪除、停用、重新啟用、匯入等）。"""

    message: str


class ImportResponse(BaseModel):
    """匯入操作回應。"""

    message: str
    imported: int
    errors: list[str] = []


class HealthResponse(BaseModel):
    """GET /health 回應。"""

    status: str
    service: str


class AcceptedResponse(BaseModel):
    """非同步操作已接受回應。"""

    status: str = "accepted"
    message: str
