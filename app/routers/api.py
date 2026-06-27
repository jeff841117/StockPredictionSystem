from fastapi import APIRouter, Query, Request, status

from app.api_errors import ApiError, build_common_api_error_responses
from app.schemas.api import (
    AuditLogResponse,
    ApiMessageResponse,
    PortfolioOverviewResponse,
    PortfolioSummaryResponse,
    PositionSummaryResponse,
    TradeRecordResponse,
    UnrealizedPnlSummaryResponse,
    WatchlistCreateRequest,
    VirtualCashSummaryResponse,
    WatchlistItemResponse,
)
from app.schemas.stock import StockLookupResult
from app.services.audit_service import list_audit_logs
from app.services.auth_service import PermissionDeniedError, get_current_user, require_role
from app.services.stock_service import (
    ExternalServiceError,
    InvalidDateRangeError,
    InvalidStockCodeError,
    StockNotFoundError,
    fetch_stock_detail,
)
from app.services.trade_service import get_portfolio_overview, get_portfolio_summary, get_virtual_cash_summary, list_trades
from app.services.watchlist_service import (
    DuplicateWatchlistItemError,
    InvalidWatchlistItemError,
    WatchlistItemNotFoundError,
    add_to_watchlist,
    list_watchlist,
    remove_from_watchlist,
)


router = APIRouter(prefix="/api")

STOCK_LOOKUP_RESPONSE_EXAMPLE = {
    "stock_no": "2330",
    "stock_name": "台積電",
    "source_name": "TWSE 每日成交資訊",
    "interval_start": "2024-05-01",
    "interval_end": "2024-05-31",
    "rows": [
        {
            "trade_date": "2024-05-31",
            "open_price": "838.00",
            "high_price": "846.00",
            "low_price": "821.00",
            "close_price": "821.00",
            "volume": "90,177,283",
            "ma5": "850.00",
            "ma20": "833.85",
        }
    ],
}

WATCHLIST_LIST_RESPONSE_EXAMPLE = [
    {
        "stock_no": "2330",
        "stock_name": "台積電",
        "created_at": "2024-05-31 10:00:00",
    }
]

TRADE_HISTORY_RESPONSE_EXAMPLE = [
    {
        "id": 12,
        "stock_no": "2330",
        "stock_name": "台積電",
        "trade_type": "SELL",
        "price": "900.00",
        "quantity": 40,
        "trade_time": "2024-06-01 09:00:00",
        "total_amount": "36,000.00",
        "realized_pnl": "4,000.00",
    }
]

VIRTUAL_CASH_RESPONSE_EXAMPLE = {
    "initial_cash": "1,000,000.00",
    "used_cash": "44,000.00",
    "available_cash": "956,000.00",
}

PORTFOLIO_OVERVIEW_RESPONSE_EXAMPLE = {
    "positions": [
        {
            "stock_no": "2330",
            "stock_name": "台積電",
            "quantity": 60,
            "average_cost": "800.00",
            "total_buy_amount": "48,000.00",
            "current_price": "850.00",
            "market_value": "51,000.00",
            "unrealized_pnl": "3,000.00",
            "price_note": "",
        }
    ],
    "unrealized_summary": {
        "total_unrealized_pnl": "3,000.00",
        "priced_position_count": 1,
        "missing_price_count": 0,
    },
}

PORTFOLIO_SUMMARY_RESPONSE_EXAMPLE = {
    "initial_cash": "1,000,000.00",
    "available_cash": "956,000.00",
    "used_cash": "44,000.00",
    "holdings_market_value": "51,000.00",
    "total_realized_pnl": "4,000.00",
    "total_unrealized_pnl": "3,000.00",
    "total_asset_estimate": "1,007,000.00",
    "missing_price_count": 0,
}


def _require_api_user(request: Request) -> int:
    user = get_current_user(request)
    if user is None:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "UNAUTHORIZED",
            "請先登入後再存取這個 API。",
        )
    return user.id


def _require_api_admin(request: Request) -> None:
    try:
        require_role(request, "admin")
    except PermissionDeniedError as exc:
        if str(exc) == "UNAUTHENTICATED":
            raise ApiError(
                status.HTTP_401_UNAUTHORIZED,
                "UNAUTHORIZED",
                "請先登入後再存取這個 API。",
            ) from exc
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "FORBIDDEN",
            "你目前沒有權限存取這個 API。",
        ) from exc


