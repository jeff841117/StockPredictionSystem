import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app import database
from app.database import init_database
from app.main import app
from app.services.watchlist_service import (
    DuplicateWatchlistItemError,
    WatchlistItemNotFoundError,
    add_to_watchlist,
    list_watchlist,
    remove_from_watchlist,
)


class WatchlistTests(unittest.TestCase):
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

    def test_add_to_watchlist_success(self) -> None:
        item = add_to_watchlist("2330", "台積電", self.db_path)
        items = list_watchlist(self.db_path)

        self.assertEqual(item.stock_no, "2330")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].stock_name, "台積電")

    def test_add_to_watchlist_duplicate(self) -> None:
        add_to_watchlist("2330", "台積電", self.db_path)

        with self.assertRaises(DuplicateWatchlistItemError):
            add_to_watchlist("2330", "台積電", self.db_path)

    def test_remove_from_watchlist_success(self) -> None:
        add_to_watchlist("2330", "台積電", self.db_path)
        remove_from_watchlist("2330", self.db_path)

        self.assertEqual(list_watchlist(self.db_path), [])

    def test_remove_from_watchlist_not_found(self) -> None:
        with self.assertRaises(WatchlistItemNotFoundError):
            remove_from_watchlist("2330", self.db_path)

    def test_watchlist_page_shows_items(self) -> None:
        add_to_watchlist("2330", "台積電", self.db_path)

        response = self.client.get("/watchlist")

        self.assertEqual(response.status_code, 200)
        self.assertIn("2330", response.text)
        self.assertIn("台積電", response.text)

    def test_watchlist_add_route_success(self) -> None:
        response = self.client.post(
            "/watchlist/add",
            data={"stock_no": "2330", "stock_name": "台積電"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("已成功加入收藏清單", response.text)
        self.assertIn("2330", response.text)

    def test_watchlist_add_route_duplicate(self) -> None:
        add_to_watchlist("2330", "台積電", self.db_path)

        response = self.client.post(
            "/watchlist/add",
            data={"stock_no": "2330", "stock_name": "台積電"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("無法重複加入", response.text)

    def test_watchlist_add_route_missing_data(self) -> None:
        response = self.client.post("/watchlist/add", data={"stock_no": "", "stock_name": ""})

        self.assertEqual(response.status_code, 400)
        self.assertIn("缺少股票代號或股票名稱", response.text)

    def test_watchlist_remove_route_success(self) -> None:
        add_to_watchlist("2330", "台積電", self.db_path)

        response = self.client.post(
            "/watchlist/remove",
            data={"stock_no": "2330"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("已成功移除收藏股票", response.text)
        self.assertIn("目前尚無收藏股票", response.text)

    def test_watchlist_api_create_success(self) -> None:
        response = self.client.post(
            "/api/watchlist/items",
            json={"stock_no": "2330", "stock_name": "台積電"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["stock_no"], "2330")
        self.assertEqual(payload["stock_name"], "台積電")

    def test_watchlist_api_create_duplicate_returns_uniform_error_schema(self) -> None:
        add_to_watchlist("2330", "台積電", self.db_path)

        response = self.client.post(
            "/api/watchlist/items",
            json={"stock_no": "2330", "stock_name": "台積電"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {
                "error_code": "DUPLICATE_RESOURCE",
                "message": "該股票已在收藏清單中，無法重複加入。",
                "validation_errors": [],
            },
        )

    def test_watchlist_api_create_validation_error_returns_translated_message(self) -> None:
        response = self.client.post(
            "/api/watchlist/items",
            json={"stock_no": "2330"},
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["error_code"], "VALIDATION_ERROR")
        self.assertEqual(payload["message"], "API 請求參數驗證失敗，請確認必填欄位與格式。")
        self.assertEqual(payload["validation_errors"][0]["field"], "body.stock_name")
        self.assertEqual(payload["validation_errors"][0]["message"], "缺少必要欄位。")

    def test_watchlist_api_delete_not_found_returns_uniform_error_schema(self) -> None:
        response = self.client.delete("/api/watchlist/items/2330")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "error_code": "NOT_FOUND",
                "message": "找不到要移除的收藏股票。",
                "validation_errors": [],
            },
        )
