from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator

from taskflow.controllers import tasks as task_controller
from taskflow.utils.validators import validate_title

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    title: str
    description: str = ""

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str) -> str:
        validate_title(value)
        return value.strip()


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    completed: bool | None = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str | None) -> str | None:
        if value is not None:
            validate_title(value)
            return value.strip()
        return value

    @model_validator(mode="after")
    def _reject_explicit_null(self) -> TaskUpdate:
        for field in ("title", "description", "completed"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} must not be null")
        return self


@router.get("")
def list_tasks():
    return task_controller.list_tasks()


@router.post("", status_code=201)
def create_task(payload: TaskIn):
    return task_controller.create_task(payload.title, payload.description)


@router.get("/{task_id}")
def get_task(task_id: UUID):
    task = task_controller.get_task(str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.put("/{task_id}")
def update_task(task_id: UUID, payload: TaskUpdate):
    task = task_controller.update_task(
        str(task_id),
        title=payload.title,
        description=payload.description,
        completed=payload.completed,
    )
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: UUID):
    if not task_controller.delete_task(str(task_id)):
        raise HTTPException(status_code=404, detail="task not found")
