from dataclasses import dataclass


@dataclass(slots=True)
class AuditLogRecord:
    event_type: str
    username: str
    created_at: str
    target_type: str
    target_value: str
    status: str
    context: str
