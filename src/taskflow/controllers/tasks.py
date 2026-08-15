from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taskflow.utils.validators import validate_title


class Task(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    completed: bool = False

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str) -> str:
        validate_title(value)
        return value.strip()


_tasks: dict[str, Task] = {}


def clear_tasks() -> None:
    _tasks.clear()


def list_tasks() -> list[Task]:
    return list(_tasks.values())


def create_task(title: str, description: str = "") -> Task:
    task = Task(title=title, description=description)
    _tasks[task.id] = task
    return task


def get_task(task_id: str) -> Task | None:
    return _tasks.get(task_id)


def update_task(
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    completed: bool | None = None,
) -> Task | None:
    task = _tasks.get(task_id)
    if task is None:
        return None
    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if completed is not None:
        task.completed = completed
    return task


def delete_task(task_id: str) -> bool:
    return _tasks.pop(task_id, None) is not None
