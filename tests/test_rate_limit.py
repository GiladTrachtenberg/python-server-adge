from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise, connections

from src.config import Settings
from src.db import get_tortoise_config
from src.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

AUTH = "/api/v1/auth"


@pytest.fixture
async def rl_client(
    database_url: str,
    redis_url: str,
    minio_config: dict[str, Any],
) -> AsyncGenerator[AsyncClient]:
    settings = Settings(
        debug=True,
        database_url=database_url,
        redis_url=redis_url,
        celery_broker_url=redis_url,
        minio_endpoint=minio_config["endpoint"],
        minio_access_key=minio_config["access_key"],
        minio_secret_key=minio_config["secret_key"],
        minio_bucket="test-bucket",
        rate_limit_enabled=True,
    )
    config = get_tortoise_config(database_url)
    await Tortoise.init(config=config)
    await Tortoise.generate_schemas(safe=True)
    await connections.close_all()

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        conn = connections.get("default")
        for table in ("jobs", "refresh_tokens", "users"):
            await conn.execute_query(f"TRUNCATE {table} CASCADE")


@pytest.mark.asyncio
async def test_register_rate_limit(rl_client: AsyncClient) -> None:
    for i in range(3):
        resp = await rl_client.post(
            f"{AUTH}/register",
            json={"email": f"rl{i}@test.com", "password": "strongpass1"},
        )
        assert resp.status_code in (201, 409)

    resp = await rl_client.post(
        f"{AUTH}/register",
        json={"email": "rl_extra@test.com", "password": "strongpass1"},
    )
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_login_rate_limit(rl_client: AsyncClient) -> None:
    await rl_client.post(
        f"{AUTH}/register",
        json={"email": "rl_login@test.com", "password": "strongpass1"},
    )

    for _ in range(5):
        resp = await rl_client.post(
            f"{AUTH}/login",
            json={"email": "rl_login@test.com", "password": "strongpass1"},
        )
        assert resp.status_code == 200

    resp = await rl_client.post(
        f"{AUTH}/login",
        json={"email": "rl_login@test.com", "password": "strongpass1"},
    )
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_error_envelope(rl_client: AsyncClient) -> None:
    for i in range(3):
        await rl_client.post(
            f"{AUTH}/register",
            json={"email": f"env{i}@test.com", "password": "strongpass1"},
        )

    resp = await rl_client.post(
        f"{AUTH}/register",
        json={"email": "env_extra@test.com", "password": "strongpass1"},
    )
    assert resp.status_code == 429
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "rate_limited"
    assert body["error"]["message"] == "Too many requests"
