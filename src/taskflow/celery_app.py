import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "taskflow", broker=REDIS_URL, include=["taskflow.tasks.notifications"]
)

celery_app.conf.update(
    task_always_eager=os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower()
    in ("1", "true", "yes"),
    task_eager_propagates=True,
    task_track_started=True,
)
