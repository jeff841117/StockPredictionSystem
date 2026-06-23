import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.stock import StockLookupResult, StockPriceRow
from app.services.stock_service import (
    ExternalServiceError,
    InvalidDateRangeError,
    StockNotFoundError,
    build_research_summary,
    build_close_price_chart,
    fetch_stock_detail,
)


class StockSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("app.routers.stocks.get_position_for_stock")
    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_success(self, mock_fetch, mock_position) -> None:
        mock_position.return_value = None
        mock_fetch.return_value = StockLookupResult(
            stock_no="2330",
            stock_name="台積電",
            source_name="TWSE 每日成交資訊",
            interval_start="2024-05-01",
            interval_end="2024-05-31",
            rows=[
                StockPriceRow(
                    trade_date="2024-05-31",
                    open_price="838.00",
                    high_price="846.00",
                    low_price="821.00",
                    close_price="821.00",
                    volume="90,177,283",
                    ma5="850.00",
                    ma20="833.85",
                ),
                StockPriceRow(
                    trade_date="2024-05-30",
                    open_price="841.00",
                    high_price="848.00",
                    low_price="838.00",
                    close_price="838.00",
                    volume="42,535,118",
                    ma5="850.60",
                    ma20="837.10",
                ),
            ],
        )

        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "2330", "start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("台積電", response.text)
        self.assertIn("2024-05-01 至 2024-05-31", response.text)
        self.assertIn("MA5", response.text)
        self.assertIn("MA20", response.text)
        self.assertIn("aria-label=\"收盤價走勢圖\"", response.text)
        self.assertIn("850.00", response.text)
        self.assertIn("Research Summary", response.text)
        self.assertIn("區間最高 / 最低", response.text)
        self.assertIn("目前未持有", response.text)

    @patch("app.routers.stocks.get_position_for_stock")
    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_success_with_insufficient_rows_shows_chart_fallback(self, mock_fetch, mock_position) -> None:
        mock_position.return_value = None
        mock_fetch.return_value = StockLookupResult(
            stock_no="2330",
            stock_name="台積電",
            source_name="TWSE 每日成交資訊",
            interval_start="2024-05-31",
            interval_end="2024-05-31",
            rows=[
                StockPriceRow(
                    trade_date="2024-05-31",
                    open_price="838.00",
                    high_price="846.00",
                    low_price="821.00",
                    close_price="821.00",
                    volume="90,177,283",
                )
            ],
        )

        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "2330", "start_date": "2024-05-31", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("資料筆數不足，暫時無法繪製收盤價走勢圖", response.text)

    @patch("app.routers.stocks.get_position_for_stock")
    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_research_summary_shows_holding_status(self, mock_fetch, mock_position) -> None:
        mock_position.return_value = Mock(quantity=1000, average_cost="800.00")
        mock_fetch.return_value = StockLookupResult(
            stock_no="2330",
            stock_name="台積電",
            source_name="TWSE 每日成交資訊",
            interval_start="2024-05-01",
            interval_end="2024-05-31",
            rows=[
                StockPriceRow(
                    trade_date="2024-05-31",
                    open_price="838.00",
                    high_price="846.00",
                    low_price="821.00",
                    close_price="821.00",
                    volume="90,177,283",
                    ma5="850.00",
                    ma20="833.85",
                ),
                StockPriceRow(
                    trade_date="2024-05-01",
                    open_price="790.00",
                    high_price="812.00",
                    low_price="780.00",
                    close_price="800.00",
                    volume="42,535,118",
                    ma5="-",
                    ma20="-",
                ),
            ],
        )

        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "2330", "start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("目前持有 1000 股", response.text)
        self.assertIn("平均成本 800.00", response.text)
        self.assertIn("目前價格高於平均成本", response.text)

    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_not_found_message(self, mock_fetch) -> None:
        mock_fetch.side_effect = StockNotFoundError(
            "查無資料，請確認股票代號是否存在，或該查詢區間內是否有成交資料。"
        )

        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "9999", "start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("查詢區間內是否有成交資料", response.text)

    def test_search_stock_invalid_date_order(self) -> None:
        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "2330", "start_date": "2024-06-01", "end_date": "2024-05-01"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("開始日期不可晚於結束日期", response.text)

    def test_search_stock_invalid_date_format(self) -> None:
        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "2330", "start_date": "2024/05/01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("日期格式錯誤", response.text)

    def test_search_stock_missing_date(self) -> None:
        response = self.client.get("/stocks/search", params={"stock_no": "2330", "start_date": "2024-05-01"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("請輸入開始日期與結束日期", response.text)

    @patch("app.services.stock_service.requests.get")
    def test_fetch_stock_detail_twse_not_found_message(self, mock_get) -> None:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"stat": "很抱歉，沒有符合條件的資料!"}
        mock_get.return_value = mock_response

        with self.assertRaises(StockNotFoundError) as context:
            fetch_stock_detail("9999", "2024-05-01", "2024-05-31")

        self.assertIn("查詢區間內是否有成交資料", str(context.exception))

    @patch("app.services.stock_service.requests.get")
    def test_fetch_stock_detail_cross_month_query(self, mock_get) -> None:
        may_response = Mock()
        may_response.raise_for_status.return_value = None
        may_response.json.return_value = {
            "stat": "OK",
            "title": "113年05月 2330 台積電 各日成交資訊",
            "data": [
                ["113/05/30", "1,000", "1", "100.00", "101.00", "99.00", "100.00", "0.00", "1", ""],
                ["113/05/31", "1,000", "1", "101.00", "102.00", "100.00", "101.00", "0.00", "1", ""],
            ],
        }
        june_response = Mock()
        june_response.raise_for_status.return_value = None
        june_response.json.return_value = {
            "stat": "OK",
            "title": "113年06月 2330 台積電 各日成交資訊",
            "data": [
                ["113/06/03", "1,000", "1", "102.00", "103.00", "101.00", "102.00", "0.00", "1", ""],
                ["113/06/04", "1,000", "1", "103.00", "104.00", "102.00", "103.00", "0.00", "1", ""],
            ],
        }
        mock_get.side_effect = [may_response, june_response]

        result = fetch_stock_detail("2330", "2024-05-30", "2024-06-04")

        self.assertEqual(result.interval_start, "2024-05-30")
        self.assertEqual(result.interval_end, "2024-06-04")
        self.assertEqual(result.rows[0].trade_date, "2024-06-04")
        self.assertEqual(result.rows[-1].trade_date, "2024-05-30")
        self.assertEqual(len(result.rows), 4)

    def test_fetch_stock_detail_adds_moving_averages(self) -> None:
        result = fetch_stock_detail("2330", "2024-05-01", "2024-05-31")

        self.assertEqual(result.rows[0].trade_date, "2024-05-31")
        self.assertEqual(result.rows[0].ma5, "850.00")
        self.assertEqual(result.rows[0].ma20, "833.85")
        self.assertEqual(result.rows[-1].ma5, "-")
        self.assertEqual(result.rows[-1].ma20, "-")

    def test_build_close_price_chart_includes_ma_paths(self) -> None:
        result = StockLookupResult(
            stock_no="2330",
            stock_name="台積電",
            source_name="TWSE 每日成交資訊",
            interval_start="2024-05-02",
            interval_end="2024-05-06",
            rows=[
                StockPriceRow(
                    trade_date="2024-05-06",
                    open_price="10.00",
                    high_price="10.00",
                    low_price="10.00",
                    close_price="10.00",
                    volume="1",
                    ma5="8.00",
                    ma20="-",
                ),
                StockPriceRow(
                    trade_date="2024-05-05",
                    open_price="9.00",
                    high_price="9.00",
                    low_price="9.00",
                    close_price="9.00",
                    volume="1",
                    ma5="7.50",
                    ma20="-",
                ),
                StockPriceRow(
                    trade_date="2024-05-04",
                    open_price="8.00",
                    high_price="8.00",
                    low_price="8.00",
                    close_price="8.00",
                    volume="1",
                    ma5="7.00",
                    ma20="-",
                ),
                StockPriceRow(
                    trade_date="2024-05-03",
                    open_price="7.00",
                    high_price="7.00",
                    low_price="7.00",
                    close_price="7.00",
                    volume="1",
                    ma5="6.50",
                    ma20="-",
                ),
                StockPriceRow(
                    trade_date="2024-05-02",
                    open_price="6.00",
                    high_price="6.00",
                    low_price="6.00",
                    close_price="6.00",
                    volume="1",
                    ma5="6.00",
                    ma20="-",
                ),
            ],
        )

        chart = build_close_price_chart(result)

        self.assertIsNotNone(chart)
        self.assertTrue(bool(chart.close_price_svg_path))
        self.assertTrue(bool(chart.ma5_svg_path))
        self.assertEqual(chart.ma20_svg_path, "")

    def test_build_research_summary_matches_result_data(self) -> None:
        result = StockLookupResult(
            stock_no="2330",
            stock_name="台積電",
            source_name="TWSE 每日成交資訊",
            interval_start="2024-05-01",
            interval_end="2024-05-31",
            rows=[
                StockPriceRow(
                    trade_date="2024-05-31",
                    open_price="838.00",
                    high_price="846.00",
                    low_price="821.00",
                    close_price="821.00",
                    volume="90,177,283",
                    ma5="850.00",
                    ma20="833.85",
                ),
                StockPriceRow(
                    trade_date="2024-05-01",
                    open_price="790.00",
                    high_price="812.00",
                    low_price="780.00",
                    close_price="800.00",
                    volume="42,535,118",
                    ma5="-",
                    ma20="-",
                ),
            ],
        )

        summary = build_research_summary(result, holding_quantity=1000, holding_average_cost="800.00")

        self.assertEqual(summary.latest_close, "821.00")
        self.assertEqual(summary.interval_change, "+21.00")
        self.assertEqual(summary.interval_change_percent, "+2.62%")
        self.assertEqual(summary.period_high, "846.00")
        self.assertEqual(summary.period_low, "780.00")
        self.assertEqual(summary.latest_ma5, "850.00")
        self.assertEqual(summary.latest_ma20, "833.85")
        self.assertTrue(summary.holding.is_holding)
        self.assertEqual(summary.holding.quantity, 1000)
        self.assertEqual(summary.holding.average_cost, "800.00")
        self.assertEqual(summary.holding.price_vs_average_cost, "目前價格高於平均成本")

    def test_search_stock_invalid_code(self) -> None:
        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "abcd", "start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("股票代號格式錯誤", response.text)

    def test_search_stock_invalid_code_with_short_length(self) -> None:
        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "233", "start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("股票代號格式錯誤", response.text)

    def test_search_stock_invalid_code_with_long_length(self) -> None:
        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "1234567", "start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("股票代號格式錯誤", response.text)

    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_external_service_error(self, mock_fetch) -> None:
        mock_fetch.side_effect = ExternalServiceError("股票資料來源暫時無法使用，請稍後再試。")

        response = self.client.get(
            "/stocks/search",
            params={"stock_no": "2330", "start_date": "2024-05-01", "end_date": "2024-05-31"},
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("股票資料來源暫時無法使用", response.text)


if __name__ == "__main__":
    unittest.main()
