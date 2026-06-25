from fastapi import APIRouter, Query, status

from app.api_errors import ApiError, build_common_api_error_responses
from app.schemas.api import (
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


@router.get(
    "/stocks/{stock_no}",
    tags=["Stocks API"],
    summary="查詢單一台股歷史資料",
    description=(
        "回傳單一股票在指定日期區間內的歷史成交資料與 MA5 / MA20。"
        "此端點為 JSON 資料介面；若要使用頁面版研究工作台，請改走 `/stocks/search`。"
    ),
    response_model=StockLookupResult,
    responses=build_common_api_error_responses(include_not_found=True, include_external_failure=True),
)
def get_stock_detail_api(
    stock_no: str,
    start_date: str = Query(..., description="查詢開始日期，格式為 YYYY-MM-DD。"),
    end_date: str = Query(..., description="查詢結束日期，格式為 YYYY-MM-DD。"),
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
    description="回傳目前 SQLite 中的收藏股票清單。此端點只讀，不改動收藏資料。",
    response_model=list[WatchlistItemResponse],
    responses=build_common_api_error_responses(),
)
def get_watchlist_items_api() -> list[WatchlistItemResponse]:
    try:
        return [WatchlistItemResponse(**item.__dict__) for item in list_watchlist()]
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
    description="以 JSON API 新增一筆收藏股票資料。此端點不影響既有 HTML 表單提交流程。",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses=build_common_api_error_responses(include_conflict=True),
)
def create_watchlist_item_api(payload: WatchlistCreateRequest) -> WatchlistItemResponse:
    try:
        item = add_to_watchlist(payload.stock_no, payload.stock_name)
        return WatchlistItemResponse(**item.__dict__)
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
    description="以 JSON API 移除一筆收藏股票資料。此端點不影響既有 HTML 表單提交流程。",
    response_model=ApiMessageResponse,
    responses=build_common_api_error_responses(include_not_found=True),
)
def delete_watchlist_item_api(stock_no: str) -> ApiMessageResponse:
    try:
        remove_from_watchlist(stock_no)
        return ApiMessageResponse(message="已成功移除收藏股票。")
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
    description="回傳目前 BUY / SELL 模擬交易紀錄，預設依交易時間新到舊排序。",
    response_model=list[TradeRecordResponse],
    responses=build_common_api_error_responses(),
)
def get_trade_history_api() -> list[TradeRecordResponse]:
    try:
        return [TradeRecordResponse(**trade.__dict__) for trade in list_trades()]
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
    description="回傳初始虛擬資金、已使用資金與目前可用資金。",
    response_model=VirtualCashSummaryResponse,
    responses=build_common_api_error_responses(),
)
def get_virtual_cash_summary_api() -> VirtualCashSummaryResponse:
    try:
        return VirtualCashSummaryResponse(**get_virtual_cash_summary().__dict__)
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
    description="回傳目前持股、最近收盤價估值與未實現損益摘要。",
    response_model=PortfolioOverviewResponse,
    responses=build_common_api_error_responses(),
)
def get_portfolio_positions_api() -> PortfolioOverviewResponse:
    try:
        positions, unrealized_summary = get_portfolio_overview()
        return PortfolioOverviewResponse(
            positions=[PositionSummaryResponse(**position.__dict__) for position in positions],
            unrealized_summary=UnrealizedPnlSummaryResponse(**unrealized_summary.__dict__),
        )
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
        "回傳整體投資組合摘要，包含現金、持股市值、已實現損益、未實現損益與總資產估值。"
    ),
    response_model=PortfolioSummaryResponse,
    responses=build_common_api_error_responses(),
)
def get_portfolio_summary_api() -> PortfolioSummaryResponse:
    try:
        return PortfolioSummaryResponse(**get_portfolio_summary().__dict__)
    except Exception as exc:
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "投資組合摘要讀取失敗，請稍後再試。",
        ) from exc
