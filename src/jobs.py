from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import JSONResponse

from src.auth import CurrentUser, SettingsDep
from src.jobs_schemas import job_to_response, make_pagination_meta
from src.models import Job, JobStatus
from src.rate_limit import GET_LIMIT, JOBS_CREATE_LIMIT, get_user_or_ip, limiter
from src.schemas import ErrorBody, ErrorResponse
from src.storage import get_minio_client, presigned_url
from src.tasks import process_job

jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])


def _error(code: str, message: str, status_code: int) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def _get_user_job(job_id: UUID, user_id: UUID) -> Job | JSONResponse:
    """Fetch a job, returning an error response if not found or not owned."""
    job = await Job.get_or_none(id=job_id)
    if job is None:
        return _error("not_found", "Job not found", status.HTTP_404_NOT_FOUND)
    if job.user_id != user_id:  # type: ignore[attr-defined]
        return _error("forbidden", "Not your job", status.HTTP_403_FORBIDDEN)
    return job


@jobs_router.post("", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(JOBS_CREATE_LIMIT, key_func=get_user_or_ip)  # type: ignore[union-attr]
async def create_job(request: Request, user: CurrentUser) -> JSONResponse:
    job = await Job.create(user_id=user.id)
    result = process_job.delay(str(job.id), str(user.id))
    job.celery_task_id = result.id
    await job.save(update_fields=["celery_task_id"])

    data = job_to_response(job)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"data": data.model_dump(mode="json")},
    )


@jobs_router.get("")
@limiter.limit(GET_LIMIT, key_func=get_user_or_ip)  # type: ignore[union-attr]
async def list_jobs(
    request: Request,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    base_qs = Job.filter(user_id=user.id)
    total = await base_qs.count()
    offset = (page - 1) * per_page
    jobs = await base_qs.order_by("-created_at").offset(offset).limit(per_page)

    data = [job_to_response(j).model_dump(mode="json") for j in jobs]
    meta = make_pagination_meta(total, page, per_page)
    return JSONResponse(content={"data": data, "meta": meta.model_dump()})


@jobs_router.get("/{job_id}")
@limiter.limit(GET_LIMIT, key_func=get_user_or_ip)  # type: ignore[union-attr]
async def get_job(
    request: Request,
    job_id: UUID,
    user: CurrentUser,
    settings: SettingsDep,
) -> JSONResponse:
    result = await _get_user_job(job_id, user.id)
    if isinstance(result, JSONResponse):
        return result
    job = result

    download_url: str | None = None
    if job.status == JobStatus.COMPLETED and job.minio_object_key:
        client = get_minio_client(settings)
        download_url = presigned_url(
            client,
            settings.minio_bucket,
            job.minio_object_key,
        )

    data = job_to_response(job, download_url=download_url)
    return JSONResponse(content={"data": data.model_dump(mode="json")})


@jobs_router.post("/{job_id}/cancel")
@limiter.limit(JOBS_CREATE_LIMIT, key_func=get_user_or_ip)  # type: ignore[union-attr]
async def cancel_job(request: Request, job_id: UUID, user: CurrentUser) -> JSONResponse:
    result = await _get_user_job(job_id, user.id)
    if isinstance(result, JSONResponse):
        return result
    job = result

    if job.status not in (JobStatus.PENDING, JobStatus.PROCESSING):
        return _error(
            "not_cancellable",
            "Job cannot be cancelled in current state",
            status.HTTP_409_CONFLICT,
        )

    job.status = JobStatus.CANCELLED
    await job.save(update_fields=["status", "updated_at"])

    data = job_to_response(job)
    return JSONResponse(content={"data": data.model_dump(mode="json")})
