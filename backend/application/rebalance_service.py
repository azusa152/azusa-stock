"""
Application — Rebalance Service：再平衡分析、匯率曝險、X-Ray、FX 警報。
"""

import json as _json
from datetime import datetime, timezone

from sqlmodel import Session, select

from application.stock_service import StockNotFoundError
from domain.constants import (
    DEFAULT_USER_ID,
    FX_HIGH_CONCENTRATION_PCT,
    FX_MEDIUM_CONCENTRATION_PCT,
    FX_SIGNIFICANT_CHANGE_PCT,
    XRAY_SINGLE_STOCK_WARN_PCT,
    XRAY_SKIP_CATEGORIES,
)
from domain.entities import Holding, UserInvestmentProfile
from domain.rebalance import calculate_rebalance as _pure_rebalance
from infrastructure.market_data import (
    get_etf_top_holdings,
    get_exchange_rates,
    get_forex_history,
    get_technical_signals,
    prewarm_etf_holdings_batch,
    prewarm_signals_batch,
)
from infrastructure.notification import is_notification_enabled, send_telegram_message_dual
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
    共用邏輯：計算所有持倉的市值（已換算目標幣別）。
    回傳 (currency_values, cash_currency_values, ticker_agg)。

    - currency_values: {幣別: 總市值} — 全部持倉
    - cash_currency_values: {幣別: 現金市值} — 僅現金部位
    - ticker_agg: {ticker: {category, currency, qty, mv, cost_sum, cost_qty, price, fx}}
    """
    currency_values: dict[str, float] = {}
    cash_currency_values: dict[str, float] = {}
    ticker_agg: dict[str, dict] = {}

    for h in holdings:
        cat = h.category.value if hasattr(h.category, "value") else str(h.category)
        fx = fx_rates.get(h.currency, 1.0)
        price: float | None = None

        if h.is_cash:
            market_value = h.quantity * fx
            price = 1.0
            cash_currency_values[h.currency] = (
                cash_currency_values.get(h.currency, 0.0) + market_value
            )
        else:
            signals = get_technical_signals(h.ticker)
            price = signals.get("price") if signals else None
            if price is not None and isinstance(price, (int, float)):
                market_value = h.quantity * price * fx
            elif h.cost_basis is not None:
                market_value = h.quantity * h.cost_basis * fx
            else:
                market_value = 0.0

        currency_values[h.currency] = currency_values.get(h.currency, 0.0) + market_value

        key = h.ticker
        if key not in ticker_agg:
            ticker_agg[key] = {
                "category": cat,
                "currency": h.currency,
                "qty": 0.0,
                "mv": 0.0,
                "cost_sum": 0.0,
                "cost_qty": 0.0,
                "price": price,
                "fx": fx,
            }
        ticker_agg[key]["qty"] += h.quantity
        ticker_agg[key]["mv"] += market_value
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
    # 1) 取得目標配置
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()

    if not profile:
        raise StockNotFoundError("尚未設定投資組合目標配置，請先選擇投資人格。")

    target_config: dict[str, float] = _json.loads(profile.config)

    # 2) 取得所有持倉
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()

    if not holdings:
        raise StockNotFoundError("尚未輸入任何持倉，請先新增資產。")

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
        holdings, fx_rates,
    )

    # 4.5) 取得每個分類的市值合計
    category_values: dict[str, float] = {}
    for _key, agg in ticker_agg.items():
        cat = agg["category"]
        category_values[cat] = category_values.get(cat, 0.0) + agg["mv"]

    # 5) 委託 domain 純函式計算
    result = _pure_rebalance(category_values, target_config)

    # 6) 建立個股明細（含佔比）
    total_value = result["total_value"]
    holdings_detail = []
    for ticker, agg in ticker_agg.items():
        avg_cost = (
            round(agg["cost_sum"] / agg["cost_qty"], 2)
            if agg["cost_qty"] > 0
            else None
        )
        weight_pct = (
            round((agg["mv"] / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        cur_price = agg["price"]
        holdings_detail.append(
            {
                "ticker": ticker,
                "category": agg["category"],
                "currency": agg["currency"],
                "quantity": round(agg["qty"], 4),
                "market_value": round(agg["mv"], 2),
                "weight_pct": weight_pct,
                "avg_cost": avg_cost,
                "current_price": (
                    round(cur_price, 2)
                    if cur_price is not None and isinstance(cur_price, (int, float))
                    else None
                ),
                "fx": round(agg["fx"], 6),
            }
        )

    # Sort by weight descending (largest positions first)
    holdings_detail.sort(key=lambda x: x["weight_pct"], reverse=True)
    result["holdings_detail"] = holdings_detail
    result["display_currency"] = display_currency

    # 7) X-Ray: 穿透式持倉分析（解析 ETF 成分股，計算真實曝險）
    # 先並行預熱所有可能的 ETF 成分股快取
    xray_tickers = [
        t for t, agg in ticker_agg.items()
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
        direct_pct = round((data["direct"] / total_value) * 100, 2) if total_value > 0 else 0.0
        indirect_pct = round((data["indirect"] / total_value) * 100, 2) if total_value > 0 else 0.0
        total_pct = round((total_val / total_value) * 100, 2) if total_value > 0 else 0.0
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
    warnings: list[str] = []
    for entry in xray_entries:
        total_pct = entry.get("total_weight_pct", 0.0)
        indirect_val = entry.get("indirect_value", 0.0)
        if total_pct > XRAY_SINGLE_STOCK_WARN_PCT and indirect_val > 0:
            symbol = entry["symbol"]
            direct_pct = entry.get("direct_weight_pct", 0.0)
            sources = ", ".join(entry.get("indirect_sources", []))
            msg = (
                f"⚠️ X-Ray 警告：{symbol} 直接持倉佔 {direct_pct:.1f}%，"
                f"加上 ETF 間接曝險（{sources}），"
                f"真實曝險已達 {total_pct:.1f}%，"
                f"超過單一標的風險建議值 {XRAY_SINGLE_STOCK_WARN_PCT:.0f}%。"
            )
            warnings.append(msg)

    if warnings:
        if is_notification_enabled(session, "xray_alerts"):
            full_msg = "🔬 穿透式持倉 X-Ray 分析\n\n" + "\n\n".join(warnings)
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


def calculate_currency_exposure(session: Session, home_currency: str | None = None) -> dict:
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
            "advice": ["尚無持倉資料。"],
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    # 3) 取得匯率（all currencies → home_currency）
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(home_currency, holding_currencies)
    logger.info("匯率曝險分析 → %s：%s", home_currency, {k: round(v, 4) for k, v in fx_rates.items()})

    # 3.5) 並行預熱所有非現金持倉的技術訊號
    non_cash_tickers = list({h.ticker for h in holdings if not h.is_cash})
    if non_cash_tickers:
        prewarm_signals_batch(non_cash_tickers)

    # 4) 使用共用邏輯計算市值（以本幣計價），同時追蹤現金部位
    currency_values, cash_currency_values, _ticker_agg = _compute_holding_market_values(
        holdings, fx_rates,
    )

    total_value_home = sum(currency_values.values())
    total_cash_home = sum(cash_currency_values.values())

    # 5) 建立幣別分佈（全資產）
    breakdown = []
    for cur, val in sorted(currency_values.items(), key=lambda x: x[1], reverse=True):
        pct = round((val / total_value_home) * 100, 2) if total_value_home > 0 else 0.0
        breakdown.append({
            "currency": cur,
            "value": round(val, 2),
            "percentage": pct,
            "is_home": cur == home_currency,
        })

    non_home_pct = round(
        sum(b["percentage"] for b in breakdown if not b["is_home"]),
        2,
    )

    # 5b) 建立現金幣別分佈
    cash_breakdown = []
    for cur, val in sorted(cash_currency_values.items(), key=lambda x: x[1], reverse=True):
        pct = round((val / total_cash_home) * 100, 2) if total_cash_home > 0 else 0.0
        cash_breakdown.append({
            "currency": cur,
            "value": round(val, 2),
            "percentage": pct,
            "is_home": cur == home_currency,
        })

    cash_non_home_pct = round(
        sum(b["percentage"] for b in cash_breakdown if not b["is_home"]),
        2,
    )

    # 6) 偵測近期匯率變動（非本幣 → 本幣）
    fx_movements = []
    non_home_currencies = [cur for cur in currency_values if cur != home_currency]
    for cur in non_home_currencies:
        history = get_forex_history(cur, home_currency)
        if len(history) >= 2:
            first_close = history[0]["close"]
            last_close = history[-1]["close"]
            if first_close > 0:
                change_pct = round(((last_close - first_close) / first_close) * 100, 2)
                direction = "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
                fx_movements.append({
                    "pair": f"{cur}/{home_currency}",
                    "current_rate": last_close,
                    "change_pct": change_pct,
                    "direction": direction,
                })

    # 7) 風險等級
    if non_home_pct >= FX_HIGH_CONCENTRATION_PCT:
        risk_level = "high"
    elif non_home_pct >= FX_MEDIUM_CONCENTRATION_PCT:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 8) 建議（包含現金部位資訊）
    advice = _generate_fx_advice(
        home_currency,
        breakdown,
        non_home_pct,
        risk_level,
        fx_movements,
        cash_breakdown=cash_breakdown,
        cash_non_home_pct=cash_non_home_pct,
        total_cash_home=total_cash_home,
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
    cash_breakdown: list[dict] | None = None,
    cash_non_home_pct: float = 0.0,
    total_cash_home: float = 0.0,
) -> list[str]:
    """根據匯率曝險分析結果產出建議文字。"""
    advice: list[str] = []

    # 集中度建議
    if risk_level == "high":
        top_foreign = [b for b in breakdown if not b["is_home"]]
        if top_foreign:
            top_cur = top_foreign[0]["currency"]
            top_pct = top_foreign[0]["percentage"]
            advice.append(
                f"⚠️ 非本幣（{home_currency}）資產佔比達 {non_home_pct:.1f}%，"
                f"其中 {top_cur} 佔 {top_pct:.1f}%，匯率風險較高。"
                f"建議評估是否需要調整幣別配置以降低單一貨幣曝險。"
            )
    elif risk_level == "medium":
        advice.append(
            f"📊 非本幣資產佔比 {non_home_pct:.1f}%，處於中等水準。"
            f"持續關注主要外幣匯率走勢。"
        )
    else:
        advice.append(
            f"✅ 非本幣資產佔比 {non_home_pct:.1f}%，匯率風險較低。"
        )

    # 現金部位專屬建議
    if cash_breakdown:
        foreign_cash = [b for b in cash_breakdown if not b["is_home"]]
        if foreign_cash and cash_non_home_pct > 0:
            top_cash_cur = foreign_cash[0]["currency"]
            top_cash_val = foreign_cash[0]["value"]
            advice.append(
                f"💵 您的現金部位中，{cash_non_home_pct:.1f}% 為非本幣。"
                f"最大外幣現金為 {top_cash_cur}（約 {top_cash_val:,.0f} {home_currency}），"
                f"受匯率波動直接影響。"
            )

    # 匯率變動建議（含現金金額）
    cash_by_cur = {b["currency"]: b["value"] for b in (cash_breakdown or [])}
    for mv in fx_movements:
        abs_change = abs(mv["change_pct"])
        if abs_change >= FX_SIGNIFICANT_CHANGE_PCT:
            pair = mv["pair"]
            base_cur = pair.split("/")[0]
            cash_amt = cash_by_cur.get(base_cur, 0.0)
            cash_note = (
                f"（其中 {base_cur} 現金約 {cash_amt:,.0f} {home_currency} 直接受影響）"
                if cash_amt > 0
                else ""
            )
            if mv["direction"] == "up":
                advice.append(
                    f"📈 {pair} 近期升值 {mv['change_pct']:+.2f}%，"
                    f"您持有的 {base_cur} 資產以 {home_currency} 計價正在增值。"
                    f"{cash_note}"
                )
            else:
                advice.append(
                    f"📉 {pair} 近期貶值 {mv['change_pct']:+.2f}%，"
                    f"您持有的 {base_cur} 資產以 {home_currency} 計價正在縮水，"
                    f"建議留意是否需要避險。{cash_note}"
                )

    return advice


# ===========================================================================
# FX Alerts
# ===========================================================================


def check_fx_alerts(session: Session) -> list[str]:
    """
    檢查匯率曝險警報：偵測顯著匯率變動，產出 Telegram 通知文字。
    回傳警報訊息列表（強調現金部位影響）。
    """
    exposure = calculate_currency_exposure(session)
    alerts: list[str] = []

    home_cur = exposure["home_currency"]
    cash_by_cur = {
        b["currency"]: b["value"]
        for b in exposure.get("cash_breakdown", [])
    }

    # 匯率變動警報（含現金金額）
    for mv in exposure.get("fx_movements", []):
        abs_change = abs(mv["change_pct"])
        if abs_change >= FX_SIGNIFICANT_CHANGE_PCT:
            pair = mv["pair"]
            base_cur = pair.split("/")[0]
            cash_amt = cash_by_cur.get(base_cur, 0.0)
            cash_note = (
                f"\n💵 其中 {base_cur} 現金約 {cash_amt:,.0f} {home_cur} 直接受影響。"
                if cash_amt > 0
                else ""
            )
            if mv["direction"] == "up":
                alerts.append(
                    f"📈 {pair} 升值 {mv['change_pct']:+.2f}%（現價 {mv['current_rate']:.4f}）。"
                    f"您的 {base_cur} 購買力上升。{cash_note}"
                )
            else:
                alerts.append(
                    f"📉 {pair} 貶值 {mv['change_pct']:+.2f}%（現價 {mv['current_rate']:.4f}）。"
                    f"您的 {base_cur} 資產以 {home_cur} 計價正在縮水。{cash_note}"
                )

    # 高集中度警報（整體 + 現金）
    non_home_pct = exposure.get("non_home_pct", 0.0)
    cash_non_home_pct = exposure.get("cash_non_home_pct", 0.0)
    if non_home_pct >= FX_HIGH_CONCENTRATION_PCT:
        alerts.append(
            f"⚠️ 非本幣資產佔比高達 {non_home_pct:.1f}%，匯率風險顯著。"
            f"建議評估是否需要降低外幣曝險。"
        )
    if cash_non_home_pct >= FX_HIGH_CONCENTRATION_PCT:
        total_cash = exposure.get("total_cash_home", 0.0)
        alerts.append(
            f"💵 現金部位中非本幣佔 {cash_non_home_pct:.1f}%"
            f"（現金總額約 {total_cash:,.0f} {home_cur}），"
            f"匯率風險直接影響您的流動性資產。"
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
