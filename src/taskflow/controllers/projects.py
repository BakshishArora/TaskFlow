from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taskflow.db import SessionLocal
from taskflow.models import Project as ProjectModel
from taskflow.utils.validators import validate_title


class Project(BaseModel):
    model_config = ConfigDict(validate_assignment=True, from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    owner_id: UUID

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        validate_title(value)
        return value.strip()


def clear_projects() -> None:
    with SessionLocal() as session:
        session.query(ProjectModel).delete()
        session.commit()


def create_project(name: str, owner_id: UUID) -> Project:
    project = Project(name=name, owner_id=owner_id)
    with SessionLocal() as session:
        row = ProjectModel(id=project.id, name=project.name, owner_id=project.owner_id)
        session.add(row)
        session.commit()
    return project


def get_project(project_id: str) -> Project | None:
    with SessionLocal() as session:
        row = session.get(ProjectModel, project_id)
        return Project.model_validate(row) if row is not None else None


def update_project(
    project_id: str,
    name: str | None = None,
    owner_id: UUID | None = None,
) -> Project | None:
    with SessionLocal() as session:
        row = session.get(ProjectModel, project_id)
        if row is None:
            return None
        data = Project.model_validate(row).model_dump()
        if name is not None:
            data["name"] = name
        if owner_id is not None:
            data["owner_id"] = owner_id
        project = Project(**data)
        row.name = project.name
        row.owner_id = project.owner_id
        session.commit()
        return Project.model_validate(row)


def list_projects(owner_id: UUID) -> list[Project]:
    with SessionLocal() as session:
        rows = (
            session.query(ProjectModel).filter(ProjectModel.owner_id == owner_id).all()
        )
        return [Project.model_validate(row) for row in rows]
