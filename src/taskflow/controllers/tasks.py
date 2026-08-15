from datetime import date
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taskflow.db import SessionLocal
from taskflow.models import Task as TaskModel
from taskflow.models import TaskStatus
from taskflow.utils.validators import validate_due_date, validate_title


class Task(BaseModel):
    model_config = ConfigDict(validate_assignment=True, from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    title: str
    status: TaskStatus = TaskStatus.TODO
    assignee: str | None = None
    due_date: date
    description: str = ""

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str) -> str:
        validate_title(value)
        return value.strip()


class TaskPage(BaseModel):
    items: list[Task]
    total: int
    page: int
    page_size: int


def clear_tasks() -> None:
    with SessionLocal() as session:
        session.query(TaskModel).delete()
        session.commit()


def create_task(
    project_id: str,
    title: str,
    status: TaskStatus = TaskStatus.TODO,
    assignee: str | None = None,
    due_date: date = ...,
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


def list_tasks(
    project_id: str,
    status: TaskStatus | None = None,
    assignee: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> TaskPage:
    with SessionLocal() as session:
        query = session.query(TaskModel).filter(TaskModel.project_id == project_id)
        if status is not None:
            query = query.filter(TaskModel.status == status)
        if assignee:
            query = query.filter(TaskModel.assignee == assignee)
        if due_from is not None:
            query = query.filter(TaskModel.due_date >= due_from)
        if due_to is not None:
            query = query.filter(TaskModel.due_date <= due_to)
        total = query.count()
        rows = (
            query.order_by(TaskModel.due_date, TaskModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return TaskPage(
            items=[Task.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )


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
        if due_date is not None:
            validate_due_date(due_date)
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
