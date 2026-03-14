# Video Processing Demo

Async job processing showcase: FastAPI + Celery + Redis + Postgres + MinIO,
deployed on Kubernetes (Kind) with ArgoCD.

## Architecture

```
Browser ──► nginx (React SPA) ──► FastAPI API ──► Postgres (CNPG)
                                       │
                                       ├──► Redis (pub/sub + broker)
                                       │        │
                                       │        ▼
                                       │    Celery Worker ──► MinIO
                                       │
                                       └──► SSE stream ──► Browser
```

A user creates a job via the API. Celery picks it up, generates a 5-50 MB file,
uploads it to MinIO, and publishes status events through Redis pub/sub. The
browser receives real-time updates via a single user-scoped SSE connection.
Completed jobs include a presigned MinIO download URL directly in the event
payload.

## Stack

| Layer       | Technology                                          |
|-------------|-----------------------------------------------------|
| API         | FastAPI, Tortoise ORM, Pydantic, JWT (Argon2)       |
| Worker      | Celery with Redis broker                             |
| Storage     | MinIO (S3-compatible), presigned URLs                |
| Database    | PostgreSQL via CloudNativePG operator                |
| Realtime    | Server-Sent Events (user-scoped, Redis pub/sub)     |
| Frontend    | React 19, Vite, TypeScript                           |
| CI          | GitHub Actions (lint → type-check → test → build)   |
| CD          | ArgoCD ApplicationSet with RollingSync               |
| Infra       | Kind (3-node), Helm, SealedSecrets                   |

## API Endpoints

| Method | Path                       | Description                      |
|--------|----------------------------|----------------------------------|
| POST   | `/api/v1/auth/register`    | Create account                   |
| POST   | `/api/v1/auth/login`       | Get access + refresh tokens      |
| POST   | `/api/v1/auth/refresh`     | Rotate tokens                    |
| GET    | `/api/v1/auth/me`          | Current user profile             |
| POST   | `/api/v1/jobs`             | Create a processing job          |
| GET    | `/api/v1/jobs`             | List jobs (paginated)            |
| GET    | `/api/v1/jobs/{id}`        | Job detail + presigned URL       |
| POST   | `/api/v1/jobs/{id}/cancel` | Cancel pending/processing job    |
| GET    | `/api/v1/jobs/events`      | SSE stream (all user job events) |
| GET    | `/healthz`, `/readyz`      | Liveness / readiness probes      |

## Project Structure

```
src/
├── main.py             # App factory, lifespan, route registration
├── config.py           # Pydantic settings (WorkerSettings, Settings)
├── auth.py             # JWT, Argon2, token rotation, CurrentUserSSE
├── jobs.py             # Job CRUD endpoints
├── sse.py              # User-scoped SSE endpoint
├── tasks.py            # Celery worker (file generation, Redis publish)
├── models.py           # Tortoise ORM models (User, Job, RefreshToken)
├── storage.py          # MinIO client (upload, presigned URLs)
├── rate_limit.py       # slowapi rate limiting
└── *_schemas.py        # Pydantic request/response schemas

web/src/
├── App.tsx             # View routing, auth state
├── SseContext.tsx       # Shared EventSource provider
├── JobsPage.tsx        # Job list (real-time via SSE)
├── JobDetailPage.tsx   # Job detail (status + download)
├── AuthPage.tsx        # Login / register
└── api.ts              # Typed API client

deploy/
├── app/values-api.yaml     # Helm values for API pods
├── app/values-worker.yaml  # Helm values for Worker pods
└── web/values-web.yaml     # Helm values for Web (nginx) pods

tests/                  # pytest + testcontainers (Postgres, Redis, MinIO)
```

## Local Development

### Docker Compose (full stack)

```bash
docker compose up -d
# App:    http://localhost:3000
# API:    http://localhost:8081
# MinIO:  http://localhost:9001 (console)
```

### Native (backend only)

```bash
uv sync --frozen --extra dev

# Start dependencies
docker run -d --name pg -e POSTGRES_USER=demo -e POSTGRES_PASSWORD=demo -e POSTGRES_DB=video_demo -p 5434:5432 postgres:16-alpine
docker run -d --name redis -p 6380:6379 redis:7-alpine
docker run -d --name minio -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address :9001

# Run migrations
DATABASE_URL=postgres://demo:demo@localhost:5434/video_demo DEBUG=true uv run aerich upgrade

# Start API
DEBUG=true DATABASE_URL=postgres://demo:demo@localhost:5434/video_demo REDIS_URL=redis://localhost:6380/0 uv run uvicorn src.main:create_app --factory --port 8081

# Start worker (separate terminal)
DEBUG=true DATABASE_URL=postgres://demo:demo@localhost:5434/video_demo REDIS_URL=redis://localhost:6380/0 CELERY_BROKER_URL=redis://localhost:6380/1 uv run celery -A src.tasks:celery_app worker --loglevel=info
```

### Frontend

```bash
cd web && npm ci && npm run dev
# http://localhost:5173 (proxies /api to localhost:8081)
```

## CI/CD

Two path-filtered GitHub Actions workflows:

- **ci-backend.yml** (`src/`, `tests/`, `Dockerfile`): lint → type-check → test → build → update-manifests
- **ci-frontend.yml** (`web/`): lint → build → update-manifests

Both push multi-arch images to GHCR and update the image tag in the
corresponding `deploy/*/values-*.yaml` files. ArgoCD detects the commit and
syncs automatically.

## Testing

```bash
uv run ruff check src/ tests/          # Lint
uv run ruff format --check src/ tests/ # Format check
uv run mypy src/ tests/                # Type check (strict)
uv run pytest -v                       # Tests (needs Docker for testcontainers)
```

## Kubernetes Deployment

This repo holds application code and Helm values. The shared Helm chart and
cluster infrastructure live in
[python-server-infra](https://github.com/giladtrachtenberg/python-server-infra).

```bash
# In the infra repo:
bash deploy/kind/bootstrap.sh   # Create cluster, install operators, deploy apps
bash deploy/kind/validate.sh    # Run E2E validation
bash deploy/kind/teardown.sh    # Delete cluster
```

## Using the App

### With Docker Compose

```bash
docker compose up -d
```

Open http://localhost:3000 once all services are healthy (~15 seconds).

### With Kind (Kubernetes)

After running `bootstrap.sh`, wait about 60 seconds for ArgoCD to sync all
apps and for pods to become ready. You can watch progress with:

```bash
kubectl get pods -n demo -w
```

Once all pods show `Running` / `Ready`, open http://localhost:8082.

### Walkthrough

1. **Sign up** — enter an email and password on the auth page
2. **Log in** — use the same credentials, you'll land on the jobs page
3. **Create a job** — click "New Job". The job starts as `pending`, then moves
   to `processing` in real time (no page refresh needed — the status badge
   updates via SSE)
4. **Watch it complete** — after 2-4 seconds of processing, the status flips to
   `completed`. Click the job row to see its detail page
5. **Download the file** — the detail page shows a "Download File" link
   (presigned MinIO URL, valid for 1 hour)
6. **Create more jobs** — go back to the jobs list and create several. All
   status updates stream in real time through a single SSE connection

## Documentation

| Document                  | Contents                                     |
|---------------------------|----------------------------------------------|
| `docs/ARCHITECTURE.md`    | 35 key architectural decisions (D1-D35)      |
| `docs/API-OVERVIEW.md`    | Endpoint details, patterns, rationale        |
| `docs/DOWNLOAD-FLOW.md`   | End-to-end file generation and download flow |
| `STATE.md`                | Current development phase and progress       |
