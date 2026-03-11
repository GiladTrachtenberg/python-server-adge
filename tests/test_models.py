from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from tortoise.exceptions import IntegrityError

from src.models import Job, JobStatus, RefreshToken, User


@pytest.mark.usefixtures("db")
class TestUserModel:
    async def test_create_user(self) -> None:
        user = await User.create(
            email="alice@example.com",
            password_hash="hashed_pw",
        )
        assert user.id is not None
        assert user.email == "alice@example.com"
        assert user.created_at is not None

    async def test_email_uniqueness(self) -> None:
        await User.create(email="dup@example.com", password_hash="h1")
        with pytest.raises(IntegrityError):
            await User.create(email="dup@example.com", password_hash="h2")

    async def test_user_str(self) -> None:
        user = await User.create(email="str@example.com", password_hash="h")
        assert "str@example.com" in str(user)


@pytest.mark.usefixtures("db")
class TestRefreshTokenModel:
    async def test_create_refresh_token(self) -> None:
        user = await User.create(email="rt@example.com", password_hash="h")
        token = await RefreshToken.create(
            user=user,
            token_hash="abc123hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert token.id is not None
        assert token.revoked is False
        assert token.family_id is not None

    async def test_token_cascade_delete(self) -> None:
        user = await User.create(email="cascade@example.com", password_hash="h")
        await RefreshToken.create(
            user=user,
            token_hash="hash1",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        await user.delete()
        assert await RefreshToken.all().count() == 0

    async def test_revoke_token(self) -> None:
        user = await User.create(email="revoke@example.com", password_hash="h")
        token = await RefreshToken.create(
            user=user,
            token_hash="hash2",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        token.revoked = True
        await token.save()
        refreshed = await RefreshToken.get(id=token.id)
        assert refreshed.revoked is True

    async def test_family_id_set_by_default(self) -> None:
        user = await User.create(email="family@example.com", password_hash="h")
        token = await RefreshToken.create(
            user=user,
            token_hash="hash3",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert token.family_id is not None

    async def test_explicit_family_id(self) -> None:
        user = await User.create(email="fam2@example.com", password_hash="h")
        family = uuid4()
        token = await RefreshToken.create(
            user=user,
            token_hash="hash4",
            family_id=family,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert token.family_id == family


@pytest.mark.usefixtures("db")
class TestJobModel:
    async def test_create_job_defaults(self) -> None:
        user = await User.create(email="job@example.com", password_hash="h")
        job = await Job.create(user=user)
        assert job.status == JobStatus.PENDING
        assert job.celery_task_id is None
        assert job.minio_object_key is None
        assert job.error_message is None
        assert job.created_at is not None
        assert job.updated_at is not None

    async def test_job_status_transitions(self) -> None:
        user = await User.create(email="trans@example.com", password_hash="h")
        job = await Job.create(user=user)
        for next_status in (JobStatus.PROCESSING, JobStatus.COMPLETED):
            job.status = next_status
            await job.save()
            refreshed = await Job.get(id=job.id)
            assert refreshed.status == next_status

    async def test_job_failure_stores_error(self) -> None:
        user = await User.create(email="fail@example.com", password_hash="h")
        job = await Job.create(user=user, status=JobStatus.FAILED, error_message="OOM")
        refreshed = await Job.get(id=job.id)
        assert refreshed.error_message == "OOM"
        assert refreshed.status == JobStatus.FAILED

    async def test_job_cascade_delete(self) -> None:
        user = await User.create(email="jcas@example.com", password_hash="h")
        await Job.create(user=user)
        await user.delete()
        assert await Job.all().count() == 0

    async def test_job_str(self) -> None:
        user = await User.create(email="jstr@example.com", password_hash="h")
        job = await Job.create(user=user)
        assert "pending" in str(job)


@pytest.mark.usefixtures("db")
class TestJobStatusEnum:
    def test_enum_values(self) -> None:
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"

    def test_enum_count(self) -> None:
        assert len(JobStatus) == 5
