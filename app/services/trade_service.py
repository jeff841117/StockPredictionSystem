from contextlib import closing
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.config import get_settings
from app.database import get_connection, init_database
from app.models.trade import (
    PortfolioSummary,
    PositionSummary,
    RealizedPnlSummary,
    TradeRecord,
    UnrealizedPnlSummary,
    VirtualCashSummary,
)
from app.services.audit_service import record_audit_event
from app.services.auth_service import get_user_by_id
from app.services.stock_service import StockServiceError, get_latest_close_price


settings = get_settings()


class TradeServiceError(Exception):
    """Base error for trade operations."""


class InvalidTradeInputError(TradeServiceError):
    """Raised when trade input is missing or malformed."""


class InsufficientFundsError(TradeServiceError):
    """Raised when virtual cash is not enough for the buy order."""


class InsufficientHoldingsError(TradeServiceError):
    """Raised when holdings are not enough for the sell order."""


def get_virtual_cash_summary(user_id: int | None = None, db_path: str | None = None) -> VirtualCashSummary:
    if user_id is None:
        return _build_empty_cash_summary()

    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        row = connection.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN trade_type = 'BUY' THEN total_amount ELSE 0 END), 0) AS buy_total,
                COALESCE(SUM(CASE WHEN trade_type = 'SELL' THEN total_amount ELSE 0 END), 0) AS sell_total
            FROM trades
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    used_cash = Decimal(str(row["buy_total"])) - Decimal(str(row["sell_total"]))
    initial_cash = settings.initial_virtual_cash
    available_cash = initial_cash - used_cash
    return VirtualCashSummary(
        initial_cash=_format_money(initial_cash),
        used_cash=_format_money(used_cash),
        available_cash=_format_money(available_cash),
    )


def list_trades(user_id: int | None = None, db_path: str | None = None) -> list[TradeRecord]:
    _, trade_records, _ = _build_trade_ledger(user_id, db_path)
    return list(reversed(trade_records))


def list_positions(user_id: int | None = None, db_path: str | None = None) -> list[PositionSummary]:
    raw_positions, _, _ = _build_trade_ledger(user_id, db_path)
    return _build_position_summaries(raw_positions)


def get_position_for_stock(stock_no: str, user_id: int | None = None, db_path: str | None = None) -> PositionSummary | None:
    normalized_stock_no = stock_no.strip()
    for position in list_positions(user_id, db_path):
        if position.stock_no == normalized_stock_no:
            return position
    return None


def get_portfolio_overview(
    user_id: int | None = None,
    db_path: str | None = None,
) -> tuple[list[PositionSummary], UnrealizedPnlSummary]:
    raw_positions, _, _ = _build_trade_ledger(user_id, db_path)
    base_positions = _build_position_summaries(raw_positions)
    positions: list[PositionSummary] = []
    total_unrealized_pnl = Decimal("0")
    priced_position_count = 0
    missing_price_count = 0

    for position in base_positions:
        try:
            latest_close_price = get_latest_close_price(position.stock_no)
        except StockServiceError:
            latest_close_price = None

        if latest_close_price is None:
            missing_price_count += 1
            positions.append(
                PositionSummary(
                    stock_no=position.stock_no,
                    stock_name=position.stock_name,
                    quantity=position.quantity,
                    average_cost=position.average_cost,
                    total_buy_amount=position.total_buy_amount,
                    price_note="最近收盤價暫時無法取得，未納入未實現損益計算。",
                )
            )
            continue

        try:
            current_price = Decimal(latest_close_price)
        except InvalidOperation:
            missing_price_count += 1
            positions.append(
                PositionSummary(
                    stock_no=position.stock_no,
                    stock_name=position.stock_name,
                    quantity=position.quantity,
                    average_cost=position.average_cost,
                    total_buy_amount=position.total_buy_amount,
                    price_note="最近收盤價格式異常，未納入未實現損益計算。",
                )
            )
            continue

        cost_basis = Decimal(position.total_buy_amount.replace(",", ""))
        market_value = current_price * position.quantity
        unrealized_pnl = market_value - cost_basis
        total_unrealized_pnl += unrealized_pnl
        priced_position_count += 1
        positions.append(
            PositionSummary(
                stock_no=position.stock_no,
                stock_name=position.stock_name,
                quantity=position.quantity,
                average_cost=position.average_cost,
                total_buy_amount=position.total_buy_amount,
                current_price=_format_money(current_price),
                market_value=_format_money(market_value),
                unrealized_pnl=_format_money(unrealized_pnl),
            )
        )

    return positions, UnrealizedPnlSummary(
        total_unrealized_pnl=_format_money(total_unrealized_pnl),
        priced_position_count=priced_position_count,
        missing_price_count=missing_price_count,
    )


