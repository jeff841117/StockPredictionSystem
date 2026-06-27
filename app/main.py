from pathlib import Path

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles

from app.api_errors import ApiError, build_api_error_content, build_validation_issues
from app.database import init_database
from app.config import get_settings
from app.error_monitoring import record_error_event
from app.services.auth_service import get_current_user_role, get_current_username
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
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
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(stocks_router)
app.include_router(trades_router)
app.include_router(watchlist_router)
app.include_router(api_router)
init_database()


@app.middleware("http")
async def attach_current_user_to_request(request, call_next):
    request.state.current_username = get_current_username(request)
    request.state.current_user_role = get_current_user_role(request)
    return await call_next(request)


def _is_api_request_path(path: str) -> bool:
    return path == "/api" or path.startswith("/api/")


@app.exception_handler(ApiError)
async def api_error_exception_handler(request, exc: ApiError):
    record_error_event(
        flow="api",
        category=_map_error_code_to_category(exc.error_code),
        route=request.url.path,
        user_message=exc.message,
        internal_message=f"{exc.error_code}: {exc.message}",
        status_code=exc.status_code,
        request=request,
    )
    return JSONResponse(status_code=exc.status_code, content=exc.to_response().model_dump())


@app.exception_handler(RequestValidationError)
async def api_request_validation_exception_handler(request, exc: RequestValidationError):
    if not _is_api_request_path(request.url.path):
        return await request_validation_exception_handler(request, exc)

    record_error_event(
        flow="api",
        category="validation_error",
        route=request.url.path,
        user_message="API 請求參數驗證失敗，請確認必填欄位與格式。",
        internal_message=str(exc.errors()),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request=request,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_api_error_content(
            "VALIDATION_ERROR",
            "API 請求參數驗證失敗，請確認必填欄位與格式。",
            validation_errors=build_validation_issues(exc.errors()),
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def api_http_exception_handler(request, exc: StarletteHTTPException):
    if not _is_api_request_path(request.url.path):
        return await http_exception_handler(request, exc)

    error_code = "NOT_FOUND" if exc.status_code == status.HTTP_404_NOT_FOUND else "HTTP_ERROR"
    message = exc.detail if isinstance(exc.detail, str) else "API 請求失敗。"
    record_error_event(
        flow="api",
        category="not_found" if exc.status_code == status.HTTP_404_NOT_FOUND else "http_error",
        route=request.url.path,
        user_message=message,
        internal_message=f"HTTP {exc.status_code}: {message}",
        status_code=exc.status_code,
        request=request,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=build_api_error_content(error_code, message),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    if _is_api_request_path(request.url.path):
        record_error_event(
            flow="api",
            category="internal_server_error",
            route=request.url.path,
            user_message="系統發生未預期錯誤，請稍後再試。",
            internal_message=repr(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request=request,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_api_error_content(
                "INTERNAL_SERVER_ERROR",
                "系統發生未預期錯誤，請稍後再試。",
            ),
        )

    record_error_event(
        flow="page",
        category="internal_server_error",
        route=request.url.path,
        user_message="頁面處理時發生未預期錯誤，請稍後再試。",
        internal_message=repr(exc),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request=request,
    )
    return HTMLResponse(
        content="頁面處理時發生未預期錯誤，請稍後再試。",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _map_error_code_to_category(error_code: str) -> str:
    mapping = {
        "VALIDATION_ERROR": "validation_error",
        "INVALID_INPUT": "business_rule_error",
        "DUPLICATE_RESOURCE": "business_rule_error",
        "NOT_FOUND": "not_found",
        "EXTERNAL_SERVICE_ERROR": "external_service_error",
        "UNAUTHORIZED": "unauthorized",
        "FORBIDDEN": "forbidden",
        "INTERNAL_SERVER_ERROR": "internal_server_error",
    }
    return mapping.get(error_code, "api_error")


@app.get(
    "/health",
    tags=["System"],
    summary="健康檢查",
    description="回傳最小平台健康狀態，用於確認 FastAPI 應用已成功啟動。",
    response_model=HealthCheckResponse,
)
def health_check() -> HealthCheckResponse:
    return {"status": "ok"}
