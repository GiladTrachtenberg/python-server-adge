<!-- STATE.md — must stay under 80 lines -->
# Project State

## Current Phase

**Phase 1: Core Application** — Step 6 of 11

## Progress

| Step | Description                                      | Status      |
|------|--------------------------------------------------|-------------|
| 1    | FastAPI skeleton with /healthz + /readyz          | DONE        |
| 2    | Tortoise ORM models + Aerich migrations setup    | DONE        |
| 3    | Auth (register, login, refresh with rotation)    | DONE        |
| 4    | Jobs API + Celery worker + MinIO + SSE           | DONE        |
| 5    | Rate limiting + Dockerfile + CI                  | DONE        |
| 6    | React frontend (auth, jobs, SSE, download)       | NOT STARTED |
| 7    | Frontend Dockerfile + CI + Helm values           | NOT STARTED |
| 8    | Helm chart + Kind cluster + K8s manifests        | NOT STARTED |
| 9    | ArgoCD + Sealed Secrets setup on Kind            | NOT STARTED |
| 10   | ApplicationSet + sync waves (full GitOps deploy) | NOT STARTED |
| 11   | End-to-end validation on Kind (full stack)       | NOT STARTED |

## Up Next — Step 6: React Frontend

- Vite + TypeScript + React (no component library, plain CSS)
- 3 pages: Login/Register, Jobs list, Job detail (SSE + download)
- `web/` directory with flat file structure (~8 source files)
- Patch backend SSE endpoint to accept `?token=` query param

## Step 7: Frontend Infra

- Multi-stage Dockerfile: node:22-alpine → nginx:alpine
- nginx.conf: SPA routing + /api proxy (SSE buffering off)
- CI: add frontend-lint + frontend-build-image jobs
- Helm values-web.yaml for frontend deployment

## Step 10: ApplicationSet + Sync Waves

- CNPG(1) → Redis(2) → MinIO(3) → API(4) → Worker(5) → Web(6)
- Frontend is the last sync wave

## Step 11: End-to-End Validation on Kind

- Full flow via frontend: register, login, create job, watch SSE, download
- Validate ArgoCD sync status for all Applications

## Completed

- **Step 1-3**: FastAPI skeleton, ORM + migrations, auth with token rotation
- **Step 4**: Jobs CRUD, Celery task (generates 5-50MB files), MinIO, SSE
- **Step 5**: Rate limiting (slowapi), Dockerfile, .dockerignore, GitHub Actions CI

## Blocked

(nothing blocked)
