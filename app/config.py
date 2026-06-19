from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")


class Settings:
    """Minimal application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "台股分析與模擬交易系統")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.host = os.getenv("HOST", "127.0.0.1")
        self.port = int(os.getenv("PORT", "8000"))
        self.stock_query_source = os.getenv(
            "STOCK_QUERY_SOURCE",
            "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY",
        )
        self.stock_query_date = os.getenv("STOCK_QUERY_DATE", "20240501")


@lru_cache
def get_settings() -> Settings:
    return Settings()
