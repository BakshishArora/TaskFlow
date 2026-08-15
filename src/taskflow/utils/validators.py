from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException

from taskflow.controllers import projects


def validate_title(title: str) -> None:
    if title is None or not title.strip():
        raise ValueError("title must not be empty")


def validate_due_date(due_date: date) -> None:
    if due_date < datetime.now(UTC).date():
        raise ValueError("due date is already expired")


def _require_owned_project(project_id: str, user_id: UUID) -> projects.Project:
    project = projects.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    if project.owner_id != user_id:
        raise HTTPException(status_code=403, detail="not authorized")
    return project
