from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from taskflow.controllers import projects, tasks, users
from taskflow.main import app
from taskflow.utils import auth

client = TestClient(app)

OWNER_1 = uuid4()
OWNER_2 = uuid4()


@pytest.fixture(autouse=True)
def reset_store():
    projects.clear_projects()
    tasks.clear_tasks()
    users.clear_users()
    users.create_user("owner1", "pw12345", user_id=OWNER_1)
    users.create_user("owner2", "pw12345", user_id=OWNER_2)


@pytest.fixture
def auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {auth.create_token(user_id=OWNER_1)}"}


@pytest.fixture
def other_auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {auth.create_token(user_id=OWNER_2)}"}


def _create_project(name: str, owner_id: UUID) -> str:
    return projects.create_project(name, owner_id=owner_id).id


def test_list_tasks_happy_path(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tasks.create_task(pid, "One")
    tasks.create_task(pid, "Two")
    resp = client.get(f"/projects/{pid}/tasks", headers=auth_header)
    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()] == ["One", "Two"]


def test_list_tasks_requires_auth():
    resp = client.get(f"/projects/{uuid4()}/tasks")
    assert resp.status_code == 401


def test_list_tasks_invalid_token():
    resp = client.get(
        f"/projects/{uuid4()}/tasks",
        headers={"Authorization": "Bearer garbage"},
    )
    assert resp.status_code == 401


def test_list_tasks_forbidden_other_users_project(other_auth_header):
    pid = _create_project("Mine", owner_id=OWNER_1)
    resp = client.get(f"/projects/{pid}/tasks", headers=other_auth_header)
    assert resp.status_code == 403


def test_list_tasks_missing_project_returns_404(auth_header):
    resp = client.get(f"/projects/{uuid4()}/tasks", headers=auth_header)
    assert resp.status_code == 404


def test_create_project_endpoint_removed(auth_header):
    resp = client.post("/projects", json={"name": "X"}, headers=auth_header)
    assert resp.status_code == 405


def test_list_own_projects(auth_header):
    _create_project("Mine", owner_id=OWNER_1)
    _create_project("Also mine", owner_id=OWNER_1)
    _create_project("Yours", owner_id=OWNER_2)
    resp = client.get("/projects", headers=auth_header)
    assert resp.status_code == 200
    assert [p["name"] for p in resp.json()] == ["Mine", "Also mine"]


def test_list_projects_requires_auth():
    resp = client.get("/projects")
    assert resp.status_code == 401


def test_create_task_endpoint_removed(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "X"},
        headers=auth_header,
    )
    assert resp.status_code == 405
