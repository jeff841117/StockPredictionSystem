from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str


class WatchlistItemResponse(BaseModel):
    stock_no: str
    stock_name: str
    created_at: str


class TradeRecordResponse(BaseModel):
    id: int
    stock_no: str
    stock_name: str
    trade_type: str
    price: str
    quantity: int
    trade_time: str
    total_amount: str
    realized_pnl: str


class VirtualCashSummaryResponse(BaseModel):
    initial_cash: str
    used_cash: str
    available_cash: str


class PositionSummaryResponse(BaseModel):
    stock_no: str
    stock_name: str
    quantity: int
    average_cost: str
    total_buy_amount: str
    current_price: str
    market_value: str
    unrealized_pnl: str
    price_note: str


class UnrealizedPnlSummaryResponse(BaseModel):
    total_unrealized_pnl: str
    priced_position_count: int
    missing_price_count: int


class PortfolioOverviewResponse(BaseModel):
    positions: list[PositionSummaryResponse]
    unrealized_summary: UnrealizedPnlSummaryResponse


class PortfolioSummaryResponse(BaseModel):
    initial_cash: str
    available_cash: str
    used_cash: str
    holdings_market_value: str
    total_realized_pnl: str
    total_unrealized_pnl: str
    total_asset_estimate: str
    missing_price_count: int
