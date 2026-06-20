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
    build_close_price_chart,
    fetch_stock_detail,
    get_default_date_range,
    get_default_interval_label,
)
from app.services.trade_service import get_virtual_cash_summary


router = APIRouter(prefix="/stocks", tags=["stocks"])
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
settings = get_settings()


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
            "stock_no": stock_no,
            "start_date": start_date or default_start_date,
            "end_date": end_date or default_end_date,
            "error_message": message,
        },
        status_code=status_code,
    )


@router.get("/search", response_class=HTMLResponse)
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

    return templates.TemplateResponse(
        request=request,
        name="stock_detail.html",
        context={
            "close_price_chart": build_close_price_chart(result),
            "project_name": settings.app_name,
            "result": result,
            "trade_message": trade_message,
            "trade_error_message": trade_error_message,
            "virtual_cash_summary": get_virtual_cash_summary(),
        },
    )