def get_portfolio_summary(user_id: int | None = None, db_path: str | None = None) -> PortfolioSummary:
    virtual_cash_summary = get_virtual_cash_summary(user_id, db_path)
    realized_pnl_summary = get_realized_pnl_summary(user_id, db_path)
    positions, unrealized_pnl_summary = get_portfolio_overview(user_id, db_path)

    holdings_market_value = Decimal("0")
    for position in positions:
        if position.market_value == "-":
            continue
        holdings_market_value += Decimal(position.market_value.replace(",", ""))

    available_cash = Decimal(virtual_cash_summary.available_cash.replace(",", ""))
    total_asset_estimate = available_cash + holdings_market_value

    return PortfolioSummary(
        initial_cash=virtual_cash_summary.initial_cash,
        available_cash=virtual_cash_summary.available_cash,
        used_cash=virtual_cash_summary.used_cash,
        holdings_market_value=_format_money(holdings_market_value),
        total_realized_pnl=realized_pnl_summary.total_realized_pnl,
        total_unrealized_pnl=unrealized_pnl_summary.total_unrealized_pnl,
        total_asset_estimate=_format_money(total_asset_estimate),
        missing_price_count=unrealized_pnl_summary.missing_price_count,
    )


def _build_position_summaries(raw_positions: dict[str, dict[str, Decimal | int | str]]) -> list[PositionSummary]:
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


def get_realized_pnl_summary(user_id: int | None = None, db_path: str | None = None) -> RealizedPnlSummary:
    _, _, total_realized_pnl = _build_trade_ledger(user_id, db_path)
    return RealizedPnlSummary(total_realized_pnl=_format_money(total_realized_pnl))


def create_buy_trade(
    stock_no: str,
    stock_name: str,
    price_text: str,
    quantity_text: str,
    trade_time_text: str,
    user_id: int,
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
    available_cash = Decimal(get_virtual_cash_summary(user_id, db_path).available_cash.replace(",", ""))
    if total_amount > available_cash:
        raise InsufficientFundsError("虛擬資金不足，無法完成此次買進。")

    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        cursor = connection.execute(
            """
            INSERT INTO trades (user_id, stock_no, stock_name, trade_type, price, quantity, trade_time, total_amount)
            VALUES (?, ?, ?, 'BUY', ?, ?, ?, ?)
            """,
            (
                user_id,
                normalized_stock_no,
                normalized_stock_name,
                _format_storage_amount(price),
                quantity,
                trade_time.strftime("%Y-%m-%d %H:%M:%S"),
                _format_storage_amount(total_amount),
            ),
        )
        connection.commit()

    user = get_user_by_id(user_id, db_path)
    if user is not None:
        record_audit_event(
            event_type="TRADE_BUY",
            username=user.username,
            user_id=user.id,
            target_type="stock",
            target_value=normalized_stock_no,
            context={
                "stock_name": normalized_stock_name,
                "price": _format_storage_amount(price),
                "quantity": quantity,
                "trade_time": trade_time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            db_path=db_path,
        )

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
    user_id: int,
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

    holdings_lookup = {position.stock_no: position for position in list_positions(user_id, db_path)}
    position = holdings_lookup.get(normalized_stock_no)
    if position is None or quantity > position.quantity:
        raise InsufficientHoldingsError("目前持股不足，無法完成此次賣出。")

    raw_positions, _, _ = _build_trade_ledger(user_id, db_path)
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
            INSERT INTO trades (user_id, stock_no, stock_name, trade_type, price, quantity, trade_time, total_amount)
            VALUES (?, ?, ?, 'SELL', ?, ?, ?, ?)
            """,
            (
                user_id,
                normalized_stock_no,
                normalized_stock_name,
                _format_storage_amount(price),
                quantity,
                trade_time.strftime("%Y-%m-%d %H:%M:%S"),
                _format_storage_amount(total_amount),
            ),
        )
        connection.commit()

    user = get_user_by_id(user_id, db_path)
    if user is not None:
        record_audit_event(
            event_type="TRADE_SELL",
            username=user.username,
            user_id=user.id,
            target_type="stock",
            target_value=normalized_stock_no,
            context={
                "stock_name": normalized_stock_name,
                "price": _format_storage_amount(price),
                "quantity": quantity,
                "trade_time": trade_time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            db_path=db_path,
        )

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


def _build_empty_cash_summary() -> VirtualCashSummary:
    initial_cash = settings.initial_virtual_cash
    return VirtualCashSummary(
        initial_cash=_format_money(initial_cash),
        used_cash=_format_money(Decimal("0")),
        available_cash=_format_money(initial_cash),
    )


def _format_money(amount: Decimal) -> str:
    return f"{amount:,.2f}"


def _format_storage_amount(amount: Decimal) -> str:
    return f"{amount:.2f}"


def _build_trade_ledger(
    user_id: int | None = None,
    db_path: str | None = None,
) -> tuple[dict[str, dict[str, Decimal | int | str]], list[TradeRecord], Decimal]:
    if user_id is None:
        return {}, [], Decimal("0")

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
            WHERE user_id = ?
            ORDER BY trade_time ASC, id ASC
            """,
            (user_id,),
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
