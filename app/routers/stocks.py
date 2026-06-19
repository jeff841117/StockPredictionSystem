from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, get_settings
from app.services.stock_service import (
    ExternalServiceError,
    InvalidStockCodeError,
    StockLookupResult,
    StockNotFoundError,
    build_close_price_chart,
    fetch_stock_detail,
    get_fixed_interval_label,
)


router = APIRouter(prefix="/stocks", tags=["stocks"])
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
settings = get_settings()


def _render_error(
    request: Request,
    stock_no: str,
    message: str,
    status_code: int,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": settings.app_name,
            "message": "輸入台股代號後，即可查詢固定區間的歷史成交資料。",
            "fixed_interval": get_fixed_interval_label(),
            "stock_no": stock_no,
            "error_message": message,
        },
        status_code=status_code,
    )


@router.get("/search", response_class=HTMLResponse)
def search_stock(
    request: Request,
    stock_no: str = Query(...),
):
    try:
        result = fetch_stock_detail(stock_no)
    except InvalidStockCodeError as exc:
        return _render_error(request, stock_no, str(exc), status.HTTP_400_BAD_REQUEST)
    except StockNotFoundError as exc:
        return _render_error(request, stock_no, str(exc), status.HTTP_404_NOT_FOUND)
    except ExternalServiceError as exc:
        return _render_error(request, stock_no, str(exc), status.HTTP_502_BAD_GATEWAY)

    return templates.TemplateResponse(
        request=request,
        name="stock_detail.html",
        context={
            "close_price_chart": build_close_price_chart(result),
            "project_name": settings.app_name,
            "result": result,
            "fixed_interval": get_fixed_interval_label(),
        },
    )
