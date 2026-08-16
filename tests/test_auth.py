from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from taskflow.controllers import projects, tasks, users
from taskflow.main import app
from taskflow.utils import auth

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    users.clear_users()


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


def test_delete_user_orphans_projects_and_tasks():
    owner_id = uuid4()
    users.create_user("orphan_owner", "pw12345", user_id=owner_id)
    other_id = uuid4()
    users.create_user("other", "pw12345", user_id=other_id)
    pid = projects.create_project("Mine", owner_id=owner_id).id
    other_pid = projects.create_project("Other", owner_id=other_id).id
    tid = tasks.create_task(pid, "In my project", due_date=date(2026, 9, 1)).id
    other_tid = tasks.create_task(
        other_pid, "Not mine", due_date=date(2026, 9, 1)
    ).id
    assigned_tid = tasks.create_task(
        other_pid, "Assigned to me", assignee=str(owner_id),
        due_date=date(2026, 9, 1),
    ).id

    token = auth.create_token(user_id=owner_id)
    resp = client.delete(
        "/auth/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(owner_id)
    assert "password_hash" not in body
    assert users.get_user_by_id(owner_id) is None
    assert projects.get_project(pid).owner_id is None
    assert projects.get_project(other_pid).owner_id == other_id
    assert tasks.get_task(tid).assignee == "Orphaned"
    assert tasks.get_task(assigned_tid).assignee == "Orphaned"
    assert tasks.get_task(other_tid).assignee is None


def test_delete_user_requires_auth():
    resp = client.delete("/auth/users")
    assert resp.status_code == 401
