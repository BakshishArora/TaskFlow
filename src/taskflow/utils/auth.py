import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException, Request

_SECRET = os.environ.get(
    "TASKFLOW_SECRET", "s3cr3t"
)
_ALGORITHM = "HS256"


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


def get_current_user(request: Request) -> UUID:
    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing authorization header")
    return decode_token(header.removeprefix("Bearer "))
