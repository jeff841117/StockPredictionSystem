from contextlib import closing
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.config import get_settings
from app.database import get_connection, init_database
from app.models.trade import PositionSummary, RealizedPnlSummary, TradeRecord, VirtualCashSummary


settings = get_settings()


class TradeServiceError(Exception):
    """Base error for trade operations."""


class InvalidTradeInputError(TradeServiceError):
    """Raised when trade input is missing or malformed."""


class InsufficientFundsError(TradeServiceError):
    """Raised when virtual cash is not enough for the buy order."""


class InsufficientHoldingsError(TradeServiceError):
    """Raised when holdings are not enough for the sell order."""


def get_virtual_cash_summary(db_path: str | None = None) -> VirtualCashSummary:
    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        row = connection.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN trade_type = 'BUY' THEN total_amount ELSE 0 END), 0) AS buy_total,
                COALESCE(SUM(CASE WHEN trade_type = 'SELL' THEN total_amount ELSE 0 END), 0) AS sell_total
            FROM trades
            """
        ).fetchone()
    used_cash = Decimal(str(row["buy_total"])) - Decimal(str(row["sell_total"]))
    initial_cash = settings.initial_virtual_cash
    available_cash = initial_cash - used_cash
    return VirtualCashSummary(
        initial_cash=_format_money(initial_cash),
        used_cash=_format_money(used_cash),
        available_cash=_format_money(available_cash),
    )


def list_trades(db_path: str | None = None) -> list[TradeRecord]:
    _, trade_records, _ = _build_trade_ledger(db_path)
    return list(reversed(trade_records))


def list_positions(db_path: str | None = None) -> list[PositionSummary]:
    raw_positions, _, _ = _build_trade_ledger(db_path)
    positions: list[PositionSummary] = []
    for stock_no in sorted(raw_positions.keys()):
        state = raw_positions[stock_no]
        quantity = int(state["quantity"])
        if quantity <= 0:
            continue
        cost_basis = Decimal(str(state["cost_basis"]))
        average_cost = cost_basis / Decimal(quantity)
        positions.append(
            PositionSummary(
                stock_no=stock_no,
                stock_name=str(state["stock_name"]),
                quantity=quantity,
                average_cost=_format_money(average_cost),
                total_buy_amount=_format_money(cost_basis),
            )
        )
    return positions


def get_realized_pnl_summary(db_path: str | None = None) -> RealizedPnlSummary:
    _, _, total_realized_pnl = _build_trade_ledger(db_path)
    return RealizedPnlSummary(total_realized_pnl=_format_money(total_realized_pnl))


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


def create_sell_trade(
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
        raise InvalidTradeInputError("模擬賣出失敗，缺少必要欄位。")

    try:
        price = Decimal(price_text)
    except InvalidOperation as exc:
        raise InvalidTradeInputError("賣出價格格式錯誤，請輸入大於 0 的數值。") from exc
    if price <= 0:
        raise InvalidTradeInputError("賣出價格格式錯誤，請輸入大於 0 的數值。")

    try:
        quantity = int(quantity_text)
    except ValueError as exc:
        raise InvalidTradeInputError("賣出股數格式錯誤，請輸入大於 0 的整數。") from exc
    if quantity <= 0:
        raise InvalidTradeInputError("賣出股數格式錯誤，請輸入大於 0 的整數。")

    try:
        trade_time = datetime.fromisoformat(trade_time_text)
    except ValueError as exc:
        raise InvalidTradeInputError("賣出時間格式錯誤，請重新輸入。") from exc

    holdings_lookup = {position.stock_no: position for position in list_positions(db_path)}
    position = holdings_lookup.get(normalized_stock_no)
    if position is None or quantity > position.quantity:
        raise InsufficientHoldingsError("目前持股不足，無法完成此次賣出。")

    raw_positions, _, _ = _build_trade_ledger(db_path)
    state = raw_positions.get(normalized_stock_no)
    if state is None:
        raise InsufficientHoldingsError("目前持股不足，無法完成此次賣出。")
    current_quantity = int(state["quantity"])
    cost_basis = Decimal(str(state["cost_basis"]))
    average_cost = cost_basis / Decimal(current_quantity)
    total_amount = price * quantity
    realized_pnl = total_amount - (average_cost * quantity)
    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        cursor = connection.execute(
            """
            INSERT INTO trades (stock_no, stock_name, trade_type, price, quantity, trade_time, total_amount)
            VALUES (?, ?, 'SELL', ?, ?, ?, ?)
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
        trade_type="SELL",
        price=_format_money(price),
        quantity=quantity,
        trade_time=trade_time.strftime("%Y-%m-%d %H:%M:%S"),
        total_amount=_format_money(total_amount),
        realized_pnl=_format_money(realized_pnl),
    )


def _format_money(amount: Decimal) -> str:
    return f"{amount:,.2f}"


def _format_storage_amount(amount: Decimal) -> str:
    return f"{amount:.2f}"


def _build_trade_ledger(
    db_path: str | None = None,
) -> tuple[dict[str, dict[str, Decimal | int | str]], list[TradeRecord], Decimal]:
    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                stock_no,
                stock_name,
                trade_type,
                quantity,
                price,
                total_amount,
                trade_time
            FROM trades
            ORDER BY trade_time ASC, id ASC
            """
        ).fetchall()

    raw_positions: dict[str, dict[str, Decimal | int | str]] = {}
    trade_records: list[TradeRecord] = []
    total_realized_pnl = Decimal("0")

    for row in rows:
        stock_no = row["stock_no"]
        if stock_no not in raw_positions:
            raw_positions[stock_no] = {
                "stock_name": row["stock_name"],
                "quantity": 0,
                "cost_basis": Decimal("0"),
            }

        state = raw_positions[stock_no]
        quantity = int(row["quantity"])
        price = Decimal(str(row["price"]))
        total_amount = Decimal(str(row["total_amount"]))
        cost_basis = Decimal(str(state["cost_basis"]))
        current_quantity = int(state["quantity"])
        realized_pnl = None

        if row["trade_type"] == "BUY":
            state["quantity"] = current_quantity + quantity
            state["cost_basis"] = cost_basis + total_amount
        else:
            if current_quantity > 0:
                average_cost = cost_basis / Decimal(current_quantity)
                realized_pnl = total_amount - (average_cost * quantity)
                remaining_quantity = current_quantity - quantity
                remaining_cost_basis = cost_basis - (average_cost * quantity)
                state["quantity"] = max(remaining_quantity, 0)
                state["cost_basis"] = remaining_cost_basis if remaining_quantity > 0 else Decimal("0")
                total_realized_pnl += realized_pnl

        trade_records.append(
            TradeRecord(
                id=row["id"],
                stock_no=stock_no,
                stock_name=row["stock_name"],
                trade_type=row["trade_type"],
                price=_format_money(price),
                quantity=quantity,
                trade_time=row["trade_time"],
                total_amount=_format_money(total_amount),
                realized_pnl=_format_money(realized_pnl) if realized_pnl is not None else "-",
            )
        )

    return raw_positions, trade_records, total_realized_pnl
