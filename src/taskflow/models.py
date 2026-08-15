from datetime import date
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Date, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from taskflow.db import Base


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


def _status_values(enum_type: type[TaskStatus]) -> list[str]:
    return [member.value for member in enum_type]


def _uuid() -> str:
    return str(uuid4())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, values_callable=_status_values),
        nullable=False,
        default=TaskStatus.TODO,
    )
    assignee: Mapped[str | None] = mapped_column(String, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
