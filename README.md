# StockPredictionSystem

台股分析與模擬交易系統的第一輪 FastAPI 基礎骨架。

## 目前內容

- FastAPI 應用入口
- 首頁路由與 Jinja2 模板
- 靜態樣式目錄
- 環境變數範例
- 基本安裝與啟動說明
- 單一股票最小查詢流程

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
```

## 安裝方式

1. 建立虛擬環境
2. 安裝套件
3. 依需要建立 `.env`

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

可先參考 `.env.example` 建立自己的 `.env`。
程式啟動時會自動從專案根目錄載入 `.env`。

## 啟動方式

```bash
uvicorn app.main:app --reload
```

若要套用自訂主機、連接埠或專案名稱，可先建立 `.env`，例如：

```env
APP_NAME=台股分析與模擬交易系統
DEBUG=false
HOST=127.0.0.1
PORT=8000
STOCK_QUERY_SOURCE=https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY
STOCK_QUERY_DATE=20240501
INITIAL_VIRTUAL_CASH=1000000
```

啟動後可開啟：

- 首頁: `http://127.0.0.1:8000/`
- 健康檢查: `http://127.0.0.1:8000/health`

## 股票查詢

- 資料來源：TWSE `STOCK_DAY` 官方 JSON 端點
- 預設日期區間：`2024-05-01` 至 `2024-05-31`
- 使用方式：在首頁輸入單一台股代號，並指定開始日期與結束日期，例如 `2330` + `2024-05-01` 到 `2024-05-31`
- 走勢圖方式：結果頁內嵌 SVG 收盤價折線圖
- 技術指標：MA5、MA20（依查詢區間收盤價計算）
- 收藏清單：SQLite 本機資料庫儲存最小 watchlist
- 模擬買進：SQLite 本機資料庫儲存最小 BUY 交易紀錄
- 交易紀錄：可查看已保存的 BUY 模擬交易資料
- 持股總覽：依 BUY 交易彙總持股數量、平均成本與累計買進金額

本輪會顯示：

- 股票代號
- 股票名稱
- 查詢區間
- 資料筆數
- 顯示順序（固定為日期由新到舊）
- 日期
- 開盤價
- 最高價
- 最低價
- 收盤價
- MA5
- MA20
- 成交量
- 收盤價走勢圖（X 軸為日期、Y 軸為收盤價，並疊加 MA5、MA20）
- 收藏清單（股票代號、股票名稱、加入時間）
- 模擬買進（股票代號、股票名稱、價格、股數、時間）
- 交易紀錄頁（股票代號、股票名稱、交易類型、價格、股數、時間、總金額）
- 持股總覽頁（股票代號、股票名稱、持股數量、平均成本、累計買進金額）

## 本輪不包含

- AI 預測功能
- 使用者登入功能
