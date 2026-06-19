from pydantic import BaseModel


class StockPriceRow(BaseModel):
    trade_date: str
    open_price: str
    high_price: str
    low_price: str
    close_price: str
    volume: str


class StockLookupResult(BaseModel):
    stock_no: str
    stock_name: str
    source_name: str
    interval_start: str
    interval_end: str
    rows: list[StockPriceRow]
