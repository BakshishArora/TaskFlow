from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from taskflow.controllers import projects, tasks
from taskflow.utils.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])

CurrentUser = Annotated[UUID, Depends(get_current_user)]


def _require_owned_project(project_id: str, user_id: UUID) -> projects.Project:
    project = projects.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    if project.owner_id != user_id:
        raise HTTPException(status_code=403, detail="not authorized")
    return project


@router.get("")
def list_projects(user_id: CurrentUser):
    return projects.list_projects(owner_id=user_id)


@router.get("/{project_id}/tasks")
def list_tasks(
    project_id: UUID,
    user_id: CurrentUser,
):
    _require_owned_project(str(project_id), user_id)
    return tasks.list_tasks(str(project_id))
