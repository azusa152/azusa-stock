"""
Application — Guru heat map service.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from cachetools import TTLCache

from application.stock.filing_service import get_grand_portfolio
from domain.constants import GURU_HEATMAP_CACHE_TTL
from domain.enums import HoldingAction
from i18n import t
from infrastructure.repositories import (
    find_all_active_gurus,
    find_holdings_by_filing,
    find_latest_filing_by_guru,
)
from logging_config import get_logger

if TYPE_CHECKING:
    from sqlmodel import Session

logger = get_logger(__name__)

_heatmap_cache: TTLCache = TTLCache(maxsize=12, ttl=GURU_HEATMAP_CACHE_TTL)
_heatmap_cache_lock = threading.Lock()
_heatmap_in_progress: threading.Event | None = None


def invalidate_heatmap_cache() -> None:
    """Invalidate in-memory heat map cache."""
    global _heatmap_in_progress
    with _heatmap_cache_lock:
        _heatmap_cache.clear()
        if _heatmap_in_progress is not None:
            _heatmap_in_progress.set()
        _heatmap_in_progress = None


def get_heatmap(
    session: Session, style: str | None = None, lang: str = "zh-TW"
) -> dict:
    """Get cached heat map payload."""
    global _heatmap_in_progress
    cache_key = f"heatmap:{style or 'all'}:{lang}"

    while True:
        with _heatmap_cache_lock:
            cached = _heatmap_cache.get(cache_key)
            if cached is not None:
                logger.debug("Guru heatmap cache hit: %s", cache_key)
                return cached

            if _heatmap_in_progress is None:
                _heatmap_in_progress = threading.Event()
                owner = True
            else:
                wait_event = _heatmap_in_progress
                owner = False

        if not owner:
            wait_event.wait(timeout=60)
            continue
        break

    try:
        payload = _build_heatmap_payload(session, style=style, lang=lang)
    except Exception:
        with _heatmap_cache_lock:
            if _heatmap_in_progress is not None:
                _heatmap_in_progress.set()
            _heatmap_in_progress = None
        raise

    with _heatmap_cache_lock:
        _heatmap_cache[cache_key] = payload
        if _heatmap_in_progress is not None:
            _heatmap_in_progress.set()
        _heatmap_in_progress = None
    logger.debug("Guru heatmap cache store: %s", cache_key)
    return payload


def _build_heatmap_payload(
    session: Session, style: str | None = None, lang: str = "zh-TW"
) -> dict:
    grand_portfolio = get_grand_portfolio(session, style=style)
    details_by_ticker, latest_report_date = _build_guru_details(session, style=style)

    items: list[dict] = []
    for item in grand_portfolio.get("items", []):
        ticker = item.get("ticker")
        if not ticker:
            continue
        items.append(
            {
                "ticker": ticker,
                "company_name": item.get("company_name", ""),
                "sector": item.get("sector"),
                "guru_count": item.get("guru_count", 0),
                "gurus": details_by_ticker.get(ticker, []),
                "combined_value": item.get("total_value", 0.0),
                "combined_weight_pct": item.get("combined_weight_pct", 0.0),
                "dominant_action": item.get(
                    "dominant_action", HoldingAction.UNCHANGED.value
                ),
                "action_breakdown": item.get("action_counts", {}),
            }
        )

    return {
        "items": items,
        "sectors": grand_portfolio.get("sector_breakdown", []),
        "report_date": latest_report_date,
        "filing_delay_note": t(
            "guru.heatmap_filing_delay_note",
            lang=lang,
            report_date=latest_report_date or "-",
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _build_guru_details(
    session: Session, style: str | None = None
) -> tuple[dict[str, list[dict]], str | None]:
    gurus = find_all_active_gurus(session)
    if style:
        gurus = [g for g in gurus if g.style == style]

    details_by_ticker: dict[str, list[dict]] = {}
    latest_report_date: str | None = None

    for guru in gurus:
        latest_filing = find_latest_filing_by_guru(session, guru.id)
        if latest_filing is None:
            continue

        if latest_report_date is None or latest_filing.report_date > latest_report_date:
            latest_report_date = latest_filing.report_date

        holdings = find_holdings_by_filing(session, latest_filing.id)
        for holding in holdings:
            if not holding.ticker or holding.action == HoldingAction.SOLD_OUT.value:
                continue
            details_by_ticker.setdefault(holding.ticker, []).append(
                {
                    "guru_id": guru.id,
                    "guru_display_name": guru.display_name,
                    "weight_pct": holding.weight_pct,
                    "action": holding.action,
                    "value": holding.value,
                }
            )

    for ticker in details_by_ticker:
        details_by_ticker[ticker].sort(
            key=lambda item: item.get("weight_pct") or 0.0,
            reverse=True,
        )

    return details_by_ticker, latest_report_date
