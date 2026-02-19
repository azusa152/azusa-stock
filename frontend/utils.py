"""
Folio — Shared utilities for the Streamlit frontend.
API helpers, cached data fetchers, and reusable UI rendering functions.
"""

import logging
from datetime import datetime as dt
from datetime import timezone
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_sortables import sort_items

from config import (
    API_DELETE_TIMEOUT,
    API_DIVIDEND_TIMEOUT,
    API_GET_ENRICHED_TIMEOUT,
    API_EARNINGS_TIMEOUT,
    API_FEAR_GREED_TIMEOUT,
    API_FX_HISTORY_TIMEOUT,
    API_GET_TIMEOUT,
    API_GURU_DASHBOARD_TIMEOUT,
    API_GURU_GET_TIMEOUT,
    API_GURU_SYNC_TIMEOUT,
    API_PATCH_TIMEOUT,
    API_POST_TIMEOUT,
    API_PRICE_HISTORY_TIMEOUT,
    API_PUT_TIMEOUT,
    API_REBALANCE_TIMEOUT,
    API_SIGNALS_TIMEOUT,
    API_STRESS_TEST_TIMEOUT,
    API_WITHDRAW_TIMEOUT,
    BACKEND_URL,
    BIAS_OVERHEATED_UI,
    BIAS_OVERSOLD_UI,
    RSI_OVERBOUGHT_UI,
    RSI_OVERSOLD_UI,
    VOL_SURGE_HIGH_UI,
    VOL_SURGE_UI,
    CACHE_TTL_ALERTS,
    CACHE_TTL_DIVIDEND,
    CACHE_TTL_EARNINGS,
    CACHE_TTL_GURU_DASHBOARD,
    CACHE_TTL_GURU_FILING,
    CACHE_TTL_GURU_LIST,
    CACHE_TTL_HOLDINGS,
    CACHE_TTL_LAST_SCAN,
    CACHE_TTL_MOAT,
    CACHE_TTL_PREFERENCES,
    CACHE_TTL_PRICE_HISTORY,
    CACHE_TTL_PROFILE,
    CACHE_TTL_REMOVED,
    CACHE_TTL_REBALANCE,
    CACHE_TTL_RESONANCE,
    CACHE_TTL_SCAN_HISTORY,
    CACHE_TTL_SIGNALS,
    CACHE_TTL_STRESS_TEST,
    CACHE_TTL_FEAR_GREED,
    CACHE_TTL_FX_HISTORY,
    CACHE_TTL_FX_WATCH,
    CACHE_TTL_STOCKS,
    CACHE_TTL_TEMPLATES,
    CACHE_TTL_THESIS,
    CATEGORY_OPTIONS,
    ALERT_DEFAULTS,
    DEFAULT_ALERT_THRESHOLD,
    DEFAULT_TAG_OPTIONS,
    EARNINGS_BADGE_DAYS_THRESHOLD,
    FOLIO_API_KEY,
    MARGIN_BAD_CHANGE_THRESHOLD,
    PRICE_CHART_DEFAULT_PERIOD,
    PRICE_CHART_HEIGHT,
    PRICE_CHART_PERIODS,
    PRICE_WEAK_BIAS_THRESHOLD,
    REORDER_MIN_STOCKS,
    ROGUE_WAVE_PERCENTILE_UI,
    ROGUE_WAVE_WARNING_PERCENTILE_UI,
    SCAN_HISTORY_CARD_LIMIT,
    SCAN_SIGNAL_ICONS,
    SCAN_SIGNAL_LABELS,
    SKIP_MOAT_CATEGORIES,
    SKIP_SIGNALS_CATEGORIES,
    PRIVACY_MASK,
    WHALEWISDOM_STOCK_URL,
    get_category_labels,
    get_ticker_market_label,
)
from i18n import t

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core Helpers
# ---------------------------------------------------------------------------


def refresh_ui() -> None:
    """Rerun the page. Caller should clear specific caches first."""
    st.rerun()


_TOAST_DISPATCH = {
    "success": st.success,
    "error": st.error,
    "warning": st.warning,
    "info": st.info,
}


def show_toast(level: str, msg: str) -> None:
    """Display a Streamlit toast/message via level name.

    Safely dispatches to ``st.success``, ``st.error``, or ``st.warning``.
    Falls back to ``st.error`` for unrecognised levels.
    """
    _TOAST_DISPATCH.get(level, st.error)(msg)


# ---------------------------------------------------------------------------
# Targeted Cache Invalidation
# ---------------------------------------------------------------------------


def invalidate_stock_caches() -> None:
    """After adding/removing/updating stocks."""
    fetch_stocks.clear()
    fetch_enriched_stocks.clear()
    fetch_removed_stocks.clear()


def invalidate_holding_caches() -> None:
    """After adding/removing/editing holdings."""
    fetch_holdings.clear()
    fetch_rebalance.clear()
    fetch_currency_exposure.clear()
    fetch_stress_test.clear()


def invalidate_profile_caches() -> None:
    """After changing investment profile/config."""
    fetch_profile.clear()
    fetch_rebalance.clear()
    fetch_currency_exposure.clear()
    fetch_stress_test.clear()


def invalidate_all_caches() -> None:
    """Clear frontend Streamlit caches, forcing re-fetch from backend API."""
    st.cache_data.clear()


def format_utc_timestamp(iso_str: str, tz_name: str | None = None) -> str:
    """Convert UTC ISO timestamp to 'YYYY-MM-DD HH:MM:SS (TZ)' in user timezone."""
    try:
        utc_dt = dt.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
        if tz_name:
            local_dt = utc_dt.astimezone(ZoneInfo(tz_name))
            return f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name})"
        return f"{iso_str[:19].replace('T', ' ')} (UTC)"
    except Exception:
        return f"{iso_str[:19].replace('T', ' ')} (UTC)"


def infer_market_label(ticker: str) -> str:
    """Infer market label from ticker suffix (e.g. '.TW' -> '🇹🇼 台股')."""
    return get_ticker_market_label(ticker)


# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------

# Create a session with API key header (if configured)
_session = requests.Session()
if FOLIO_API_KEY:
    _session.headers["X-API-Key"] = FOLIO_API_KEY


