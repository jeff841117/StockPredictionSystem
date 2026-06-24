from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, get_settings
from app.services.stock_service import (
    ExternalServiceError,
    InvalidDateRangeError,
    InvalidStockCodeError,
    StockLookupResult,
    StockNotFoundError,
    build_research_summary,
    build_close_price_chart,
    fetch_stock_detail,
    get_default_date_range,
    get_default_interval_label,
)
from app.services.trade_service import get_portfolio_summary, get_position_for_stock, get_virtual_cash_summary


router = APIRouter(prefix="/stocks")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
settings = get_settings()


def _build_quote_snapshot(result: StockLookupResult) -> dict[str, str]:
    latest_close = result.rows[0].close_price
    latest_date = result.rows[0].trade_date
    previous_close = result.rows[1].close_price if len(result.rows) > 1 else latest_close

    try:
        latest_value = Decimal(latest_close.replace(",", ""))
        previous_value = Decimal(previous_close.replace(",", ""))
        change_value = latest_value - previous_value
        change_percent = Decimal("0") if previous_value == 0 else (change_value / previous_value) * Decimal("100")
    except (AttributeError, InvalidOperation):
        return {
            "latest_close": latest_close,
            "latest_date": latest_date,
            "change_value": "-",
            "change_percent": "-",
        }

    sign = "+" if change_value >= 0 else ""
    return {
        "latest_close": f"{latest_value:,.2f}",
        "latest_date": latest_date,
        "change_value": f"{sign}{change_value:,.2f}",
        "change_percent": f"{sign}{change_percent:.2f}%",
    }


def _render_error(
    request: Request,
    stock_no: str,
    start_date: str | None,
    end_date: str | None,
    message: str,
    status_code: int,
) -> HTMLResponse:
    default_start_date, default_end_date = get_default_date_range()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": settings.app_name,
            "message": "輸入台股代號與日期區間後，即可查詢對應的歷史成交資料。",
            "fixed_interval": get_default_interval_label(),
            "portfolio_summary": get_portfolio_summary(),
            "stock_no": stock_no,
            "start_date": start_date or default_start_date,
            "end_date": end_date or default_end_date,
            "error_message": message,
        },
        status_code=status_code,
    )


@router.get(
    "/search",
    response_class=HTMLResponse,
    tags=["Stock Pages"],
    summary="個股研究頁",
    description=(
        "回傳個股研究工作台 HTML，整合歷史價格表、收盤價走勢圖、MA5 / MA20 與 Research Summary。"
    ),
)
def search_stock(
    request: Request,
    stock_no: str = Query(...),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    trade_message: str = Query(""),
    trade_error_message: str = Query(""),
):
    try:
        result = fetch_stock_detail(stock_no, start_date, end_date)
    except InvalidStockCodeError as exc:
        return _render_error(request, stock_no, start_date, end_date, str(exc), status.HTTP_400_BAD_REQUEST)
    except InvalidDateRangeError as exc:
        return _render_error(request, stock_no, start_date, end_date, str(exc), status.HTTP_400_BAD_REQUEST)
    except StockNotFoundError as exc:
        return _render_error(request, stock_no, start_date, end_date, str(exc), status.HTTP_404_NOT_FOUND)
    except ExternalServiceError as exc:
        return _render_error(request, stock_no, start_date, end_date, str(exc), status.HTTP_502_BAD_GATEWAY)

    position = get_position_for_stock(result.stock_no)

    return templates.TemplateResponse(
        request=request,
        name="stock_detail.html",
        context={
            "close_price_chart": build_close_price_chart(result),
            "project_name": settings.app_name,
            "quote_snapshot": _build_quote_snapshot(result),
            "research_summary": build_research_summary(
                result,
                holding_quantity=position.quantity if position is not None else 0,
                holding_average_cost=position.average_cost if position is not None else "-",
            ),
            "result": result,
            "trade_message": trade_message,
            "trade_error_message": trade_error_message,
            "virtual_cash_summary": get_virtual_cash_summary(),
        },
    )
