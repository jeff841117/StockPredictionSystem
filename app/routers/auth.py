from pathlib import Path
from fastapi import APIRouter, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.error_monitoring import record_error_event
from app.services.audit_service import record_audit_event
from app.services.auth_service import (
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidRegistrationInputError,
    get_current_username,
    login_user,
    logout_user,
    register_user,
    authenticate_user,
    sanitize_next_path,
)


router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
settings = get_settings()


def _render_auth_page(
    request: Request,
    *,
    name: str,
    error_message: str = "",
    success_message: str = "",
    next_path: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={
            "project_name": settings.app_name,
            "error_message": error_message,
            "success_message": success_message,
            "next_path": next_path,
            "current_username": get_current_username(request),
            "single_user_scope_notice": "目前登入版已提供登入狀態、頁面保護與最小資料隔離，收藏與交易資料會依登入使用者區分。",
        },
        status_code=status_code,
    )


@router.get("/login", response_class=HTMLResponse, tags=["Pages"], summary="登入頁")
def login_page(request: Request, next: str = Query(""), message: str = Query("")):
    if get_current_username(request) is not None:
        return RedirectResponse(url=sanitize_next_path(next), status_code=status.HTTP_303_SEE_OTHER)
    return _render_auth_page(
        request,
        name="login.html",
        next_path=sanitize_next_path(next) if next else "",
        success_message=message,
    )


@router.post("/login", tags=["Pages"], summary="提交登入表單")
def login_submit(
    request: Request,
    username: str | None = Form(None),
    password: str | None = Form(None),
    next_path: str | None = Form(None),
):
    try:
        user = authenticate_user(username or "", password or "")
    except InvalidCredentialsError as exc:
        record_error_event(
            flow="page",
            category="business_rule_error",
            route="/auth/login",
            user_message=str(exc),
            internal_message=repr(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request,
        )
        return _render_auth_page(
            request,
            name="login.html",
            error_message=str(exc),
            next_path=sanitize_next_path(next_path) if next_path else "",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    response = RedirectResponse(url=sanitize_next_path(next_path), status_code=status.HTTP_303_SEE_OTHER)
    login_user(response, user.username)
    record_audit_event(
        event_type="AUTH_LOGIN",
        username=user.username,
        user_id=user.id,
        target_type="session",
        target_value=sanitize_next_path(next_path),
    )
    return response


@router.get("/register", response_class=HTMLResponse, tags=["Pages"], summary="註冊頁")
def register_page(request: Request):
    if get_current_username(request) is not None:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return _render_auth_page(request, name="register.html")


@router.post("/register", tags=["Pages"], summary="提交註冊表單")
def register_submit(
    request: Request,
    username: str | None = Form(None),
    password: str | None = Form(None),
):
    try:
        user = register_user(username or "", password or "")
    except (InvalidRegistrationInputError, DuplicateUserError) as exc:
        record_error_event(
            flow="page",
            category="validation_error" if isinstance(exc, InvalidRegistrationInputError) else "business_rule_error",
            route="/auth/register",
            user_message=str(exc),
            internal_message=repr(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request,
        )
        return _render_auth_page(
            request,
            name="register.html",
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    record_audit_event(
        event_type="AUTH_REGISTER",
        username=user.username,
        user_id=user.id,
        target_type="user",
        target_value=user.username,
    )
    return RedirectResponse(
        url="/auth/login?message=註冊成功，請使用新帳號登入。",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/logout", tags=["Pages"], summary="登出")
def logout(request: Request):
    current_username = get_current_username(request)
    response = RedirectResponse(url="/?message=已成功登出。", status_code=status.HTTP_303_SEE_OTHER)
    logout_user(response)
    if current_username is not None:
        record_audit_event(
            event_type="AUTH_LOGOUT",
            username=current_username,
            target_type="session",
            target_value="/",
        )
    return response
