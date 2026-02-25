#!/usr/bin/env python3
"""
Add new i18n keys to all 4 backend locale files.
Run from project root: python backend/scripts/add_locale_keys.py
"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "i18n" / "locales"

new_keys = {
    "api": {
        "holding_not_found": {
            "zh-TW": "持倉不存在。",
            "en": "Holding not found.",
            "ja": "保有が見つかりません。",
            "zh-CN": "持仓不存在。",
        },
        "holding_deleted": {
            "zh-TW": "持倉 {ticker} 已刪除。",
            "en": "Holding {ticker} deleted.",
            "ja": "保有 {ticker} を削除しました。",
            "zh-CN": "持仓 {ticker} 已删除。",
        },
        "import_item_failed": {
            "zh-TW": "第 {index} 筆匯入失敗",
            "en": "Import item {index} failed",
            "ja": "{index} 番目のインポートに失敗",
            "zh-CN": "第 {index} 笔导入失败",
        },
        "import_done": {
            "zh-TW": "匯入完成：{count} 筆成功。",
            "en": "Import complete: {count} successful.",
            "ja": "インポート完了：{count} 件成功。",
            "zh-CN": "导入完成：{count} 笔成功。",
        },
        "xray_done": {
            "zh-TW": "X-Ray 分析完成，{count} 筆警告已發送。",
            "en": "X-Ray analysis complete, {count} warnings sent.",
            "ja": "X-Ray分析完了、{count} 件の警告を送信。",
            "zh-CN": "X-Ray 分析完成，{count} 笔警告已发送。",
        },
        "fx_alert_done": {
            "zh-TW": "匯率曝險檢查完成，{count} 筆警報已發送。",
            "en": "FX exposure check complete, {count} alerts sent.",
            "ja": "為替エクスポージャーチェック完了、{count} 件のアラートを送信。",
            "zh-CN": "汇率曝险检查完成，{count} 笔警报已发送。",
        },
        "scenario_range_error": {
            "zh-TW": "scenario_drop_pct 必須在 -50 到 0 之間",
            "en": "scenario_drop_pct must be between -50 and 0",
            "ja": "scenario_drop_pctは-50から0の間である必要があります",
            "zh-CN": "scenario_drop_pct 必须在 -50 到 0 之间",
        },
        "profile_not_found": {
            "zh-TW": "配置不存在。",
            "en": "Profile not found.",
            "ja": "プロファイルが見つかりません。",
            "zh-CN": "配置不存在。",
        },
        "profile_deactivated": {
            "zh-TW": "配置 '{name}' 已停用。",
            "en": "Profile '{name}' deactivated.",
            "ja": "プロファイル '{name}' を無効化しました。",
            "zh-CN": "配置 '{name}' 已停用。",
        },
        "scan_in_progress": {
            "zh-TW": "掃描正在執行中，請稍後再試。",
            "en": "Scan in progress. Please try again later.",
            "ja": "スキャン実行中です。しばらくお待ちください。",
            "zh-CN": "扫描正在执行中，请稍后再试。",
        },
        "scan_started": {
            "zh-TW": "掃描已啟動，結果將透過 Telegram 通知。",
            "en": "Scan started. Results will be sent via Telegram.",
            "ja": "スキャンを開始しました。結果はTelegramで通知されます。",
            "zh-CN": "扫描已启动，结果将通过 Telegram 通知。",
        },
        "digest_in_progress": {
            "zh-TW": "每週摘要正在生成中，請稍後再試。",
            "en": "Weekly digest is being generated. Please try again later.",
            "ja": "週次ダイジェスト生成中です。しばらくお待ちください。",
            "zh-CN": "每周摘要正在生成中，请稍后再试。",
        },
        "telegram_not_configured": {
            "zh-TW": "尚未設定 Telegram Chat ID，請先儲存設定。",
            "en": "Telegram Chat ID not configured. Please save settings first.",
            "ja": "Telegram Chat IDが未設定です。先に設定を保存してください。",
            "zh-CN": "尚未设定 Telegram Chat ID，请先保存设定。",
        },
        "telegram_test_msg": {
            "zh-TW": "✅ <b>Folio 測試訊息</b>\n\n恭喜！你的 Telegram 通知設定正確運作。",
            "en": "✅ <b>Folio Test Message</b>\n\nCongratulations! Your Telegram notification settings are working correctly.",
            "ja": "✅ <b>Folio テストメッセージ</b>\n\nおめでとうございます！Telegram通知設定は正常に動作しています。",
            "zh-CN": "✅ <b>Folio 测试消息</b>\n\n恭喜！你的 Telegram 通知设定正确运作。",
        },
        "telegram_test_sent": {
            "zh-TW": "✅ 測試訊息已發送，請檢查 Telegram。",
            "en": "✅ Test message sent. Please check Telegram.",
            "ja": "✅ テストメッセージを送信しました。Telegramを確認してください。",
            "zh-CN": "✅ 测试消息已发送，请检查 Telegram。",
        },
        "tag_validation_error": {
            "zh-TW": "每個標籤必須非空且不超過 50 字元",
            "en": "Each tag must be non-empty and no longer than 50 characters",
            "ja": "各タグは空でなく、50文字以内である必要があります",
            "zh-CN": "每个标签必须非空且不超过 50 字符",
        },
    },
    "constants": {
        "removal_reason_unknown": {
            "zh-TW": "未知",
            "en": "Unknown",
            "ja": "不明",
            "zh-CN": "未知",
        },
        "default_webhook_thesis": {
            "zh-TW": "由 AI agent 新增。",
            "en": "Added by AI agent.",
            "ja": "AIエージェントにより追加。",
            "zh-CN": "由 AI agent 新增。",
        },
        "generic_error": {
            "zh-TW": "操作失敗，請稍後再試。",
            "en": "Operation failed. Please try again later.",
            "ja": "操作に失敗しました。しばらくしてから再試行してください。",
            "zh-CN": "操作失败，请稍后再试。",
        },
        "generic_validation_error": {
            "zh-TW": "輸入資料格式不正確。",
            "en": "Invalid input format.",
            "ja": "入力データの形式が正しくありません。",
            "zh-CN": "输入数据格式不正确。",
        },
        "generic_telegram_error": {
            "zh-TW": "Telegram 通知設定失敗。",
            "en": "Telegram notification setup failed.",
            "ja": "Telegram通知の設定に失敗しました。",
            "zh-CN": "Telegram 通知设定失败。",
        },
        "generic_preferences_error": {
            "zh-TW": "偏好設定更新失敗。",
            "en": "Preference update failed.",
            "ja": "設定の更新に失敗しました。",
            "zh-CN": "偏好设定更新失败。",
        },
        "generic_webhook_error": {
            "zh-TW": "處理請求時發生錯誤。",
            "en": "An error occurred while processing the request.",
            "ja": "リクエスト処理中にエラーが発生しました。",
            "zh-CN": "处理请求时发生错误。",
        },
        "notification_scan_alerts": {
            "zh-TW": "掃描訊號通知（THESIS_BROKEN / OVERHEATED / CONTRARIAN_BUY）",
            "en": "Scan signal alerts (THESIS_BROKEN / OVERHEATED / CONTRARIAN_BUY)",
            "ja": "スキャンシグナル通知（THESIS_BROKEN / OVERHEATED / CONTRARIAN_BUY）",
            "zh-CN": "扫描信号通知（THESIS_BROKEN / OVERHEATED / CONTRARIAN_BUY）",
        },
        "notification_price_alerts": {
            "zh-TW": "自訂價格警報觸發通知",
            "en": "Custom price alert triggers",
            "ja": "カスタム価格アラートトリガー",
            "zh-CN": "自定义价格警报触发通知",
        },
        "notification_weekly_digest": {
            "zh-TW": "每週投資摘要",
            "en": "Weekly investment digest",
            "ja": "週次投資ダイジェスト",
            "zh-CN": "每周投资摘要",
        },
        "notification_xray_alerts": {
            "zh-TW": "X-Ray 集中度警告",
            "en": "X-Ray concentration warnings",
            "ja": "X-Ray集中度警告",
            "zh-CN": "X-Ray 集中度警告",
        },
        "notification_fx_alerts": {
            "zh-TW": "匯率曝險警報",
            "en": "FX exposure alerts",
            "ja": "為替エクスポージャーアラート",
            "zh-CN": "汇率曝险警报",
        },
        "notification_fx_watch_alerts": {
            "zh-TW": "外匯換匯時機警報",
            "en": "FX exchange timing alerts",
            "ja": "外為換金タイミングアラート",
            "zh-CN": "外汇换汇时机警报",
        },
        "stress_pain_low": {
            "zh-TW": "微風輕拂 (Just a Scratch)",
            "en": "Just a Scratch",
            "ja": "そよ風 (Just a Scratch)",
            "zh-CN": "微风轻拂 (Just a Scratch)",
        },
        "stress_pain_moderate": {
            "zh-TW": "有感修正 (Correction)",
            "en": "Noticeable Correction",
            "ja": "実感できる調整 (Correction)",
            "zh-CN": "有感修正 (Correction)",
        },
        "stress_pain_high": {
            "zh-TW": "傷筋動骨 (Bear Market)",
            "en": "Significant Damage (Bear Market)",
            "ja": "かなりのダメージ (Bear Market)",
            "zh-CN": "伤筋动骨 (Bear Market)",
        },
        "stress_pain_panic": {
            "zh-TW": "睡不著覺 (Panic Zone)",
            "en": "Sleepless Nights (Panic Zone)",
            "ja": "眠れない夜 (Panic Zone)",
            "zh-CN": "睡不着觉 (Panic Zone)",
        },
        "stress_disclaimer": {
            "zh-TW": "⚠️ 此為線性 CAPM 簡化模型，實際崩盤中相關性會趨近 1、流動性枯竭可能導致更大跌幅。本模擬僅供參考，不構成投資建議。",
            "en": "⚠️ This is a simplified linear CAPM model. In actual crashes, correlations tend toward 1 and liquidity drought may cause larger declines. This simulation is for reference only and does not constitute investment advice.",
            "ja": "⚠️ これは線形CAPMの簡易モデルです。実際の暴落では相関が1に近づき、流動性枯渇によりさらに大きな下落が発生する可能性があります。本シミュレーションは参考用であり、投資助言ではありません。",
            "zh-CN": "⚠️ 此为线性 CAPM 简化模型，实际崩盘中相关性会趋近 1、流动性枯竭可能导致更大跌幅。本模拟仅供参考，不构成投资建议。",
        },
    },
    "market": {
        "no_trend_stocks": {
            "zh-TW": "無風向球股票可供分析",
            "en": "No trend setter stocks available for analysis",
            "ja": "分析可能なトレンドセッター銘柄がありません",
            "zh-CN": "无风向球股票可供分析",
        },
        "caution_details": {
            "zh-TW": "多數風向球股價轉弱（{below}/{total} 跌破 60MA）",
            "en": "Most trend setters weakening ({below}/{total} below 60MA)",
            "ja": "大半のトレンドセッターが軟調（{below}/{total} が60MA割れ）",
            "zh-CN": "多数风向球股价转弱（{below}/{total} 跌破 60MA）",
        },
        "positive_details": {
            "zh-TW": "風向球整體穩健（{below}/{total} 跌破 60MA）",
            "en": "Trend setters overall healthy ({below}/{total} below 60MA)",
            "ja": "トレンドセッター全体は堅調（{below}/{total} が60MA割れ）",
            "zh-CN": "风向球整体稳健（{below}/{total} 跌破 60MA）",
        },
        "fallback_optimistic": {
            "zh-TW": "無法判斷，預設樂觀",
            "en": "Unable to determine, defaulting to optimistic",
            "ja": "判定不能、デフォルトで楽観的",
            "zh-CN": "无法判断，默认乐观",
        },
        "insufficient_history": {
            "zh-TW": "⚠️ {ticker} 歷史資料不足，無法計算技術指標。",
            "en": "⚠️ {ticker} insufficient history data for technical indicators.",
            "ja": "⚠️ {ticker} テクニカル指標の計算に十分な履歴データがありません。",
            "zh-CN": "⚠️ {ticker} 历史数据不足，无法计算技术指标。",
        },
        "signals_fetch_error": {
            "zh-TW": "⚠️ 無法取得 {ticker} 技術訊號：{error}",
            "en": "⚠️ Failed to fetch {ticker} technical signals: {error}",
            "ja": "⚠️ {ticker} のテクニカルシグナル取得に失敗：{error}",
            "zh-CN": "⚠️ 无法获取 {ticker} 技术信号：{error}",
        },
    },
    "withdrawal": {
        "no_profile": {
            "zh-TW": "尚未設定投資組合目標配置，請先選擇投資人格。",
            "en": "No portfolio target allocation set. Please select an investor profile first.",
            "ja": "ポートフォリオ目標配分が未設定です。先に投資家プロファイルを選択してください。",
            "zh-CN": "尚未设定投资组合目标配置，请先选择投资人格。",
        },
        "no_holdings": {
            "zh-TW": "⚠️ 尚未輸入任何持倉，無法計算提款建議。",
            "en": "⚠️ No holdings found. Cannot calculate withdrawal plan.",
            "ja": "⚠️ 保有がありません。出金プランを計算できません。",
            "zh-CN": "⚠️ 尚未输入任何持仓，无法计算提款建议。",
        },
        "shortfall": {
            "zh-TW": "⚠️ 投資組合市值不足，缺口 {amount} {currency}。以下為最大可提取建議。",
            "en": "⚠️ Portfolio value insufficient, shortfall {amount} {currency}. Below are maximum withdrawal suggestions.",
            "ja": "⚠️ ポートフォリオ時価が不足、不足額 {amount} {currency}。以下は最大出金提案です。",
            "zh-CN": "⚠️ 投资组合市值不足，缺口 {amount} {currency}。以下为最大可提取建议。",
        },
        "no_sellable": {
            "zh-TW": "⚠️ 無可賣出的持倉。",
            "en": "⚠️ No sellable holdings.",
            "ja": "⚠️ 売却可能な保有がありません。",
            "zh-CN": "⚠️ 无可卖出的持仓。",
        },
        "plan_generated": {
            "zh-TW": "✅ 聰明提款建議已產生，共 {count} 筆賣出建議。",
            "en": "✅ Smart withdrawal plan generated, {count} sell recommendations.",
            "ja": "✅ スマート出金プランを生成しました。{count} 件の売却提案。",
            "zh-CN": "✅ 聪明提款建议已生成，共 {count} 笔卖出建议。",
        },
        "no_holdings_stress": {
            "zh-TW": "尚未輸入任何持倉，請先新增資產。",
            "en": "No holdings found. Please add assets first.",
            "ja": "保有がありません。先に資産を追加してください。",
            "zh-CN": "尚未输入任何持仓，请先新增资产。",
        },
    },
    "webhook": {
        "price_alerts_header": {
            "zh-TW": "{ticker} 價格警報：",
            "en": "{ticker} price alerts:",
            "ja": "{ticker} 価格アラート：",
            "zh-CN": "{ticker} 价格警报：",
        },
        "signals_line": {
            "zh-TW": "{ticker} — 現價 ${price}, RSI={rsi}, Bias={bias}%",
            "en": "{ticker} — Price ${price}, RSI={rsi}, Bias={bias}%",
            "ja": "{ticker} — 現在値 ${price}, RSI={rsi}, Bias={bias}%",
            "zh-CN": "{ticker} — 现价 ${price}, RSI={rsi}, Bias={bias}%",
        },
    },
}


def deep_merge(base: dict, additions: dict) -> dict:
    """Recursively merge additions into base. Additions take precedence for leaf values."""
    result = dict(base)
    for key, value in additions.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def main() -> None:
    for locale_file in ["zh-TW.json", "en.json", "ja.json", "zh-CN.json"]:
        lang_code = locale_file.replace(".json", "")
        path = LOCALES_DIR / locale_file

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # Build additions for this locale from new_keys
        additions: dict = {}
        for top_key, nested in new_keys.items():
            if top_key not in additions:
                additions[top_key] = {}
            for sub_key, translations in nested.items():
                if lang_code in translations:
                    if sub_key not in additions[top_key]:
                        additions[top_key][sub_key] = translations[lang_code]
                    else:
                        additions[top_key][sub_key] = translations[lang_code]

        data = deep_merge(data, additions)

        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

        print(f"Updated {locale_file}")  # noqa: T201


if __name__ == "__main__":
    main()
