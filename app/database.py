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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_watchlist_table(connection)
        _ensure_trades_table(connection)
        connection.commit()


def _ensure_watchlist_table(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "watchlist"):
        connection.execute(
            """
            CREATE TABLE watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_no TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, stock_no),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        return

    columns = _get_column_names(connection, "watchlist")
    if "user_id" in columns:
        return

    fallback_user_id = _get_first_user_id(connection)
    connection.execute("ALTER TABLE watchlist RENAME TO watchlist_legacy")
    connection.execute(
        """
        CREATE TABLE watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_no TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, stock_no),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    if fallback_user_id is not None:
        connection.execute(
            """
            INSERT INTO watchlist (user_id, stock_no, stock_name, created_at)
            SELECT ?, stock_no, stock_name, created_at
            FROM watchlist_legacy
            """,
            (fallback_user_id,),
        )
    connection.execute("DROP TABLE watchlist_legacy")


def _ensure_trades_table(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "trades"):
        connection.execute(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_no TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                price TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                trade_time TEXT NOT NULL,
                total_amount TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        return

    columns = _get_column_names(connection, "trades")
    if "user_id" in columns:
        return

    fallback_user_id = _get_first_user_id(connection)
    connection.execute("ALTER TABLE trades RENAME TO trades_legacy")
    connection.execute(
        """
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_no TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            price TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            trade_time TEXT NOT NULL,
            total_amount TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    if fallback_user_id is not None:
        connection.execute(
            """
            INSERT INTO trades (
                user_id,
                stock_no,
                stock_name,
                trade_type,
                price,
                quantity,
                trade_time,
                total_amount
            )
            SELECT
                ?,
                stock_no,
                stock_name,
                trade_type,
                price,
                quantity,
                trade_time,
                total_amount
            FROM trades_legacy
            """,
            (fallback_user_id,),
        )
    connection.execute("DROP TABLE trades_legacy")


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _get_first_user_id(connection: sqlite3.Connection) -> int | None:
    row = connection.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1").fetchone()
    if row is None:
        return None
    return int(row["id"])
