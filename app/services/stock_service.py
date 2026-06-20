import calendar
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import requests

from app.config import get_settings
from app.schemas.stock import ClosePriceChart, ClosePriceChartPoint, StockLookupResult, StockPriceRow


settings = get_settings()
STOCK_NO_PATTERN = re.compile(r"^\d{4,6}$")
NOT_FOUND_MESSAGE = "查無資料，請確認股票代號是否存在，或該查詢區間內是否有成交資料。"


class StockServiceError(Exception):
    """Base error for stock lookup failures."""


class InvalidStockCodeError(StockServiceError):
    """Raised when the stock number format is invalid."""


class InvalidDateRangeError(StockServiceError):
    """Raised when the date range input is invalid."""


class StockNotFoundError(StockServiceError):
    """Raised when the stock or data cannot be found."""


class ExternalServiceError(StockServiceError):
    """Raised when the external data source fails."""


def get_default_date_range() -> tuple[str, str]:
    return _month_bounds_from_token(settings.stock_query_date)


def get_default_interval_label() -> str:
    start, end = get_default_date_range()
    return f"{start} 至 {end}"


def build_close_price_chart(result: StockLookupResult) -> ClosePriceChart | None:
    chronological_rows = list(reversed(result.rows))
    points: list[ClosePriceChartPoint] = []
    ma5_points: list[ClosePriceChartPoint] = []
    ma20_points: list[ClosePriceChartPoint] = []

    for row in chronological_rows:
        close_price_value = float(row.close_price)
        points.append(
            ClosePriceChartPoint(
                trade_date=row.trade_date,
                close_price=close_price_value,
                close_price_label=row.close_price,
            )
        )
        if row.ma5 != "-":
            ma5_points.append(
                ClosePriceChartPoint(
                    trade_date=row.trade_date,
                    close_price=float(row.ma5),
                    close_price_label=row.ma5,
                )
            )
        if row.ma20 != "-":
            ma20_points.append(
                ClosePriceChartPoint(
                    trade_date=row.trade_date,
                    close_price=float(row.ma20),
                    close_price_label=row.ma20,
                )
            )

    if len(points) < 2:
        return None

    width = 640
    height = 240
    padding_x = 36
    padding_y = 24
    min_price = min(
        [point.close_price for point in points]
        + [point.close_price for point in ma5_points]
        + [point.close_price for point in ma20_points]
    )
    max_price = max(
        [point.close_price for point in points]
        + [point.close_price for point in ma5_points]
        + [point.close_price for point in ma20_points]
    )
    price_span = max(max_price - min_price, 1.0)
    usable_width = width - (padding_x * 2)
    usable_height = height - (padding_y * 2)
    total_points = len(points)

    return ClosePriceChart(
        points=points,
        close_price_svg_path=_build_svg_path(
            points,
            points,
            total_points,
            min_price,
            price_span,
            height,
            padding_x,
            padding_y,
            usable_width,
            usable_height,
        ),
        ma5_svg_path=_build_svg_path(
            ma5_points,
            points,
            total_points,
            min_price,
            price_span,
            height,
            padding_x,
            padding_y,
            usable_width,
            usable_height,
        ),
        ma20_svg_path=_build_svg_path(
            ma20_points,
            points,
            total_points,
            min_price,
            price_span,
            height,
            padding_x,
            padding_y,
            usable_width,
            usable_height,
        ),
        min_price_label=f"{min_price:.2f}",
        max_price_label=f"{max_price:.2f}",
        start_date=points[0].trade_date,
        end_date=points[-1].trade_date,
    )


def fetch_stock_detail(stock_no: str, start_date_text: str | None, end_date_text: str | None) -> StockLookupResult:
    normalized_stock_no = stock_no.strip()
    if not STOCK_NO_PATTERN.fullmatch(normalized_stock_no):
        raise InvalidStockCodeError("股票代號格式錯誤，請輸入 4 到 6 碼數字。")

    start_date, end_date = _parse_date_range(start_date_text, end_date_text)
    payloads = []
    rows: list[StockPriceRow] = []
    for month_start in _iterate_month_starts(start_date, end_date):
        payload = _fetch_month_payload(normalized_stock_no, month_start)
        if payload is None:
            continue
        payloads.append(payload)
        rows.extend(_parse_rows(payload.get("data", []), start_date, end_date))

    if not rows:
        raise StockNotFoundError(NOT_FOUND_MESSAGE)

    _apply_moving_averages(rows)
    stock_name = _extract_stock_name(payloads[0].get("title", ""), normalized_stock_no)
    return StockLookupResult(
        stock_no=normalized_stock_no,
        stock_name=stock_name,
        source_name="TWSE 每日成交資訊",
        interval_start=start_date.isoformat(),
        interval_end=end_date.isoformat(),
        rows=list(reversed(rows)),
    )


