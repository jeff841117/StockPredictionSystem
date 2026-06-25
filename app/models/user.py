from dataclasses import dataclass


@dataclass(frozen=True)
class UserRecord:
    id: int
    username: str
    password_hash: str
    created_at: str
