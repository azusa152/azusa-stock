"""
Application — Rebalance Service：再平衡分析、匯率曝險、X-Ray、FX 警報。
"""

import json as _json
from datetime import datetime, timezone

from sqlmodel import Session, select

from application.stock_service import StockNotFoundError
from domain.analysis import compute_daily_change_pct
from domain.constants import (
    DEFAULT_USER_ID,
    XRAY_SINGLE_STOCK_WARN_PCT,
    XRAY_SKIP_CATEGORIES,
)
from domain.entities import Holding, UserInvestmentProfile
from domain.enums import FX_ALERT_LABEL
from domain.fx_analysis import (
    FXRateAlert,
    analyze_fx_rate_changes,
    determine_fx_risk_level,
)
from domain.rebalance import calculate_rebalance as _pure_rebalance
from i18n import get_user_language, t
from infrastructure.market_data import (
    get_etf_top_holdings,
    get_exchange_rates,
    get_forex_history,
    get_forex_history_long,
    get_technical_signals,
    prewarm_etf_holdings_batch,
    prewarm_signals_batch,
)
from infrastructure.notification import (
    is_notification_enabled,
    send_telegram_message_dual,
)
from logging_config import get_logger

logger = get_logger(__name__)


# ===========================================================================
# 共用持倉市值計算
# ===========================================================================


def _compute_holding_market_values(
    holdings: list,
    fx_rates: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], dict[str, dict]]:
    """
    共用邏輯：計算所有持倉的當前與前一交易日市值（已換算目標幣別）。
    回傳 (currency_values, cash_currency_values, ticker_agg)。

    - currency_values: {幣別: 總市值} — 全部持倉（當前）
    - cash_currency_values: {幣別: 現金市值} — 僅現金部位
    - ticker_agg: {ticker: {category, currency, qty, mv, prev_mv, cost_sum, cost_qty, price, fx}}
      其中 prev_mv 為前一交易日市值，用於日漲跌計算
    """
    currency_values: dict[str, float] = {}
    cash_currency_values: dict[str, float] = {}
    ticker_agg: dict[str, dict] = {}

    for h in holdings:
        cat = h.category.value if hasattr(h.category, "value") else str(h.category)
        fx = fx_rates.get(h.currency, 1.0)
        price: float | None = None
        previous_close: float | None = None

        has_prev_close = False

        if h.is_cash:
            # 現金部位無日內價格變動
            market_value = h.quantity * fx
            previous_market_value = market_value  # 現金前後市值相同
            has_prev_close = True  # 現金視為「有前日資料」（變動固定為 0）
            price = 1.0
            cash_currency_values[h.currency] = (
                cash_currency_values.get(h.currency, 0.0) + market_value
            )
        else:
            # 非現金持倉：取得當前與前一交易日價格
            signals = get_technical_signals(h.ticker)
            price = signals.get("price") if signals else None
            previous_close = signals.get("previous_close") if signals else None

            # 計算當前市值
            if price is not None and isinstance(price, (int, float)):
                market_value = h.quantity * price * fx
            elif h.cost_basis is not None:
                market_value = h.quantity * h.cost_basis * fx
            else:
                market_value = 0.0

            # 計算前一交易日市值
            if previous_close is not None and isinstance(previous_close, (int, float)):
                previous_market_value = h.quantity * previous_close * fx
                has_prev_close = True
            else:
                # 無 previous_close 時回退至當前市值，使組合層級日漲跌不受影響
                previous_market_value = market_value

        currency_values[h.currency] = (
            currency_values.get(h.currency, 0.0) + market_value
        )

        key = h.ticker
        if key not in ticker_agg:
            ticker_agg[key] = {
                "category": cat,
                "currency": h.currency,
                "qty": 0.0,
                "mv": 0.0,
                "prev_mv": 0.0,
                "cost_sum": 0.0,
                "cost_qty": 0.0,
                "price": price,
                "fx": fx,
                "has_prev_close": False,
            }
        ticker_agg[key]["qty"] += h.quantity
        ticker_agg[key]["mv"] += market_value
        ticker_agg[key]["prev_mv"] += previous_market_value
        if has_prev_close:
            ticker_agg[key]["has_prev_close"] = True
        if h.cost_basis is not None:
            ticker_agg[key]["cost_sum"] += h.cost_basis * h.quantity
            ticker_agg[key]["cost_qty"] += h.quantity

    return currency_values, cash_currency_values, ticker_agg


