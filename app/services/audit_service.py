from __future__ import annotations

from contextlib import closing
from datetime import datetime
import json

from app.database import get_connection, init_database
from app.models.audit import AuditLogRecord


def record_audit_event(
    *,
    event_type: str,
    username: str,
    target_type: str,
    target_value: str,
    status: str = "success",
    context: dict | None = None,
    user_id: int | None = None,
    db_path: str | None = None,
) -> None:
    init_database(db_path)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context_json = json.dumps(context or {}, ensure_ascii=False, sort_keys=True)
    with closing(get_connection(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO audit_logs (
                user_id,
                username,
                event_type,
                target_type,
                target_value,
                status,
                context,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                event_type,
                target_type,
                target_value,
                status,
                context_json,
                created_at,
            ),
        )
        connection.commit()


def list_audit_logs(db_path: str | None = None) -> list[AuditLogRecord]:
    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT event_type, username, created_at, target_type, target_value, status, context
            FROM audit_logs
            ORDER BY id ASC
            """
        ).fetchall()
    return [
        AuditLogRecord(
            event_type=row["event_type"],
            username=row["username"],
            created_at=row["created_at"],
            target_type=row["target_type"],
            target_value=row["target_value"],
            status=row["status"],
            context=row["context"],
        )
        for row in rows
    ]
