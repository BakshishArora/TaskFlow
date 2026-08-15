from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taskflow.utils.validators import validate_title


class Project(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    owner_id: UUID

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        validate_title(value)
        return value.strip()


_projects: dict[str, Project] = {}


def clear_projects() -> None:
    _projects.clear()


def create_project(name: str, owner_id: UUID) -> Project:
    project = Project(name=name, owner_id=owner_id)
    _projects[project.id] = project
    return project


def get_project(project_id: str) -> Project | None:
    return _projects.get(project_id)


def list_projects(owner_id: UUID) -> list[Project]:
    return [p for p in _projects.values() if p.owner_id == owner_id]