# ===========================================================================
# 再平衡分析
# ===========================================================================


def calculate_rebalance(session: Session, display_currency: str = "USD") -> dict:
    """
    計算再平衡分析：比較目標配置與實際持倉。
    1. 讀取啟用中的 UserInvestmentProfile（目標配置）
    2. 讀取所有 Holding（實際持倉）
    3. 取得匯率，將所有持倉轉換為 display_currency
    4. 對非現金持倉查詢即時價格
    5. 委託 domain.rebalance 純函式計算偏移與建議
    """
    lang = get_user_language(session)

    # 1) 取得目標配置
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()

    if not profile:
        raise StockNotFoundError(t("rebalance.no_profile", lang=lang))

    target_config: dict[str, float] = _json.loads(profile.config)

    # 2) 取得所有持倉
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()

    if not holdings:
        raise StockNotFoundError(t("rebalance.no_holdings", lang=lang))

    # 3) 取得匯率：收集所有持倉幣別，批次取得相對 display_currency 的匯率
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(display_currency, holding_currencies)
    logger.info(
        "匯率轉換（→ %s）：%s",
        display_currency,
        {k: round(v, 4) for k, v in fx_rates.items()},
    )

    # 3.5) 並行預熱所有非現金持倉的技術訊號（避免逐一串行呼叫 yfinance）
    non_cash_tickers = list({h.ticker for h in holdings if not h.is_cash})
    if non_cash_tickers:
        logger.info("並行預熱 %d 檔股票技術訊號...", len(non_cash_tickers))
        prewarm_signals_batch(non_cash_tickers)

    # 4) 使用共用邏輯計算各持倉市值
    currency_values, _cash_values, ticker_agg = _compute_holding_market_values(
        holdings,
        fx_rates,
    )

    # 4.5) 取得每個分類的市值合計
    category_values: dict[str, float] = {}
    for _key, agg in ticker_agg.items():
        cat = agg["category"]
        category_values[cat] = category_values.get(cat, 0.0) + agg["mv"]

    # 5) 委託 domain 純函式計算
    result = _pure_rebalance(category_values, target_config)

    # 6) 計算投資組合日漲跌
    total_value = result["total_value"]
    previous_total_value = sum(agg["prev_mv"] for agg in ticker_agg.values())
    total_value_change = round(total_value - previous_total_value, 2)
    total_value_change_pct = compute_daily_change_pct(total_value, previous_total_value)

    logger.info(
        "投資組合日漲跌：previous=%.2f, current=%.2f, change=%.2f (%.2f%%)",
        previous_total_value,
        total_value,
        total_value_change,
        total_value_change_pct if total_value_change_pct is not None else 0.0,
    )

    # 加入結果
    result["previous_total_value"] = round(previous_total_value, 2)
    result["total_value_change"] = round(total_value_change, 2)
    result["total_value_change_pct"] = total_value_change_pct

    # 7) 建立個股明細（含佔比）
    holdings_detail = []
    for ticker, agg in ticker_agg.items():
        avg_cost = (
            round(agg["cost_sum"] / agg["cost_qty"], 2) if agg["cost_qty"] > 0 else None
        )
        weight_pct = (
            round((agg["mv"] / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        cur_price = agg["price"]

        # 計算個股日漲跌百分比（無前日資料時回傳 None → 前端顯示 N/A）
        if agg["has_prev_close"]:
            holding_change_pct = compute_daily_change_pct(agg["mv"], agg["prev_mv"])
        else:
            holding_change_pct = None

        cost_total = (
            round(agg["cost_sum"] * agg["fx"], 2) if agg["cost_qty"] > 0 else None
        )

        holdings_detail.append(
            {
                "ticker": ticker,
                "category": agg["category"],
                "currency": agg["currency"],
                "quantity": round(agg["qty"], 4),
                "market_value": round(agg["mv"], 2),
                "weight_pct": weight_pct,
                "avg_cost": avg_cost,
                "cost_total": cost_total,
                "current_price": (
                    round(cur_price, 2)
                    if cur_price is not None and isinstance(cur_price, (int, float))
                    else None
                ),
                "fx": round(agg["fx"], 6),
                "change_pct": holding_change_pct,
            }
        )

    # 依權重降序排列（最大持倉在前）
    holdings_detail.sort(key=lambda x: x["weight_pct"], reverse=True)
    result["holdings_detail"] = holdings_detail
    result["display_currency"] = display_currency

    # 8) X-Ray: 穿透式持倉分析（解析 ETF 成分股，計算真實曝險）
    # 先並行預熱所有可能的 ETF 成分股快取
    xray_tickers = [
        t
        for t, agg in ticker_agg.items()
        if agg["category"] not in XRAY_SKIP_CATEGORIES and agg["mv"] > 0
    ]
    if xray_tickers:
        logger.info("並行預熱 %d 檔 ETF 成分股...", len(xray_tickers))
        prewarm_etf_holdings_batch(xray_tickers)

    xray_map: dict[str, dict] = {}  # symbol -> {direct, indirect, sources, name}

    for ticker, agg in ticker_agg.items():
        cat = agg["category"]
        mv = agg["mv"]
        if cat in XRAY_SKIP_CATEGORIES or mv <= 0:
            continue

        # 嘗試取得 ETF 成分股
        constituents = get_etf_top_holdings(ticker)
        if constituents:
            # 此 ticker 是 ETF — 計算間接曝險
            for c in constituents:
                sym = c["symbol"]
                weight = c["weight"]
                indirect_mv = mv * weight
                if sym not in xray_map:
                    xray_map[sym] = {
                        "name": c.get("name", ""),
                        "direct": 0.0,
                        "indirect": 0.0,
                        "sources": [],
                    }
                xray_map[sym]["indirect"] += indirect_mv
                src_pct = round(weight * 100, 2)
                xray_map[sym]["sources"].append(f"{ticker} ({src_pct}%)")
        else:
            # 非 ETF — 記錄為直接持倉
            if ticker not in xray_map:
                xray_map[ticker] = {
                    "name": "",
                    "direct": 0.0,
                    "indirect": 0.0,
                    "sources": [],
                }
            xray_map[ticker]["direct"] += mv

    # 組合 X-Ray 結果
    xray_entries = []
    for symbol, data in xray_map.items():
        total_val = data["direct"] + data["indirect"]
        if total_val <= 0:
            continue
        direct_pct = (
            round((data["direct"] / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        indirect_pct = (
            round((data["indirect"] / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        total_pct = (
            round((total_val / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        xray_entries.append(
            {
                "symbol": symbol,
                "name": data["name"],
                "direct_value": round(data["direct"], 2),
                "direct_weight_pct": direct_pct,
                "indirect_value": round(data["indirect"], 2),
                "indirect_weight_pct": indirect_pct,
                "total_value": round(total_val, 2),
                "total_weight_pct": total_pct,
                "indirect_sources": data["sources"],
            }
        )

    xray_entries.sort(key=lambda x: x["total_weight_pct"], reverse=True)
    result["xray"] = xray_entries
    result["calculated_at"] = datetime.now(timezone.utc).isoformat()

    return result


def send_xray_warnings(
    xray_entries: list[dict],
    display_currency: str,
    session: Session,
) -> list[str]:
    """
    檢查 X-Ray 結果，對超過單一標的風險門檻的持倉發送 Telegram 警告。
    回傳已發送的警告訊息列表。
    """
    lang = get_user_language(session)
    warnings: list[str] = []
    for entry in xray_entries:
        total_pct = entry.get("total_weight_pct", 0.0)
        indirect_val = entry.get("indirect_value", 0.0)
        if total_pct > XRAY_SINGLE_STOCK_WARN_PCT and indirect_val > 0:
            symbol = entry["symbol"]
            direct_pct = entry.get("direct_weight_pct", 0.0)
            sources = ", ".join(entry.get("indirect_sources", []))
            msg = t(
                "rebalance.xray_warning",
                lang=lang,
                symbol=symbol,
                direct_pct=direct_pct,
                sources=sources,
                total_pct=total_pct,
                threshold=XRAY_SINGLE_STOCK_WARN_PCT,
            )
            warnings.append(msg)

    if warnings:
        if is_notification_enabled(session, "xray_alerts"):
            full_msg = (
                t("rebalance.xray_header", lang=lang) + "\n\n" + "\n\n".join(warnings)
            )
            try:
                send_telegram_message_dual(full_msg, session)
                logger.info("已發送 X-Ray 警告（%d 筆）", len(warnings))
            except Exception as e:
                logger.warning("X-Ray Telegram 警告發送失敗：%s", e)
        else:
            logger.info("X-Ray 通知已被使用者停用，跳過發送。")

    return warnings


# ===========================================================================
# Currency Exposure Monitor
# ===========================================================================


def calculate_currency_exposure(
    session: Session, home_currency: str | None = None
) -> dict:
    """
    計算匯率曝險分析：
    1. 讀取使用者 Profile 的 home_currency（或使用參數覆寫）
    2. 將所有持倉按幣別分組，計算以本幣計價的市值
    3. 偵測近期匯率變動
    4. 產出風險等級與建議
    """
    # 1) 決定本幣
    if not home_currency:
        profile = session.exec(
            select(UserInvestmentProfile)
            .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
            .where(UserInvestmentProfile.is_active == True)  # noqa: E712
        ).first()
        home_currency = profile.home_currency if profile else "TWD"

    # 2) 取得所有持倉
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()

    if not holdings:
        return {
            "home_currency": home_currency,
            "total_value_home": 0.0,
            "breakdown": [],
            "non_home_pct": 0.0,
            "cash_breakdown": [],
            "cash_non_home_pct": 0.0,
            "total_cash_home": 0.0,
            "fx_movements": [],
            "risk_level": "low",
            "advice": [
                t("rebalance.no_holdings_data", lang=get_user_language(session))
            ],
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    # 3) 取得匯率（all currencies → home_currency）
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(home_currency, holding_currencies)
    logger.info(
        "匯率曝險分析 → %s：%s",
        home_currency,
        {k: round(v, 4) for k, v in fx_rates.items()},
    )

    # 3.5) 並行預熱所有非現金持倉的技術訊號
    non_cash_tickers = list({h.ticker for h in holdings if not h.is_cash})
    if non_cash_tickers:
        prewarm_signals_batch(non_cash_tickers)

    # 4) 使用共用邏輯計算市值（以本幣計價），同時追蹤現金部位
    currency_values, cash_currency_values, _ticker_agg = _compute_holding_market_values(
        holdings,
        fx_rates,
    )

    total_value_home = sum(currency_values.values())
    total_cash_home = sum(cash_currency_values.values())

    # 5) 建立幣別分佈（全資產）
    breakdown = []
    for cur, val in sorted(currency_values.items(), key=lambda x: x[1], reverse=True):
        pct = round((val / total_value_home) * 100, 2) if total_value_home > 0 else 0.0
        breakdown.append(
            {
                "currency": cur,
                "value": round(val, 2),
                "percentage": pct,
                "is_home": cur == home_currency,
            }
        )

    non_home_pct = round(
        sum(b["percentage"] for b in breakdown if not b["is_home"]),
        2,
    )

    # 5b) 建立現金幣別分佈
    cash_breakdown = []
    for cur, val in sorted(
        cash_currency_values.items(), key=lambda x: x[1], reverse=True
    ):
        pct = round((val / total_cash_home) * 100, 2) if total_cash_home > 0 else 0.0
        cash_breakdown.append(
            {
                "currency": cur,
                "value": round(val, 2),
                "percentage": pct,
                "is_home": cur == home_currency,
            }
        )

    cash_non_home_pct = round(
        sum(b["percentage"] for b in cash_breakdown if not b["is_home"]),
        2,
    )

    # 6) 偵測近期匯率變動（非本幣 → 本幣）
    fx_movements = []
    non_home_currencies = [cur for cur in currency_values if cur != home_currency]
    currency_histories: dict[str, list[dict]] = {}
    for cur in non_home_currencies:
        history = get_forex_history(cur, home_currency)
        currency_histories[cur] = history
        if len(history) >= 2:
            first_close = history[0]["close"]
            last_close = history[-1]["close"]
            if first_close > 0:
                change_pct = round(((last_close - first_close) / first_close) * 100, 2)
                direction = (
                    "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
                )
                fx_movements.append(
                    {
                        "pair": f"{cur}/{home_currency}",
                        "current_rate": last_close,
                        "change_pct": change_pct,
                        "direction": direction,
                    }
                )

    # 6b) 三層匯率變動警報（單日 / 5日 / 3月）
    all_fx_alerts: list[FXRateAlert] = []
    for cur in non_home_currencies:
        short_hist = currency_histories.get(cur, [])
        long_hist = get_forex_history_long(cur, home_currency)
        current_rate = short_hist[-1]["close"] if short_hist else 0.0
        alerts_for_pair = analyze_fx_rate_changes(
            pair=f"{cur}/{home_currency}",
            current_rate=current_rate,
            short_history=short_hist,
            long_history=long_hist,
        )
        all_fx_alerts.extend(alerts_for_pair)

    # 7) 風險等級（基於匯率變動警報嚴重程度）
    risk_level = determine_fx_risk_level(all_fx_alerts)

    # 8) 序列化警報
    fx_rate_alerts_serialized = [
        {
            "pair": a.pair,
            "alert_type": a.alert_type.value,
            "change_pct": a.change_pct,
            "direction": a.direction,
            "current_rate": a.current_rate,
            "period_label": a.period_label,
        }
        for a in all_fx_alerts
    ]

    # 9) 建議（包含現金部位資訊）
    lang = get_user_language(session)
    advice = _generate_fx_advice(
        home_currency,
        breakdown,
        non_home_pct,
        risk_level,
        fx_movements,
        fx_rate_alerts=all_fx_alerts,
        cash_breakdown=cash_breakdown,
        cash_non_home_pct=cash_non_home_pct,
        total_cash_home=total_cash_home,
        lang=lang,
    )

    return {
        "home_currency": home_currency,
        "total_value_home": round(total_value_home, 2),
        "breakdown": breakdown,
        "non_home_pct": non_home_pct,
        "cash_breakdown": cash_breakdown,
        "cash_non_home_pct": cash_non_home_pct,
        "total_cash_home": round(total_cash_home, 2),
        "fx_movements": fx_movements,
        "fx_rate_alerts": fx_rate_alerts_serialized,
        "risk_level": risk_level,
        "advice": advice,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def _generate_fx_advice(
    home_currency: str,
    breakdown: list[dict],
    non_home_pct: float,
    risk_level: str,
    fx_movements: list[dict],
    *,
    fx_rate_alerts: list[FXRateAlert] | None = None,
    cash_breakdown: list[dict] | None = None,
    cash_non_home_pct: float = 0.0,
    total_cash_home: float = 0.0,
    lang: str = "zh-TW",
) -> list[str]:
    """根據匯率變動警報產出建議文字。"""
    advice: list[str] = []
    fx_rate_alerts = fx_rate_alerts or []

    # 匯率變動風險摘要
    if risk_level == "high":
        advice.append(t("rebalance.fx_risk_high", lang=lang))
    elif risk_level == "medium":
        advice.append(t("rebalance.fx_risk_medium", lang=lang))
    else:
        advice.append(t("rebalance.fx_risk_low", lang=lang))

    # 非本幣佔比資訊（保留但不作為警報觸發）
    if non_home_pct > 0:
        advice.append(
            t("rebalance.non_home_pct", lang=lang, home=home_currency, pct=non_home_pct)
        )

    # 現金部位專屬建議
    if cash_breakdown:
        foreign_cash = [b for b in cash_breakdown if not b["is_home"]]
        if foreign_cash and cash_non_home_pct > 0:
            top_cash_cur = foreign_cash[0]["currency"]
            top_cash_val = foreign_cash[0]["value"]
            advice.append(
                t(
                    "rebalance.foreign_cash_warning",
                    lang=lang,
                    pct=cash_non_home_pct,
                    currency=top_cash_cur,
                    value=top_cash_val,
                    home=home_currency,
                )
            )

    # 個別警報詳情
    cash_by_cur = {b["currency"]: b["value"] for b in (cash_breakdown or [])}
    for alert in fx_rate_alerts:
        base_cur = alert.pair.split("/")[0]
        cash_amt = cash_by_cur.get(base_cur, 0.0)
        cash_note = (
            t(
                "rebalance.cash_impact",
                lang=lang,
                currency=base_cur,
                amount=cash_amt,
                home=home_currency,
            )
            if cash_amt > 0
            else ""
        )
        type_label = FX_ALERT_LABEL.get(alert.alert_type.value, alert.alert_type.value)
        if alert.direction == "up":
            advice.append(
                t(
                    "rebalance.fx_alert_up",
                    lang=lang,
                    pair=alert.pair,
                    type_label=type_label,
                    period=alert.period_label,
                    change_pct=alert.change_pct,
                    rate=alert.current_rate,
                    cash_note=cash_note,
                )
            )
        else:
            advice.append(
                t(
                    "rebalance.fx_alert_down",
                    lang=lang,
                    pair=alert.pair,
                    type_label=type_label,
                    period=alert.period_label,
                    change_pct=alert.change_pct,
                    rate=alert.current_rate,
                    cash_note=cash_note,
                )
            )

    return advice


# ===========================================================================
# FX Alerts
# ===========================================================================


def check_fx_alerts(session: Session) -> list[str]:
    """
    檢查匯率曝險警報：偵測三層級匯率變動，產出 Telegram 通知文字。
    """
    exposure = calculate_currency_exposure(session)
    alerts: list[str] = []

    home_cur = exposure["home_currency"]

    # 匯率變動警報（三層級偵測）
    for alert_data in exposure.get("fx_rate_alerts", []):
        pair = alert_data["pair"]
        base_cur = pair.split("/")[0]
        type_label = FX_ALERT_LABEL.get(
            alert_data["alert_type"], alert_data["alert_type"]
        )
        if alert_data["direction"] == "up":
            alerts.append(
                f"📈 {pair} {type_label}：{alert_data['period_label']}升值 "
                f"{alert_data['change_pct']:+.2f}%"
                f"（現價 {alert_data['current_rate']:.4f}）。"
                f"您的 {base_cur} 購買力上升。"
            )
        else:
            alerts.append(
                f"📉 {pair} {type_label}：{alert_data['period_label']}貶值 "
                f"{alert_data['change_pct']:+.2f}%"
                f"（現價 {alert_data['current_rate']:.4f}）。"
                f"您的 {base_cur} 資產以 {home_cur} 計價正在縮水。"
            )

    return alerts


def send_fx_alerts(session: Session) -> list[str]:
    """
    執行匯率曝險檢查，若有警報則發送 Telegram 通知。
    回傳已發送的警報列表。
    """
    alerts = check_fx_alerts(session)

    if alerts:
        if is_notification_enabled(session, "fx_alerts"):
            full_msg = "💱 匯率曝險監控\n\n" + "\n\n".join(alerts)
            try:
                send_telegram_message_dual(full_msg, session)
                logger.info("已發送匯率曝險警報（%d 筆）", len(alerts))
            except Exception as e:
                logger.warning("匯率曝險 Telegram 警報發送失敗：%s", e)
        else:
            logger.info("匯率曝險通知已被使用者停用，跳過發送。")

    return alerts


# ===========================================================================
# Smart Withdrawal — 聰明提款機
# ===========================================================================


def calculate_withdrawal(
    session: Session,
    target_amount: float,
    display_currency: str = "USD",
    notify: bool = True,
) -> dict:
    """
    聰明提款：根據 Liquidity Waterfall 演算法產生賣出建議。
    1. 讀取投資組合目標配置與持倉
    2. 取得匯率與即時價格
    3. 計算再平衡偏移
    4. 委託 domain.withdrawal 純函式產生賣出計劃
    5. （可選）發送 Telegram 通知
    """
    from application.formatters import format_withdrawal_telegram
    from domain.withdrawal import HoldingData, plan_withdrawal

    logger.info("聰明提款計算：目標 %.2f %s", target_amount, display_currency)

    # 1) 取得目標配置
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()

    if not profile:
        lang = get_user_language(session)
        raise StockNotFoundError(t("withdrawal.no_profile", lang=lang))

    target_config: dict[str, float] = _json.loads(profile.config)

    # 2) 取得所有持倉
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()

    if not holdings:
        lang = get_user_language(session)
        return {
            "recommendations": [],
            "total_sell_value": 0.0,
            "target_amount": target_amount,
            "shortfall": target_amount,
            "post_sell_drifts": {},
            "message": t("withdrawal.no_holdings", lang=lang),
        }

    # 3) 取得匯率
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(display_currency, holding_currencies)

    # 4) 計算各持倉市值，建立 HoldingData 列表
    category_values: dict[str, float] = {}
    holdings_data: list[HoldingData] = []

    for h in holdings:
        fx = fx_rates.get(h.currency, 1.0)
        price: float | None = None

        if h.is_cash:
            market_value = h.quantity * fx
            price = 1.0
        else:
            signals = get_technical_signals(h.ticker)
            price = signals.get("price") if signals else None
            if price is not None and isinstance(price, (int, float)):
                market_value = h.quantity * price * fx
            elif h.cost_basis is not None:
                market_value = h.quantity * h.cost_basis * fx
            else:
                market_value = 0.0

        cat = h.category.value if hasattr(h.category, "value") else str(h.category)
        category_values[cat] = category_values.get(cat, 0.0) + market_value

        holdings_data.append(
            HoldingData(
                ticker=h.ticker,
                category=cat,
                quantity=h.quantity,
                cost_basis=h.cost_basis,
                current_price=price,
                market_value=market_value,
                currency=h.currency,
                is_cash=h.is_cash,
                fx_rate=fx,
            )
        )

    total_value = sum(category_values.values())

    # 5) 計算再平衡偏移
    rebalance_result = _pure_rebalance(category_values, target_config)
    category_drifts = {
        cat: info["drift_pct"]
        for cat, info in rebalance_result.get("categories", {}).items()
    }

    # 6) 執行 Liquidity Waterfall 演算法
    plan = plan_withdrawal(
        target_amount=target_amount,
        holdings_data=holdings_data,
        category_drifts=category_drifts,
        total_portfolio_value=total_value,
        target_config=target_config,
    )

    # 7) 建立回傳結果
    recs = [
        {
            "ticker": r.ticker,
            "category": r.category,
            "quantity_to_sell": r.quantity_to_sell,
            "sell_value": r.sell_value,
            "reason": r.reason,
            "unrealized_pl": r.unrealized_pl,
            "priority": r.priority,
        }
        for r in plan.recommendations
    ]

    lang = get_user_language(session)
    if plan.shortfall > 0:
        message = t(
            "withdrawal.shortfall",
            lang=lang,
            amount=f"{plan.shortfall:,.2f}",
            currency=display_currency,
        )
    elif not plan.recommendations:
        message = t("withdrawal.no_sellable", lang=lang)
    else:
        message = t("withdrawal.plan_generated", lang=lang, count=len(recs))

    result = {
        "recommendations": recs,
        "total_sell_value": plan.total_sell_value,
        "target_amount": plan.target_amount,
        "shortfall": plan.shortfall,
        "post_sell_drifts": plan.post_sell_drifts,
        "message": message,
    }

    # 8) 發送 Telegram 通知
    if notify and plan.recommendations:
        if is_notification_enabled(session, "withdrawal"):
            try:
                withdrawal_lang = get_user_language(session)
                tg_msg = format_withdrawal_telegram(
                    plan, display_currency, lang=withdrawal_lang
                )
                send_telegram_message_dual(tg_msg, session)
                logger.info("聰明提款建議已發送至 Telegram。")
            except Exception as e:
                logger.warning("聰明提款 Telegram 通知發送失敗：%s", e)
        else:
            logger.info("聰明提款通知已被使用者停用，跳過發送。")

    return result
