from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from taskflow.controllers import tasks as task_controller

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    title: str
    description: str = ""


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    completed: bool | None = None


@router.get("")
def list_tasks():
    return task_controller.list_tasks()


@router.post("", status_code=201)
def create_task(payload: TaskIn):
    try:
        return task_controller.create_task(payload.title, payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{task_id}")
def get_task(task_id: int):
    task = task_controller.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.put("/{task_id}")
def update_task(task_id: int, payload: TaskUpdate):
    try:
        task = task_controller.update_task(
            task_id,
            title=payload.title,
            description=payload.description,
            completed=payload.completed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not task_controller.delete_task(task_id):
        raise HTTPException(status_code=404, detail="task not found")