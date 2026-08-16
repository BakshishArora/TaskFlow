FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=300

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    CELERY_TASK_ALWAYS_EAGER=true

COPY --from=builder /app/.venv ./.venv

EXPOSE 8000

CMD ["uvicorn", "taskflow.main:app", "--host", "0.0.0.0", "--port", "8000"]
