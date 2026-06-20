import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app import database
from app.database import init_database
from app.main import app
from app.services.trade_service import (
    InsufficientFundsError,
    InvalidTradeInputError,
    create_buy_trade,
    get_virtual_cash_summary,
)


class TradeTests(unittest.TestCase):
    def setUp(self) -> None:
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        os.unlink(self.db_path)
        self.original_db_path = database.settings.watchlist_db_path
        database.settings.watchlist_db_path = self.db_path
        init_database(self.db_path)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        database.settings.watchlist_db_path = self.original_db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_buy_trade_success(self) -> None:
        trade = create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        summary = get_virtual_cash_summary(self.db_path)

        self.assertEqual(trade.stock_no, "2330")
        self.assertEqual(trade.stock_name, "台積電")
        self.assertEqual(trade.price, "800.00")
        self.assertEqual(trade.quantity, 100)
        self.assertEqual(trade.total_amount, "80,000.00")
        self.assertEqual(summary.used_cash, "80,000.00")
        self.assertEqual(summary.available_cash, "920,000.00")

    def test_create_buy_trade_insufficient_funds(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            create_buy_trade("2330", "台積電", "2000", "1000", "2024-05-31T09:00", self.db_path)

    def test_create_buy_trade_invalid_missing_fields(self) -> None:
        with self.assertRaises(InvalidTradeInputError):
            create_buy_trade("", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

    def test_create_buy_trade_invalid_price(self) -> None:
        with self.assertRaises(InvalidTradeInputError):
            create_buy_trade("2330", "台積電", "-1", "100", "2024-05-31T09:00", self.db_path)

    def test_create_buy_trade_invalid_quantity(self) -> None:
        with self.assertRaises(InvalidTradeInputError):
            create_buy_trade("2330", "台積電", "800", "0", "2024-05-31T09:00", self.db_path)

    def test_buy_trade_route_success(self) -> None:
        response = self.client.post(
            "/trades/buy",
            data={
                "stock_no": "2330",
                "stock_name": "台積電",
                "buy_price": "800",
                "buy_quantity": "100",
                "trade_time": "2024-05-31T09:00",
                "start_date": "2024-05-01",
                "end_date": "2024-05-31",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("/stocks/search?", response.headers["location"])
        self.assertIn("trade_message=", response.headers["location"])

    def test_buy_trade_route_invalid_input(self) -> None:
        response = self.client.post(
            "/trades/buy",
            data={
                "stock_no": "2330",
                "stock_name": "台積電",
                "buy_price": "",
                "buy_quantity": "100",
                "trade_time": "2024-05-31T09:00",
                "start_date": "2024-05-01",
                "end_date": "2024-05-31",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("trade_error_message=", response.headers["location"])

    def test_buy_trade_route_insufficient_funds(self) -> None:
        response = self.client.post(
            "/trades/buy",
            data={
                "stock_no": "2330",
                "stock_name": "台積電",
                "buy_price": "5000",
                "buy_quantity": "1000",
                "trade_time": "2024-05-31T09:00",
                "start_date": "2024-05-01",
                "end_date": "2024-05-31",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("trade_error_message=", response.headers["location"])
