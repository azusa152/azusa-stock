# Azusa Radar — 投資雷達

系統化追蹤股票、管理觀點演進、並透過三層漏斗自動掃描技術面與基本面異常。

## 功能特色

- **四大分類追蹤** — 風向球 / 護城河 / 成長夢想 / ETF，各類有專屬分頁
- **觀點版控 (Thesis Versioning)** — 每次更新觀點自動遞增版號，完整保留歷史演進
- **動態標籤 (Dynamic Tagging)** — 為股票標記領域標籤（AI、Cloud、SaaS...），標籤隨觀點版控一併快照
- **V2 三層漏斗掃描** — 市場情緒 → 護城河趨勢 → 技術面訊號 → 自動產生決策燈號
- **護城河健檢** — 毛利率 5 季走勢圖 + YoY 診斷（錯殺機會 / Thesis Broken）
- **拖曳排序** — 透過 drag-and-drop 調整股票顯示順位，順位寫入資料庫持久化
- **移除與封存** — 移除股票時記錄原因，封存至「已移除」分頁，含完整移除歷史
- **匯出 / 匯入** — JSON 格式匯出觀察名單，匯入腳本支援 upsert（新增或更新）
- **Telegram 警報** — 掃描異常時自動推播通知
- **內建 SOP 指引** — Dashboard 內附操作說明書

## 核心邏輯

### 分類與掃描規則

| 分類 | 說明 | Layer 1 參與 |
|------|------|:------------:|
| **風向球 (Trend Setter)** | 大盤 ETF、巨頭，觀察資金流向與 Capex | 是 |
| **護城河 (Moat)** | 供應鏈中不可替代的賣鏟子公司 | 否 |
| **成長夢想 (Growth)** | 高波動、具想像空間的成長股 | 否 |
| **ETF** | 指數型基金，被動追蹤市場或主題 | 否 |

### V2 三層漏斗

```mermaid
flowchart TD
    L1["Layer 1: 市場情緒"] -->|"風向球跌破 60MA 比例"| Decision{">50%?"}
    Decision -->|"是"| CAUTION["CAUTION 雨天"]
    Decision -->|"否"| POSITIVE["POSITIVE 晴天"]

    L2["Layer 2: 護城河趨勢"] -->|"毛利率 YoY"| MoatCheck{"衰退 >2pp?"}
    MoatCheck -->|"是"| BROKEN["THESIS_BROKEN"]
    MoatCheck -->|"否"| L3

    L3["Layer 3: 技術面"] -->|"RSI, Bias, Volume Ratio"| TechCheck
    TechCheck -->|"RSI<35 + 市場正面"| BUY["CONTRARIAN_BUY"]
    TechCheck -->|"Bias>20%"| HOT["OVERHEATED"]
    TechCheck -->|"其他"| NORMAL["NORMAL"]
```

## 技術架構

```mermaid
graph LR
  subgraph docker [Docker Compose]
    FE["Streamlit Frontend :8501"]
    BE["FastAPI Backend :8000"]
    DB[("SQLite radar.db")]
  end
  YF["yfinance API"]
  TG["Telegram Bot API"]
  FE -->|"HTTP requests"| BE
  BE -->|"read/write"| DB
  BE -->|"fetch market data"| YF
  BE -->|"send alerts"| TG
```

- **Backend** — FastAPI + SQLModel，負責 API、資料庫、掃描邏輯
- **Frontend** — Streamlit Dashboard，分頁顯示四類股票（+ 已移除封存）與觀點編輯
- **Database** — SQLite，透過 Docker Volume 持久化
- **資料來源** — yfinance（使用 curl_cffi 繞過 bot 防護），含 `cachetools` 記憶體快取
- **通知** — Telegram Bot API
- **拖曳排序** — `streamlit-sortables` 元件

## 快速開始

### 前置需求

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 已安裝並啟動
- Python 3（僅限本機執行匯入腳本時需要）

