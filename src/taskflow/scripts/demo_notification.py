"""Demo: trigger a task status change and print the queued notifications."""

import time
import uuid
from datetime import UTC, datetime, timedelta

from taskflow.controllers import projects, tasks
from taskflow.controllers.notifications import list_notifications_for_user
from taskflow.db import Base, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    owner = uuid.uuid4()
    project = projects.create_project("Demo Project", owner_id=owner)
    task = tasks.create_task(
        project.id,
        "Demo task",
        assignee="alice",
        due_date=datetime.now(UTC).date() + timedelta(days=7),
    )
    print(f"Created demo project {project.id} and task {task.id}")

    tasks.update_task(task.id, status="in_progress")
    print("Triggered status change -> 'in_progress'; waiting for Celery worker...")

    rows = []
    for _ in range(20):
        time.sleep(0.5)
        rows = list_notifications_for_user(str(owner))
        if rows:
            break

    if not rows:
        print("No notifications written yet — is the worker running and Redis up?")
        return
    for row in rows:
        print(f"  [{row.id}] {row.message} (user={row.user_id}, read={row.read})")


if __name__ == "__main__":
    main()
