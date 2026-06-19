import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.stock import StockLookupResult, StockPriceRow
from app.services.stock_service import ExternalServiceError, StockNotFoundError, fetch_stock_detail


class StockSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_success(self, mock_fetch) -> None:
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
                ),
                StockPriceRow(
                    trade_date="2024-05-02",
                    open_price="789.00",
                    high_price="789.00",
                    low_price="772.00",
                    close_price="772.00",
                    volume="47,536,363",
                )
            ],
        )

        response = self.client.get("/stocks/search", params={"stock_no": "2330"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("台積電", response.text)
        self.assertIn("2024-05-31", response.text)
        self.assertIn("查詢區間", response.text)
        self.assertIn("資料筆數", response.text)
        self.assertIn("顯示順序", response.text)
        self.assertIn("成交量（股）", response.text)
        self.assertIn("收盤價走勢圖", response.text)
        self.assertIn("aria-label=\"收盤價走勢圖\"", response.text)

    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_success_with_insufficient_rows_shows_chart_fallback(self, mock_fetch) -> None:
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
                )
            ],
        )

        response = self.client.get("/stocks/search", params={"stock_no": "2330"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("資料筆數不足，暫時無法繪製收盤價走勢圖", response.text)

    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_not_found_message(self, mock_fetch) -> None:
        mock_fetch.side_effect = StockNotFoundError(
            "查無資料，請確認股票代號是否存在，或該固定查詢區間內是否有成交資料。"
        )

        response = self.client.get("/stocks/search", params={"stock_no": "9999"})

        self.assertEqual(response.status_code, 404)
        self.assertIn("固定查詢區間內是否有成交資料", response.text)

    @patch("app.services.stock_service.requests.get")
    def test_fetch_stock_detail_twse_not_found_message(self, mock_get) -> None:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "stat": "很抱歉，沒有符合條件的資料!"
        }
        mock_get.return_value = mock_response

        with self.assertRaises(StockNotFoundError) as context:
            fetch_stock_detail("9999")

        self.assertIn("固定查詢區間內是否有成交資料", str(context.exception))

    def test_search_stock_invalid_code(self) -> None:
        response = self.client.get("/stocks/search", params={"stock_no": "abcd"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("股票代號格式錯誤", response.text)

    def test_search_stock_invalid_code_with_short_length(self) -> None:
        response = self.client.get("/stocks/search", params={"stock_no": "233"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("股票代號格式錯誤", response.text)

    def test_search_stock_invalid_code_with_long_length(self) -> None:
        response = self.client.get("/stocks/search", params={"stock_no": "1234567"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("股票代號格式錯誤", response.text)

    @patch("app.routers.stocks.fetch_stock_detail")
    def test_search_stock_external_service_error(self, mock_fetch) -> None:
        mock_fetch.side_effect = ExternalServiceError("股票資料來源暫時無法使用，請稍後再試。")

        response = self.client.get("/stocks/search", params={"stock_no": "2330"})

        self.assertEqual(response.status_code, 502)
        self.assertIn("股票資料來源暫時無法使用", response.text)


if __name__ == "__main__":
    unittest.main()
