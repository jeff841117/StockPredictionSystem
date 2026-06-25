from contextlib import closing
from datetime import datetime
import hashlib
import hmac
import os
import sqlite3
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse, Response

from app.database import get_connection, init_database
from app.models.user import UserRecord
from app.config import get_settings


class AuthServiceError(Exception):
    """Base error for auth operations."""


class InvalidRegistrationInputError(AuthServiceError):
    """Raised when registration input is missing or invalid."""


class DuplicateUserError(AuthServiceError):
    """Raised when the username already exists."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when login credentials are invalid."""


SESSION_USER_KEY = "auth_username"
AUTH_COOKIE_NAME = "auth_session"
settings = get_settings()


def register_user(username: str, password: str, db_path: str | None = None) -> UserRecord:
    normalized_username = username.strip()
    if not normalized_username:
        raise InvalidRegistrationInputError("註冊失敗，請輸入帳號。")
    if len(normalized_username) < 3:
        raise InvalidRegistrationInputError("註冊失敗，帳號至少需要 3 個字元。")
    if not password:
        raise InvalidRegistrationInputError("註冊失敗，請輸入密碼。")
    if len(password) < 6:
        raise InvalidRegistrationInputError("註冊失敗，密碼至少需要 6 個字元。")

    init_database(db_path)
    password_hash = _hash_password(password)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with closing(get_connection(db_path)) as connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (normalized_username, password_hash, created_at),
            )
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise DuplicateUserError("該帳號已存在，請改用其他帳號名稱。") from exc

    return UserRecord(
        id=cursor.lastrowid,
        username=normalized_username,
        password_hash=password_hash,
        created_at=created_at,
    )


def authenticate_user(username: str, password: str, db_path: str | None = None) -> UserRecord:
    normalized_username = username.strip()
    if not normalized_username or not password:
        raise InvalidCredentialsError("登入失敗，請輸入帳號與密碼。")

    user = get_user_by_username(normalized_username, db_path)
    if user is None or not _verify_password(password, user.password_hash):
        raise InvalidCredentialsError("登入失敗，帳號或密碼錯誤。")
    return user


def get_user_by_username(username: str, db_path: str | None = None) -> UserRecord | None:
    init_database(db_path)
    with closing(get_connection(db_path)) as connection:
        row = connection.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if row is None:
        return None
    return UserRecord(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
    )


def get_current_username(request: Request) -> str | None:
    raw_cookie = request.cookies.get(AUTH_COOKIE_NAME, "")
    if not raw_cookie:
        return None
    try:
        username, signature = raw_cookie.split(":", maxsplit=1)
    except ValueError:
        return None
    expected_signature = _sign_username(username)
    if not hmac.compare_digest(signature, expected_signature):
        return None
    return username or None


def login_user(response: Response, username: str) -> None:
    cookie_value = f"{username}:{_sign_username(username)}"
    response.set_cookie(
        AUTH_COOKIE_NAME,
        cookie_value,
        httponly=True,
        samesite="lax",
    )


def logout_user(response: Response) -> None:
    response.delete_cookie(AUTH_COOKIE_NAME)


def require_login(request: Request, next_path: str | None = None) -> RedirectResponse | None:
    if get_current_username(request) is not None:
        return None

    target = next_path or str(request.url.path)
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(
        url=f"/auth/login?{urlencode({'next': target})}",
        status_code=303,
    )


def sanitize_next_path(next_path: str | None) -> str:
    if not next_path:
        return "/"
    normalized = next_path.strip()
    if not normalized.startswith("/"):
        return "/"
    if normalized.startswith("//"):
        return "/"
    return normalized


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", maxsplit=1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected_digest = bytes.fromhex(digest_hex)
    candidate_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(candidate_digest, expected_digest)


def _sign_username(username: str) -> str:
    return hmac.new(
        settings.session_secret.encode("utf-8"),
        username.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
