from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from taskflow.controllers import users
from taskflow.main import app
from taskflow.utils import auth

client = TestClient(app)


def test_create_token_roundtrips_user_id():
    uid = uuid4()
    token = auth.create_token(user_id=uid)
    assert auth.decode_token(token) == uid


def test_decode_garbage_raises():
    with pytest.raises(HTTPException) as exc:
        auth.decode_token("not.a.jwt")
    assert exc.value.status_code == 401


def test_decode_token_wrong_secret_raises():
    token = auth.create_token(user_id=uuid4())
    with pytest.raises(HTTPException):
        auth.decode_token(token, secret="other-secret-0123456789abcdefghi")


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_returns_id_for_existing_user():
    user = users.create_user("alice", "pw12345")
    token = auth.create_token(user_id=UUID(user.id))
    assert auth.get_current_user(_credentials(token)) == UUID(user.id)


def test_get_current_user_missing_credentials_raises():
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(None)
    assert exc.value.status_code == 401


def test_get_current_user_invalid_token_raises():
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(_credentials("garbage"))
    assert exc.value.status_code == 401


def test_get_current_user_nonexistent_user_raises():
    token = auth.create_token(user_id=uuid4())
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(_credentials(token))
    assert exc.value.status_code == 401


def test_swagger_security_scheme_configured():
    schema = client.get("/openapi.json").json()
    assert "HTTPBearer" in schema["components"]["securitySchemes"]
    assert schema["paths"]["/projects"]["get"]["security"] == [{"HTTPBearer": []}]
