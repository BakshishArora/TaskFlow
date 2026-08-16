from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from taskflow.controllers import users
from taskflow.utils.auth import create_token, get_current_user
from taskflow.utils.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

CurrentUser = Annotated[UUID, Depends(get_current_user)]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, str]:
    user = users.get_user_by_username(payload.username)
    if user is None:
        user = users.create_user(payload.username, payload.password)
    elif not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"token": create_token(user_id=UUID(user.id))}


@router.delete("/users")
def delete_user(current_user: CurrentUser) -> dict[str, str]:
    deleted = users.delete_user(current_user)
    return deleted.model_dump(exclude={"password_hash"})
