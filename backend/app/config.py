from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./agencydesk.db"
    session_secret: str = "local-only-change-me"
    cookie_secure: bool = False
    upload_dir: Path = Path("./storage")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
