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

## Architecture

### System overview

TaskFlow is a layered FastAPI application backed by PostgreSQL with Redis used
both as a Celery broker and a read-through cache for task lists.

```
Client ── HTTP ──> FastAPI routes ──> controllers ──> SQLAlchemy models ──> PostgreSQL
                     │                    │
                     │ JWT auth           │ Celery task (async notifications)
                     ▼                    ▼
                 utils/auth           Redis (broker) ──> worker ──> notifications table
```

- **Routes** (`routes/`) own the HTTP surface: URL params, request/response
  bodies (Pydantic), auth dependency, and HTTP errors.
- **Controllers** (`controllers/`) own the business logic and expose plain
  Pydantic view-models to the routes.
- **Models** (`models.py`) are the SQLAlchemy ORM entities mapped to PostgreSQL.
- Tables are created automatically at startup (`Base.metadata.create_all`).

### Entity relationships


- A user **owns** many projects. Deleting a user does **not** delete their
  projects: `owner_id` is set to `NULL`, and any tasks assigned to the deleted
  user get their `assignee` rewritten to the literal string `"Orphaned"`.
- A project **contains** many tasks. Deleting a project deletes its tasks
  (explicit delete in the controller) and cascades to notifications.
- A task **assignee** is a reference to a user *by username* (not a foreign
  key). It is validated at write time to reference an existing user.
- Notifications record **who** (user_id) should be told **what** changed on
  **which** task. They are produced asynchronously whenever a task's status
  changes (project owner + assignee).
- A `Metric` row is recorded for every authenticated request (except `/metrics`
  itself), capturing endpoint, status code, timestamp, and user.

### Entity parameters

**User**

| Field         | Type           | Constraints                    |
| ------------- | -------------- | ------------------------------ |
| `id`          | string (UUID)  | primary key, default `uuid4`   |
| `username`    | string         | required, unique, indexed      |
| `password_hash` | string       | required, bcrypt hash          |

**Project**

| Field      | Type               | Constraints                                |
| ---------- | ------------------ | ------------------------------------------ |
| `id`       | string (UUID)      | primary key, default `uuid4`               |
| `name`     | string             | required, non-empty, trimmed               |
| `owner_id` | UUID \| null       | indexed; set to `NULL` when owner is deleted |

**Task**

| Field         | Type                | Constraints                                            |
| ------------- | ------------------- | ------------------------------------------------------ |
| `id`          | string (UUID)       | primary key, default `uuid4`                           |
| `project_id`  | string (UUID)       | required, FK → `projects.id`, `ON DELETE CASCADE`, indexed |
| `title`       | string              | required, non-empty, trimmed                           |
| `status`      | enum                | `todo` \| `in_progress` \| `done`, default `todo`      |
| `assignee`    | string \| null      | username of an existing user                           |
| `due_date`    | date                | required, must not be in the past                      |
| `description` | string              | default `""`                                           |

**Notification**

| Field        | Type     | Constraints                              |
| ------------ | -------- | ---------------------------------------- |
| `id`         | string   | primary key, default `uuid4`             |
| `user_id`    | string   | indexed, recipient of the notification   |
| `task_id`    | string   | FK → `tasks.id`, `ON DELETE CASCADE`, indexed |
| `message`    | string   | required                                 |
| `created_at` | datetime | UTC, timezone-aware, default now         |
| `read`       | boolean  | default `false`                          |

**Metric**

| Field         | Type     | Constraints                  |
| ------------- | -------- | ---------------------------- |
| `id`          | string   | primary key, default `uuid4` |
| `endpoint`    | string   | required                     |
| `status_code` | integer  | required                     |
| `timestamp`   | datetime | UTC, timezone-aware          |
| `user_id`     | string   | indexed                      |

### API usability

**Authentication**

Every `/projects` and `/auth/users` route requires
`Authorization: Bearer <jwt>`. Tokens are HS256 JWTs signed with
`TASKFLOW_SECRET` and expire after 24 hours. Login creates the user on first
login and otherwise verifies the password. Ownership is enforced per request:
a caller can only read/write their own projects (403 otherwise).