def api_get(path: str) -> dict | list | None:
    """GET request to Backend API."""
    try:
        resp = _session.get(f"{BACKEND_URL}{path}", timeout=API_GET_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(t("utils.api_error", error=e))
        return None


def api_post(path: str, json_data: dict | list) -> dict | None:
    """POST request to Backend API."""
    try:
        resp = _session.post(
            f"{BACKEND_URL}{path}", json=json_data, timeout=API_POST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(t("utils.api_error", error=e))
        return None


def api_patch(path: str, json_data: dict) -> dict | None:
    """PATCH request to Backend API."""
    try:
        resp = _session.patch(
            f"{BACKEND_URL}{path}", json=json_data, timeout=API_PATCH_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(t("utils.api_error", error=e))
        return None


def api_put(path: str, json_data: dict) -> dict | None:
    """PUT request to Backend API."""
    try:
        resp = _session.put(
            f"{BACKEND_URL}{path}", json=json_data, timeout=API_PUT_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(t("utils.api_error", error=e))
        return None


def api_delete(path: str) -> dict | None:
    """DELETE request to Backend API."""
    try:
        resp = _session.delete(f"{BACKEND_URL}{path}", timeout=API_DELETE_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(t("utils.api_error", error=e))
        return None


def api_get_silent(path: str, timeout: int | None = None) -> dict | list | None:
    """GET request to Backend API (silent mode — no error display)."""
    try:
        resp = _session.get(f"{BACKEND_URL}{path}", timeout=timeout or API_GET_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def api_post_silent(path: str, json_data: dict | None = None) -> dict | None:
    """POST request to Backend API (silent mode — no error display)."""
    try:
        resp = _session.post(
            f"{BACKEND_URL}{path}", json=json_data or {}, timeout=API_POST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# Cached Data Fetchers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_STOCKS, show_spinner=False)
def fetch_stocks() -> list | None:
    """Fetch all tracked stocks (DB data only)."""
    return api_get("/stocks")


@st.cache_data(ttl=CACHE_TTL_STOCKS, show_spinner=False)
def fetch_enriched_stocks() -> list | None:
    """Fetch all active stocks with signals, earnings, and dividends in one batch.

    Uses a short dedicated timeout so the page loads fast even on cold cache.
    Returns None silently if the backend hasn't finished warming up yet.
    """
    return api_get_silent("/stocks/enriched", timeout=API_GET_ENRICHED_TIMEOUT)


def build_radar_lookup() -> dict[str, str]:
    """Return {TICKER: category} from cached radar stocks for quick lookups."""
    stocks = fetch_stocks()
    if not stocks:
        return {}
    return {s["ticker"].upper(): s["category"] for s in stocks if s.get("ticker")}


@st.cache_data(ttl=CACHE_TTL_SIGNALS, show_spinner=False)
def fetch_signals(ticker: str) -> dict | None:
    """Fetch technical signals for a single stock (yfinance)."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/ticker/{ticker}/signals", timeout=API_SIGNALS_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_REMOVED, show_spinner=False)
def fetch_removed_stocks() -> list | None:
    """Fetch removed stocks list."""
    return api_get("/stocks/removed")


@st.cache_data(ttl=CACHE_TTL_EARNINGS, show_spinner=False)
def fetch_earnings(ticker: str) -> dict | None:
    """Fetch earnings date."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/ticker/{ticker}/earnings", timeout=API_EARNINGS_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_DIVIDEND, show_spinner=False)
def fetch_dividend(ticker: str) -> dict | None:
    """Fetch dividend info."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/ticker/{ticker}/dividend", timeout=API_DIVIDEND_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_MOAT, show_spinner=False)
def fetch_moat(ticker: str) -> dict | None:
    """Fetch moat analysis data."""
    return api_get(f"/ticker/{ticker}/moat")


@st.cache_data(ttl=CACHE_TTL_SCAN_HISTORY, show_spinner=False)
def fetch_scan_history(
    ticker: str, limit: int = SCAN_HISTORY_CARD_LIMIT
) -> list | None:
    """Fetch scan history."""
    return api_get(f"/ticker/{ticker}/scan-history?limit={limit}")


@st.cache_data(ttl=CACHE_TTL_ALERTS, show_spinner=False)
def fetch_alerts(ticker: str) -> list | None:
    """Fetch price alerts."""
    return api_get(f"/ticker/{ticker}/alerts")


@st.cache_data(ttl=CACHE_TTL_THESIS, show_spinner=False)
def fetch_thesis_history(ticker: str) -> list | None:
    """Fetch thesis version history."""
    return api_get(f"/ticker/{ticker}/thesis")


@st.cache_data(ttl=CACHE_TTL_PRICE_HISTORY, show_spinner=False)
def fetch_price_history(ticker: str) -> list[dict] | None:
    """Fetch closing price history (for trend chart)."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/ticker/{ticker}/price-history",
            timeout=API_PRICE_HISTORY_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# Asset Allocation — Cached API Helpers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_TEMPLATES, show_spinner=False)
def fetch_templates() -> list | None:
    """Fetch persona templates."""
    return api_get_silent("/personas/templates")


@st.cache_data(ttl=CACHE_TTL_PROFILE, show_spinner=False)
def fetch_profile() -> dict | None:
    """Fetch active investment profile."""
    return api_get_silent("/profiles")


@st.cache_data(ttl=CACHE_TTL_HOLDINGS, show_spinner=False)
def fetch_holdings() -> list | None:
    """Fetch all holdings."""
    return api_get_silent("/holdings")


@st.cache_data(ttl=CACHE_TTL_REBALANCE, show_spinner=False)
def fetch_rebalance(display_currency: str = "USD") -> dict | None:
    """Fetch rebalance analysis with optional display currency conversion.

    Returns the JSON dict on success, ``None`` on any failure.
    Error details are logged so they can be diagnosed without
    leaking transient failures into the Streamlit cache.
    """
    try:
        resp = _session.get(
            f"{BACKEND_URL}/rebalance",
            params={"display_currency": display_currency},
            timeout=API_REBALANCE_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        # --- non-200: log detail, return None (not cached on error) ---
        try:
            body = resp.json()
            detail = body.get("detail", body)
        except Exception:
            detail = resp.text
        logger.warning("再平衡 API 回傳 %s: %s", resp.status_code, detail)
        return None
    except requests.RequestException as exc:
        logger.error("再平衡 API 連線失敗: %s", exc)
        return None


@st.cache_data(ttl=CACHE_TTL_REBALANCE, show_spinner=False)
def fetch_currency_exposure() -> dict | None:
    """Fetch currency exposure analysis."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/currency-exposure",
            timeout=API_REBALANCE_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_STRESS_TEST, show_spinner=False)
def fetch_stress_test(
    scenario_drop_pct: float = -20.0,
    display_currency: str = "USD",
) -> dict | None:
    """Fetch portfolio stress test analysis.

    Args:
        scenario_drop_pct: Market crash scenario % (range: -50 to 0, default -20)
        display_currency: Display currency (default USD)

    Returns:
        dict containing stress test results on success, None on failure
    """
    try:
        resp = _session.get(
            f"{BACKEND_URL}/stress-test",
            params={
                "scenario_drop_pct": scenario_drop_pct,
                "display_currency": display_currency,
            },
            timeout=API_STRESS_TEST_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        # --- non-200: log detail, return None (not cached on error) ---
        try:
            body = resp.json()
            detail = body.get("detail", body)
        except Exception:
            detail = resp.text
        logger.warning("壓力測試 API 回傳 %s: %s", resp.status_code, detail)
        return None
    except requests.RequestException as exc:
        logger.error("壓力測試 API 連線失敗: %s", exc)
        return None


def fetch_withdraw(
    target_amount: float,
    display_currency: str = "USD",
    notify: bool = False,
) -> dict | None:
    """POST /withdraw — 聰明提款建議（Liquidity Waterfall）。

    Not cached: each call is a user-initiated action with unique parameters.
    Returns the JSON dict on success, ``None`` on any failure.
    On 404 (no profile / no holdings) returns ``{"error_code": "...", ...}``
    so the UI can show a specific message instead of a generic failure.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/withdraw",
            json={
                "target_amount": target_amount,
                "display_currency": display_currency,
                "notify": notify,
            },
            timeout=API_WITHDRAW_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        # Surface 404 (no profile / no holdings) distinctly
        if resp.status_code == 404:
            try:
                detail = resp.json().get("detail", {})
                # Normalise: backend should send a dict, but guard against
                # a plain-string detail so the caller can always do
                # ``"error_code" in result`` without TypeError.
                if isinstance(detail, dict):
                    return detail
                return {"error_code": "NOT_FOUND", "detail": str(detail)}
            except Exception:
                return {"error_code": "NOT_FOUND", "detail": resp.text}
        try:
            body = resp.json()
            detail = body.get("detail", body)
        except Exception:
            detail = resp.text
        logger.warning("提款 API 回傳 %s: %s", resp.status_code, detail)
        return None
    except requests.RequestException as exc:
        logger.error("提款 API 連線失敗: %s", exc)
        return None


def post_telegram_test() -> tuple[str, str]:
    """POST /settings/telegram/test — 發送 Telegram 測試訊息。

    Returns ``(level, message)`` where *level* is one of
    ``"success"`` / ``"warning"`` / ``"error"``, suitable for
    ``getattr(st, level)(message)``.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/settings/telegram/test",
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            return ("success", resp.json().get("message", t("api.telegram_test_sent")))
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("Telegram 測試 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.http_error", detail=detail))
    except requests.RequestException as exc:
        logger.error("Telegram 測試 API 連線失敗: %s", exc)
        return ("error", t("api.request_failed", detail=str(exc)))


def post_xray_alert(display_currency: str = "USD") -> tuple[str, str]:
    """POST /rebalance/xray-alert — 發送 X-Ray 集中度警告至 Telegram。

    Returns ``(level, message)`` where *level* is one of
    ``"success"`` / ``"error"``.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/rebalance/xray-alert",
            params={"display_currency": display_currency},
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            data = resp.json()
            w_count = len(data.get("warnings", []))
            return (
                "success",
                "✅ "
                + (data.get("message") or t("api.xray_warnings_sent", count=w_count)),
            )
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("X-Ray 警告 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.send_failed", detail=detail))
    except requests.RequestException as exc:
        logger.error("X-Ray 警告 API 連線失敗: %s", exc)
        return ("error", t("api.send_failed", detail=str(exc)))


def post_fx_exposure_alert() -> tuple[str, str]:
    """POST /currency-exposure/alert — 發送匯率曝險警報至 Telegram。

    Returns ``(level, message)`` where *level* is one of
    ``"success"`` / ``"error"``.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/currency-exposure/alert",
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            data = resp.json()
            a_count = len(data.get("alerts", []))
            return (
                "success",
                "✅ " + (data.get("message") or t("api.fx_alerts_sent", count=a_count)),
            )
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("匯率曝險警報 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.send_failed", detail=detail))
    except requests.RequestException as exc:
        logger.error("匯率曝險警報 API 連線失敗: %s", exc)
        return ("error", t("api.send_failed", detail=str(exc)))


def put_telegram_settings(payload: dict) -> tuple[str, str]:
    """PUT /settings/telegram — 儲存 Telegram 設定。

    Returns ``(level, message)`` where *level* is one of
    ``"success"`` / ``"error"``.
    """
    try:
        resp = _session.put(
            f"{BACKEND_URL}/settings/telegram",
            json=payload,
            timeout=API_PUT_TIMEOUT,
        )
        if resp.ok:
            return ("success", t("api.telegram_saved"))
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("Telegram 設定 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.save_failed", detail=detail))
    except requests.RequestException as exc:
        logger.error("Telegram 設定 API 連線失敗: %s", exc)
        return ("error", t("api.request_failed", detail=str(exc)))


def put_notification_preferences(
    privacy_mode: bool, notification_preferences: dict
) -> tuple[str, str]:
    """PUT /settings/preferences — 儲存通知偏好。

    Returns ``(level, message)`` where *level* is one of
    ``"success"`` / ``"error"``.
    """
    try:
        resp = _session.put(
            f"{BACKEND_URL}/settings/preferences",
            json={
                "privacy_mode": privacy_mode,
                "notification_preferences": notification_preferences,
            },
            timeout=API_PUT_TIMEOUT,
        )
        if resp.ok:
            return ("success", t("api.notification_saved"))
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("通知偏好 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.save_failed", detail=detail))
    except requests.RequestException as exc:
        logger.error("通知偏好 API 連線失敗: %s", exc)
        return ("error", t("api.request_failed", detail=str(exc)))


def post_digest() -> tuple[str, str]:
    """POST /digest — 觸發每週摘要（背景執行）。

    Returns ``(level, message)`` where *level* is one of
    ``"success"`` / ``"warning"`` / ``"error"``.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/digest",
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            return ("success", resp.json().get("message", t("api.digest_started")))
        if resp.status_code == 409:
            fallback = t("api.digest_in_progress")
            try:
                detail = resp.json().get("detail", fallback)
                # Backend wraps in {"detail": {"error_code": ..., "detail": ...}}
                # but guard against a plain-string detail.
                if isinstance(detail, dict):
                    msg = detail.get("detail", fallback)
                else:
                    msg = str(detail)
            except Exception:
                msg = fallback
            return ("warning", msg)
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("摘要 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.http_error", detail=detail))
    except requests.RequestException as exc:
        logger.error("摘要 API 連線失敗: %s", exc)
        return ("error", t("api.request_failed", detail=str(exc)))


# ---------------------------------------------------------------------------
# FX Watch — Action Helpers
# ---------------------------------------------------------------------------


def create_fx_watch(payload: dict) -> tuple[str, str]:
    """POST /fx-watch — 新增監控配置。

    Returns ``(level, message)``.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/fx-watch",
            json=payload,
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            pair = f"{payload.get('base_currency', '')}/{payload.get('quote_currency', '')}"
            return ("success", t("api.fx_watch_created", pair=pair))
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("FX Watch 新增 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.create_failed", detail=detail))
    except requests.RequestException as exc:
        logger.error("FX Watch 新增 API 連線失敗: %s", exc)
        return ("error", t("api.create_failed", detail=str(exc)))


def patch_fx_watch(watch_id: int, payload: dict) -> tuple[str, str]:
    """PATCH /fx-watch/{id} — 更新監控配置。

    Returns ``(level, message)``.
    """
    try:
        resp = _session.patch(
            f"{BACKEND_URL}/fx-watch/{watch_id}",
            json=payload,
            timeout=API_PATCH_TIMEOUT,
        )
        if resp.ok:
            return ("success", t("api.updated"))
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("FX Watch 更新 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.update_failed", detail=detail))
    except requests.RequestException as exc:
        logger.error("FX Watch 更新 API 連線失敗: %s", exc)
        return ("error", t("api.update_failed", detail=str(exc)))


def toggle_fx_watch(watch_id: int, is_active: bool) -> bool:
    """PATCH /fx-watch/{id} — 切換監控啟用狀態。

    Returns ``True`` on success, ``False`` on any failure.
    """
    try:
        resp = _session.patch(
            f"{BACKEND_URL}/fx-watch/{watch_id}",
            json={"is_active": not is_active},
            timeout=API_PATCH_TIMEOUT,
        )
        if resp.ok:
            return True
        logger.warning("FX Watch 切換 API 回傳 %s", resp.status_code)
        return False
    except requests.RequestException as exc:
        logger.error("FX Watch 切換 API 連線失敗: %s", exc)
        return False


def delete_fx_watch(watch_id: int) -> bool:
    """DELETE /fx-watch/{id} — 刪除監控配置。

    Returns ``True`` on success, ``False`` on any failure.
    """
    try:
        resp = _session.delete(
            f"{BACKEND_URL}/fx-watch/{watch_id}",
            timeout=API_DELETE_TIMEOUT,
        )
        if resp.ok:
            return True
        logger.warning("FX Watch 刪除 API 回傳 %s", resp.status_code)
        return False
    except requests.RequestException as exc:
        logger.error("FX Watch 刪除 API 連線失敗: %s", exc)
        return False


def post_fx_watch_check() -> tuple[str, str]:
    """POST /fx-watch/check — 手動檢查所有監控（不發送通知）。

    Returns ``(level, message)``.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/fx-watch/check",
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            data = resp.json()
            return (
                "success",
                t("api.fx_check_done", count=data.get("total_watches", 0)),
            )
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("FX Watch 檢查 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.check_failed", detail=detail))
    except requests.RequestException as exc:
        logger.error("FX Watch 檢查 API 連線失敗: %s", exc)
        return ("error", t("api.check_failed", detail=str(exc)))


def post_fx_watch_alert() -> tuple[str, str]:
    """POST /fx-watch/alert — 手動觸發 Telegram 通知。

    Returns ``(level, message)``.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/fx-watch/alert",
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            data = resp.json()
            return (
                "success",
                t(
                    "api.fx_alert_result",
                    triggered=data.get("triggered_alerts", 0),
                    sent=data.get("sent_alerts", 0),
                ),
            )
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        logger.warning("FX Watch 警報 API 回傳 %s: %s", resp.status_code, detail)
        return ("error", t("api.send_failed", detail=detail))
    except requests.RequestException as exc:
        logger.error("FX Watch 警報 API 連線失敗: %s", exc)
        return ("error", t("api.send_failed", detail=str(exc)))


@st.cache_data(ttl=CACHE_TTL_FX_WATCH, show_spinner=False)
def fetch_fx_watch_analysis() -> dict[int, dict]:
    """POST /fx-watch/check — 取得所有監控即時分析結果（快取）。

    Returns mapping of watch_id → analysis dict.
    """
    try:
        resp = _session.post(
            f"{BACKEND_URL}/fx-watch/check",
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            data = resp.json()
            results = data.get("results", [])
            return {
                r["watch_id"]: {
                    "recommendation": r["result"]["recommendation_zh"],
                    "reasoning": r["result"]["reasoning_zh"],
                    "should_alert": r["result"]["should_alert"],
                    "current_rate": r["result"]["current_rate"],
                }
                for r in results
            }
        return {}
    except Exception as exc:
        logger.warning("FX Watch 分析 API 失敗: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Dashboard — Cached API Helpers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_LAST_SCAN, show_spinner=False)
def fetch_last_scan() -> dict | None:
    """Fetch last scan timestamp and market sentiment."""
    return api_get_silent("/scan/last")


@st.cache_data(ttl=CACHE_TTL_FEAR_GREED, show_spinner=False)
def fetch_fear_greed() -> dict | None:
    """Fetch Fear & Greed Index (VIX + CNN composite)."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/market/fear-greed",
            timeout=API_FEAR_GREED_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_PREFERENCES, show_spinner=False)
def fetch_preferences() -> dict | None:
    """Fetch user preferences (privacy mode, etc.)."""
    return api_get_silent("/settings/preferences")


def save_privacy_mode(enabled: bool) -> dict | None:
    """Persist privacy mode to backend (non-cached PUT)."""
    return api_put("/settings/preferences", {"privacy_mode": enabled})


# ---------------------------------------------------------------------------
# FX Watch Cache Functions
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_FX_WATCH, show_spinner=False)
def fetch_fx_watches() -> list | None:
    """Fetch all FX watch configurations."""
    return api_get_silent("/fx-watch")


def invalidate_fx_watch_caches() -> None:
    """Invalidate all FX watch caches after mutations."""
    fetch_fx_watches.clear()
    fetch_fx_watch_analysis.clear()


# ---------------------------------------------------------------------------
# FX History Cache Function
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_FX_HISTORY, show_spinner=False)
def fetch_fx_history(base: str, quote: str) -> list[dict] | None:
    """
    Fetch 3-month daily FX rate history for a currency pair.

    Args:
        base: Base currency code (e.g., 'USD')
        quote: Quote currency code (e.g., 'TWD')

    Returns:
        List of rate records: [{"date": "YYYY-MM-DD", "close": 32.15}, ...]
        Returns None if API call fails or times out.

    Cache: 2 hours (CACHE_TTL_FX_HISTORY)
    """
    try:
        resp = _session.get(
            f"{BACKEND_URL}/forex/{base}/{quote}/history-long",
            timeout=API_FX_HISTORY_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        # Fail silently - chart rendering function will handle None
        return None


# ---------------------------------------------------------------------------
# Privacy / Masking Helpers (shared across pages)
# ---------------------------------------------------------------------------


def is_privacy() -> bool:
    """Return True when the privacy toggle is active."""
    return bool(st.session_state.get("privacy_mode"))


def on_privacy_change() -> None:
    """Callback: persist privacy mode to backend and backing key."""
    new_val = st.session_state.get("privacy_mode", False)
    st.session_state["_privacy_mode_value"] = new_val
    save_privacy_mode(new_val)


def mask_money(value: float, fmt: str = "${:,.2f}") -> str:
    """Format a monetary value, or return the mask placeholder in privacy mode."""
    if is_privacy():
        return PRIVACY_MASK
    return fmt.format(value)


def mask_qty(value: float, fmt: str = "{:,.4f}") -> str:
    """Format a quantity, or return the mask placeholder in privacy mode."""
    if is_privacy():
        return PRIVACY_MASK
    return fmt.format(value)


def mask_id(value: str, visible_suffix: int = 3) -> str:
    """Mask a sensitive ID string, or return as-is when privacy mode is off."""
    if not is_privacy() or not value:
        return value
    if len(value) > visible_suffix:
        return "***" + value[-visible_suffix:]
    return "***"


# ---------------------------------------------------------------------------
# Rendering Helpers
# ---------------------------------------------------------------------------


def render_thesis_history(history: list[dict]) -> None:
    """Render thesis version history (shared between stock cards and archive)."""
    if history:
        st.markdown(t("utils.thesis.history_title"))
        for entry in history:
            ver = entry.get("version", "?")
            content = entry.get("content", "")
            created = entry.get("created_at", "")
            entry_tags = entry.get("tags", [])
            st.markdown(
                t(
                    "utils.thesis.version",
                    ver=ver,
                    date=created[:10] if created else t("utils.thesis.unknown_date"),
                )
            )
            if entry_tags:
                st.caption(
                    t("utils.thesis.tags") + " ".join(f"`{tag}`" for tag in entry_tags)
                )
            st.text(content)
            st.divider()
    else:
        st.caption(t("utils.thesis.no_history"))


def _render_signal_metrics(signals: dict) -> None:
    """Compact single-line summary of the 3 most actionable indicators: RSI, Bias, Volume Ratio."""
    if "error" in signals:
        st.warning(signals["error"])
        return

    rsi = signals.get("rsi")
    bias = signals.get("bias")
    volume_ratio = signals.get("volume_ratio")
    bias_percentile = signals.get("bias_percentile")
    is_rogue_wave = signals.get("is_rogue_wave", False)

    # RSI chip
    if rsi is not None:
        rsi_color = "🔴" if rsi > RSI_OVERBOUGHT_UI else ("🟢" if rsi < RSI_OVERSOLD_UI else "⚪")
        rsi_part = t("utils.signals.summary_rsi", color=rsi_color, value=rsi)
    else:
        rsi_part = t("utils.signals.summary_rsi_na")

    # Bias chip
    if bias is not None:
        bias_color = (
            "🔴"
            if bias > BIAS_OVERHEATED_UI
            else ("🟢" if bias < BIAS_OVERSOLD_UI else "⚪")
        )
        if bias_percentile is not None:
            pct_int = int(round(bias_percentile))
            pct_color = (
                "🔴"
                if bias_percentile >= ROGUE_WAVE_PERCENTILE_UI
                else (
                    "🟠"
                    if bias_percentile >= ROGUE_WAVE_WARNING_PERCENTILE_UI
                    else ""
                )
            )
            bias_part = t(
                "utils.signals.summary_bias_pct",
                color=bias_color,
                value=bias,
                pct_color=pct_color,
                percentile=pct_int,
            )
        else:
            bias_part = t("utils.signals.summary_bias", color=bias_color, value=bias)
    else:
        bias_part = t("utils.signals.summary_bias_na")

    # Volume ratio chip
    if volume_ratio is not None:
        vol_color = "🔴" if volume_ratio >= VOL_SURGE_HIGH_UI else ("🟡" if volume_ratio >= VOL_SURGE_UI else "⚪")
        vol_part = t(
            "utils.signals.summary_vol", color=vol_color, value=volume_ratio
        )
    else:
        vol_part = t("utils.signals.summary_vol_na")

    st.markdown(f"{rsi_part} · {bias_part} · {vol_part}")

    if is_rogue_wave:
        st.warning(t("utils.signals.rogue_wave_warning"))


def _render_full_metrics(signals: dict) -> None:
    """Full metrics grid: price, RSI, MA200, MA60, bias, volume ratio, fetched_at."""
    if "error" in signals:
        st.warning(signals["error"])
        return

    price = signals.get("price", "N/A")
    rsi = signals.get("rsi", "N/A")
    ma200 = signals.get("ma200", "N/A")
    ma60 = signals.get("ma60", "N/A")
    bias = signals.get("bias")
    volume_ratio = signals.get("volume_ratio")
    bias_percentile = signals.get("bias_percentile")
    is_rogue_wave = signals.get("is_rogue_wave", False)

    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric(t("utils.signals.price"), f"${price}")
        st.metric(t("utils.signals.rsi"), rsi)
    with metrics_col2:
        st.metric(t("utils.signals.ma200"), f"${ma200}" if ma200 else "N/A")
        st.metric(t("utils.signals.ma60"), f"${ma60}" if ma60 else "N/A")

    chip_col1, chip_col2 = st.columns(2)
    with chip_col1:
        if bias is not None:
            bias_color = (
                "🔴"
                if bias > BIAS_OVERHEATED_UI
                else ("🟢" if bias < BIAS_OVERSOLD_UI else "⚪")
            )
            if bias_percentile is not None:
                pct_int = int(round(bias_percentile))
                pct_color = (
                    "🔴"
                    if bias_percentile >= ROGUE_WAVE_PERCENTILE_UI
                    else (
                        "🟠"
                        if bias_percentile >= ROGUE_WAVE_WARNING_PERCENTILE_UI
                        else ""
                    )
                )
                pct_tag = t("utils.signals.bias_percentile", percentile=pct_int)
                bias_label = t(
                    "utils.signals.bias_with_color",
                    color=f"{bias_color}{pct_color} {pct_tag}",
                )
            else:
                bias_label = t("utils.signals.bias_with_color", color=bias_color)
            st.metric(bias_label, f"{bias}%")
        else:
            st.metric(t("utils.signals.bias"), "N/A")
    with chip_col2:
        if volume_ratio is not None:
            st.metric(t("utils.signals.volume_ratio"), f"{volume_ratio}x")
        else:
            st.metric(t("utils.signals.volume_ratio"), "N/A")

    if is_rogue_wave:
        st.warning(t("utils.signals.rogue_wave_warning"))

    for s in signals.get("status", []):
        st.write(s)

    fetched_at = signals.get("fetched_at")
    if fetched_at:
        browser_tz = st.session_state.get("browser_tz")
        st.caption(
            t(
                "utils.signals.data_updated",
                time=format_utc_timestamp(fetched_at, browser_tz),
            )
        )


def _render_moat_section(ticker: str, signals: dict) -> None:
    """Render moat health check tab content."""
    moat_data = fetch_moat(ticker)

    if moat_data and moat_data.get("moat") != "N/A":
        curr_margin = moat_data.get("current_margin")
        margin_change = moat_data.get("change")

        if curr_margin is not None and margin_change is not None:
            st.metric(
                t("utils.moat.metric_label"),
                f"{curr_margin:.1f}%",
                delta=f"{margin_change:+.2f} pp (YoY)",
            )
        else:
            st.metric(t("utils.moat.metric_label"), "N/A")

        trend = moat_data.get("margin_trend", [])
        valid_trend = [t for t in trend if t.get("value") is not None]
        if valid_trend:
            dates = [t["date"] for t in valid_trend]
            values = [t["value"] for t in valid_trend]

            is_up = values[-1] >= values[0]
            line_color = "#00C805" if is_up else "#FF5252"
            fill_color = "rgba(0,200,5,0.1)" if is_up else "rgba(255,82,82,0.1)"

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode="lines+markers",
                    line=dict(color=line_color, width=2),
                    marker=dict(size=5, color=line_color),
                    fill="tozeroy",
                    fillcolor=fill_color,
                    hovertemplate=f"%{{x}}<br>{t('chart.gross_margin')}: %{{y:.1f}}%<extra></extra>",
                    name=t("chart.gross_margin"),
                )
            )

            y_min = min(values)
            y_max = max(values)
            y_range = y_max - y_min
            padding = y_range * 0.05 if y_range > 0 else y_max * 0.02

            fig.update_layout(
                height=PRICE_CHART_HEIGHT,
                margin=dict(l=0, r=0, t=0, b=0),
                yaxis=dict(
                    range=[y_min - padding, y_max + padding],
                    showgrid=True,
                    gridcolor="rgba(128,128,128,0.15)",
                    ticksuffix="%",
                ),
                xaxis=dict(showgrid=False),
                showlegend=False,
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(
                fig, use_container_width=True, config={"displayModeBar": False}
            )
        else:
            st.caption(t("utils.moat.insufficient_data"))

        bias_val = signals.get("bias")
        price_is_weak = bias_val is not None and bias_val < PRICE_WEAK_BIAS_THRESHOLD
        margin_is_strong = margin_change is not None and margin_change > 0
        margin_is_bad = (
            margin_change is not None and margin_change < MARGIN_BAD_CHANGE_THRESHOLD
        )

        if margin_is_bad:
            st.error(t("utils.moat.thesis_broken"))
        elif price_is_weak and margin_is_strong:
            st.success(t("utils.moat.contrarian_buy"))
        elif margin_is_strong:
            st.success(t("utils.moat.moat_stable"))
        elif price_is_weak:
            st.warning(t("utils.moat.price_weak"))
        else:
            st.info(t("utils.moat.observing"))

        details = moat_data.get("details", "")
        if details:
            st.caption(f"📊 {details}")
    else:
        st.warning(t("utils.moat.no_data"))


def _render_scan_history_section(ticker: str) -> None:
    """Render scan history tab content."""
    scan_hist = fetch_scan_history(ticker)
    if scan_hist:
        latest_sig = scan_hist[0].get("signal", "NORMAL")
        consecutive = 1
        for i in range(1, len(scan_hist)):
            if scan_hist[i].get("signal") == latest_sig:
                consecutive += 1
            else:
                break
        if latest_sig != "NORMAL" and consecutive > 1:
            st.warning(
                t(
                    "utils.scan_history.consecutive_warning",
                    signal=latest_sig,
                    count=consecutive,
                )
            )

        for entry in scan_hist:
            sig = entry.get("signal", "NORMAL")
            scanned = entry.get("scanned_at", "")
            sig_icon = SCAN_SIGNAL_ICONS.get(sig, "⚪")
            date_str = scanned[:16] if scanned else "N/A"
            st.caption(f"{sig_icon} {sig} — {date_str}")
    else:
        st.caption(t("utils.scan_history.no_history"))


def _render_price_alerts_section(ticker: str, signals: dict) -> None:
    """Render price alerts tab content (list + create form)."""
    alerts = fetch_alerts(ticker)
    if alerts:
        st.markdown(t("utils.alerts.current_title"))
        for a in alerts:
            op_str = "<" if a["operator"] == "lt" else ">"
            active_badge = "🟢" if a["is_active"] else "⚪"
            triggered = a.get("last_triggered_at")
            trigger_info = (
                t("utils.alerts.last_triggered", date=triggered[:10])
                if triggered
                else ""
            )
            # Proximity indicator: how close is current value to threshold?
            proximity_label = ""
            current_sig = signals.get(a["metric"])
            if current_sig is not None:
                threshold = float(a["threshold"])
                current = float(current_sig)
                if a["operator"] == "lt":
                    delta = current - threshold  # positive = not triggered
                    if delta <= 0:
                        proximity_label = t("utils.alerts.proximity_triggered")
                    else:
                        pct = delta / abs(threshold) if threshold != 0 else delta
                        if pct < 0.10:
                            proximity_label = t("utils.alerts.proximity_close")
                else:  # gt
                    delta = threshold - current  # positive = not triggered
                    if delta <= 0:
                        proximity_label = t("utils.alerts.proximity_triggered")
                    else:
                        pct = delta / abs(threshold) if threshold != 0 else delta
                        if pct < 0.10:
                            proximity_label = t("utils.alerts.proximity_close")
            col_toggle, col_info, col_delete = st.columns([1, 4, 1])
            with col_toggle:
                toggle_icon = "⏸️" if a["is_active"] else "▶️"
                toggle_help = t("utils.alerts.pause_help") if a["is_active"] else t("utils.alerts.resume_help")
                if st.button(toggle_icon, key=f"toggle_alert_{a['id']}", help=toggle_help):
                    api_patch(f"/alerts/{a['id']}/toggle", {})
                    fetch_alerts.clear()
                    refresh_ui()
            with col_info:
                st.caption(
                    f"{active_badge} {a['metric']} {op_str} "
                    f"{a['threshold']}{trigger_info}"
                    + (f"  {proximity_label}" if proximity_label else "")
                )
            with col_delete:
                if st.button(
                    "🗑️", key=f"del_alert_{a['id']}", help=t("utils.alerts.delete_help")
                ):
                    api_delete(f"/alerts/{a['id']}")
                    fetch_alerts.clear()
                    refresh_ui()
        st.divider()

    st.markdown(t("utils.alerts.add_title"))
    alert_cols = st.columns(3)
    with alert_cols[0]:
        alert_metric = st.selectbox(
            t("utils.alerts.metric_label"),
            options=["rsi", "price", "bias"],
            key=f"alert_metric_{ticker}",
            label_visibility="collapsed",
        )
        current_val = signals.get(alert_metric)
        if current_val is not None:
            st.caption(t("utils.alerts.current_value", metric=alert_metric.upper(), value=f"{current_val:.2f}"))
    with alert_cols[1]:
        alert_op = st.selectbox(
            t("utils.alerts.condition_label"),
            options=["lt", "gt"],
            format_func=lambda x: t("utils.alerts.op_lt")
            if x == "lt"
            else t("utils.alerts.op_gt"),
            key=f"alert_op_{ticker}",
            label_visibility="collapsed",
        )
    with alert_cols[2]:
        metric_defaults = ALERT_DEFAULTS.get(alert_metric, {})
        if alert_metric == "price":
            raw_price = signals.get("price")
            default_val = float(raw_price) if raw_price is not None else DEFAULT_ALERT_THRESHOLD
        else:
            default_val = metric_defaults.get(alert_op, DEFAULT_ALERT_THRESHOLD)
        alert_threshold = st.number_input(
            t("utils.alerts.threshold_label"),
            value=default_val,
            step=1.0,
            key=f"alert_threshold_{ticker}_{alert_metric}_{alert_op}",
            label_visibility="collapsed",
        )

    if st.button(t("utils.alerts.add_button"), key=f"add_alert_{ticker}"):
        result = api_post(
            f"/ticker/{ticker}/alerts",
            {
                "metric": alert_metric,
                "operator": alert_op,
                "threshold": alert_threshold,
            },
        )
        if result:
            st.success(result.get("message", t("utils.alerts.created")))
            fetch_alerts.clear()
            refresh_ui()


def _render_thesis_editor(ticker: str, stock: dict) -> None:
    """Render thesis history + editor tab content."""
    current_tags = stock.get("current_tags", [])
    history = fetch_thesis_history(ticker)
    render_thesis_history(history or [])

    st.markdown(t("utils.thesis.add_title"))
    new_thesis_content = st.text_area(
        t("utils.thesis.content_label"),
        key=f"thesis_input_{ticker}",
        placeholder=t("utils.thesis.placeholder"),
        label_visibility="collapsed",
    )

    all_tag_options = sorted(set(DEFAULT_TAG_OPTIONS + current_tags))
    selected_tags = st.multiselect(
        t("utils.thesis.tags_label"),
        options=all_tag_options,
        default=current_tags,
        key=f"tag_select_{ticker}",
    )

    if st.button(t("utils.thesis.update_button"), key=f"thesis_btn_{ticker}"):
        if new_thesis_content.strip():
            result = api_post(
                f"/ticker/{ticker}/thesis",
                {"content": new_thesis_content.strip(), "tags": selected_tags},
            )
            if result:
                st.success(result.get("message", t("utils.thesis.updated")))
                fetch_thesis_history.clear()
                fetch_stocks.clear()
                refresh_ui()
        else:
            st.warning(t("utils.thesis.empty_error"))


@st.fragment
def _render_price_chart(ticker: str) -> None:
    """Render interactive price trend chart with 60MA overlay."""
    price_data = fetch_price_history(ticker)
    if price_data and len(price_data) > 5:
        period_tabs = list(PRICE_CHART_PERIODS.keys())
        default_idx = period_tabs.index(PRICE_CHART_DEFAULT_PERIOD)
        period_label = st.radio(
            t("chart.trend_period"),
            period_tabs,
            index=default_idx,
            horizontal=True,
            key=f"chart_period_{ticker}",
            label_visibility="collapsed",
        )
        n_days = PRICE_CHART_PERIODS[period_label]
        sliced = price_data[-n_days:]

        dates = [p["date"] for p in sliced]
        prices = [p["close"] for p in sliced]

        is_up = prices[-1] >= prices[0]
        line_color = "#00C805" if is_up else "#FF5252"
        fill_color = "rgba(0,200,5,0.1)" if is_up else "rgba(255,82,82,0.1)"

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=prices,
                mode="lines",
                line=dict(color=line_color, width=2),
                fill="tozeroy",
                fillcolor=fill_color,
                hovertemplate="%{x}<br>$%{y:.2f}<extra></extra>",
                name=t("chart.close_price"),
            )
        )

        if len(sliced) >= 60:
            df_ma = pd.DataFrame(sliced)
            ma60 = df_ma["close"].rolling(window=60).mean().tolist()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=ma60,
                    mode="lines",
                    line=dict(color="#888", width=1, dash="dot"),
                    name="60MA",
                    hovertemplate="%{x}<br>60MA: $%{y:.2f}<extra></extra>",
                )
            )

        y_min = min(prices)
        y_max = max(prices)
        y_range = y_max - y_min
        padding = y_range * 0.05 if y_range > 0 else y_max * 0.02

        fig.update_layout(
            height=PRICE_CHART_HEIGHT,
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(
                range=[y_min - padding, y_max + padding],
                showgrid=True,
                gridcolor="rgba(128,128,128,0.15)",
            ),
            xaxis=dict(showgrid=False),
            showlegend=False,
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption(t("utils.price_chart.insufficient_data"))


def render_stock_card(
    stock: dict,
    enrichment: dict | None = None,
    resonance: list | None = None,
) -> None:
    """Render a single stock card with technical indicators and thesis editing.

    Args:
        stock: Stock data dict from the /stocks endpoint.
        enrichment: Optional pre-fetched enrichment data from /stocks/enriched.
            When provided, avoids individual API calls for signals, earnings,
            and dividends (lazy-loading optimisation).
        resonance: Optional list of guru resonance dicts for this ticker.
            When provided, shows a 🏆 badge in the card header.
    """
    ticker = stock["ticker"]
    cat = stock.get("category", "")

    # Use pre-fetched data when available, otherwise fall back to individual calls
    if enrichment and cat not in SKIP_SIGNALS_CATEGORIES:
        signals = enrichment.get("signals") or {}
    elif cat in SKIP_SIGNALS_CATEGORIES:
        signals = {}
    else:
        signals = fetch_signals(ticker) or {}

    # Build expander header with signal icon, ticker, category, price, daily change, and market
    if enrichment and enrichment.get("computed_signal"):
        last_signal = enrichment["computed_signal"]
    else:
        last_signal = stock.get("last_scan_signal", "NORMAL")
    signal_icon = SCAN_SIGNAL_ICONS.get(last_signal, "⚪")
    cat_label_short = get_category_labels().get(cat, cat).split("(")[0].strip()
    price = signals.get("price", "")
    price_str = f" | ${price}" if price and price != "N/A" else ""

    # Add daily change to header
    change_pct = signals.get("change_pct")
    if change_pct is not None:
        arrow = "▲" if change_pct >= 0 else "▼"
        change_str = f" ({arrow}{abs(change_pct):.2f}%)"
    else:
        change_str = ""

    market_label = infer_market_label(ticker)
    resonance_badge = f" | 🏆×{len(resonance)}" if resonance else ""
    signal_label = SCAN_SIGNAL_LABELS.get(last_signal, "")
    signal_label_str = f" | {signal_label}" if signal_label else ""
    header = f"{signal_icon} {ticker} — {cat_label_short}{price_str}{change_str} | {market_label}{resonance_badge}{signal_label_str}"

    with st.expander(header, expanded=False):
        # ── Tier 1: At-a-Glance ────────────────────────────────────────────
        _render_signal_metrics(signals)

        st.markdown(t("utils.stock_card.current_thesis_title"))
        st.info(stock.get("current_thesis", t("utils.stock_card.no_thesis")))

        _render_price_chart(ticker)

        current_tags = stock.get("current_tags", [])
        if current_tags:
            tag_badges = " ".join(f"`{tag}`" for tag in current_tags)
            st.markdown(f"🏷️ {tag_badges}")

        # ── Tier 2: Detail Tabs ────────────────────────────────────────────
        _show_moat = stock.get("category") not in SKIP_MOAT_CATEGORIES
        _tab_labels = [t("utils.stock_card.tab.metrics")]
        if _show_moat:
            _tab_labels.append(t("utils.stock_card.tab.moat"))
        _tab_labels += [
            t("utils.stock_card.tab.scan_history"),
            t("utils.stock_card.tab.chips"),
            t("utils.stock_card.tab.alerts"),
            t("utils.stock_card.mgmt.thesis"),
            t("utils.stock_card.mgmt.category"),
            t("utils.stock_card.mgmt.remove"),
        ]
        _tabs = st.tabs(_tab_labels)
        _tab_idx = 0

        # -- Metrics tab --
        with _tabs[_tab_idx]:
            _render_full_metrics(signals)

            # Earnings & Dividend
            info_cols = st.columns(2)
            if enrichment:
                earnings_data = enrichment.get("earnings")
            else:
                earnings_data = fetch_earnings(ticker)
            earnings_date_str = (
                earnings_data.get("earnings_date") if earnings_data else None
            )
            with info_cols[0]:
                if earnings_date_str:
                    try:
                        ed = dt.strptime(earnings_date_str, "%Y-%m-%d")
                        days_left = (ed - dt.now()).days
                        badge = (
                            t("utils.stock_card.earnings_badge", days=days_left)
                            if 0 < days_left <= EARNINGS_BADGE_DAYS_THRESHOLD
                            else ""
                        )
                        st.caption(
                            t(
                                "utils.stock_card.earnings_date",
                                date=earnings_date_str,
                                badge=badge,
                            )
                        )
                    except ValueError:
                        st.caption(
                            t(
                                "utils.stock_card.earnings_date",
                                date=earnings_date_str,
                                badge="",
                            )
                        )
                else:
                    st.caption(t("utils.earnings.na"))

            with info_cols[1]:
                if cat in ("Moat", "Bond"):
                    if enrichment:
                        div_data = enrichment.get("dividend")
                    else:
                        div_data = fetch_dividend(ticker)
                    if div_data and div_data.get("dividend_yield"):
                        dy = div_data["dividend_yield"]
                        ex_date = div_data.get("ex_dividend_date", "N/A")
                        st.caption(
                            t("utils.stock_card.dividend_yield", dy=dy, ex_date=ex_date)
                        )
                    else:
                        st.caption(t("utils.dividend.na"))

            if resonance:
                guru_names = ", ".join(
                    g.get("guru_display_name", "?") for g in resonance
                )
                st.caption(
                    t(
                        "utils.stock_card.resonance_badge",
                        count=len(resonance),
                        gurus=guru_names,
                    )
                )
        _tab_idx += 1

        # -- Moat tab (conditional) --
        if _show_moat:
            with _tabs[_tab_idx]:
                _render_moat_section(ticker, signals)
            _tab_idx += 1

        # -- Scan History tab --
        with _tabs[_tab_idx]:
            _render_scan_history_section(ticker)
        _tab_idx += 1

        # -- Chips (13F) tab --
        with _tabs[_tab_idx]:
            st.link_button(
                t("utils.stock_card.whalewisdom_button"),
                WHALEWISDOM_STOCK_URL.format(ticker=ticker.lower()),
                use_container_width=True,
            )
            st.caption(t("utils.stock_card.whalewisdom_hint"))
            holders = signals.get("institutional_holders")
            if holders and isinstance(holders, list) and len(holders) > 0:
                st.markdown(t("utils.stock_card.top_holders_title"))
                st.dataframe(holders, use_container_width=True, hide_index=True)
            else:
                st.info(t("utils.stock_card.no_holders"))
        _tab_idx += 1

        # -- Alerts tab --
        with _tabs[_tab_idx]:
            _render_price_alerts_section(ticker, signals)
        _tab_idx += 1

        # -- Thesis Versioning tab --
        with _tabs[_tab_idx]:
            _render_thesis_editor(ticker, stock)
        _tab_idx += 1

        # -- Change Category tab --
        with _tabs[_tab_idx]:
            current_cat = stock.get("category", "Growth")
            other_categories = [c for c in CATEGORY_OPTIONS if c != current_cat]
            current_label = get_category_labels().get(current_cat, current_cat)
            st.caption(
                t("utils.stock_card.current_category", category=current_label)
            )
            new_cat = st.selectbox(
                t("utils.stock_card.new_category"),
                options=other_categories,
                format_func=lambda x: get_category_labels().get(x, x),
                key=f"cat_select_{ticker}",
                label_visibility="collapsed",
            )
            if st.button(
                t("utils.stock_card.confirm_switch"), key=f"cat_btn_{ticker}"
            ):
                result = api_patch(
                    f"/ticker/{ticker}/category",
                    {"category": new_cat},
                )
                if result:
                    st.success(
                        result.get(
                            "message", t("utils.stock_card.category_changed")
                        )
                    )
                    invalidate_stock_caches()
                    refresh_ui()
        _tab_idx += 1

        # -- Remove tab --
        with _tabs[_tab_idx]:
            st.warning(t("utils.stock_card.remove_warning"))
            removal_reason = st.text_area(
                t("utils.stock_card.removal_reason_label"),
                key=f"removal_input_{ticker}",
                placeholder=t("utils.stock_card.removal_placeholder"),
                label_visibility="collapsed",
            )
            if st.button(
                t("utils.stock_card.confirm_remove"),
                key=f"removal_btn_{ticker}",
                type="primary",
            ):
                if removal_reason.strip():
                    result = api_post(
                        f"/ticker/{ticker}/deactivate",
                        {"reason": removal_reason.strip()},
                    )
                    if result:
                        st.success(
                            result.get("message", t("utils.stock_card.removed"))
                        )
                        invalidate_stock_caches()
                        refresh_ui()
                else:
                    st.warning(t("utils.stock_card.remove_reason_required"))


def render_reorder_section(category_key: str, stocks_in_cat: list[dict]) -> None:
    """Render drag-and-drop reorder section (only when enabled by user)."""
    if len(stocks_in_cat) < REORDER_MIN_STOCKS:
        return
    reorder_on = st.checkbox(
        t("utils.reorder.checkbox"), key=f"reorder_{category_key}", value=False
    )
    if reorder_on:
        ticker_list = [s["ticker"] for s in stocks_in_cat]
        sorted_tickers = sort_items(ticker_list, key=f"sort_{category_key}")
        if sorted_tickers != ticker_list:
            if st.button(
                t("utils.reorder.save_button"), key=f"save_order_{category_key}"
            ):
                result = api_put("/stocks/reorder", {"ordered_tickers": sorted_tickers})
                if result:
                    st.success(t("utils.reorder.saved"))
                    fetch_stocks.clear()
                    fetch_enriched_stocks.clear()
                    refresh_ui()
        else:
            st.caption(t("utils.reorder.hint"))


# ===========================================================================
# Smart Money (大師足跡) — Cached Fetchers
# ===========================================================================


@st.cache_data(ttl=CACHE_TTL_GURU_LIST, show_spinner=False)
def fetch_gurus() -> list | None:
    """Fetch all active gurus."""
    try:
        resp = _session.get(f"{BACKEND_URL}/gurus", timeout=API_GURU_GET_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_GURU_FILING, show_spinner=False)
def fetch_guru_filing(guru_id: int) -> dict | None:
    """Fetch latest 13F filing summary for one guru."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/gurus/{guru_id}/filing", timeout=API_GURU_GET_TIMEOUT
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_GURU_FILING, show_spinner=False)
def fetch_guru_top_holdings(guru_id: int, n: int = 10) -> list | None:
    """Fetch top N holdings by weight for one guru."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/gurus/{guru_id}/top",
            params={"n": n},
            timeout=API_GURU_GET_TIMEOUT,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_GURU_FILING, show_spinner=False)
