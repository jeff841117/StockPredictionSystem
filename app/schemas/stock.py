from pydantic import BaseModel, Field


class StockPriceRow(BaseModel):
    trade_date: str = Field(description="成交日期，格式為 `YYYY-MM-DD`。")
    open_price: str = Field(description="開盤價。")
    high_price: str = Field(description="最高價。")
    low_price: str = Field(description="最低價。")
    close_price: str = Field(description="收盤價。")
    volume: str = Field(description="成交量。")
    ma5: str = Field(default="-", description="5 日移動平均；資料不足時為 `-`。")
    ma20: str = Field(default="-", description="20 日移動平均；資料不足時為 `-`。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "trade_date": "2024-05-31",
                "open_price": "838.00",
                "high_price": "846.00",
                "low_price": "821.00",
                "close_price": "821.00",
                "volume": "90,177,283",
                "ma5": "850.00",
                "ma20": "833.85",
            }
        }
    }


class ClosePriceChartPoint(BaseModel):
    trade_date: str = Field(description="成交日期，格式為 `YYYY-MM-DD`。")
    close_price: float = Field(description="供圖表使用的數值型收盤價。")
    close_price_label: str = Field(description="原始格式化後的收盤價標籤。")


class ClosePriceChart(BaseModel):
    points: list[ClosePriceChartPoint] = Field(description="圖表點位資料。")
    close_price_svg_path: str = Field(description="收盤價折線 SVG path。")
    ma5_svg_path: str = Field(default="", description="MA5 折線 SVG path；若資料不足則為空字串。")
    ma20_svg_path: str = Field(default="", description="MA20 折線 SVG path；若資料不足則為空字串。")
    min_price_label: str = Field(description="圖表最小價格標籤。")
    max_price_label: str = Field(description="圖表最大價格標籤。")
    start_date: str = Field(description="圖表起始日期。")
    end_date: str = Field(description="圖表結束日期。")


class StockLookupResult(BaseModel):
    stock_no: str = Field(description="台股代號。")
    stock_name: str = Field(description="股票名稱。")
    source_name: str = Field(description="資料來源名稱。")
    interval_start: str = Field(description="實際查詢起始日期。")
    interval_end: str = Field(description="實際查詢結束日期。")
    rows: list[StockPriceRow] = Field(description="查詢區間內的歷史價格資料，預設依日期新到舊排序。")

    model_config = {
        "json_schema_extra": {
            "example": {
                "stock_no": "2330",
                "stock_name": "台積電",
                "source_name": "TWSE 每日成交資訊",
                "interval_start": "2024-05-01",
                "interval_end": "2024-05-31",
                "rows": [
                    {
                        "trade_date": "2024-05-31",
                        "open_price": "838.00",
                        "high_price": "846.00",
                        "low_price": "821.00",
                        "close_price": "821.00",
                        "volume": "90,177,283",
                        "ma5": "850.00",
                        "ma20": "833.85",
                    }
                ],
            }
        }
    }


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


class HomeScreenerItem(BaseModel):
    stock_no: str
    stock_name: str
    interval_start: str
    interval_end: str
    latest_close: str
    interval_change: str
    interval_change_percent: str
    latest_ma5: str
    latest_ma20: str
    ma_status: str
