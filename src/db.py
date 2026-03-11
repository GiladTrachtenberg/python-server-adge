from __future__ import annotations

from typing import Any

from src.config import get_settings


def get_tortoise_config(database_url: str | None = None) -> dict[str, Any]:
    """Build Tortoise ORM config dict"""
    url = database_url or get_settings().database_url
    return {
        "connections": {"default": url},
        "apps": {
            "models": {
                "models": ["src.models", "aerich.models"],
                "default_connection": "default",
            },
        },
    }


def __getattr__(name: str) -> dict[str, Any]:
    """Lazy module attribute — Aerich reads src.db.TORTOISE_ORM at CLI time"""
    if name == "TORTOISE_ORM":
        return get_tortoise_config()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
