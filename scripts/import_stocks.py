"""
Folio — 股票觀察名單匯入腳本（Upsert 模式）
從 JSON 檔案讀取股票清單，批次匯入至正在運行的 FastAPI 後端。
- 新股票：透過 POST /ticker 新增
- 已存在：透過 POST /ticker/{ticker}/thesis 更新觀點與標籤

使用方式：
    python3 scripts/import_stocks.py                              # 使用預設資料檔
    python3 scripts/import_stocks.py scripts/data/my_list.json    # 指定其他資料檔
    python3 scripts/import_stocks.py --api-key YOUR_KEY           # 手動指定 API Key

API Key 優先順序：--api-key > .env FOLIO_API_KEY > 無認證（dev mode）
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/ticker"
DEFAULT_DATA_FILE = Path(__file__).parent / "data" / "folio_watchlist.json"

REQUIRED_FIELDS = {"ticker", "category", "thesis"}
VALID_CATEGORIES = {"Trend_Setter", "Moat", "Growth", "Bond", "Cash"}

HEADERS: dict[str, str] = {}


def load_stock_list(file_path: Path) -> list[dict]:
    """從 JSON 檔案讀取並驗證股票清單。"""
    if not file_path.exists():
        print(f"  ❌ 找不到資料檔案：{file_path}")
        sys.exit(1)

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 格式錯誤：{e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("  ❌ JSON 檔案最外層必須是陣列 (list)。")
        sys.exit(1)

    # 驗證每筆資料
    for i, item in enumerate(data):
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            print(f"  ❌ 第 {i + 1} 筆資料缺少欄位：{missing}")
            sys.exit(1)
        if item["category"] not in VALID_CATEGORIES:
            print(
                f"  ❌ 第 {i + 1} 筆資料 category 無效：'{item['category']}'，"
                f"必須是 {VALID_CATEGORIES} 之一。"
            )
            sys.exit(1)
        # tags 為選填，預設為空列表
        if "tags" not in item:
            item["tags"] = []

    return data


def upsert_stock(item: dict) -> str:
    """
    嘗試新增股票；若已存在則更新觀點與標籤。
    回傳狀態：'inserted' / 'updated' / 'failed'
    """
    ticker = item["ticker"]
    tags = item.get("tags", [])

    # 嘗試新增
    create_payload = {
        "ticker": ticker,
        "category": item["category"],
        "thesis": item["thesis"],
        "tags": tags,
    }
    resp = requests.post(API_URL, json=create_payload, headers=HEADERS, timeout=10)

    if resp.status_code == 200:
        return "inserted"

    if resp.status_code == 409:
        # 股票已存在，更新觀點與標籤
        update_payload = {
            "content": item["thesis"],
            "tags": tags,
        }
        update_resp = requests.post(
            f"{API_URL}/{ticker}/thesis",
            json=update_payload,
            headers=HEADERS,
            timeout=10,
        )
        if update_resp.status_code == 200:
            return "updated"
        else:
            detail = update_resp.json().get("detail", update_resp.text)
            print(f"  ❌ {ticker} — 更新失敗（HTTP {update_resp.status_code}）：{detail}")
            return "failed"

    # 其他錯誤
    detail = resp.json().get("detail", resp.text)
    print(f"  ❌ {ticker} — 失敗（HTTP {resp.status_code}）：{detail}")
    return "failed"


def _mask_key(key: str) -> str:
    """Show only the last 4 characters of an API key."""
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]


def main() -> None:
    global HEADERS  # noqa: PLW0603

    load_dotenv()

    api_key = os.getenv("FOLIO_API_KEY", "")

    # Accept --api-key CLI override
    for i, arg in enumerate(sys.argv):
        if arg == "--api-key" and i + 1 < len(sys.argv):
            api_key = sys.argv[i + 1]
            break

    if api_key:
        HEADERS = {"X-API-Key": api_key}

    # 決定資料檔案路徑：first positional arg that isn't a flag
    data_file = DEFAULT_DATA_FILE
    positional_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if positional_args:
        data_file = Path(positional_args[0])

    stock_list = load_stock_list(data_file)

    auth_display = _mask_key(api_key) if api_key else "(dev mode — no key)"
    print("=" * 60)
    print("  Folio — 股票觀察名單匯入（Upsert 模式）")
    print(f"  資料來源：{data_file}")
    print(f"  目標 API：{BASE_URL}")
    print(f"  API Key ：{auth_display}")
    print(f"  共 {len(stock_list)} 檔股票")
    print("=" * 60)
    print()

    inserted = 0
    updated = 0
    failed = 0

    for item in stock_list:
        ticker = item["ticker"]
        tags_display = f" [{', '.join(item.get('tags', []))}]" if item.get("tags") else ""
        try:
            result = upsert_stock(item)

            if result == "inserted":
                print(f"  ✅ {ticker} — 新增成功{tags_display}")
                inserted += 1
            elif result == "updated":
                print(f"  🔄 {ticker} — 已更新觀點與標籤{tags_display}")
                updated += 1
            else:
                failed += 1

        except requests.ConnectionError:
            print(f"  ❌ {ticker} — 無法連線至 {BASE_URL}，請確認後端是否啟動。")
            failed += 1
            break
        except requests.RequestException as e:
            print(f"  ❌ {ticker} — 請求錯誤：{e}")
            failed += 1

    print()
    print("-" * 60)
    print(f"  匯入完成！新增：{inserted} / 更新：{updated} / 失敗：{failed}")
    print("-" * 60)


if __name__ == "__main__":
    main()
