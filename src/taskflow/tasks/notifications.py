import logging

from taskflow.celery_app import celery_app
from taskflow.controllers.notifications import create_status_change_notifications

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def notify_status_change(
    self,
    task_id: str,
    old_status: str,
    new_status: str,
) -> int:
    try:
        return create_status_change_notifications(task_id, old_status, new_status)
    except Exception:
        logger.exception("Failed to write notifications for task %s", task_id)
        raise