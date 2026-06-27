import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

from app.database import CURRENT_SCHEMA_VERSION, DatabaseMigrationError, get_connection, get_schema_version, init_database


class DatabaseMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        os.unlink(self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_database_creates_current_schema_for_empty_database(self) -> None:
        init_database(self.db_path)

        with closing(get_connection(self.db_path)) as connection:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            watchlist_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(watchlist)").fetchall()
            }
            trades_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(trades)").fetchall()
            }
            audit_logs_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(audit_logs)").fetchall()
            }

        self.assertIn("schema_meta", tables)
        self.assertIn("users", tables)
        self.assertIn("watchlist", tables)
        self.assertIn("trades", tables)
        self.assertIn("audit_logs", tables)
        self.assertIn("user_id", watchlist_columns)
        self.assertIn("user_id", trades_columns)
        self.assertIn("event_type", audit_logs_columns)
        self.assertIn("username", audit_logs_columns)
        self.assertEqual(get_schema_version(self.db_path), CURRENT_SCHEMA_VERSION)

    def test_init_database_upgrades_legacy_database_and_preserves_rows(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE watchlist (
                    stock_no TEXT PRIMARY KEY,
                    stock_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_no TEXT NOT NULL,
                    stock_name TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    price TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    trade_time TEXT NOT NULL,
                    total_amount TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                ("demo_user", "hashed", "2024-01-01 00:00:00"),
            )
            connection.execute(
                "INSERT INTO watchlist (stock_no, stock_name, created_at) VALUES (?, ?, ?)",
                ("2330", "台積電", "2024-05-01 10:00:00"),
            )
            connection.execute(
                """
                INSERT INTO trades (
                    stock_no, stock_name, trade_type, price, quantity, trade_time, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("2330", "台積電", "BUY", "800.00", 100, "2024-05-31 09:00:00", "80000.00"),
            )
            connection.commit()

        init_database(self.db_path)

        with closing(get_connection(self.db_path)) as connection:
            watchlist_row = connection.execute(
                "SELECT user_id, stock_no, stock_name FROM watchlist"
            ).fetchone()
            trade_row = connection.execute(
                "SELECT user_id, stock_no, trade_type FROM trades"
            ).fetchone()
            audit_log_count = connection.execute("SELECT COUNT(*) AS row_count FROM audit_logs").fetchone()["row_count"]
            legacy_tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE '%_legacy'"
                ).fetchall()
            }

        self.assertEqual(watchlist_row["user_id"], 1)
        self.assertEqual(watchlist_row["stock_no"], "2330")
        self.assertEqual(trade_row["user_id"], 1)
        self.assertEqual(trade_row["trade_type"], "BUY")
        self.assertEqual(audit_log_count, 0)
        self.assertFalse(legacy_tables)
        self.assertEqual(get_schema_version(self.db_path), CURRENT_SCHEMA_VERSION)

    def test_init_database_raises_for_legacy_data_without_users(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE watchlist (
                    stock_no TEXT PRIMARY KEY,
                    stock_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO watchlist (stock_no, stock_name, created_at) VALUES (?, ?, ?)",
                ("2330", "台積電", "2024-05-01 10:00:00"),
            )
            connection.commit()

        with self.assertRaises(DatabaseMigrationError):
            init_database(self.db_path)


if __name__ == "__main__":
    unittest.main()
