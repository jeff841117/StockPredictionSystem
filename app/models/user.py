from dataclasses import dataclass


@dataclass(frozen=True)
class UserRecord:
    id: int
    username: str
    role: str
    password_hash: str
    created_at: str
