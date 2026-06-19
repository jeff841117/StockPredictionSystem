from functools import lru_cache
import os


class Settings:
    """Minimal application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "台股分析與模擬交易系統")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.host = os.getenv("HOST", "127.0.0.1")
        self.port = int(os.getenv("PORT", "8000"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
