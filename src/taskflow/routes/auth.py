from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from taskflow.controllers import users
from taskflow.utils.auth import create_token
from taskflow.utils.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


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