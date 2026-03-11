from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

_LOCAL_DEV_DB_URL: str = "postgres://postgres:postgres@localhost:5432/video_demo"


class Settings(BaseSettings):
    app_name: str = "video-demo"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = _LOCAL_DEV_DB_URL

    model_config = {"env_prefix": "", "case_sensitive": False}

    @model_validator(mode="after")
    def _reject_default_db_in_production(self) -> Settings:
        if not self.debug and self.database_url == _LOCAL_DEV_DB_URL:
            msg = "DATABASE_URL must be set explicitly in production (debug=False)"
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
