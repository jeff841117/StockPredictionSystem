from fastapi import APIRouter, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, get_settings
from app.services.auth_service import get_current_user, get_current_username, require_login
from app.services.watchlist_service import (
    DuplicateWatchlistItemError,
    InvalidWatchlistItemError,
    WatchlistItemNotFoundError,
    add_to_watchlist,
    list_watchlist,
    remove_from_watchlist,
)


router = APIRouter(prefix="/watchlist")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
settings = get_settings()


def _render_watchlist(
    request: Request,
    user_id: int,
    message: str = "",
    error_message: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="watchlist.html",
        context={
            "project_name": settings.app_name,
            "items": list_watchlist(user_id),
            "message": message,
            "error_message": error_message,
            "current_username": get_current_username(request),
            "single_user_scope_notice": "目前收藏清單已依登入使用者隔離，僅顯示你的收藏資料。",
        },
        status_code=status_code,
    )


@router.get(
    "",
    response_class=HTMLResponse,
    tags=["Watchlist Pages"],
    summary="收藏清單頁",
    description="回傳收藏清單 HTML，顯示目前已收藏股票與表單提示訊息。",
)
def watchlist_page(
    request: Request,
    message: str = Query(""),
):
    redirect_response = require_login(request)
    if redirect_response is not None:
        return redirect_response
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth/login?next=/watchlist", status_code=status.HTTP_303_SEE_OTHER)
    return _render_watchlist(request, user.id, message=message)


@router.post(
    "/add",
    tags=["Watchlist Pages"],
    summary="加入收藏清單",
    description="處理收藏表單提交，成功後導回收藏清單頁。此端點為瀏覽器表單動作，不是 JSON API。",
)
def add_watchlist_item(
    request: Request,
    stock_no: str | None = Form(None),
    stock_name: str | None = Form(None),
):
    redirect_response = require_login(request)
    if redirect_response is not None:
        return redirect_response
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth/login?next=/watchlist", status_code=status.HTTP_303_SEE_OTHER)
    try:
        add_to_watchlist(stock_no or "", stock_name or "", user.id)
    except DuplicateWatchlistItemError as exc:
        return _render_watchlist(request, user.id, error_message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)
    except InvalidWatchlistItemError as exc:
        return _render_watchlist(request, user.id, error_message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    return RedirectResponse(url="/watchlist?message=已成功加入收藏清單。", status_code=status.HTTP_303_SEE_OTHER)


@router.post(
    "/remove",
    tags=["Watchlist Pages"],
    summary="移除收藏股票",
    description="處理移除收藏表單提交，成功後導回收藏清單頁。此端點為瀏覽器表單動作，不是 JSON API。",
)
def remove_watchlist_item(
    request: Request,
    stock_no: str | None = Form(None),
):
    redirect_response = require_login(request)
    if redirect_response is not None:
        return redirect_response
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth/login?next=/watchlist", status_code=status.HTTP_303_SEE_OTHER)
    try:
        remove_from_watchlist(stock_no or "", user.id)
    except InvalidWatchlistItemError as exc:
        return _render_watchlist(request, user.id, error_message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)
    except WatchlistItemNotFoundError as exc:
        return _render_watchlist(request, user.id, error_message=str(exc), status_code=status.HTTP_404_NOT_FOUND)

    return RedirectResponse(url="/watchlist?message=已成功移除收藏股票。", status_code=status.HTTP_303_SEE_OTHER)
