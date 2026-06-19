from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.services.stock_service import get_fixed_interval_label


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
settings = get_settings()


@router.get("/", response_class=HTMLResponse, tags=["pages"])
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": settings.app_name,
            "message": "輸入台股代號後，即可查詢固定區間的歷史成交資料。",
            "fixed_interval": get_fixed_interval_label(),
        },
    )
