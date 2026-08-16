# TaskFlow

Task management API built with FastAPI, SQLAlchemy, and Celery.

## Prerequisites

- Python 3.14 and uv is required
- Docker for Postgres and Redis

## Setup

```sh
git clone https://github.com/BakshishArora/TaskFlow.git
cd TaskFlow

# install dependencies
uv sync

# start Postgres and Redis
docker compose up -d
```

Run the server:

With reload

```sh
make dev
```

or:

```sh
make run
```

The API is available at `http://localhost:8000` and the interactive docs at
`http://localhost:8000/docs`. Tables are created automatically on startup.

## Configuration

All settings are read from environment variables and have defaults that match
the `docker compose` setup, so local development works out of the box.
See `.env.example` for the full list. The app does not load `.env` files
automatically; export variables in your shell (or via direnv) if you need to
override the defaults.

| Variable                 | Default                                                    | Purpose                        |
| ------------------------ | ---------------------------------------------------------- | ------------------------------ |
| `DATABASE_URL`           | `postgresql+psycopg://root:1234@localhost:5432/taskdb`     | SQLAlchemy connection string   |
| `REDIS_URL`              | `redis://localhost:6379/0`                                 | Celery broker + task cache     |
| `TASKFLOW_SECRET`        | `s3cr3t`                                                   | JWT signing secret             |
| `CELERY_TASK_ALWAYS_EAGER` | `false`                                                  | Run Celery tasks in-process    |

Set `CELERY_TASK_ALWAYS_EAGER=true` to run notification tasks synchronously without a worker (used by the test suite).

## Celery worker

Notification tasks are dispatched through Redis. Start a worker in a separate
terminal:

```sh
make celery
```

## Tests

Tests require PostgreSQL and Redis running (the suite creates a separate
`taskdb_test` database):

```sh
make test
```

## Linting

Used Ruff for linting and formatting

```sh
make lint
make format
```

## API overview

- `POST /auth/login` - login, or create the user on first login; returns a JWT
- `GET /auth/users` - get the current user's details
- `DELETE /auth/users` - delete the current user
- `GET /health` - health check
- `GET /metrics` - list all recorded API metrics (public, no auth required)
- `GET/POST /projects` - list/create projects
- `PUT/DELETE /projects/{project_id}` - update/delete a project
- `GET/POST /projects/{project_id}/tasks` - list/create tasks (list is cached in Redis)
- `PUT/DELETE /projects/{project_id}/tasks/{task_id}` - update/delete a task

All `/projects` and `/auth/users` routes require the `Authorization: Bearer <token>`
header.

## Metrics

Authenticated requests to any endpoint are automatically recorded with their
endpoint path, status code, timestamp, and user id. The `GET /metrics` endpoint
(public, not itself recorded) returns the full history of these metrics.

## Docker image

```sh
docker build -t taskflow .
docker run -p 8000:8000 taskflow
```
