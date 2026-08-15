from datetime import date
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taskflow.utils.validators import validate_title


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    title: str
    status: TaskStatus = TaskStatus.TODO
    assignee: str | None = None
    due_date: date | None = None
    description: str = ""

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str) -> str:
        validate_title(value)
        return value.strip()


_tasks: dict[str, Task] = {}


def clear_tasks() -> None:
    _tasks.clear()


def create_task(
    project_id: str,
    title: str,
    status: TaskStatus = TaskStatus.TODO,
    assignee: str | None = None,
    due_date: date | None = None,
    description: str = "",
) -> Task:
    task = Task(
        project_id=project_id,
        title=title,
        status=status,
        assignee=assignee,
        due_date=due_date,
        description=description,
    )
    _tasks[task.id] = task
    return task


def list_tasks(project_id: str) -> list[Task]:
    return [t for t in _tasks.values() if t.project_id == project_id]


def get_task(task_id: str) -> Task | None:
    return _tasks.get(task_id)


def update_task(
    task_id: str,
    status: TaskStatus | None = None,
    assignee: str | None = None,
    due_date: date | None = None,
) -> Task | None:
    task = _tasks.get(task_id)
    if task is None:
        return None
    if status is not None:
        task.status = status
    if assignee is not None:
        task.assignee = assignee
    if due_date is not None:
        task.due_date = due_date
    return task


def delete_task(task_id: str) -> bool:
    return _tasks.pop(task_id, None) is not None
