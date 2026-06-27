from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request

from app.config import get_settings


settings = get_settings()
LOGGER_NAME = "stock_prediction_system.errors"


def get_error_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    log_path = Path(settings.error_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def record_error_event(
    *,
    flow: str,
    category: str,
    route: str,
    user_message: str,
    internal_message: str,
    status_code: int,
    request: Request | None = None,
) -> None:
    payload = {
        "event": "application_error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "flow": flow,
        "category": category,
        "route": route,
        "status_code": status_code,
        "user_message": user_message,
        "internal_message": internal_message,
    }
    if request is not None:
        payload["method"] = request.method
        payload["query"] = request.url.query

    logger = get_error_logger()
    level = _resolve_log_level(category, status_code)
    logger.log(level, json.dumps(payload, ensure_ascii=False))


def _resolve_log_level(category: str, status_code: int) -> int:
    if category in {"internal_server_error", "external_service_error"} or status_code >= 500:
        return logging.ERROR
    if category in {"validation_error", "business_rule_error", "not_found", "unauthorized", "forbidden"}:
        return logging.WARNING
    return logging.INFO
