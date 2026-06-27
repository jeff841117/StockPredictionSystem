from pathlib import Path

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.services.audit_service import list_audit_logs
from app.services.auth_service import PermissionDeniedError, get_current_username, require_role


router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
settings = get_settings()


@router.get(
    "/audit-logs",
    response_class=HTMLResponse,
    tags=["Pages"],
    summary="Audit Log 管理頁",
    description="回傳最小 audit log 管理頁。此頁目前僅限 admin 存取，用於展示最小權限管理能力。",
)
def audit_logs_page(request: Request):
    try:
        user = require_role(request, "admin")
    except PermissionDeniedError as exc:
        if str(exc) == "UNAUTHENTICATED":
            next_target = "/admin/audit-logs"
            return RedirectResponse(url=f"/auth/login?next={next_target}", status_code=status.HTTP_303_SEE_OTHER)
        return templates.TemplateResponse(
            request=request,
            name="admin_forbidden.html",
            context={
                "project_name": settings.app_name,
                "current_username": get_current_username(request),
                "required_role": "admin",
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_audit_logs.html",
        context={
            "project_name": settings.app_name,
            "audit_logs": list_audit_logs(),
            "current_username": user.username,
        },
    )
