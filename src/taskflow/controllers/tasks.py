from datetime import date
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taskflow.db import SessionLocal
from taskflow.models import Task as TaskModel
from taskflow.models import TaskStatus
from taskflow.utils.validators import validate_title


class Task(BaseModel):
    model_config = ConfigDict(validate_assignment=True, from_attributes=True)

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


def clear_tasks() -> None:
    with SessionLocal() as session:
        session.query(TaskModel).delete()
        session.commit()


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
    with SessionLocal() as session:
        row = TaskModel(
            id=task.id,
            project_id=task.project_id,
            title=task.title,
            status=task.status,
            assignee=task.assignee,
            due_date=task.due_date,
            description=task.description,
        )
        session.add(row)
        session.commit()
    return task


def list_tasks(project_id: str) -> list[Task]:
    with SessionLocal() as session:
        rows = session.query(TaskModel).filter(TaskModel.project_id == project_id).all()
        return [Task.model_validate(row) for row in rows]


def get_task(task_id: str) -> Task | None:
    with SessionLocal() as session:
        row = session.get(TaskModel, task_id)
        return Task.model_validate(row) if row is not None else None


def update_task(
    task_id: str,
    status: TaskStatus | None = None,
    assignee: str | None = None,
    due_date: date | None = None,
) -> Task | None:
    with SessionLocal() as session:
        row = session.get(TaskModel, task_id)
        if row is None:
            return None
        data = Task.model_validate(row).model_dump()
        if status is not None:
            data["status"] = status
        if assignee is not None:
            data["assignee"] = assignee
        if due_date is not None:
            data["due_date"] = due_date
        task = Task(**data)
        row.status = task.status
        row.assignee = task.assignee
        row.due_date = task.due_date
        session.commit()
        return Task.model_validate(row)


def delete_task(task_id: str) -> bool:
    with SessionLocal() as session:
        row = session.get(TaskModel, task_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True
