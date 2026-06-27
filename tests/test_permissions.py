import os
import tempfile
import unittest
from contextlib import closing

from fastapi.testclient import TestClient

from app import database
from app.database import get_connection, init_database
from app.main import app


class PermissionTests(unittest.TestCase):
    def setUp(self) -> None:
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        os.unlink(self.db_path)
        self.original_db_path = database.settings.watchlist_db_path
        database.settings.watchlist_db_path = self.db_path
        init_database(self.db_path)
        self.client = TestClient(app)
        self.client.post("/auth/register", data={"username": "demo_user", "password": "secret123"})
        self.client.post("/auth/register", data={"username": "admin_user", "password": "secret123"})
        with closing(get_connection(self.db_path)) as connection:
            connection.execute("UPDATE users SET role = 'admin' WHERE username = 'admin_user'")
            connection.commit()

    def tearDown(self) -> None:
        self.client.close()
        database.settings.watchlist_db_path = self.original_db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_default_registered_user_role_is_user(self) -> None:
        with closing(get_connection(self.db_path)) as connection:
            row = connection.execute("SELECT role FROM users WHERE username = 'demo_user'").fetchone()
        self.assertEqual(row["role"], "user")

    def test_user_cannot_access_admin_page(self) -> None:
        self.client.post("/auth/login", data={"username": "demo_user", "password": "secret123"})

        response = self.client.get("/admin/audit-logs")

        self.assertEqual(response.status_code, 403)
        self.assertIn("權限不足", response.text)

    def test_admin_can_access_admin_page(self) -> None:
        self.client.post("/auth/login", data={"username": "admin_user", "password": "secret123"})

        response = self.client.get("/admin/audit-logs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Audit Logs", response.text)

    def test_admin_page_redirects_when_not_logged_in(self) -> None:
        response = self.client.get("/admin/audit-logs", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/auth/login?next=/admin/audit-logs")

    def test_user_cannot_access_admin_api(self) -> None:
        self.client.post("/auth/login", data={"username": "demo_user", "password": "secret123"})

        response = self.client.get("/api/admin/audit-logs")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "error_code": "FORBIDDEN",
                "message": "你目前沒有權限存取這個 API。",
                "validation_errors": [],
            },
        )

    def test_admin_can_access_admin_api(self) -> None:
        self.client.post("/auth/login", data={"username": "admin_user", "password": "secret123"})

        response = self.client.get("/api/admin/audit-logs")

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_admin_api_requires_login(self) -> None:
        response = self.client.get("/api/admin/audit-logs")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error_code"], "UNAUTHORIZED")


if __name__ == "__main__":
    unittest.main()
