import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.stock import StockLookupResult, StockPriceRow
from app.services.stock_service import ExternalServiceError


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
        self.assertIn("2024-05-02", response.text)

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
