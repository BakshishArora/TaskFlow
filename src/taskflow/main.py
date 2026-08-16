from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from taskflow.controllers import metrics, users
from taskflow.db import Base, engine
from taskflow.routes import auth, health, projects
from taskflow.utils.auth import decode_token

_METRICS_PATHS = {"/metrics", "/metrics/"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="TaskFlow", lifespan=lifespan)


def _authenticated_user_id(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer ") :].strip()
    try:
        user_id = decode_token(token)
    except HTTPException:
        return None
    if users.get_user_by_id(user_id) is None:
        return None
    return str(user_id)


@app.middleware("http")
async def _record_metrics_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in _METRICS_PATHS:
        return response
    user_id = _authenticated_user_id(request)
    if user_id is not None:
        metrics.record_metric(request.url.path, response.status_code, user_id)
    return response


app.include_router(auth.router)
app.include_router(health.router)
app.include_router(projects.router)
