from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.models import Job


class JobResponse(BaseModel):
    """Single job resource."""

    id: UUID
    status: str
    celery_task_id: str | None = None
    minio_object_key: str | None = None
    download_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PaginationMeta(BaseModel):
    """Offset-based pagination metadata."""

    total: int
    page: int
    per_page: int
    total_pages: int


def job_to_response(job: Job, download_url: str | None = None) -> JobResponse:
    """Convert a Tortoise Job instance to a Pydantic response."""
    return JobResponse(
        id=job.id,
        status=job.status,
        celery_task_id=job.celery_task_id,
        minio_object_key=job.minio_object_key,
        download_url=download_url,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def make_pagination_meta(total: int, page: int, per_page: int) -> PaginationMeta:
    """Build pagination metadata from counts."""
    return PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=max(1, math.ceil(total / per_page)),
    )
