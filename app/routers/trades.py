from urllib.parse import urlencode

from fastapi import APIRouter, Form, status
from fastapi.responses import RedirectResponse

from app.services.trade_service import (
    InsufficientFundsError,
    InvalidTradeInputError,
    create_buy_trade,
)


router = APIRouter(prefix="/trades", tags=["trades"])


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
