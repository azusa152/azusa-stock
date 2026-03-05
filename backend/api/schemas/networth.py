"""
API — Net Worth Schemas。
"""

from pydantic import BaseModel, Field, field_validator, model_validator

from domain.constants import (
    NET_WORTH_ASSET_CATEGORIES,
    NET_WORTH_LIABILITY_CATEGORIES,
)


class NetWorthItemRequest(BaseModel):
    """POST /net-worth/items request."""

    name: str = Field(..., min_length=1, max_length=120)
    kind: str = Field(..., pattern="^(asset|liability)$")
    category: str = Field(..., min_length=1, max_length=50)
    value: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    fx_rate_to_usd: float | None = Field(default=None, gt=0)
    interest_rate: float | None = Field(default=None, ge=0)
    minimum_payment: float | None = Field(default=None, ge=0)
    note: str | None = Field(default="", max_length=500)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def validate_category_by_kind(self):
        if self.kind == "asset" and self.category not in NET_WORTH_ASSET_CATEGORIES:
            raise ValueError("invalid asset category")
        if (
            self.kind == "liability"
            and self.category not in NET_WORTH_LIABILITY_CATEGORIES
        ):
            raise ValueError("invalid liability category")
        return self


class UpdateNetWorthItemRequest(BaseModel):
    """PUT /net-worth/items/{item_id} request (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = Field(default=None, pattern="^(asset|liability)$")
    category: str | None = Field(default=None, min_length=1, max_length=50)
    value: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    fx_rate_to_usd: float | None = Field(default=None, gt=0)
    interest_rate: float | None = Field(default=None, ge=0)
    minimum_payment: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.upper().strip()

    @model_validator(mode="after")
    def validate_category_by_kind(self):
        if self.kind is None or self.category is None:
            return self
        if self.kind == "asset" and self.category not in NET_WORTH_ASSET_CATEGORIES:
            raise ValueError("invalid asset category")
        if (
            self.kind == "liability"
            and self.category not in NET_WORTH_LIABILITY_CATEGORIES
        ):
            raise ValueError("invalid liability category")
        return self


class NetWorthItemResponse(BaseModel):
    """Single net worth item response."""

    id: int
    name: str
    kind: str
    category: str
    value: float
    value_display: float
    currency: str
    fx_rate_to_usd: float | None = None
    interest_rate: float | None = None
    minimum_payment: float | None = None
    note: str = ""
    is_active: bool
    is_stale: bool
    days_since_update: int
    created_at: str
    updated_at: str


class NetWorthSummaryResponse(BaseModel):
    """GET /net-worth summary response."""

    display_currency: str = "USD"
    investment_value: float
    other_assets_value: float
    liabilities_value: float
    net_worth: float
    breakdown: dict[str, dict[str, float]]
    stale_count: int = 0
    items: list[NetWorthItemResponse] = []
    calculated_at: str


class NetWorthSnapshotResponse(BaseModel):
    """GET /net-worth/history entry."""

    snapshot_date: str
    investment_value: float
    other_assets_value: float
    liabilities_value: float
    net_worth: float
    display_currency: str = "USD"
    breakdown: dict[str, dict[str, float]] = {}
