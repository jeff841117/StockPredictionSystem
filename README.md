# StockPredictionSystem

台股分析與模擬交易系統的 MVP 專案。  
目前版本已完成單一股票查詢、技術指標、收藏清單、模擬交易、持股總覽與損益摘要的最小閉環。

## 目前已完成功能

- 單一台股查詢
- 自訂日期區間查詢
- 首頁 Screener 展示區
- 歷史股價表格顯示
- 收盤價走勢圖
- MA5 / MA20 技術指標
- 收藏清單新增、查看、移除
- 模擬 BUY / SELL 交易
- 交易紀錄頁
- 持股總覽頁
- 已實現損益
- 未實現損益與市值
- 投資組合摘要

## 目前版本限制

- 僅支援單一股票查詢，不支援多股票比較
- 目前價格使用最近可取得收盤價，不是即時報價
- 技術指標只提供 MA5 / MA20
- 交易只支援最小 BUY / SELL 流程，不含手續費、交易稅、零股與當沖規則
- 無使用者登入與多使用者隔離
- 無資料庫進階遷移機制，使用本機 SQLite
- 無完整 API 文件與正式部署流程

## 執行環境

- Python 3.11+ 或相容版本
- Windows PowerShell、命令提示字元或其他可執行 Python 的終端
- 可連線到 TWSE `STOCK_DAY` JSON 資料來源

## 安裝方式

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

如需自訂設定，可參考 `.env.example` 建立 `.env`。  
程式啟動時會自動從專案根目錄載入 `.env`。

## 主要設定

`.env` 範例：

```env
APP_NAME=台股分析與模擬交易系統
DEBUG=false
HOST=127.0.0.1
PORT=8000
STOCK_QUERY_SOURCE=https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY
STOCK_QUERY_DATE=20240501
INITIAL_VIRTUAL_CASH=1000000
WATCHLIST_DB_PATH=data/watchlist.db
```

說明：

- `STOCK_QUERY_SOURCE`：TWSE 每日成交資訊來源
- `STOCK_QUERY_DATE`：首頁預設日期區間基準月份
- `INITIAL_VIRTUAL_CASH`：模擬交易起始虛擬資金
- `WATCHLIST_DB_PATH`：SQLite 資料庫位置，預設為 `data/watchlist.db`

## 啟動方式

```bash
uvicorn app.main:app --reload
```

啟動後可開啟：

- 首頁：`http://127.0.0.1:8000/`
- 健康檢查：`http://127.0.0.1:8000/health`
- 交易紀錄：`http://127.0.0.1:8000/trades`
- 持股總覽：`http://127.0.0.1:8000/trades/portfolio`
- 收藏清單：`http://127.0.0.1:8000/watchlist`

## 操作流程

### 1. 股票查詢

1. 開啟首頁
2. 輸入單一台股代號，例如 `2330`
3. 輸入開始日期與結束日期
4. 送出查詢
5. 查看股票名稱、歷史價格、收盤價走勢圖與 MA5 / MA20

### 2. 收藏清單

1. 先完成一次股票查詢
2. 在結果頁加入收藏
3. 前往收藏頁查看或移除

### 3. 模擬交易

1. 在股票查詢結果頁輸入買進價格、股數、時間
2. 完成模擬買進
3. 前往交易紀錄頁查看 BUY / SELL 紀錄
4. 前往持股總覽頁查看持股、平均成本、損益與投資組合摘要
5. 在持股頁輸入賣出資料完成模擬賣出

## 功能說明

### 股票查詢

- 資料來源：TWSE `STOCK_DAY`
- 查詢方式：單一股票 + 自訂日期區間
- 錯誤處理：無效代號、日期錯誤、查無資料、外部來源失敗皆有專案自己的提示訊息

### 首頁 Screener 展示區

- 顯示位置：首頁 `Stock Screener Workspace`
- 內容來源：少量研究候選股的既有歷史查詢資料
- 目前顯示：股票代號、股票名稱、最新收盤價、區間漲跌、MA5 / MA20 狀態摘要
- 定位：研究候選展示，不是即時全市場選股器
- fallback：若部分候選資料暫時失敗，首頁仍會保留可用項目並顯示提示

### 收盤價走勢圖

- 顯示位置：股票查詢結果頁
- 圖表形式：內嵌 SVG
- 資料範圍：與表格資料相同

### MA5 / MA20

