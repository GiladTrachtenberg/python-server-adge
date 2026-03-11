from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.schemas import ErrorBody, ErrorResponse

if TYPE_CHECKING:
    from fastapi import Request
    from slowapi.errors import RateLimitExceeded

    from src.config import Settings

AUTH_LOGIN_LIMIT: str = "5/minute"
AUTH_REGISTER_LIMIT: str = "3/minute"
JOBS_CREATE_LIMIT: str = "10/minute"
GET_LIMIT: str = "60/minute"

limiter: Limiter | None = None


def get_user_or_ip(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        import jwt

        token = auth_header.removeprefix("Bearer ")
        try:
            settings: Settings = request.app.state.settings
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            user_id: str | None = payload.get("sub")
            if user_id:
                return user_id
        except jwt.InvalidTokenError:
            pass
    return get_remote_address(request)


def init_limiter(settings: Settings) -> Limiter:
    global limiter
    storage_uri = settings.redis_url if settings.rate_limit_enabled else "memory://"
    if limiter is None:
        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=storage_uri,
            enabled=settings.rate_limit_enabled,
        )
    else:
        limiter.reset()
        limiter.enabled = settings.rate_limit_enabled
    return limiter


def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(code="rate_limited", message="Too many requests"),
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=body.model_dump(),
    )
