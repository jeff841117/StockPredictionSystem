from pydantic import BaseModel


class StockPriceRow(BaseModel):
    trade_date: str
    open_price: str
    high_price: str
    low_price: str
    close_price: str
    volume: str
    ma5: str = "-"
    ma20: str = "-"


class ClosePriceChartPoint(BaseModel):
    trade_date: str
    close_price: float
    close_price_label: str


class ClosePriceChart(BaseModel):
    points: list[ClosePriceChartPoint]
    close_price_svg_path: str
    ma5_svg_path: str = ""
    ma20_svg_path: str = ""
    min_price_label: str
    max_price_label: str
    start_date: str
    end_date: str


class StockLookupResult(BaseModel):
    stock_no: str
    stock_name: str
    source_name: str
    interval_start: str
    interval_end: str
    rows: list[StockPriceRow]


class ResearchHoldingSummary(BaseModel):
    is_holding: bool
    quantity: int
    average_cost: str
    price_vs_average_cost: str = "-"


class ResearchSummary(BaseModel):
    stock_no: str
    stock_name: str
    interval_start: str
    interval_end: str
    latest_close: str
    interval_change: str
    interval_change_percent: str
    period_high: str
    period_low: str
    latest_ma5: str
    latest_ma20: str
    holding: ResearchHoldingSummary
