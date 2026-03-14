from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from src.auth import CurrentUserSSE, SettingsDep
from src.rate_limit import GET_LIMIT, get_user_or_ip, limiter

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger: logging.Logger = logging.getLogger(__name__)

sse_router = APIRouter(prefix="/jobs", tags=["sse"])


def _sse_event(data: str, event: str | None = None, id: str | None = None) -> str:
    """Format a single SSE event."""
    lines: list[str] = []
    if id is not None:
        lines.append(f"id: {id}")
    if event is not None:
        lines.append(f"event: {event}")
    lines.append(f"data: {data}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


async def _stream_events(
    redis_url: str,
    user_id: str,
) -> AsyncGenerator[str]:
    """Subscribe to the user's Redis channel and yield SSE events."""
    yield _sse_event(json.dumps({"user_id": user_id}), event="connected")

    r = aioredis.from_url(redis_url)
    pubsub = r.pubsub()
    channel = f"jobs:user:{user_id}"
    try:
        await pubsub.subscribe(channel)
        while True:
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=30.0,
            )
            if msg is not None and msg["type"] == "message":
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                parsed = json.loads(data)
                event_id = f"{parsed.get('job_id', '')}:{parsed.get('status', '')}"
                yield _sse_event(data, event="status", id=event_id)
            else:
                yield _sse_event("", event="ping")

    except asyncio.CancelledError:
        logger.debug("SSE client disconnected for user %s", user_id)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await r.aclose()


@sse_router.get("/events", response_model=None)
@limiter.limit(GET_LIMIT, key_func=get_user_or_ip)  # type: ignore[union-attr]
async def job_events(
    user: CurrentUserSSE,
    settings: SettingsDep,
    request: Request,
) -> StreamingResponse:
    return StreamingResponse(
        _stream_events(settings.redis_url, str(user.id)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
