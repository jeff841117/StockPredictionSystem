from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers.pages import router as pages_router


BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(pages_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
