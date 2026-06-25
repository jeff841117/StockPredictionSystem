import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app import database
from app.database import init_database
from app.main import app
from app.services.auth_service import get_user_by_username


class AuthTests(unittest.TestCase):
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

    def test_register_success_stores_hashed_password(self) -> None:
        response = self.client.post(
            "/auth/register",
            data={"username": "demo_user", "password": "secret123"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        user = get_user_by_username("demo_user", self.db_path)
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, "secret123")
        self.assertIn("$", user.password_hash)

    def test_login_success_and_logout(self) -> None:
        self.client.post("/auth/register", data={"username": "demo_user", "password": "secret123"})

        login_response = self.client.post(
            "/auth/login",
            data={"username": "demo_user", "password": "secret123", "next_path": "/watchlist"},
            follow_redirects=False,
        )

        self.assertEqual(login_response.status_code, 303)
        self.assertEqual(login_response.headers["location"], "/watchlist")

        protected_response = self.client.get("/watchlist")
        self.assertEqual(protected_response.status_code, 200)
        self.assertIn("收藏清單", protected_response.text)

        logout_response = self.client.get("/auth/logout", follow_redirects=False)
        self.assertEqual(logout_response.status_code, 303)

        redirected_response = self.client.get("/watchlist", follow_redirects=False)
        self.assertEqual(redirected_response.status_code, 303)
        location = redirected_response.headers["location"]
        self.assertTrue(location.startswith("/auth/login?"))
        next_value = parse_qs(urlparse(location).query)["next"][0]
        self.assertEqual(next_value, "/watchlist")

    def test_login_failure(self) -> None:
        self.client.post("/auth/register", data={"username": "demo_user", "password": "secret123"})

        response = self.client.post(
            "/auth/login",
            data={"username": "demo_user", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("登入失敗，帳號或密碼錯誤", response.text)

    def test_protected_page_redirects_when_not_logged_in(self) -> None:
        response = self.client.get("/trades", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        next_value = parse_qs(urlparse(response.headers["location"]).query)["next"][0]
        self.assertEqual(next_value, "/trades")

    def test_protected_page_redirect_preserves_full_query_string(self) -> None:
        response = self.client.get("/trades/portfolio?trade_error_message=持股不足&tab=summary", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        location = response.headers["location"]
        self.assertTrue(location.startswith("/auth/login?"))
        parsed = urlparse(location)
        next_value = parse_qs(parsed.query)["next"][0]
        next_parsed = urlparse(next_value)
        self.assertEqual(next_parsed.path, "/trades/portfolio")
        nested_query = parse_qs(next_parsed.query)
        self.assertEqual(nested_query["trade_error_message"][0], "持股不足")
        self.assertEqual(nested_query["tab"][0], "summary")

    def test_login_redirect_restores_full_query_string(self) -> None:
        self.client.post("/auth/register", data={"username": "demo_user", "password": "secret123"})

        redirect_response = self.client.get(
            "/trades/portfolio?trade_error_message=持股不足&tab=summary",
            follow_redirects=False,
        )
        next_value = parse_qs(urlparse(redirect_response.headers["location"]).query)["next"][0]

        login_response = self.client.post(
            "/auth/login",
            data={"username": "demo_user", "password": "secret123", "next_path": next_value},
            follow_redirects=False,
        )

        self.assertEqual(login_response.status_code, 303)
        redirected_target = urlparse(login_response.headers["location"])
        self.assertEqual(redirected_target.path, "/trades/portfolio")
        redirected_query = parse_qs(redirected_target.query)
        self.assertEqual(redirected_query["trade_error_message"][0], "持股不足")
        self.assertEqual(redirected_query["tab"][0], "summary")


if __name__ == "__main__":
    unittest.main()
