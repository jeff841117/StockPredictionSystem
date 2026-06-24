# Swagger / OpenAPI 與 API 分層整理

本文件整理目前專案的頁面型路由與資料型 API 分工，作為 `main` 平台主線第一輪的交接摘要。

## 1. 目前分層原則

目前專案分成兩種對外入口：

1. 頁面型路由
用途：回傳 HTML，服務作品集展示、研究工作台與表單提交流程。

2. 資料型 API
用途：回傳 JSON，服務 Swagger / OpenAPI 展示與程式化讀取需求。

## 2. 頁面型路由

- `/`
  - 首頁 `Stock Screener Workspace`
- `/stocks/search`
  - 個股研究頁 `Research Workspace`
- `/watchlist`
  - 收藏清單頁
- `/trades`
  - 交易紀錄頁
- `/trades/portfolio`
  - 持股與投資組合頁

表單動作端點：

- `/watchlist/add`
- `/watchlist/remove`
- `/trades/buy`
- `/trades/sell`

這些端點主要服務瀏覽器提交後導頁，不是純 JSON API。

## 3. 資料型 API

### Stocks API

- `GET /api/stocks/{stock_no}`
  - 依日期區間查詢單一股票歷史資料
  - 回傳欄位包含 OHLC、成交量、MA5、MA20

### Watchlist API

- `GET /api/watchlist/items`
  - 讀取目前收藏股票清單

### Trading API

- `GET /api/trades/history`
  - 讀取 BUY / SELL 模擬交易紀錄
- `GET /api/trades/cash-summary`
  - 讀取虛擬資金摘要

### Portfolio API

- `GET /api/portfolio/positions`
  - 讀取目前持股、最近收盤價估值與未實現損益
- `GET /api/portfolio/summary`
  - 讀取投資組合摘要

## 4. 文件入口

- Swagger UI：`/docs`
- ReDoc：`/redoc`
- OpenAPI JSON：`/openapi.json`
- 健康檢查：`/health`

## 5. 本輪限制

1. 本輪沒有重寫既有商業邏輯
2. 本輪沒有把所有表單端點改成 JSON API
3. 目前 JSON API 以讀取與展示為主，目標是提升平台感與作品集說服力
