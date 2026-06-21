from dataclasses import dataclass


@dataclass(frozen=True)
class TradeRecord:
    id: int
    stock_no: str
    stock_name: str
    trade_type: str
    price: str
    quantity: int
    trade_time: str
    total_amount: str
    realized_pnl: str = "-"


@dataclass(frozen=True)
class VirtualCashSummary:
    initial_cash: str
    used_cash: str
    available_cash: str


@dataclass(frozen=True)
class PositionSummary:
    stock_no: str
    stock_name: str
    quantity: int
    average_cost: str
    total_buy_amount: str


@dataclass(frozen=True)
class RealizedPnlSummary:
    total_realized_pnl: str
