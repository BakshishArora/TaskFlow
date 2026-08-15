import os
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from taskflow.controllers import users

_SECRET = os.environ.get("TASKFLOW_SECRET", "s3cr3t")
_ALGORITHM = "HS256"

bearer = HTTPBearer(auto_error=False)


def create_token(user_id: UUID, secret: str | None = None) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(days=1),
    }
    return jwt.encode(payload, secret or _SECRET, algorithm=_ALGORITHM)


def decode_token(token: str, secret: str | None = None) -> UUID:
    try:
        payload = jwt.decode(token, secret or _SECRET, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return UUID(payload["sub"])


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> UUID:
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing authorization header")
    user_id = decode_token(credentials.credentials)
    if users.get_user_by_id(user_id) is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user_id
