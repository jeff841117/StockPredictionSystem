from contextlib import closing
from datetime import datetime
import sqlite3

from app.database import get_connection, init_database
from app.models.watchlist import WatchlistItem
from app.services.audit_service import record_audit_event
from app.services.auth_service import get_user_by_id


class WatchlistServiceError(Exception):
    """Base error for watchlist operations."""


class InvalidWatchlistItemError(WatchlistServiceError):
    """Raised when required watchlist data is missing or invalid."""


class DuplicateWatchlistItemError(WatchlistServiceError):
    """Raised when a stock is already in the watchlist."""


class WatchlistItemNotFoundError(WatchlistServiceError):
    """Raised when the stock is not found in the watchlist."""


def add_to_watchlist(stock_no: str, stock_name: str, user_id: int, db_path: str | None = None) -> WatchlistItem:
    normalized_stock_no = stock_no.strip()
    normalized_stock_name = stock_name.strip()
    if not normalized_stock_no or not normalized_stock_name:
        raise InvalidWatchlistItemError("加入收藏失敗，缺少股票代號或股票名稱。")

    init_database(db_path)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with closing(get_connection(db_path)) as connection:
            connection.execute(
                "INSERT INTO watchlist (user_id, stock_no, stock_name, created_at) VALUES (?, ?, ?, ?)",
                (user_id, normalized_stock_no, normalized_stock_name, created_at),
            )
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise DuplicateWatchlistItemError("該股票已在收藏清單中，無法重複加入。") from exc

    user = get_user_by_id(user_id, db_path)
    if user is not None:
        record_audit_event(
            event_type="WATCHLIST_ADD",
            username=user.username,
            user_id=user.id,
            target_type="stock",
            target_value=normalized_stock_no,
            context={"stock_name": normalized_stock_name},
            db_path=db_path,
        )

    return WatchlistItem(
        stock_no=normalized_stock_no,
        stock_name=normalized_stock_name,
        created_at=created_at,
    )


def list_watchlist(user_id: int | None, db_path: str | None = None) -> list[WatchlistItem]:
    if user_id is None:
        return []

    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT stock_no, stock_name, created_at
            FROM watchlist
            WHERE user_id = ?
            ORDER BY created_at DESC, stock_no DESC
            """,
            (user_id,),
        ).fetchall()
    return [
        WatchlistItem(
            stock_no=row["stock_no"],
            stock_name=row["stock_name"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def remove_from_watchlist(stock_no: str, user_id: int, db_path: str | None = None) -> None:
    normalized_stock_no = stock_no.strip()
    if not normalized_stock_no:
        raise InvalidWatchlistItemError("移除收藏失敗，缺少股票代號。")

    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        cursor = connection.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND stock_no = ?",
            (user_id, normalized_stock_no),
        )
        connection.commit()
    if cursor.rowcount == 0:
        raise WatchlistItemNotFoundError("找不到要移除的收藏股票。")

    user = get_user_by_id(user_id, db_path)
    if user is not None:
        record_audit_event(
            event_type="WATCHLIST_REMOVE",
            username=user.username,
            user_id=user.id,
            target_type="stock",
            target_value=normalized_stock_no,
            db_path=db_path,
        )
