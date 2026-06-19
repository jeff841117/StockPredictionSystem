# StockPredictionSystem

台股分析與模擬交易系統的第一輪 FastAPI 基礎骨架。

## 目前內容

- FastAPI 應用入口
- 首頁路由與 Jinja2 模板
- 靜態樣式目錄
- 環境變數範例
- 基本安裝與啟動說明

## 專案結構

```text
app/
├─ main.py
├─ config.py
├─ routers/
│  └─ pages.py
├─ templates/
│  ├─ base.html
│  └─ index.html
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

## 啟動方式

```bash
uvicorn app.main:app --reload
```

啟動後可開啟：

- 首頁: `http://127.0.0.1:8000/`
- 健康檢查: `http://127.0.0.1:8000/health`

## 本輪不包含

- 股票資料 API 串接
- 資料庫商業邏輯
- 模擬交易功能
- AI 預測功能
- 使用者登入功能