def _parse_date_range(start_date_text: str | None, end_date_text: str | None) -> tuple[date, date]:
    if not start_date_text or not end_date_text:
        raise InvalidDateRangeError("請輸入開始日期與結束日期。")
    try:
        start_date = date.fromisoformat(start_date_text)
        end_date = date.fromisoformat(end_date_text)
    except ValueError as exc:
        raise InvalidDateRangeError("日期格式錯誤，請使用 YYYY-MM-DD。") from exc

    if start_date > end_date:
        raise InvalidDateRangeError("開始日期不可晚於結束日期。")
    return start_date, end_date


def _fetch_month_payload(stock_no: str, month_start: date) -> dict | None:
    try:
        response = requests.get(
            settings.stock_query_source,
            params={
                "date": month_start.strftime("%Y%m%d"),
                "stockNo": stock_no,
                "response": "json",
            },
            headers={"User-Agent": "StockPredictionSystem/1.0"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        raise ExternalServiceError("股票資料來源暫時無法使用，請稍後再試。") from exc
    except requests.RequestException as exc:
        raise ExternalServiceError("無法連線到股票資料來源，請稍後再試。") from exc
    except ValueError as exc:
        raise ExternalServiceError("股票資料來源回傳格式異常，請稍後再試。") from exc

    stat = payload.get("stat")
    if stat == "OK":
        return payload
    if stat in {"很抱歉，沒有符合條件的資料!", "查詢日期大於今日，請重新查詢!"}:
        return None
    raise ExternalServiceError("股票資料來源回傳失敗，請稍後再試。")


def _parse_rows(raw_rows: list[list[str]], start_date: date, end_date: date) -> list[StockPriceRow]:
    rows: list[StockPriceRow] = []
    for row in raw_rows:
        if len(row) < 7:
            continue
        trade_date = _convert_roc_date(row[0])
        trade_date_obj = date.fromisoformat(trade_date)
        if trade_date_obj < start_date or trade_date_obj > end_date:
            continue
        rows.append(
            StockPriceRow(
                trade_date=trade_date,
                open_price=_normalize_price(row[3]),
                high_price=_normalize_price(row[4]),
                low_price=_normalize_price(row[5]),
                close_price=_normalize_price(row[6]),
                volume=_normalize_int(row[1]),
            )
        )
    return rows


def _apply_moving_averages(rows: list[StockPriceRow]) -> None:
    close_prices = [float(row.close_price) for row in rows]
    for index, row in enumerate(rows):
        row.ma5 = _format_average(close_prices, index, 5)
        row.ma20 = _format_average(close_prices, index, 20)


def _format_average(close_prices: list[float], index: int, window: int) -> str:
    if index + 1 < window:
        return "-"
    return f"{(sum(close_prices[index - window + 1 : index + 1]) / window):.2f}"


def _build_svg_path(
    line_points: list[ClosePriceChartPoint],
    axis_points: list[ClosePriceChartPoint],
    total_points: int,
    min_price: float,
    price_span: float,
    height: int,
    padding_x: int,
    padding_y: int,
    usable_width: int,
    usable_height: int,
) -> str:
    index_lookup = {point.trade_date: index for index, point in enumerate(axis_points)}
    coordinates: list[str] = []
    for point in line_points:
        index = index_lookup.get(point.trade_date)
        if index is None:
            continue
        x = padding_x if total_points == 1 else padding_x + (usable_width * index / (total_points - 1))
        normalized_price = (point.close_price - min_price) / price_span
        y = height - padding_y - (normalized_price * usable_height)
        coordinates.append(f"{x:.2f},{y:.2f}")
    return " ".join(coordinates)


def _convert_roc_date(raw_value: str) -> str:
    year_text, month_text, day_text = raw_value.split("/")
    return f"{int(year_text) + 1911:04d}-{int(month_text):02d}-{int(day_text):02d}"


def _normalize_price(raw_value: str) -> str:
    cleaned = raw_value.replace(",", "").strip()
    if cleaned in {"--", ""}:
        return "-"
    try:
        return f"{Decimal(cleaned):.2f}"
    except InvalidOperation:
        return cleaned


def _normalize_int(raw_value: str) -> str:
    cleaned = raw_value.replace(",", "").strip()
    if cleaned in {"--", ""}:
        return "-"
    return f"{int(cleaned):,}"


def _extract_stock_name(title: str, stock_no: str) -> str:
    match = re.search(rf"{re.escape(stock_no)}\s+(.+?)\s+各日成交資訊", title)
    if match:
        return match.group(1).strip()
    return "未知名稱"


def _month_bounds_from_token(month_token: str) -> tuple[str, str]:
    target_year = int(month_token[0:4])
    target_month = int(month_token[4:6])
    last_day = calendar.monthrange(target_year, target_month)[1]
    return (
        date(target_year, target_month, 1).isoformat(),
        date(target_year, target_month, last_day).isoformat(),
    )


def _iterate_month_starts(start_date: date, end_date: date) -> list[date]:
    months: list[date] = []
    current = date(start_date.year, start_date.month, 1)
    final = date(end_date.year, end_date.month, 1)
    while current <= final:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months
