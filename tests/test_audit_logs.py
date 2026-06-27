import json
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app import database
from app.database import init_database
from app.main import app
from app.services.audit_service import list_audit_logs
from app.services.auth_service import get_user_by_username
from app.services.trade_service import create_buy_trade


class AuditLogTests(unittest.TestCase):
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

    def test_register_login_and_logout_write_audit_logs(self) -> None:
        self.client.post("/auth/register", data={"username": "demo_user", "password": "secret123"})
        self.client.post("/auth/login", data={"username": "demo_user", "password": "secret123", "next_path": "/watchlist"})
        self.client.get("/auth/logout")

        logs = list_audit_logs(self.db_path)

        self.assertEqual([log.event_type for log in logs], ["AUTH_REGISTER", "AUTH_LOGIN", "AUTH_LOGOUT"])
        self.assertEqual(logs[0].username, "demo_user")
        self.assertEqual(logs[0].status, "success")
        self.assertEqual(logs[1].target_type, "session")
        self.assertEqual(logs[1].target_value, "/watchlist")
        self.assertEqual(logs[2].target_value, "/")

    def test_watchlist_add_and_remove_write_audit_logs(self) -> None:
        self.client.post("/auth/register", data={"username": "demo_user", "password": "secret123"})
        self.client.post("/auth/login", data={"username": "demo_user", "password": "secret123"})

        self.client.post("/watchlist/add", data={"stock_no": "2330", "stock_name": "台積電"})
        self.client.post("/watchlist/remove", data={"stock_no": "2330"})

        logs = [log for log in list_audit_logs(self.db_path) if log.event_type.startswith("WATCHLIST_")]

        self.assertEqual([log.event_type for log in logs], ["WATCHLIST_ADD", "WATCHLIST_REMOVE"])
        self.assertEqual(logs[0].target_value, "2330")
        self.assertEqual(json.loads(logs[0].context)["stock_name"], "台積電")

    def test_buy_and_sell_write_audit_logs(self) -> None:
        self.client.post("/auth/register", data={"username": "demo_user", "password": "secret123"})
        user = get_user_by_username("demo_user", self.db_path)
        assert user is not None

        create_buy_trade("2330", "台積電", "800", "100", "2024-05-31T09:00", user.id, self.db_path)

        self.client.post("/auth/login", data={"username": "demo_user", "password": "secret123"})
        self.client.post(
            "/trades/sell",
            data={
                "stock_no": "2330",
                "stock_name": "台積電",
                "sell_price": "900",
                "sell_quantity": "40",
                "trade_time": "2024-06-01T09:00",
            },
        )

        logs = [log for log in list_audit_logs(self.db_path) if log.event_type.startswith("TRADE_")]

        self.assertEqual([log.event_type for log in logs], ["TRADE_BUY", "TRADE_SELL"])
        self.assertEqual(logs[0].username, "demo_user")
        self.assertEqual(json.loads(logs[0].context)["quantity"], 100)
        self.assertEqual(json.loads(logs[1].context)["quantity"], 40)


if __name__ == "__main__":
    unittest.main()
