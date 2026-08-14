import itertools
from dataclasses import dataclass

from taskflow.utils.validators import validate_title


@dataclass
class Task:
    id: int
    title: str
    description: str = ""
    completed: bool = False


_tasks: dict[int, Task] = {}
_ids: itertools.count = itertools.count(1)


def clear_tasks() -> None:
    global _ids
    _tasks.clear()
    _ids = itertools.count(1)


def list_tasks() -> list[Task]:
    return sorted(_tasks.values(), key=lambda t: t.id)


def create_task(title: str, description: str = "") -> Task:
    validate_title(title)
    task = Task(id=next(_ids), title=title.strip(), description=description)
    _tasks[task.id] = task
    return task


def get_task(task_id: int) -> Task | None:
    return _tasks.get(task_id)


def update_task(
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    completed: bool | None = None,
) -> Task | None:
    task = _tasks.get(task_id)
    if task is None:
        return None
    if title is not None:
        validate_title(title)
        task.title = title.strip()
    if description is not None:
        task.description = description
    if completed is not None:
        task.completed = completed
    return task


def delete_task(task_id: int) -> bool:
    return _tasks.pop(task_id, None) is not None