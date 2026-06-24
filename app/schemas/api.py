from pydantic import BaseModel, Field


class ApiValidationIssue(BaseModel):
    field: str
    message: str


class ApiErrorResponse(BaseModel):
    error_code: str = Field(description="固定錯誤代碼，用於區分錯誤類型。")
    message: str = Field(description="給 API 使用者閱讀的錯誤訊息。")
    validation_errors: list[ApiValidationIssue] = Field(
        default_factory=list,
        description="輸入驗證錯誤明細；非驗證錯誤時為空陣列。",
    )


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