- 依查詢區間內的收盤價計算
- 前段資料不足時顯示 `-`
- 同步顯示於表格與走勢圖

### 收藏清單

- 儲存方式：SQLite
- 最小欄位：股票代號、股票名稱、建立時間
- 同一股票不可重複加入

### 模擬 BUY / SELL

- 儲存方式：SQLite `trades` 資料表
- BUY 會檢查虛擬資金是否足夠
- SELL 會檢查目前持股是否足夠
- 價格、股數、交易時間皆有基本驗證

### 交易紀錄

- 預設依交易時間新到舊排序
- 顯示股票代號、股票名稱、交易類型、價格、股數、交易時間、交易總金額、已實現損益

### 持股總覽

- 依 BUY / SELL 交易推導目前持股
- 顯示持股數量、平均成本、持股成本基礎
- 顯示最近可取得收盤價、估算市值、未實現損益

### Research Summary

- 顯示位置：個股頁 `Research Workspace` 上方
- 內容來源：目前查詢結果與既有持股資料
- 目前顯示：最新收盤價、區間漲跌、區間高低、最新 MA5 / MA20、是否持有、持股數量、平均成本
- 只做研究摘要整理，不提供投資建議語句

### 已實現 / 未實現損益

- 已實現損益：依 SELL 交易與加權平均成本計算
- 未實現損益：依最近可取得收盤價估算
- 缺價時不會讓整頁失敗，僅標示未納入估值部分

### 投資組合摘要

持股總覽頁目前會顯示：

- 初始虛擬資金
- 目前可用資金
- 目前已使用資金
- 目前持股市值
- 累計已實現損益
- 整體未實現損益
- 目前總資產估值

固定計算規則：

- `總資產估值 = 可用資金 + 持股市值`

## 測試方式

執行最小自動化測試：

```bash
python -m unittest discover -s tests -v
```

目前測試涵蓋：

- 股票查詢成功與錯誤情境
- 走勢圖與 MA 欄位
- 收藏清單 CRUD
- BUY / SELL 驗證與資金檢查
- 交易紀錄排序
- 持股總覽、已實現損益、未實現損益與投資組合摘要

### 真實價格路徑 smoke test

此測試會實際打到 TWSE 真實資料來源，用來補強 `get_latest_close_price()` 與最近價格回補路徑驗證。  
預設不會在一般單元測試中強制執行，避免外部資料波動讓主測試流程變得不穩定。

執行方式：

```bash
set RUN_TWSE_SMOKE=1
python -m unittest discover -s tests -p "test_stock_price_smoke.py" -v
```

用途：

- 驗證常見有效股票代號可取得最近收盤價
- 驗證需要時可向前回補查找
- 區分外部資料異常與程式邏輯異常

結果判讀：

- `ok`：真實價格路徑正常
- `EXTERNAL_DATA_ERROR`：TWSE 連線、限流或回傳異常
- `EXTERNAL_DATA_STATE`：當下外部資料暫時不可得
- `LOGIC_ERROR`：程式執行或回補邏輯異常

## 專案結構

```text
app/
├─ main.py
├─ config.py
├─ database.py
├─ models/
│  ├─ trade.py
│  └─ watchlist.py
├─ routers/
│  ├─ pages.py
│  ├─ stocks.py
│  ├─ trades.py
│  └─ watchlist.py
├─ schemas/
│  └─ stock.py
├─ services/
│  ├─ stock_service.py
│  ├─ trade_service.py
│  └─ watchlist_service.py
├─ templates/
│  ├─ base.html
│  ├─ index.html
│  ├─ portfolio.html
│  ├─ stock_detail.html
│  ├─ trades.html
│  └─ watchlist.html
└─ static/
   └─ css/
      └─ style.css

tests/
├─ test_stocks.py
├─ test_trades.py
└─ test_watchlist.py
```

更完整的說明可參考：

- [docs/project-structure.md](docs/project-structure.md)
- [docs/dev-workflow.md](docs/dev-workflow.md)
- [docs/mvp-plan.md](docs/mvp-plan.md)
- [docs/features/current-mvp-features.md](docs/features/current-mvp-features.md)
- [docs/features/mvp-v1-acceptance-summary.md](docs/features/mvp-v1-acceptance-summary.md)

## 尚未完成項目

- 使用者登入
- 多使用者資料隔離
- 即時行情
- 更多技術指標
- 正式部署教學
- 完整 API 文件
- 資料庫 migration / schema versioning
- 投資組合進階分析與圖表
