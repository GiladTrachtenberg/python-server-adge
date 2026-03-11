from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_readyz_with_db_returns_ok(db_client: AsyncClient) -> None:
    response = await db_client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
