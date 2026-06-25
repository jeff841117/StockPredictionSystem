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
) -> dict[int, dict]:
    responses = {
        status.HTTP_400_BAD_REQUEST: {
            "model": ApiErrorResponse,
            "description": "輸入內容不符合業務規則，例如股票代號或日期區間格式錯誤。",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ApiErrorResponse,
            "description": "請求參數缺漏或格式不符合 API 輸入驗證。",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ApiErrorResponse,
            "description": "伺服器內部錯誤。",
        },
    }

    if include_not_found:
        responses[status.HTTP_404_NOT_FOUND] = {
            "model": ApiErrorResponse,
            "description": "查無資料。",
        }

    if include_external_failure:
        responses[status.HTTP_502_BAD_GATEWAY] = {
            "model": ApiErrorResponse,
            "description": "外部資料來源暫時失敗。",
        }

    if include_conflict:
        responses[status.HTTP_409_CONFLICT] = {
            "model": ApiErrorResponse,
            "description": "資料衝突，例如重複新增相同資源。",
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
