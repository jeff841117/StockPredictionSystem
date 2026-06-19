from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings


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
            "message": "FastAPI 專案骨架已成功啟動。",
        },
    )
