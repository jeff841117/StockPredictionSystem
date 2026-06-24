from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.api import (
    PortfolioOverviewResponse,
    PortfolioSummaryResponse,
    PositionSummaryResponse,
    TradeRecordResponse,
    UnrealizedPnlSummaryResponse,
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
from app.services.watchlist_service import list_watchlist


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
)
def get_stock_detail_api(
    stock_no: str,
    start_date: str = Query(..., description="查詢開始日期，格式為 YYYY-MM-DD。"),
    end_date: str = Query(..., description="查詢結束日期，格式為 YYYY-MM-DD。"),
) -> StockLookupResult:
    try:
        return fetch_stock_detail(stock_no, start_date, end_date)
    except InvalidStockCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidDateRangeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except StockNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ExternalServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get(
    "/watchlist/items",
    tags=["Watchlist API"],
    summary="取得收藏清單",
    description="回傳目前 SQLite 中的收藏股票清單。此端點只讀，不改動收藏資料。",
    response_model=list[WatchlistItemResponse],
)
def get_watchlist_items_api() -> list[WatchlistItemResponse]:
    return [WatchlistItemResponse(**item.__dict__) for item in list_watchlist()]


@router.get(
    "/trades/history",
    tags=["Trading API"],
    summary="取得模擬交易紀錄",
    description="回傳目前 BUY / SELL 模擬交易紀錄，預設依交易時間新到舊排序。",
    response_model=list[TradeRecordResponse],
)
def get_trade_history_api() -> list[TradeRecordResponse]:
    return [TradeRecordResponse(**trade.__dict__) for trade in list_trades()]


@router.get(
    "/trades/cash-summary",
    tags=["Trading API"],
    summary="取得虛擬資金摘要",
    description="回傳初始虛擬資金、已使用資金與目前可用資金。",
    response_model=VirtualCashSummaryResponse,
)
def get_virtual_cash_summary_api() -> VirtualCashSummaryResponse:
    return VirtualCashSummaryResponse(**get_virtual_cash_summary().__dict__)


@router.get(
    "/portfolio/positions",
    tags=["Portfolio API"],
    summary="取得目前持股與未實現損益",
    description="回傳目前持股、最近收盤價估值與未實現損益摘要。",
    response_model=PortfolioOverviewResponse,
)
def get_portfolio_positions_api() -> PortfolioOverviewResponse:
    positions, unrealized_summary = get_portfolio_overview()
    return PortfolioOverviewResponse(
        positions=[PositionSummaryResponse(**position.__dict__) for position in positions],
        unrealized_summary=UnrealizedPnlSummaryResponse(**unrealized_summary.__dict__),
    )


@router.get(
    "/portfolio/summary",
    tags=["Portfolio API"],
    summary="取得投資組合摘要",
    description=(
        "回傳整體投資組合摘要，包含現金、持股市值、已實現損益、未實現損益與總資產估值。"
    ),
    response_model=PortfolioSummaryResponse,
)
def get_portfolio_summary_api() -> PortfolioSummaryResponse:
    return PortfolioSummaryResponse(**get_portfolio_summary().__dict__)