### 1. 設定環境變數

編輯專案根目錄的 `.env` 檔案，填入 Telegram Bot 憑證：

```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
TELEGRAM_CHAT_ID=your-telegram-chat-id-here
```

> 若不需要 Telegram 通知，保留預設值即可，系統會自動跳過發送。

### 2. 啟動服務

```bash
docker compose up --build
```

- **Backend API** — http://localhost:8000（Swagger 文件：http://localhost:8000/docs）
- **Frontend Dashboard** — http://localhost:8501

### 3. 匯入觀察名單

```bash
# 建立虛擬環境（首次）
python3 -m venv .venv
source .venv/bin/activate
pip install requests

# 匯入預設觀察名單
python scripts/import_stocks.py

# 或指定自訂 JSON 檔案
python scripts/import_stocks.py path/to/custom_list.json
```

> 匯入腳本支援 upsert：若股票已存在，會自動更新觀點與標籤（版控遞增）。

### 4. 重置資料庫

```bash
docker compose down -v
docker compose up --build
```

`-v` 會移除 Docker Volume（含 `radar.db`），重啟後自動建立空白資料庫。

## API 參考

| Method | Path | 說明 |
|--------|------|------|
| `GET` | `/health` | Health check（Docker 健康檢查用） |
| `POST` | `/ticker` | 新增追蹤股票（含初始觀點與標籤） |
| `GET` | `/stocks` | 取得所有追蹤股票（僅 DB 資料） |
| `PUT` | `/stocks/reorder` | 批次更新股票顯示順位 |
| `GET` | `/stocks/export` | 匯出所有股票（JSON 格式，含觀點與標籤） |
| `GET` | `/stocks/removed` | 取得所有已移除股票 |
| `GET` | `/ticker/{ticker}/signals` | 取得單一股票的技術訊號（yfinance，含快取） |
| `GET` | `/ticker/{ticker}/moat` | 護城河健檢（毛利率 5 季走勢 + YoY 診斷） |
| `POST` | `/ticker/{ticker}/thesis` | 新增觀點（自動版控 version +1，含標籤） |
| `GET` | `/ticker/{ticker}/thesis` | 取得觀點版控歷史 |
| `PATCH` | `/ticker/{ticker}/category` | 切換股票分類 |
| `POST` | `/ticker/{ticker}/deactivate` | 移除追蹤（含移除原因） |
| `GET` | `/ticker/{ticker}/removals` | 取得移除歷史 |
| `POST` | `/scan` | V2 三層漏斗掃描 + Telegram 警報 |

### 範例：新增股票（含標籤）

```bash
curl -X POST http://localhost:8000/ticker \
  -H "Content-Type: application/json" \
  -d '{"ticker": "NVDA", "category": "Moat", "thesis": "賣鏟子給巨頭的王。", "tags": ["AI", "Semiconductor"]}'
```

### 範例：更新觀點（含標籤）

```bash
curl -X POST http://localhost:8000/ticker/NVDA/thesis \
  -H "Content-Type: application/json" \
  -d '{"content": "GB200 需求超預期，上調目標價。", "tags": ["AI", "Semiconductor", "Hardware"]}'
```

### 範例：觸發掃描

```bash
curl -X POST http://localhost:8000/scan
```

## 專案結構（Clean Architecture）

後端採用 Clean Architecture 四層架構，依賴方向由外向內，各層職責明確：

```mermaid
graph TB
  subgraph layers [Backend 架構]
    API["api/ — 薄控制器"]
    APP["application/ — 服務編排"]
    DOMAIN["domain/ — 純業務邏輯"]
    INFRA["infrastructure/ — 外部適配器"]
  end
  API --> APP
  APP --> DOMAIN
  APP --> INFRA
  INFRA --> DOMAIN
```

