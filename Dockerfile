FROM python:3.14-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    pip install uv && \
    uv sync --frozen --no-dev

COPY src/ ./src/
COPY migrations/ ./migrations/

FROM python:3.14-slim AS runtime

RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src/
COPY --from=builder /app/migrations ./migrations/
COPY pyproject.toml ./

ENV PATH="/app/.venv/bin:$PATH"

USER app

EXPOSE 8000

CMD ["uvicorn", "src.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
