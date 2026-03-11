<!-- STATE.md — must stay under 80 lines -->
# Project State

## Current Phase

**Phase 1: Core Application** — Step 5 of 9

## Phase 1 Progress

| Step | Description                                      | Status      |
|------|--------------------------------------------------|-------------|
| 1    | FastAPI skeleton with /healthz + /readyz          | DONE        |
| 2    | Tortoise ORM models + Aerich migrations setup    | DONE        |
| 3    | Auth (register, login, refresh with rotation)    | DONE        |
| 4    | Jobs API + Celery worker + MinIO + SSE           | DONE        |
| 5    | Rate limiting + Dockerfile + CI                  | NOT STARTED |
| 6    | Helm chart + Kind cluster + K8s manifests        | NOT STARTED |
| 7    | ArgoCD + Sealed Secrets setup on Kind            | NOT STARTED |
| 8    | ApplicationSet + sync waves (full GitOps deploy) | NOT STARTED |
| 9    | End-to-end validation on Kind                    | NOT STARTED |

## Up Next — Step 5: Build & Validate

- Rate limiting via slowapi + Redis backend
- Dockerfile (multi-stage, cache mounts, non-root user)
- .dockerignore
- GitHub Actions CI (lint, type-check, test, build image)

## Step 6: Deploy to Kubernetes

- Helm chart under `deploy/app/` (deployment, service, configmap, sealedsecret, migration job)
- Kind cluster config + setup script under `deploy/kind/`
- Infra values: `deploy/infra/{cnpg-cluster,redis,minio}/`
- K8s namespace manifest

## Step 7: ArgoCD + Sealed Secrets

- ArgoCD installation on Kind
- Sealed Secrets controller installation
- SealedSecrets for CNPG, Redis, MinIO, app credentials, ArgoCD admin
- All secrets under `deploy/sealed-secrets/`

## Step 8: ApplicationSet + Sync Waves

- ApplicationSet under `deploy/argocd/`
- ArgoCD tracks `deploy/` on main branch
- Sync waves: CNPG(1) → Redis(2) → MinIO(3) → API(4) → Worker(5)

## Step 9: End-to-End Validation on Kind

- Verify full flow on Kind: register, login, create job, poll, download
- Validate ArgoCD sync status for all Applications
- Confirm sealed secrets decrypted correctly

## Completed

- **Step 1**: FastAPI skeleton — app factory, health routes, error envelope
- **Step 2**: Tortoise ORM — models, Aerich migration, testcontainers fixtures
- **Step 3**: Auth — register/login/refresh, argon2 + PyJWT, token rotation
- **Step 4**: Jobs API (CRUD + cancel), Celery async task, MinIO upload +
  presigned URLs, SSE via Redis pub/sub, 11 integration tests

## Blocked

(nothing blocked)

## Key Files Created

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Agent instructions + pointer index |
| `docs/demo-architecture.md` | Full architecture plan |
| `docs/ARCHITECTURE.md` | Key decisions with rationale |
| `pyproject.toml` | Project config, deps, tool settings, aerich config |
| `src/main.py` | App factory, health routes, error handler, lifespan |
| `src/config.py` | Settings from env vars + production guards |
| `src/schemas.py` | ErrorResponse + HealthResponse envelopes |
| `src/db.py` | Tortoise ORM config |
| `src/models.py` | User, Job, RefreshToken models |
| `src/auth.py` | Auth router, JWT, password hashing, token rotation |
| `src/auth_schemas.py` | Auth request/response schemas |
| `src/jobs.py` | Jobs router (create, list, detail, cancel) |
| `src/jobs_schemas.py` | Job response + pagination schemas |
| `src/tasks.py` | Celery app + async process_job task |
| `src/storage.py` | MinIO wrapper (upload, presigned URL, bucket init) |
| `src/sse.py` | SSE endpoint with Redis pub/sub + reconnection |
| `tests/conftest.py` | Testcontainers (Postgres + Redis + MinIO) fixtures |
| `tests/test_auth.py` | Auth integration tests (14 tests) |
| `tests/test_jobs.py` | Jobs integration tests (11 tests) |

## Known Issues

(none)