@router.get(
    "/stocks/{stock_no}",
    tags=["Stocks API"],
    summary="查詢單一台股歷史資料",
    description=(
        "回傳單一股票在指定日期區間內的歷史成交資料與 MA5 / MA20。"
        "此端點為 JSON 資料介面；若要使用頁面版研究工作台，請改走 `/stocks/search`。"
    ),
    response_model=StockLookupResult,
    responses={
        200: {
            "description": "成功回傳單一股票的歷史資料與均線欄位。",
            "content": {"application/json": {"example": STOCK_LOOKUP_RESPONSE_EXAMPLE}},
        },
        **build_common_api_error_responses(include_not_found=True, include_external_failure=True),
    },
)
def get_stock_detail_api(
    stock_no: str,
    start_date: str = Query(..., description="查詢開始日期，格式為 YYYY-MM-DD。", example="2024-05-01"),
    end_date: str = Query(..., description="查詢結束日期，格式為 YYYY-MM-DD。", example="2024-05-31"),
) -> StockLookupResult:
    try:
        return fetch_stock_detail(stock_no, start_date, end_date)
    except InvalidStockCodeError as exc:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "INVALID_INPUT", str(exc)) from exc
    except InvalidDateRangeError as exc:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "INVALID_INPUT", str(exc)) from exc
    except StockNotFoundError as exc:
        raise ApiError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", str(exc)) from exc
    except ExternalServiceError as exc:
        raise ApiError(status.HTTP_502_BAD_GATEWAY, "EXTERNAL_SERVICE_ERROR", str(exc)) from exc
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "API 查詢處理失敗，請稍後再試。",
        ) from exc


@router.get(
    "/watchlist/items",
    tags=["Watchlist API"],
    summary="取得收藏清單",
    description="回傳目前登入使用者的收藏股票清單。此端點只讀，不改動收藏資料。",
    response_model=list[WatchlistItemResponse],
    responses={
        200: {
            "description": "成功回傳目前登入使用者的收藏股票清單。",
            "content": {"application/json": {"example": WATCHLIST_LIST_RESPONSE_EXAMPLE}},
        },
        **build_common_api_error_responses(include_unauthorized=True),
    },
)
def get_watchlist_items_api(request: Request) -> list[WatchlistItemResponse]:
    try:
        user_id = _require_api_user(request)
        return [WatchlistItemResponse(**item.__dict__) for item in list_watchlist(user_id)]
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "收藏清單讀取失敗，請稍後再試。",
        ) from exc


@router.post(
    "/watchlist/items",
    tags=["Watchlist API"],
    summary="新增收藏股票",
    description="以 JSON API 為目前登入使用者新增一筆收藏股票資料。此端點不影響既有 HTML 表單提交流程。",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "成功新增一筆收藏股票資料。",
            "content": {
                "application/json": {
                    "example": {
                        "stock_no": "2330",
                        "stock_name": "台積電",
                        "created_at": "2024-05-31 10:00:00",
                    }
                }
            },
        },
        **build_common_api_error_responses(include_conflict=True, include_unauthorized=True),
    },
)
def create_watchlist_item_api(request: Request, payload: WatchlistCreateRequest) -> WatchlistItemResponse:
    try:
        user_id = _require_api_user(request)
        item = add_to_watchlist(payload.stock_no, payload.stock_name, user_id)
        return WatchlistItemResponse(**item.__dict__)
    except ApiError:
        raise
    except InvalidWatchlistItemError as exc:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "INVALID_INPUT", str(exc)) from exc
    except DuplicateWatchlistItemError as exc:
        raise ApiError(status.HTTP_409_CONFLICT, "DUPLICATE_RESOURCE", str(exc)) from exc
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "收藏清單寫入失敗，請稍後再試。",
        ) from exc


@router.delete(
    "/watchlist/items/{stock_no}",
    tags=["Watchlist API"],
    summary="移除收藏股票",
    description="以 JSON API 移除目前登入使用者的一筆收藏股票資料。此端點不影響既有 HTML 表單提交流程。",
    response_model=ApiMessageResponse,
    responses={
        200: {
            "description": "成功移除收藏股票。",
            "content": {"application/json": {"example": {"message": "已成功移除收藏股票。"}}},
        },
        **build_common_api_error_responses(include_not_found=True, include_unauthorized=True),
    },
)
def delete_watchlist_item_api(request: Request, stock_no: str) -> ApiMessageResponse:
    try:
        user_id = _require_api_user(request)
        remove_from_watchlist(stock_no, user_id)
        return ApiMessageResponse(message="已成功移除收藏股票。")
    except ApiError:
        raise
    except InvalidWatchlistItemError as exc:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "INVALID_INPUT", str(exc)) from exc
    except WatchlistItemNotFoundError as exc:
        raise ApiError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", str(exc)) from exc
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "收藏清單刪除失敗，請稍後再試。",
        ) from exc


