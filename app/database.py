from contextlib import closing
from pathlib import Path
import sqlite3

from app.config import get_settings


settings = get_settings()


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    target_path = Path(db_path or settings.watchlist_db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_database(db_path: str | None = None) -> None:
    with closing(get_connection(db_path)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                stock_no TEXT PRIMARY KEY,
                stock_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
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
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
