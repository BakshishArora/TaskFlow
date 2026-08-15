from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from taskflow.db import SessionLocal
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


def get_user_by_username(username: str) -> User | None:
    with SessionLocal() as session:
        row = (
            session.query(UserModel).filter(UserModel.username == username).first()
        )
        return User.model_validate(row) if row is not None else None


def create_user(username: str, password: str) -> User:
    user = User(username=username, password_hash=hash_password(password))
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