from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.services.stock_service import get_default_date_range, get_default_interval_label, get_home_screener_items
from app.services.trade_service import get_portfolio_summary


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
settings = get_settings()


@router.get("/", response_class=HTMLResponse, tags=["pages"])
def index(request: Request):
    start_date, end_date = get_default_date_range()
    screener_items, screener_fallback_message = get_home_screener_items(start_date_text=start_date, end_date_text=end_date)
    portfolio_summary = get_portfolio_summary()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": settings.app_name,
            "message": "輸入台股代號與日期區間後，即可查詢對應的歷史成交資料。",
            "fixed_interval": get_default_interval_label(),
            "portfolio_summary": portfolio_summary,
            "screener_fallback_message": screener_fallback_message,
            "screener_items": screener_items,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