def fetch_guru_holding_changes(guru_id: int, limit: int = 20) -> list | None:
    """
    Fetch holdings with action != UNCHANGED for one guru.
    
    Args:
        guru_id: The guru ID
        limit: Max number of changes to return (default 20)
    
    Returns:
        List of holding changes sorted by significance, or None on error
    """
    try:
        resp = _session.get(
            f"{BACKEND_URL}/gurus/{guru_id}/holdings",
            params={"limit": limit},
            timeout=API_GURU_GET_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_RESONANCE, show_spinner=False)
def fetch_great_minds() -> dict | None:
    """Fetch Great Minds Think Alike resonance list."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/resonance/great-minds", timeout=API_GURU_GET_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_GURU_DASHBOARD, show_spinner=False)
def fetch_guru_dashboard() -> dict | None:
    """Fetch aggregated dashboard summary across all gurus (GET /gurus/dashboard)."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/gurus/dashboard", timeout=API_GURU_DASHBOARD_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_GURU_FILING, show_spinner=False)
def fetch_guru_filings(guru_id: int) -> list | None:
    """Fetch all synced filing history for one guru (GET /gurus/{id}/filings)."""
    try:
        resp = _session.get(
            f"{BACKEND_URL}/gurus/{guru_id}/filings", timeout=API_GURU_GET_TIMEOUT
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return data.get("filings", [])
    except requests.RequestException:
        return None


def sync_guru(guru_id: int) -> dict | None:
    """Trigger 13F sync for a single guru (not cached — mutating)."""
    try:
        resp = _session.post(
            f"{BACKEND_URL}/gurus/{guru_id}/sync", timeout=API_GURU_SYNC_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error("guru sync 失敗 (id=%s): %s", guru_id, exc)
        return None


def add_guru(name: str, cik: str, display_name: str) -> dict | None:
    """Add a custom guru by CIK."""
    return api_post("/gurus", {"name": name, "cik": cik, "display_name": display_name})


@st.cache_data(ttl=CACHE_TTL_RESONANCE, show_spinner=False)
def fetch_resonance_overview() -> dict[str, list] | None:
    """Fetch portfolio resonance overview as a ticker→gurus map (1 API call).

    Calls GET /resonance which returns all guru overlaps in a single response,
    then inverts the guru-centric structure into a ticker-keyed dict suitable
    for O(1) lookup when rendering each stock card.

    Returns:
        {ticker: [{guru_display_name, action, weight_pct, ...}, ...], ...}
        or None on backend error.
    """
    try:
        resp = _session.get(f"{BACKEND_URL}/resonance", timeout=API_GURU_GET_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None

    # Invert: guru-centric → ticker-centric map
    ticker_map: dict[str, list] = {}
    for entry in data.get("results", []):
        guru_name = entry.get("guru_display_name", "?")
        for holding in entry.get("holdings", []):
            ticker = holding.get("ticker")
            if not ticker:
                continue
            guru_info = {**holding, "guru_display_name": guru_name}
            ticker_map.setdefault(ticker, []).append(guru_info)
    return ticker_map


def invalidate_guru_caches() -> None:
    """Clear all Smart Money caches after sync or add."""
    fetch_gurus.clear()
    fetch_guru_filing.clear()
    fetch_guru_top_holdings.clear()
    fetch_guru_holding_changes.clear()
    fetch_guru_dashboard.clear()
    fetch_guru_filings.clear()
    fetch_great_minds.clear()
    fetch_resonance_overview.clear()