**Endpoint reference**

| Method & path                                        | Auth | Body / query params                                            | Notes                                   |
| ---------------------------------------------------- | ---- | -------------------------------------------------------------- | --------------------------------------- |
| `POST /auth/login`                                   | –    | `{username, password}`                                         | Creates user on first login; returns `{token}` |
| `GET /auth/users`                                    | yes  | –                                                              | Current user, excludes `password_hash`  |
| `DELETE /auth/users`                                 | yes  | –                                                              | Deletes user; orphans projects/assignees |
| `GET /health`                                        | –    | –                                                              | Health check                            |
| `GET /metrics`                                       | –    | –                                                              | All recorded API metrics                |
| `GET /projects`                                      | yes  | –                                                              | Projects owned by the caller            |
| `POST /projects`                                     | yes  | `{name}`                                                       | 201                                     |
| `PUT /projects/{project_id}`                         | yes  | `{name?, owner_id?}`                                           | 404 if missing, 403 if not owner        |
| `DELETE /projects/{project_id}`                      | yes  | –                                                              | Deletes tasks too                       |
| `GET /projects/{project_id}/tasks`                   | yes  | `status`, `assignee`, `due_from`, `due_to`, `page`, `page_size` | Cached in Redis (2 h TTL); paginated    |
| `POST /projects/{project_id}/tasks`                  | yes  | `{title, status?, assignee?, due_date, description?}`           | 201; invalidates cache                  |
| `PUT /projects/{project_id}/tasks/{task_id}`         | yes  | `{status?, assignee?, due_date?}`                               | Status change triggers async notification |
| `DELETE /projects/{project_id}/tasks/{task_id}`      | yes  | –                                                              | Invalidates cache                       |

**Query filtering & pagination**

`GET /projects/{project_id}/tasks` supports filtering by `status`
(`todo`/`in_progress`/`done`), `assignee`, and a `due_from`/`due_to` date
range. Results are ordered by `due_date` then `id`, and paginated with
`page` (≥ 1) and `page_size` (1–100, default 20). The response envelope is
`{items, total, page, page_size}`.

**Validation & errors**

- Request/response bodies use `extra="forbid"`, so unknown fields are
  rejected with a 422.
- `title` must be non-empty; `due_date` must not be in the past; `assignee`
  must reference an existing user.
- Error codes: `401` missing/invalid/expired token, `403` project not owned,
  `404` missing project or task, `422` validation failure.

**Caching**

Task listings are cached in Redis under
`tasks_of_<project_id>:<md5 of params>` with a 2-hour TTL. Any task/project
create, update, or delete invalidates all cached listings for that project.
Redis failures degrade gracefully — the request falls through to the database.

**Async notifications**

When a task's status changes, `notify_status_change` is dispatched to Celery
(Redis broker) and writes a `Notification` for the project owner and the
assignee. The task retries up to 3 times with backoff on failure. Set
`CELERY_TASK_ALWAYS_EAGER=true` to run it in-process (used by the test suite)
instead of requiring a running worker.

## Docker image

```sh
docker build -t taskflow .
docker run -p 8000:8000 taskflow
```

## Tradeoffs and things I would have done with more time

- In deployment, I have used celery synchronously in cloud, if I would have had more time to implement I would have launched celery workers to to make the notification process completely asynchronous.

- Currently the requests are handled synchronously, i.e. multiple requests from the user are based on timestamp and are executed in a blocking manner. If I had more time I would hav created the mechanism asynchronously.

- There is a no friction on-boarding i.e. whenever a new user tries to access the api, it can without going through a robust mechanism of SignUp. If I had more time I would have established a robust mechanism for user registration and email verification. 

- In current deployment, the DELETE Apis execute hard deletion, it removes users, projects and tasks completely without any backup. If I would have had more time I would have implemented soft deletion mechanism.