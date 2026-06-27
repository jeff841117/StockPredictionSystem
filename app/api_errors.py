from fastapi import status

from app.schemas.api import ApiErrorResponse, ApiValidationIssue


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        validation_errors: list[ApiValidationIssue] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.validation_errors = validation_errors or []
        super().__init__(message)

    def to_response(self) -> ApiErrorResponse:
        return ApiErrorResponse(
            error_code=self.error_code,
            message=self.message,
            validation_errors=self.validation_errors,
        )


def build_api_error_content(
    error_code: str,
    message: str,
    validation_errors: list[ApiValidationIssue] | None = None,
) -> dict:
    return ApiErrorResponse(
        error_code=error_code,
        message=message,
        validation_errors=validation_errors or [],
    ).model_dump()


def build_common_api_error_responses(
    *,
    include_not_found: bool = False,
    include_external_failure: bool = False,
    include_conflict: bool = False,
    include_unauthorized: bool = False,
    include_forbidden: bool = False,
) -> dict[int, dict]:
    responses = {
        status.HTTP_400_BAD_REQUEST: {
            "model": ApiErrorResponse,
            "description": "輸入內容不符合業務規則，例如股票代號或日期區間格式錯誤。",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_input": {
                            "summary": "商業規則錯誤",
                            "value": build_api_error_content(
                                "INVALID_INPUT",
                                "股票代號格式錯誤，請輸入 4 位數台股代號。",
                            ),
                        }
                    }
                }
            },
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ApiErrorResponse,
            "description": "請求參數缺漏或格式不符合 API 輸入驗證。",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": {
                            "summary": "欄位驗證失敗",
                            "value": build_api_error_content(
                                "VALIDATION_ERROR",
                                "API 請求參數驗證失敗，請確認必填欄位與格式。",
                                [
                                    ApiValidationIssue(
                                        field="body.stock_name",
                                        message="缺少必要欄位。",
                                    )
                                ],
                            ),
                        }
                    }
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ApiErrorResponse,
            "description": "伺服器內部錯誤。",
            "content": {
                "application/json": {
                    "examples": {
                        "server_error": {
                            "summary": "一般伺服器錯誤",
                            "value": build_api_error_content(
                                "INTERNAL_SERVER_ERROR",
                                "API 查詢處理失敗，請稍後再試。",
                            ),
                        }
                    }
                }
            },
        },
    }

    if include_not_found:
        responses[status.HTTP_404_NOT_FOUND] = {
            "model": ApiErrorResponse,
            "description": "查無資料。",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {
                            "summary": "查無資料",
                            "value": build_api_error_content(
                                "NOT_FOUND",
                                "查無資料，請確認股票代號是否存在，或該查詢區間內是否有成交資料。",
                            ),
                        }
                    }
                }
            },
        }

    if include_external_failure:
        responses[status.HTTP_502_BAD_GATEWAY] = {
            "model": ApiErrorResponse,
            "description": "外部資料來源暫時失敗。",
            "content": {
                "application/json": {
                    "examples": {
                        "external_service_error": {
                            "summary": "外部資料來源失敗",
                            "value": build_api_error_content(
                                "EXTERNAL_SERVICE_ERROR",
                                "股票資料來源暫時無法使用，請稍後再試。",
                            ),
                        }
                    }
                }
            },
        }

    if include_conflict:
        responses[status.HTTP_409_CONFLICT] = {
            "model": ApiErrorResponse,
            "description": "資料衝突，例如重複新增相同資源。",
            "content": {
                "application/json": {
                    "examples": {
                        "duplicate_resource": {
                            "summary": "重複資源",
                            "value": build_api_error_content(
                                "DUPLICATE_RESOURCE",
                                "該股票已在收藏清單中，無法重複加入。",
                            ),
                        }
                    }
                }
            },
        }

    if include_unauthorized:
        responses[status.HTTP_401_UNAUTHORIZED] = {
            "model": ApiErrorResponse,
            "description": "尚未登入，無法存取需要登入的資料。",
            "content": {
                "application/json": {
                    "examples": {
                        "unauthorized": {
                            "summary": "未登入",
                            "value": build_api_error_content(
                                "UNAUTHORIZED",
                                "請先登入後再存取這個 API。",
                            ),
                        }
                    }
                }
            },
        }

    if include_forbidden:
        responses[status.HTTP_403_FORBIDDEN] = {
            "model": ApiErrorResponse,
            "description": "已登入但沒有足夠權限存取此 API。",
            "content": {
                "application/json": {
                    "examples": {
                        "forbidden": {
                            "summary": "權限不足",
                            "value": build_api_error_content(
                                "FORBIDDEN",
                                "你目前沒有權限存取這個 API。",
                            ),
                        }
                    }
                }
            },
        }

    return responses


def build_validation_issues(validation_errors: list[dict]) -> list[ApiValidationIssue]:
    issues: list[ApiValidationIssue] = []
    for error in validation_errors:
        location = ".".join(str(part) for part in error.get("loc", []) if part != "query")
        issues.append(
            ApiValidationIssue(
                field=location or "request",
                message=_translate_validation_message(error),
            )
        )
    return issues


def _translate_validation_message(error: dict) -> str:
    error_type = error.get("type", "")
    location = ".".join(str(part) for part in error.get("loc", []) if part != "query") or "欄位"

    if error_type == "missing":
        return "缺少必要欄位。"

    if error_type in {"date_from_datetime_parsing", "date_parsing"}:
        return "日期格式錯誤，請使用 YYYY-MM-DD。"

    if error_type in {"int_parsing", "int_type"}:
        return f"{location} 格式錯誤，請輸入整數。"

    if error_type in {"float_parsing", "float_type", "decimal_parsing"}:
        return f"{location} 格式錯誤，請輸入數值。"

    if error_type in {"string_type", "string_unicode"}:
        return f"{location} 格式錯誤，請輸入文字。"

    if error_type == "bool_parsing":
        return f"{location} 格式錯誤，請輸入布林值。"

    return "查詢參數格式錯誤。"