@router.get(
    "/trades/history",
    tags=["Trading API"],
    summary="取得模擬交易紀錄",
    description="回傳目前登入使用者的 BUY / SELL 模擬交易紀錄，預設依交易時間新到舊排序。",
    response_model=list[TradeRecordResponse],
    responses={
        200: {
            "description": "成功回傳目前登入使用者的交易紀錄。",
            "content": {"application/json": {"example": TRADE_HISTORY_RESPONSE_EXAMPLE}},
        },
        **build_common_api_error_responses(include_unauthorized=True),
    },
)
def get_trade_history_api(request: Request) -> list[TradeRecordResponse]:
    try:
        user_id = _require_api_user(request)
        return [TradeRecordResponse(**trade.__dict__) for trade in list_trades(user_id)]
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "交易紀錄讀取失敗，請稍後再試。",
        ) from exc


@router.get(
    "/trades/cash-summary",
    tags=["Trading API"],
    summary="取得虛擬資金摘要",
    description="回傳目前登入使用者的初始虛擬資金、已使用資金與目前可用資金。",
    response_model=VirtualCashSummaryResponse,
    responses={
        200: {
            "description": "成功回傳目前登入使用者的虛擬資金摘要。",
            "content": {"application/json": {"example": VIRTUAL_CASH_RESPONSE_EXAMPLE}},
        },
        **build_common_api_error_responses(include_unauthorized=True),
    },
)
def get_virtual_cash_summary_api(request: Request) -> VirtualCashSummaryResponse:
    try:
        user_id = _require_api_user(request)
        return VirtualCashSummaryResponse(**get_virtual_cash_summary(user_id).__dict__)
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "虛擬資金摘要讀取失敗，請稍後再試。",
        ) from exc


@router.get(
    "/portfolio/positions",
    tags=["Portfolio API"],
    summary="取得目前持股與未實現損益",
    description="回傳目前登入使用者的持股、最近收盤價估值與未實現損益摘要。",
    response_model=PortfolioOverviewResponse,
    responses={
        200: {
            "description": "成功回傳目前登入使用者的持股與未實現損益摘要。",
            "content": {"application/json": {"example": PORTFOLIO_OVERVIEW_RESPONSE_EXAMPLE}},
        },
        **build_common_api_error_responses(include_unauthorized=True),
    },
)
def get_portfolio_positions_api(request: Request) -> PortfolioOverviewResponse:
    try:
        user_id = _require_api_user(request)
        positions, unrealized_summary = get_portfolio_overview(user_id)
        return PortfolioOverviewResponse(
            positions=[PositionSummaryResponse(**position.__dict__) for position in positions],
            unrealized_summary=UnrealizedPnlSummaryResponse(**unrealized_summary.__dict__),
        )
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "持股與未實現損益資料讀取失敗，請稍後再試。",
        ) from exc


@router.get(
    "/portfolio/summary",
    tags=["Portfolio API"],
    summary="取得投資組合摘要",
    description=(
        "回傳目前登入使用者的整體投資組合摘要，包含現金、持股市值、已實現損益、未實現損益與總資產估值。"
    ),
    response_model=PortfolioSummaryResponse,
    responses={
        200: {
            "description": "成功回傳目前登入使用者的投資組合摘要。",
            "content": {"application/json": {"example": PORTFOLIO_SUMMARY_RESPONSE_EXAMPLE}},
        },
        **build_common_api_error_responses(include_unauthorized=True),
    },
)
def get_portfolio_summary_api(request: Request) -> PortfolioSummaryResponse:
    try:
        user_id = _require_api_user(request)
        return PortfolioSummaryResponse(**get_portfolio_summary(user_id).__dict__)
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "投資組合摘要讀取失敗，請稍後再試。",
        ) from exc


@router.get(
    "/admin/audit-logs",
    tags=["System"],
    summary="取得操作日誌",
    description="回傳最小 audit log 清單。此端點目前僅限 admin 存取，用於展示最小角色權限管理。",
    response_model=list[AuditLogResponse],
    responses={
        200: {
            "description": "成功回傳 audit log 清單。",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "event_type": "AUTH_LOGIN",
                            "username": "admin_user",
                            "created_at": "2024-05-31 09:00:00",
                            "target_type": "session",
                            "target_value": "/admin/audit-logs",
                            "status": "success",
                            "context": "{}",
                        }
                    ]
                }
            },
        },
        **build_common_api_error_responses(include_unauthorized=True, include_forbidden=True),
    },
)
def get_admin_audit_logs_api(request: Request) -> list[AuditLogResponse]:
    try:
        _require_api_admin(request)
        return [
            AuditLogResponse(
                event_type=item.event_type,
                username=item.username,
                created_at=item.created_at,
                target_type=item.target_type,
                target_value=item.target_value,
                status=item.status,
                context=item.context,
            )
            for item in list_audit_logs()
        ]
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "操作日誌讀取失敗，請稍後再試。",
        ) from exc
