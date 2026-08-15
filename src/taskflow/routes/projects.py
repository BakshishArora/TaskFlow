from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, field_validator

from taskflow.controllers import projects, tasks
from taskflow.models import TaskStatus
from taskflow.utils.auth import get_current_user
from taskflow.utils.validators import _require_owned_project, validate_title

router = APIRouter(prefix="/projects", tags=["projects"])

CurrentUser = Annotated[UUID, Depends(get_current_user)]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        validate_title(value)
        return value.strip()


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    owner_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str | None) -> str | None:
        if value is not None:
            validate_title(value)
            return value.strip()
        return value


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


@router.post("", status_code=201)
def create_project(payload: ProjectCreate, user_id: CurrentUser):
    return projects.create_project(payload.name, owner_id=user_id)


@router.put("/{project_id}")
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    user_id: CurrentUser,
):
    _require_owned_project(str(project_id), user_id)
    updated = projects.update_project(str(project_id), payload.name, payload.owner_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="project not found")
    return updated


@router.get("")
def list_projects(user_id: CurrentUser):
    return projects.list_projects(owner_id=user_id)


@router.get("/{project_id}/tasks")
def list_tasks(
    project_id: UUID,
    user_id: CurrentUser,
    status: TaskStatus | None = None,
    assignee: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    _require_owned_project(str(project_id), user_id)
    return tasks.list_tasks(
        str(project_id),
        status=status,
        assignee=assignee,
        due_from=due_from,
        due_to=due_to,
        page=page,
        page_size=page_size,
    )


@router.post("/{project_id}/tasks", status_code=201)
def create_task(
    project_id: UUID,
    payload: TaskCreate,
    user_id: CurrentUser,
):
    _require_owned_project(str(project_id), user_id)
    return tasks.create_task(
        str(project_id),
        payload.title,
        status=payload.status,
        assignee=payload.assignee,
        due_date=payload.due_date,
        description=payload.description,
    )