```
azusa-stock/
├── .env                              # Telegram Bot 憑證
├── .gitignore
├── .cursorrules                      # Cursor AI 架構師指引
├── docker-compose.yml                # Backend + Frontend 服務定義
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                       # 進入點：建立 App、註冊路由
│   ├── logging_config.py             # 集中式日誌（跨層共用）
│   │
│   ├── domain/                       # 領域層：純業務邏輯，無框架依賴
│   │   ├── enums.py                  #   分類、狀態列舉 + 常數
│   │   ├── entities.py               #   SQLModel 資料表 (Stock, ThesisLog, RemovalLog)
│   │   └── analysis.py               #   純計算：RSI, Bias, 決策引擎（可獨立測試）
│   │
│   ├── application/                  # 應用層：Use Case 編排
│   │   └── services.py               #   Stock / Thesis / Scan 服務
│   │
│   ├── infrastructure/               # 基礎設施層：外部適配器
│   │   ├── database.py               #   SQLite engine + session 管理
│   │   ├── repositories.py           #   Repository Pattern（集中 DB 查詢）
│   │   ├── market_data.py            #   yfinance 適配器（含快取）
│   │   └── notification.py           #   Telegram Bot 適配器
│   │
│   └── api/                          # API 層：薄控制器
│       ├── schemas.py                #   Pydantic 請求/回應 Schema
│       ├── stock_routes.py           #   股票管理路由
│       ├── thesis_routes.py          #   觀點版控路由
│       └── scan_routes.py            #   三層漏斗掃描路由
│
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                        # Dashboard：四分頁 + 封存 + 觀點編輯器
│
├── scripts/
│   ├── import_stocks.py              # 從 JSON 匯入股票至 API（支援 upsert）
│   └── data/
│       └── azusa_watchlist.json      # 預設觀察名單
│
└── logs/                             # 日誌檔案（bind-mount 自動產生）
    ├── radar.log                     # 當日日誌
    └── radar.log.YYYY-MM-DD         # 歷史日誌（保留 3 天）
```

**各層職責：**

| 層 | 目錄 | 職責 | 依賴 |
|----|------|------|------|
| **Domain** | `domain/` | 純業務規則、計算、列舉。不依賴框架，可獨立單元測試。 | 無 |
| **Application** | `application/` | Use Case 編排：協調 Repository 與 Adapter 完成業務流程。 | Domain, Infrastructure |
| **Infrastructure** | `infrastructure/` | 外部適配器：DB、yfinance、Telegram。可替換不影響業務。 | Domain |
| **API** | `api/` | 薄控制器：解析 HTTP 請求 → 呼叫 Service → 回傳回應。 | Application |

## 日誌管理

日誌檔案透過 bind-mount 映射至專案根目錄的 `logs/` 資料夾，可直接在本機存取。

```bash
# 即時追蹤日誌
tail -f logs/radar.log

# 或直接在 Cursor / VS Code 中開啟 logs/radar.log
```

**輪替規則：**
- 每日 UTC 午夜自動輪替
- 保留最近 3 天的歷史日誌，超過自動刪除
- 格式：`2026-02-09 14:30:00 | INFO     | main | 股票 TSLA 已成功新增至追蹤清單。`

**環境變數調整：**
- `LOG_LEVEL` — 日誌等級，預設 `INFO`（可設為 `DEBUG` 取得更詳細資訊）
- `LOG_DIR` — 日誌目錄，預設 `/app/data/logs`

## 資料檔案格式

匯入用的 JSON 檔案格式（`azusa_watchlist.json`）：

```json
[
  {
    "ticker": "NVDA",
    "category": "Moat",
    "thesis": "你對這檔股票的觀點。",
    "tags": ["AI", "Semiconductor"]
  }
]
```

- `ticker` — 股票代號（美股）
- `category` — 分類，必須是 `Trend_Setter`、`Moat`、`Growth`、`ETF` 之一
- `thesis` — 初始觀點
- `tags` — 領域標籤（選填，預設為空陣列）
