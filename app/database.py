from contextlib import closing
from pathlib import Path
import sqlite3

from app.config import get_settings


settings = get_settings()
SCHEMA_VERSION_KEY = "schema_version"
LEGACY_SCHEMA_VERSION = 1
CURRENT_SCHEMA_VERSION = 2


class DatabaseMigrationError(RuntimeError):
    """Raised when the minimal SQLite migration cannot safely proceed."""


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    target_path = Path(db_path or settings.watchlist_db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_database(db_path: str | None = None) -> None:
    with closing(get_connection(db_path)) as connection:
        _ensure_schema_meta_table(connection)
        current_version = _detect_schema_version(connection)
        if current_version == 0:
            _create_current_schema(connection)
            _set_schema_version(connection, CURRENT_SCHEMA_VERSION)
        elif current_version < CURRENT_SCHEMA_VERSION:
            _apply_migrations(connection, current_version)
        connection.commit()


def get_schema_version(db_path: str | None = None) -> int:
    with closing(get_connection(db_path)) as connection:
        _ensure_schema_meta_table(connection)
        return _detect_schema_version(connection)


def _apply_migrations(connection: sqlite3.Connection, current_version: int) -> None:
    next_version = current_version
    if next_version < CURRENT_SCHEMA_VERSION:
        _migrate_to_v2(connection)
        next_version = CURRENT_SCHEMA_VERSION
    _set_schema_version(connection, next_version)


def _migrate_to_v2(connection: sqlite3.Connection) -> None:
    _create_users_table(connection)
    _ensure_watchlist_table(connection)
    _ensure_trades_table(connection)


def _create_current_schema(connection: sqlite3.Connection) -> None:
    _create_users_table(connection)
    _create_watchlist_table(connection)
    _create_trades_table(connection)


def _create_users_table(connection: sqlite3.Connection) -> None:
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


def _create_watchlist_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlist (
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


def _create_trades_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
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


def _ensure_watchlist_table(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "watchlist"):
        _create_watchlist_table(connection)
        return

    columns = _get_column_names(connection, "watchlist")
    if "user_id" in columns:
        return

    fallback_user_id = _resolve_legacy_fallback_user_id(connection, "watchlist")
    connection.execute("ALTER TABLE watchlist RENAME TO watchlist_legacy")
    _create_watchlist_table(connection)
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
        _create_trades_table(connection)
        return

    columns = _get_column_names(connection, "trades")
    if "user_id" in columns:
        return

    fallback_user_id = _resolve_legacy_fallback_user_id(connection, "trades")
    connection.execute("ALTER TABLE trades RENAME TO trades_legacy")
    _create_trades_table(connection)
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


def _ensure_schema_meta_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )


def _detect_schema_version(connection: sqlite3.Connection) -> int:
    explicit_version = _read_schema_version(connection)
    if explicit_version is not None:
        return explicit_version

    if not any(_table_exists(connection, name) for name in ("users", "watchlist", "trades")):
        return 0

    has_user_scoped_watchlist = _table_exists(connection, "watchlist") and "user_id" in _get_column_names(connection, "watchlist")
    has_user_scoped_trades = _table_exists(connection, "trades") and "user_id" in _get_column_names(connection, "trades")
    if _table_exists(connection, "users") and has_user_scoped_watchlist and has_user_scoped_trades:
        return CURRENT_SCHEMA_VERSION

    return LEGACY_SCHEMA_VERSION


def _read_schema_version(connection: sqlite3.Connection) -> int | None:
    row = connection.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        (SCHEMA_VERSION_KEY,),
    ).fetchone()
    if row is None:
        return None
    return int(row["value"])


def _set_schema_version(connection: sqlite3.Connection, version: int) -> None:
    connection.execute(
        """
        INSERT INTO schema_meta (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (SCHEMA_VERSION_KEY, str(version)),
    )


def _resolve_legacy_fallback_user_id(connection: sqlite3.Connection, table_name: str) -> int | None:
    legacy_row_count = connection.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}").fetchone()["row_count"]
    fallback_user_id = _get_first_user_id(connection)
    if legacy_row_count > 0 and fallback_user_id is None:
        raise DatabaseMigrationError(
            f"偵測到舊版 {table_name} 資料，但目前 users 為空，無法安全完成最小 migration。"
        )
    return fallback_user_id


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
