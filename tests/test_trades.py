import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import database
from app.database import init_database
from app.main import app
from app.services.trade_service import (
    InsufficientHoldingsError,
    InsufficientFundsError,
    InvalidTradeInputError,
    create_buy_trade,
    create_sell_trade,
    get_portfolio_overview,
    get_portfolio_summary,
    get_realized_pnl_summary,
    get_virtual_cash_summary,
    list_positions,
    list_trades,
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

    def test_create_sell_trade_success(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        trade = create_sell_trade("2330", "台積電", "900", "40", "2024-06-01T09:00", self.db_path)
        positions = list_positions(self.db_path)
        summary = get_virtual_cash_summary(self.db_path)

        self.assertEqual(trade.trade_type, "SELL")
        self.assertEqual(trade.total_amount, "36,000.00")
        self.assertEqual(trade.realized_pnl, "4,000.00")
        self.assertEqual(positions[0].quantity, 60)
        self.assertEqual(positions[0].average_cost, "800.00")
        self.assertEqual(positions[0].total_buy_amount, "48,000.00")
        self.assertEqual(summary.used_cash, "44,000.00")
        self.assertEqual(summary.available_cash, "956,000.00")

    def test_create_sell_trade_insufficient_holdings(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        with self.assertRaises(InsufficientHoldingsError):
            create_sell_trade("2330", "台積電", "900", "200", "2024-06-01T09:00", self.db_path)

    def test_create_sell_trade_invalid_price(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        with self.assertRaises(InvalidTradeInputError):
            create_sell_trade("2330", "台積電", "0", "10", "2024-06-01T09:00", self.db_path)

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

    def test_sell_trade_route_success(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        response = self.client.post(
            "/trades/sell",
            data={
                "stock_no": "2330",
                "stock_name": "台積電",
                "sell_price": "900",
                "sell_quantity": "40",
                "trade_time": "2024-06-01T09:00",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/trades/portfolio")

    def test_sell_trade_route_insufficient_holdings(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        response = self.client.post(
            "/trades/sell",
            data={
                "stock_no": "2330",
                "stock_name": "台積電",
                "sell_price": "900",
                "sell_quantity": "200",
                "trade_time": "2024-06-01T09:00",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("trade_error_message=", response.headers["location"])

    def test_list_trades_sorted_newest_first(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_buy_trade("2317", "鴻海", "120", "200", "2024-06-01T10:00", self.db_path)

        trades = list_trades(self.db_path)

        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0].stock_no, "2317")
        self.assertEqual(trades[1].stock_no, "2330")

    def test_trades_page_shows_empty_message(self) -> None:
        response = self.client.get("/trades")

        self.assertEqual(response.status_code, 200)
        self.assertIn("目前尚無交易紀錄", response.text)

    def test_trades_page_shows_saved_trades(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_sell_trade("2330", "台積電", "900", "40", "2024-06-01T09:00", self.db_path)

        response = self.client.get("/trades")

        self.assertEqual(response.status_code, 200)
        self.assertIn("2330", response.text)
        self.assertIn("台積電", response.text)
        self.assertIn("BUY", response.text)
        self.assertIn("SELL", response.text)
        self.assertIn("800.00", response.text)
        self.assertIn("80,000.00", response.text)
        self.assertIn("4,000.00", response.text)

    def test_list_positions_weighted_average_cost(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_buy_trade("2330", "台積電", "1000", "50", "2024-06-01T09:00", self.db_path)

        positions = list_positions(self.db_path)

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].stock_no, "2330")
        self.assertEqual(positions[0].quantity, 150)
        self.assertEqual(positions[0].average_cost, "866.67")
        self.assertEqual(positions[0].total_buy_amount, "130,000.00")

    def test_list_positions_multiple_stocks(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_buy_trade("2317", "鴻海", "120", "200", "2024-06-01T10:00", self.db_path)

        positions = list_positions(self.db_path)

        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[0].stock_no, "2317")
        self.assertEqual(positions[1].stock_no, "2330")

    def test_portfolio_page_shows_empty_message(self) -> None:
        response = self.client.get("/trades/portfolio")

        self.assertEqual(response.status_code, 200)
        self.assertIn("目前尚無持股資料", response.text)
        self.assertIn("初始虛擬資金", response.text)
        self.assertIn("1,000,000.00", response.text)
        self.assertIn("Portfolio Summary", response.text)
        self.assertIn("現金面", response.text)
        self.assertIn("部位面", response.text)
        self.assertIn("損益面", response.text)

    def test_portfolio_page_shows_positions(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        with patch("app.services.trade_service.get_latest_close_price", return_value="850.00"):
            response = self.client.get("/trades/portfolio")

        self.assertEqual(response.status_code, 200)
        self.assertIn("2330", response.text)
        self.assertIn("台積電", response.text)
        self.assertIn("100", response.text)
        self.assertIn("800.00", response.text)
        self.assertIn("80,000.00", response.text)
        self.assertIn("850.00", response.text)
        self.assertIn("85,000.00", response.text)
        self.assertIn("5,000.00", response.text)
        self.assertIn("920,000.00", response.text)
        self.assertIn("1,005,000.00", response.text)
        self.assertIn("總資產估值", response.text)
        self.assertIn("可用資金 + 已知持股市值", response.text)

    def test_portfolio_page_missing_price_shows_clear_fallback(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        with patch("app.services.trade_service.get_latest_close_price", return_value=None):
            response = self.client.get("/trades/portfolio")

        self.assertEqual(response.status_code, 200)
        self.assertIn("暫時無法取得最近收盤價", response.text)
        self.assertIn("總資產估值與未實現損益僅納入已知市值部分", response.text)

    def test_portfolio_updates_after_sell(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_sell_trade("2330", "台積電", "900", "40", "2024-06-01T09:00", self.db_path)

        positions = list_positions(self.db_path)

        self.assertEqual(positions[0].quantity, 60)
        self.assertEqual(positions[0].average_cost, "800.00")

    def test_realized_pnl_single_sell(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_sell_trade("2330", "台積電", "900", "40", "2024-06-01T09:00", self.db_path)

        trades = list_trades(self.db_path)
        summary = get_realized_pnl_summary(self.db_path)

        self.assertEqual(trades[0].trade_type, "SELL")
        self.assertEqual(trades[0].realized_pnl, "4,000.00")
        self.assertEqual(summary.total_realized_pnl, "4,000.00")

    def test_realized_pnl_weighted_average_after_multiple_buys(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_buy_trade("2330", "台積電", "1000", "50", "2024-06-01T09:00", self.db_path)
        sell = create_sell_trade("2330", "台積電", "900", "60", "2024-06-02T09:00", self.db_path)

        self.assertEqual(sell.realized_pnl, "2,000.00")

    def test_realized_pnl_accumulates_multiple_sells(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_sell_trade("2330", "台積電", "900", "40", "2024-06-01T09:00", self.db_path)
        create_sell_trade("2330", "台積電", "700", "20", "2024-06-02T09:00", self.db_path)

        summary = get_realized_pnl_summary(self.db_path)
        trades = list_trades(self.db_path)

        self.assertEqual(summary.total_realized_pnl, "2,000.00")
        sell_trades = [trade for trade in trades if trade.trade_type == "SELL"]
        self.assertEqual(sell_trades[0].realized_pnl, "-2,000.00")
        self.assertEqual(sell_trades[1].realized_pnl, "4,000.00")

    def test_realized_pnl_not_counted_for_buy_only(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        trades = list_trades(self.db_path)
        summary = get_realized_pnl_summary(self.db_path)

        self.assertEqual(trades[0].realized_pnl, "-")
        self.assertEqual(summary.total_realized_pnl, "0.00")

    def test_portfolio_overview_single_position_unrealized_pnl(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        with patch("app.services.trade_service.get_latest_close_price", return_value="850.00"):
            positions, summary = get_portfolio_overview(self.db_path)

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].current_price, "850.00")
        self.assertEqual(positions[0].market_value, "85,000.00")
        self.assertEqual(positions[0].unrealized_pnl, "5,000.00")
        self.assertEqual(summary.total_unrealized_pnl, "5,000.00")
        self.assertEqual(summary.priced_position_count, 1)
        self.assertEqual(summary.missing_price_count, 0)

    def test_portfolio_overview_multiple_stocks_unrealized_summary(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_buy_trade("2317", "鴻海", "120", "200", "2024-06-01T10:00", self.db_path)

        with patch(
            "app.services.trade_service.get_latest_close_price",
            side_effect=lambda stock_no: {"2330": "850.00", "2317": "118.00"}[stock_no],
        ):
            positions, summary = get_portfolio_overview(self.db_path)

        self.assertEqual(len(positions), 2)
        self.assertEqual(summary.total_unrealized_pnl, "4,600.00")
        self.assertEqual(summary.priced_position_count, 2)
        self.assertEqual(summary.missing_price_count, 0)
        self.assertEqual(positions[0].unrealized_pnl, "-400.00")
        self.assertEqual(positions[1].unrealized_pnl, "5,000.00")

    def test_portfolio_overview_handles_missing_price(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        with patch("app.services.trade_service.get_latest_close_price", return_value=None):
            positions, summary = get_portfolio_overview(self.db_path)

        self.assertEqual(positions[0].current_price, "-")
        self.assertEqual(positions[0].market_value, "-")
        self.assertEqual(positions[0].unrealized_pnl, "-")
        self.assertIn("最近收盤價暫時無法取得", positions[0].price_note)
        self.assertEqual(summary.total_unrealized_pnl, "0.00")
        self.assertEqual(summary.priced_position_count, 0)
        self.assertEqual(summary.missing_price_count, 1)

    def test_portfolio_summary_with_positions(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)
        create_sell_trade("2330", "台積電", "900", "40", "2024-06-01T09:00", self.db_path)

        with patch("app.services.trade_service.get_latest_close_price", return_value="850.00"):
            summary = get_portfolio_summary(self.db_path)

        self.assertEqual(summary.initial_cash, "1,000,000.00")
        self.assertEqual(summary.available_cash, "956,000.00")
        self.assertEqual(summary.used_cash, "44,000.00")
        self.assertEqual(summary.holdings_market_value, "51,000.00")
        self.assertEqual(summary.total_realized_pnl, "4,000.00")
        self.assertEqual(summary.total_unrealized_pnl, "3,000.00")
        self.assertEqual(summary.total_asset_estimate, "1,007,000.00")
        self.assertEqual(summary.missing_price_count, 0)

    def test_portfolio_summary_without_positions(self) -> None:
        summary = get_portfolio_summary(self.db_path)

        self.assertEqual(summary.initial_cash, "1,000,000.00")
        self.assertEqual(summary.available_cash, "1,000,000.00")
        self.assertEqual(summary.used_cash, "0.00")
        self.assertEqual(summary.holdings_market_value, "0.00")
        self.assertEqual(summary.total_realized_pnl, "0.00")
        self.assertEqual(summary.total_unrealized_pnl, "0.00")
        self.assertEqual(summary.total_asset_estimate, "1,000,000.00")
        self.assertEqual(summary.missing_price_count, 0)

    def test_portfolio_summary_handles_missing_price(self) -> None:
        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", self.db_path)

        with patch("app.services.trade_service.get_latest_close_price", return_value=None):
            summary = get_portfolio_summary(self.db_path)

        self.assertEqual(summary.available_cash, "920,000.00")
        self.assertEqual(summary.used_cash, "80,000.00")
        self.assertEqual(summary.holdings_market_value, "0.00")
        self.assertEqual(summary.total_unrealized_pnl, "0.00")
        self.assertEqual(summary.total_asset_estimate, "920,000.00")
        self.assertEqual(summary.missing_price_count, 1)
