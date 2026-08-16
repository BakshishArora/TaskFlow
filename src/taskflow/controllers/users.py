from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from taskflow.db import SessionLocal
from taskflow.models import Project as ProjectModel
from taskflow.models import Task as TaskModel
from taskflow.models import User as UserModel
from taskflow.utils.passwords import hash_password


class User(BaseModel):
    model_config = ConfigDict(validate_assignment=True, from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    username: str
    password_hash: str


def clear_users() -> None:
    with SessionLocal() as session:
        session.query(UserModel).delete()
        session.commit()


def get_user_by_id(user_id: UUID) -> User | None:
    with SessionLocal() as session:
        row = session.query(UserModel).filter(UserModel.id == str(user_id)).first()
        return User.model_validate(row) if row is not None else None


def get_user_by_username(username: str) -> User | None:
    with SessionLocal() as session:
        row = session.query(UserModel).filter(UserModel.username == username).first()
        return User.model_validate(row) if row is not None else None


def create_user(username: str, password: str, user_id: UUID | None = None) -> User:
    user = User(
        id=str(user_id) if user_id is not None else str(uuid4()),
        username=username,
        password_hash=hash_password(password),
    )
    with SessionLocal() as session:
        row = UserModel(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
        )
        session.add(row)
        session.commit()
    return user


def list_users() -> list[User]:
    with SessionLocal() as session:
        rows = session.query(UserModel).all()
        return [User.model_validate(row) for row in rows]


def delete_user(user_id: UUID) -> User | None:
    with SessionLocal() as session:
        row = session.get(UserModel, str(user_id))
        if row is None:
            return None
        user = User.model_validate(row)
        orphaned_project_ids = [
            pid
            for (pid,) in (
                session.query(ProjectModel.id)
                .filter(ProjectModel.owner_id == user_id)
                .all()
            )
        ]
        session.query(ProjectModel).filter(ProjectModel.owner_id == user_id).update(
            {ProjectModel.owner_id: None}
        )
        if orphaned_project_ids:
            session.query(TaskModel).filter(
                TaskModel.project_id.in_(orphaned_project_ids)
            ).update({TaskModel.assignee: "Orphaned"})
        session.query(TaskModel).filter(TaskModel.assignee == str(user_id)).update(
            {TaskModel.assignee: "Orphaned"}
        )
        session.delete(row)
        session.commit()
        return user
