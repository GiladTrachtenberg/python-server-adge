from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
import redis.asyncio as aioredis

from tests.conftest import register_and_login

if TYPE_CHECKING:
    from httpx import AsyncClient

    from src.config import Settings

pytestmark = pytest.mark.usefixtures("db")

JOBS = "/api/v1/jobs"


def _mock_delay(job_id: str) -> MagicMock:
    """Return a fake AsyncResult with an id attribute."""
    result = MagicMock()
    result.id = f"celery-{job_id}"
    return result


class TestCreateJob:
    async def test_returns_202_with_job_data(self, db_client: AsyncClient) -> None:
        headers = await register_and_login(db_client)
        with patch("src.jobs.process_job.delay", side_effect=_mock_delay):
            resp = await db_client.post(JOBS, headers=headers)

        assert resp.status_code == 202
        data = resp.json()["data"]
        UUID(data["id"])
        assert data["status"] == "pending"

    async def test_unauthenticated(self, db_client: AsyncClient) -> None:
        resp = await db_client.post(JOBS)
        assert resp.status_code == 401


class TestListJobs:
    async def test_empty_list(self, db_client: AsyncClient) -> None:
        headers = await register_and_login(db_client)
        resp = await db_client.get(JOBS, headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    async def test_pagination(self, db_client: AsyncClient) -> None:
        headers = await register_and_login(db_client)
        with patch("src.jobs.process_job.delay", side_effect=_mock_delay):
            for _ in range(3):
                await db_client.post(JOBS, headers=headers)

        resp = await db_client.get(f"{JOBS}?per_page=2", headers=headers)
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 3
        assert body["meta"]["total_pages"] == 2


class TestGetJob:
    async def test_returns_job_detail(self, db_client: AsyncClient) -> None:
        headers = await register_and_login(db_client)
        with patch("src.jobs.process_job.delay", side_effect=_mock_delay):
            create_resp = await db_client.post(JOBS, headers=headers)
        job_id = create_resp.json()["data"]["id"]

        resp = await db_client.get(f"{JOBS}/{job_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == job_id

    async def test_not_found(self, db_client: AsyncClient) -> None:
        headers = await register_and_login(db_client)
        resp = await db_client.get(f"{JOBS}/{uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_forbidden_other_user(self, db_client: AsyncClient) -> None:
        headers_a = await register_and_login(db_client)
        with patch("src.jobs.process_job.delay", side_effect=_mock_delay):
            create_resp = await db_client.post(JOBS, headers=headers_a)
        job_id = create_resp.json()["data"]["id"]

        headers_b = await register_and_login(db_client)

        resp = await db_client.get(f"{JOBS}/{job_id}", headers=headers_b)
        assert resp.status_code == 403


class TestCancelJob:
    async def test_cancel_pending_job(self, db_client: AsyncClient) -> None:
        headers = await register_and_login(db_client)
        with patch("src.jobs.process_job.delay", side_effect=_mock_delay):
            create_resp = await db_client.post(JOBS, headers=headers)
        job_id = create_resp.json()["data"]["id"]

        resp = await db_client.post(f"{JOBS}/{job_id}/cancel", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    async def test_cancel_completed_job_fails(self, db_client: AsyncClient) -> None:
        headers = await register_and_login(db_client)
        with patch("src.jobs.process_job.delay", side_effect=_mock_delay):
            create_resp = await db_client.post(JOBS, headers=headers)
        job_id = create_resp.json()["data"]["id"]

        from src.models import Job

        job = await Job.get(id=job_id)
        job.status = "completed"
        await job.save(update_fields=["status"])

        resp = await db_client.post(f"{JOBS}/{job_id}/cancel", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "not_cancellable"


class TestJobLifecycle:
    async def test_full_pipeline(
        self,
        db_client: AsyncClient,
        settings: Settings,
    ) -> None:
        """Full pipeline: create → task runs → completed + presigned URL."""
        headers = await register_and_login(db_client)
        with patch("src.jobs.process_job.delay", side_effect=_mock_delay):
            create_resp = await db_client.post(JOBS, headers=headers)
        job_id = create_resp.json()["data"]["id"]

        with patch("src.tasks.asyncio.sleep", return_value=None):
            from src.tasks import _process

            await _process(job_id, settings)

        from tortoise import Tortoise

        from src.db import get_tortoise_config

        await Tortoise.init(config=get_tortoise_config(settings.database_url))

        from src.models import Job

        job = await Job.get(id=job_id)
        assert job.status == "completed"
        assert job.minio_object_key == f"jobs/{job_id}/output.txt"

        resp = await db_client.get(f"{JOBS}/{job_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert data["download_url"] is not None
        assert "X-Amz-Signature" in data["download_url"]


class TestSSE:
    async def test_receives_published_event(
        self,
        db_client: AsyncClient,
        settings: Settings,
    ) -> None:
        """Open SSE stream, publish to Redis, verify event arrives."""
        headers = await register_and_login(db_client)
        with patch("src.jobs.process_job.delay", side_effect=_mock_delay):
            create_resp = await db_client.post(JOBS, headers=headers)
        job_id = create_resp.json()["data"]["id"]

        collected_lines: list[str] = []

        async def read_stream() -> None:
            async with db_client.stream(
                "GET",
                f"{JOBS}/{job_id}/events",
                headers=headers,
            ) as resp:
                async for line in resp.aiter_lines():
                    collected_lines.append(line)
                    if '"completed"' in line:
                        break

        stream_task = asyncio.create_task(read_stream())
        await asyncio.sleep(0.3)

        r = aioredis.from_url(settings.redis_url)
        payload = json.dumps({"job_id": job_id, "status": "completed"})
        await r.publish(f"jobs:{job_id}:status", payload)
        await r.aclose()

        await asyncio.wait_for(stream_task, timeout=5.0)

        full_output = "\n".join(collected_lines)
        assert "event: connected" in full_output
        assert '"completed"' in full_output
