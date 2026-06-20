from contextlib import closing
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.config import get_settings
from app.database import get_connection, init_database
from app.models.trade import TradeRecord, VirtualCashSummary


settings = get_settings()


class TradeServiceError(Exception):
    """Base error for trade operations."""


class InvalidTradeInputError(TradeServiceError):
    """Raised when trade input is missing or malformed."""


class InsufficientFundsError(TradeServiceError):
    """Raised when virtual cash is not enough for the buy order."""


def get_virtual_cash_summary(db_path: str | None = None) -> VirtualCashSummary:
    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        row = connection.execute("SELECT COALESCE(SUM(total_amount), '0') AS used_cash FROM trades WHERE trade_type = 'BUY'").fetchone()
    used_cash = Decimal(str(row["used_cash"]))
    initial_cash = settings.initial_virtual_cash
    available_cash = initial_cash - used_cash
    return VirtualCashSummary(
        initial_cash=_format_money(initial_cash),
        used_cash=_format_money(used_cash),
        available_cash=_format_money(available_cash),
    )


def list_trades(db_path: str | None = None) -> list[TradeRecord]:
    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT id, stock_no, stock_name, trade_type, price, quantity, trade_time, total_amount
            FROM trades
            ORDER BY trade_time DESC, id DESC
            """
        ).fetchall()

    return [
        TradeRecord(
            id=row["id"],
            stock_no=row["stock_no"],
            stock_name=row["stock_name"],
            trade_type=row["trade_type"],
            price=_format_money(Decimal(str(row["price"]))),
            quantity=row["quantity"],
            trade_time=row["trade_time"],
            total_amount=_format_money(Decimal(str(row["total_amount"]))),
        )
        for row in rows
    ]


def create_buy_trade(
    stock_no: str,
    stock_name: str,
    price_text: str,
    quantity_text: str,
    trade_time_text: str,
    db_path: str | None = None,
) -> TradeRecord:
    normalized_stock_no = stock_no.strip()
    normalized_stock_name = stock_name.strip()
    if not normalized_stock_no or not normalized_stock_name or not price_text.strip() or not quantity_text.strip() or not trade_time_text.strip():
        raise InvalidTradeInputError("模擬買進失敗，缺少必要欄位。")

    try:
        price = Decimal(price_text)
    except InvalidOperation as exc:
        raise InvalidTradeInputError("買進價格格式錯誤，請輸入大於 0 的數值。") from exc
    if price <= 0:
        raise InvalidTradeInputError("買進價格格式錯誤，請輸入大於 0 的數值。")

    try:
        quantity = int(quantity_text)
    except ValueError as exc:
        raise InvalidTradeInputError("買進股數格式錯誤，請輸入大於 0 的整數。") from exc
    if quantity <= 0:
        raise InvalidTradeInputError("買進股數格式錯誤，請輸入大於 0 的整數。")

    try:
        trade_time = datetime.fromisoformat(trade_time_text)
    except ValueError as exc:
        raise InvalidTradeInputError("買進時間格式錯誤，請重新輸入。") from exc

    total_amount = price * quantity
    available_cash = Decimal(get_virtual_cash_summary(db_path).available_cash.replace(",", ""))
    if total_amount > available_cash:
        raise InsufficientFundsError("虛擬資金不足，無法完成此次買進。")

    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        cursor = connection.execute(
            """
            INSERT INTO trades (stock_no, stock_name, trade_type, price, quantity, trade_time, total_amount)
            VALUES (?, ?, 'BUY', ?, ?, ?, ?)
            """,
            (
                normalized_stock_no,
                normalized_stock_name,
                _format_storage_amount(price),
                quantity,
                trade_time.strftime("%Y-%m-%d %H:%M:%S"),
                _format_storage_amount(total_amount),
            ),
        )
        connection.commit()

    return TradeRecord(
        id=cursor.lastrowid,
        stock_no=normalized_stock_no,
        stock_name=normalized_stock_name,
        trade_type="BUY",
        price=_format_money(price),
        quantity=quantity,
        trade_time=trade_time.strftime("%Y-%m-%d %H:%M:%S"),
        total_amount=_format_money(total_amount),
    )


def _format_money(amount: Decimal) -> str:
    return f"{amount:,.2f}"


def _format_storage_amount(amount: Decimal) -> str:
    return f"{amount:.2f}"
