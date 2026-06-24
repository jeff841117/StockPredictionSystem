from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_database
from app.config import get_settings
from app.routers.api import router as api_router
from app.routers.pages import router as pages_router
from app.routers.stocks import router as stocks_router
from app.routers.trades import router as trades_router
from app.routers.watchlist import router as watchlist_router
from app.schemas.api import HealthCheckResponse


BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    summary="台股研究、模擬交易與投資組合追蹤平台的 FastAPI 展示入口。",
    description=(
        "本專案同時提供 HTML 頁面型路由與 JSON 資料型 API。"
        "頁面型路由用於作品集展示與操作流程，`/api/*` 端點則提供較清楚的資料讀取介面，"
        "方便透過 Swagger / OpenAPI 檢視目前平台能力。"
    ),
    version="1.1.0",
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "Pages",
            "description": "首頁與展示頁面型路由，回傳 HTML，用於研究工作台與作品集展示。",
        },
        {
            "name": "Stock Pages",
            "description": "個股研究頁相關路由，回傳 HTML，整合查詢結果、圖表與摘要資訊。",
        },
        {
            "name": "Watchlist Pages",
            "description": "收藏清單展示頁與表單操作路由，主要服務瀏覽器流程。",
        },
        {
            "name": "Trade Pages",
            "description": "模擬交易、交易紀錄與投資組合展示頁，回傳 HTML。",
        },
        {
            "name": "Stocks API",
            "description": "個股查詢資料型 API，提供 JSON 回應與最小 schema 說明。",
        },
        {
            "name": "Watchlist API",
            "description": "收藏清單資料型 API，用於讀取目前收藏股票清單。",
        },
        {
            "name": "Trading API",
            "description": "模擬交易資料讀取 API，包含交易紀錄與資金摘要。",
        },
        {
            "name": "Portfolio API",
            "description": "持股、未實現損益與投資組合摘要的資料型 API。",
        },
        {
            "name": "System",
            "description": "系統層級健康檢查與平台狀態端點。",
        },
    ],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(pages_router)
app.include_router(stocks_router)
app.include_router(trades_router)
app.include_router(watchlist_router)
app.include_router(api_router)
init_database()


@app.get(
    "/health",
    tags=["System"],
    summary="健康檢查",
    description="回傳最小平台健康狀態，用於確認 FastAPI 應用已成功啟動。",
    response_model=HealthCheckResponse,
)
def health_check() -> HealthCheckResponse:
    return {"status": "ok"}
