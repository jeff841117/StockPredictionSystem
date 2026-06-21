from urllib.parse import urlencode

from fastapi import APIRouter, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, get_settings
from app.services.trade_service import (
    InsufficientHoldingsError,
    InsufficientFundsError,
    InvalidTradeInputError,
    create_buy_trade,
    create_sell_trade,
    get_portfolio_overview,
    get_realized_pnl_summary,
    get_virtual_cash_summary,
    list_trades,
)


router = APIRouter(prefix="/trades", tags=["trades"])
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
settings = get_settings()


@router.get("", response_class=HTMLResponse)
def trades_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="trades.html",
        context={
            "project_name": settings.app_name,
            "realized_pnl_summary": get_realized_pnl_summary(),
            "trades": list_trades(),
            "virtual_cash_summary": get_virtual_cash_summary(),
        },
    )


@router.get("/portfolio", response_class=HTMLResponse)
def portfolio_page(
    request: Request,
    trade_error_message: str = Query(""),
):
    positions, unrealized_pnl_summary = get_portfolio_overview()
    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context={
            "project_name": settings.app_name,
            "positions": positions,
            "trade_error_message": trade_error_message,
            "unrealized_pnl_summary": unrealized_pnl_summary,
        },
    )


@router.post("/buy")
def buy_trade(
    stock_no: str | None = Form(None),
    stock_name: str | None = Form(None),
    buy_price: str | None = Form(None),
    buy_quantity: str | None = Form(None),
    trade_time: str | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
):
    base_params = {
        "stock_no": stock_no or "",
        "start_date": start_date or "",
        "end_date": end_date or "",
    }
    try:
        create_buy_trade(
            stock_no or "",
            stock_name or "",
            buy_price or "",
            buy_quantity or "",
            trade_time or "",
        )
        query = urlencode({**base_params, "trade_message": "模擬買進成功，交易紀錄已保存。"})
        return RedirectResponse(
            url=f"/stocks/search?{query}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except (InvalidTradeInputError, InsufficientFundsError) as exc:
        query = urlencode({**base_params, "trade_error_message": str(exc)})
        return RedirectResponse(
            url=f"/stocks/search?{query}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/sell")
def sell_trade(
    stock_no: str | None = Form(None),
    stock_name: str | None = Form(None),
    sell_price: str | None = Form(None),
    sell_quantity: str | None = Form(None),
    trade_time: str | None = Form(None),
):
    try:
        create_sell_trade(
            stock_no or "",
            stock_name or "",
            sell_price or "",
            sell_quantity or "",
            trade_time or "",
        )
        return RedirectResponse(
            url="/trades/portfolio",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except (InvalidTradeInputError, InsufficientHoldingsError) as exc:
        query = urlencode({"trade_error_message": str(exc)})
        return RedirectResponse(
            url=f"/trades/portfolio?{query}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
