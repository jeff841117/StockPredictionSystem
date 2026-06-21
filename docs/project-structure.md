# 專案結構與目前模組責任

本文件描述的是「目前專案實作狀態」，不是未來理想架構草圖。  
目標是讓協作者可以快速理解檔案放置位置與主要責任分工。

## 目前專案結構

```text
StockPredictionSystem/
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ database.py
│  ├─ models/
│  │  ├─ trade.py
│  │  ├─ watchlist.py
│  │  └─ __init__.py
│  ├─ routers/
│  │  ├─ pages.py
│  │  ├─ stocks.py
│  │  ├─ trades.py
│  │  ├─ watchlist.py
│  │  └─ __init__.py
│  ├─ schemas/
│  │  ├─ stock.py
│  │  └─ __init__.py
│  ├─ services/
│  │  ├─ stock_service.py
│  │  ├─ trade_service.py
│  │  ├─ watchlist_service.py
│  │  └─ __init__.py
│  ├─ templates/
│  │  ├─ base.html
│  │  ├─ index.html
│  │  ├─ stock_detail.html
│  │  ├─ watchlist.html
│  │  ├─ trades.html
│  │  └─ portfolio.html
│  └─ static/
│     └─ css/
│        └─ style.css
├─ docs/
├─ tests/
│  ├─ test_stocks.py
│  ├─ test_trades.py
│  └─ test_watchlist.py
├─ .env.example
├─ README.md
└─ requirements.txt
```

## 核心模組說明

### `app/main.py`

- 建立 FastAPI 應用
- 掛載靜態資源
- 註冊各 router
- 提供 `/health`

### `app/config.py`

- 統一管理環境變數與預設設定
- 包含應用名稱、主機、連接埠、預設查詢月份、虛擬資金與 SQLite 路徑

### `app/database.py`

- 提供 SQLite 連線
- 初始化 `watchlist` 與 `trades` 相關資料表

## `app/routers/`

### `pages.py`

- 首頁與靜態頁面入口

### `stocks.py`

- 股票查詢流程
- 處理查詢參數、錯誤訊息與結果頁輸出

### `watchlist.py`

- 收藏清單新增、查看、移除

### `trades.py`

- 模擬 BUY / SELL
- 交易紀錄頁
- 持股總覽頁

## `app/services/`

### `stock_service.py`

- 向 TWSE 取得股票歷史資料
- 解析日期區間資料
- 計算 MA5 / MA20
- 建立收盤價 SVG 圖表資料
- 取得最近可用收盤價供持股估值使用

### `watchlist_service.py`

- 處理收藏清單 CRUD
- 檢查重複加入與缺少必要資料

### `trade_service.py`

- 處理 BUY / SELL 驗證
- 計算虛擬資金摘要
- 整理交易紀錄
- 彙總持股、平均成本、已實現損益
- 計算未實現損益、市值與投資組合摘要

## `app/models/`

### `watchlist.py`

- 收藏項目資料結構

### `trade.py`

- 交易紀錄、資金摘要、持股摘要、已實現損益、未實現損益、投資組合摘要資料結構

## `app/schemas/`

### `stock.py`

- 股票查詢結果、表格列資料、圖表資料等 schema

## `app/templates/`

### `base.html`

- 共用版型與導覽

### `index.html`

- 首頁與股票查詢表單

### `stock_detail.html`

- 股票查詢結果頁
- 顯示摘要、表格、走勢圖、MA、收藏與模擬買進入口

### `watchlist.html`

- 收藏清單頁

### `trades.html`

- 交易紀錄頁
- 顯示 BUY / SELL 明細與已實現損益摘要

### `portfolio.html`

- 持股總覽頁
- 顯示持股、未實現損益與投資組合摘要
- 提供模擬賣出入口

## `tests/`

### `test_stocks.py`

- 股票查詢、日期驗證、外部來源錯誤、走勢圖、MA 等測試

### `test_watchlist.py`

- 收藏清單新增、重複加入、移除與 route 驗證

### `test_trades.py`

- BUY / SELL 驗證
- 資金檢查
- 交易紀錄排序
- 持股、已實現 / 未實現損益與投資組合摘要

## 目前沒有採用的結構

目前專案尚未拆出以下層：

- `repositories/`
- 獨立 `portfolio_service.py`
- 完整 API versioning
- migration 工具

原因是目前仍以 MVP 最小閉環為主，優先保持結構清楚但不過度抽象。

## 後續擴充建議

若未來功能再擴大，可優先考慮：

1. 把資料庫讀寫邏輯拆成 repository 層
2. 將持股、損益、摘要計算再細分成獨立 portfolio 模組
3. 增加更多 schema 與 API 文件
4. 導入 migration 流程
