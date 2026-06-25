from urllib.parse import urlencode

from fastapi import APIRouter, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, get_settings
from app.services.auth_service import get_current_username, require_login
from app.services.trade_service import (
    InsufficientHoldingsError,
    InsufficientFundsError,
    InvalidTradeInputError,
    create_buy_trade,
    create_sell_trade,
    get_portfolio_overview,
    get_portfolio_summary,
    get_realized_pnl_summary,
    get_virtual_cash_summary,
    list_trades,
)


router = APIRouter(prefix="/trades")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
settings = get_settings()


@router.get(
    "",
    response_class=HTMLResponse,
    tags=["Trade Pages"],
    summary="交易紀錄頁",
    description="回傳交易紀錄 HTML，顯示 BUY / SELL 紀錄、已實現損益與虛擬資金摘要。",
)
def trades_page(request: Request):
    redirect_response = require_login(request)
    if redirect_response is not None:
        return redirect_response
    return templates.TemplateResponse(
        request=request,
        name="trades.html",
        context={
            "project_name": settings.app_name,
            "realized_pnl_summary": get_realized_pnl_summary(),
            "trades": list_trades(),
            "virtual_cash_summary": get_virtual_cash_summary(),
            "current_username": get_current_username(request),
            "single_user_scope_notice": "目前登入版只提供頁面保護，交易與持股資料仍是單使用者視角。",
        },
    )


@router.get(
    "/portfolio",
    response_class=HTMLResponse,
    tags=["Trade Pages"],
    summary="持股與投資組合頁",
    description="回傳持股總覽 HTML，顯示持股、未實現損益與投資組合摘要。",
)
def portfolio_page(
    request: Request,
    trade_error_message: str = Query(""),
):
    redirect_response = require_login(request)
    if redirect_response is not None:
        return redirect_response
    positions, unrealized_pnl_summary = get_portfolio_overview()
    portfolio_summary = get_portfolio_summary()
    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context={
            "project_name": settings.app_name,
            "positions": positions,
            "portfolio_summary": portfolio_summary,
            "trade_error_message": trade_error_message,
            "unrealized_pnl_summary": unrealized_pnl_summary,
            "current_username": get_current_username(request),
            "single_user_scope_notice": "目前登入版只提供頁面保護，交易與持股資料仍是單使用者視角。",
        },
    )


@router.post(
    "/buy",
    tags=["Trade Pages"],
    summary="提交模擬買進表單",
    description="處理股票結果頁的 BUY 表單，成功或失敗後會導回 HTML 頁面。此端點為瀏覽器表單動作，不是 JSON API。",
)
def buy_trade(
    request: Request,
    stock_no: str | None = Form(None),
    stock_name: str | None = Form(None),
    buy_price: str | None = Form(None),
    buy_quantity: str | None = Form(None),
    trade_time: str | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
):
    redirect_response = require_login(request, next_path="/")
    if redirect_response is not None:
        return redirect_response
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


@router.post(
    "/sell",
    tags=["Trade Pages"],
    summary="提交模擬賣出表單",
    description="處理持股頁的 SELL 表單，成功或失敗後會導回 HTML 頁面。此端點為瀏覽器表單動作，不是 JSON API。",
)
def sell_trade(
    request: Request,
    stock_no: str | None = Form(None),
    stock_name: str | None = Form(None),
    sell_price: str | None = Form(None),
    sell_quantity: str | None = Form(None),
    trade_time: str | None = Form(None),
):
    redirect_response = require_login(request, next_path="/trades/portfolio")
    if redirect_response is not None:
        return redirect_response
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
