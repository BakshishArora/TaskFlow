import hashlib
import json
import logging
import os
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_TASKS_TTL_SECONDS = 2 * 60 * 60

_redis = Redis.from_url(REDIS_URL, decode_responses=True)


def _tasks_key(project_id: str, params: dict[str, Any]) -> str:
    canonical = json.dumps(params, sort_keys=True, default=str)
    digest = hashlib.md5(canonical.encode()).hexdigest()
    return f"tasks_of_{project_id}:{digest}"


def get_tasks(project_id: str, params: dict[str, Any]) -> dict | None:
    try:
        raw = _redis.get(_tasks_key(project_id, params))
    except RedisError:
        logger.exception("Redis read failed for project %s", project_id)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Corrupt cached tasks payload for project %s", project_id)
        return None


def set_tasks(project_id: str, params: dict[str, Any], payload: dict) -> None:
    try:
        _redis.set(
            _tasks_key(project_id, params),
            json.dumps(payload),
            ex=_TASKS_TTL_SECONDS,
        )
    except RedisError:
        logger.exception("Redis write failed for project %s", project_id)


def invalidate_tasks(project_id: str) -> None:
    try:
        keys = list(_redis.scan_iter(f"tasks_of_{project_id}:*"))
        if keys:
            _redis.delete(*keys)
    except RedisError:
        logger.exception("Redis invalidation failed for project %s", project_id)