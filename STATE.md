<!-- STATE.md — must stay under 80 lines -->
# Project State

## Current Phase

**Phase 1: Core Application** — Step 3 of 7

## Phase 1 Progress

| Step | Description                                      | Status      |
|------|--------------------------------------------------|-------------|
| 1    | FastAPI skeleton with /healthz + /readyz          | DONE        |
| 2    | Tortoise ORM models + Aerich migrations setup    | DONE        |
| 3    | Auth (register, login, refresh with rotation)    | NOT STARTED |
| 4    | Job creation endpoint + Celery task (stub)       | NOT STARTED |
| 5    | MinIO integration (upload + presigned URL)       | NOT STARTED |
| 6    | SSE endpoint with Redis pub/sub                  | NOT STARTED |
| 7    | GET /jobs (list) and GET /jobs/{id} (status)     | NOT STARTED |

## Up Next — Step 3: Auth

- `src/auth.py` — JWT logic, login/register/refresh endpoints
- Password hashing (argon2/bcrypt)
- Refresh token rotation with family-based revocation
- Tests with testcontainers (Postgres)

## Completed

- **Step 1**: FastAPI skeleton — app factory, `/healthz`, `/readyz`, `/api/v1/` router, error envelope, ruff + mypy strict + 4 tests passing
- **Step 2**: Tortoise ORM — User/Job/RefreshToken models, Aerich migration, `/readyz` checks DB (503 on failure), production DB guard, testcontainers fixtures, 20 tests passing

## Blocked

(nothing blocked)

## Key Files Created

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Agent instructions |
| `STATE.md` | Project state tracking |
| `docs/demo-architecture.md` | Full architecture plan |
| `docs/ARCHITECTURE.md` | Key decisions with rationale |
| `docs/API-OVERVIEW.md` | High-level API endpoint rationale |
| `docs/CONTEXT-PROTOCOL.md` | Context update protocol |
| `pyproject.toml` | Project config, deps, tool settings, aerich config |
| `src/main.py` | App factory, health routes, error handler, Tortoise lifespan |
| `src/config.py` | Settings from env vars + production DB guard |
| `src/schemas.py` | ErrorResponse + HealthResponse envelopes |
| `src/db.py` | Tortoise ORM config, lazy TORTOISE_ORM for Aerich |
| `src/models.py` | User, Job, RefreshToken models + JobStatus enum |
| `migrations/` | Aerich migration files (initial: 3 tables) |
| `tests/conftest.py` | Testcontainers Postgres + AsyncClient fixtures |
| `tests/test_health.py` | Health endpoint tests (4 tests) |
| `tests/test_models.py` | Model CRUD/cascade/enum tests (15 tests) |
| `tests/test_readyz_db.py` | Readyz with real Postgres (1 test) |

## Known Issues

(none)
