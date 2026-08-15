from datetime import UTC, date, datetime, timedelta
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
    tasks.create_task(pid, "One", due_date=date(2026, 9, 1))
    tasks.create_task(pid, "Two", due_date=date(2026, 9, 1))
    resp = client.get(f"/projects/{pid}/tasks", headers=auth_header)
    assert resp.status_code == 200
    body = resp.json()
    assert sorted(t["title"] for t in body["items"]) == ["One", "Two"]
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 20


def test_list_tasks_filters_and_paginates(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tasks.create_task(
        pid, "Done alice", status="done", assignee="alice",
        due_date=date(2026, 8, 15),
    )
    tasks.create_task(
        pid, "Todo alice", assignee="alice", due_date=date(2026, 9, 1),
    )
    tasks.create_task(
        pid, "Todo bob", assignee="bob", due_date=date(2026, 10, 1),
    )
    resp = client.get(
        f"/projects/{pid}/tasks",
        params={"status": "done", "assignee": "alice", "page": 1, "page_size": 1},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [t["title"] for t in body["items"]] == ["Done alice"]
    assert body["total"] == 1


def test_list_tasks_due_date_range(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tasks.create_task(pid, "Aug", due_date=date(2026, 8, 15))
    tasks.create_task(pid, "Sep", due_date=date(2026, 9, 1))
    tasks.create_task(pid, "Oct", due_date=date(2026, 10, 1))
    resp = client.get(
        f"/projects/{pid}/tasks",
        params={"due_from": "2026-09-01", "due_to": "2026-10-01"},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert sorted(t["title"] for t in body["items"]) == ["Oct", "Sep"]
    assert body["total"] == 2


def test_list_tasks_invalid_status_returns_422(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.get(
        f"/projects/{pid}/tasks",
        params={"status": "paused"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_list_tasks_invalid_date_returns_422(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.get(
        f"/projects/{pid}/tasks",
        params={"due_from": "not-a-date"},
        headers=auth_header,
    )
    assert resp.status_code == 422


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


def test_create_project(auth_header):
    resp = client.post("/projects", json={"name": "Site"}, headers=auth_header)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Site"
    assert body["owner_id"] == str(OWNER_1)
    assert projects.get_project(body["id"]) is not None


def test_create_project_strips_name(auth_header):
    resp = client.post("/projects", json={"name": "  Site  "}, headers=auth_header)
    assert resp.status_code == 201
    assert resp.json()["name"] == "Site"


def test_create_project_rejects_project_id(auth_header):
    resp = client.post(
        "/projects",
        json={"name": "Site", "id": str(uuid4())},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_create_project_requires_auth():
    resp = client.post("/projects", json={"name": "Site"})
    assert resp.status_code == 401


def test_create_project_blank_name(auth_header):
    resp = client.post("/projects", json={"name": "  "}, headers=auth_header)
    assert resp.status_code == 422


def test_update_project(auth_header):
    pid = _create_project("Old", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}",
        json={"name": "New", "owner_id": str(OWNER_1)},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New"
    assert body["owner_id"] == str(OWNER_1)
    assert projects.get_project(pid).name == "New"


def test_update_project_transfers_ownership(auth_header, other_auth_header):
    pid = _create_project("Mine", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}",
        json={"name": "Mine", "owner_id": str(OWNER_2)},
        headers=auth_header,
    )
    assert resp.status_code == 200
    assert resp.json()["owner_id"] == str(OWNER_2)
    old_owner = client.put(
        f"/projects/{pid}",
        json={"name": "X", "owner_id": str(OWNER_2)},
        headers=auth_header,
    )
    assert old_owner.status_code == 403
    new_owner = client.put(
        f"/projects/{pid}",
        json={"name": "Y", "owner_id": str(OWNER_2)},
        headers=other_auth_header,
    )
    assert new_owner.status_code == 200
    assert new_owner.json()["name"] == "Y"


def test_update_project_requires_auth():
    resp = client.put(
        f"/projects/{uuid4()}",
        json={"name": "X", "owner_id": str(OWNER_1)},
    )
    assert resp.status_code == 401


def test_update_project_forbidden_other_users_project(other_auth_header):
    pid = _create_project("Mine", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}",
        json={"name": "X", "owner_id": str(OWNER_1)},
        headers=other_auth_header,
    )
    assert resp.status_code == 403


def test_update_project_missing_returns_404(auth_header):
    resp = client.put(
        f"/projects/{uuid4()}",
        json={"name": "X", "owner_id": str(OWNER_1)},
        headers=auth_header,
    )
    assert resp.status_code == 404


def test_update_project_blank_name(auth_header):
    pid = _create_project("Old", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}",
        json={"name": "  ", "owner_id": str(OWNER_1)},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_update_project_name_only(auth_header):
    pid = _create_project("Old", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}",
        json={"name": "New"},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New"
    assert body["owner_id"] == str(OWNER_1)


def test_update_project_owner_only(auth_header):
    pid = _create_project("Old", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}",
        json={"owner_id": str(OWNER_2)},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Old"
    assert body["owner_id"] == str(OWNER_2)


def test_update_project_empty_payload(auth_header):
    pid = _create_project("Old", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}",
        json={},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Old"
    assert body["owner_id"] == str(OWNER_1)


def test_update_project_rejects_unknown_field(auth_header):
    pid = _create_project("Old", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}",
        json={"name": "New", "bogus": 1},
        headers=auth_header,
    )
    assert resp.status_code == 422


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


def test_create_task(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "Ship it", "due_date": "2026-09-01"},
        headers=auth_header,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Ship it"
    assert body["project_id"] == pid
    assert body["status"] == "todo"
    assert body["due_date"] == "2026-09-01"
    assert tasks.get_task(body["id"]) is not None


def test_create_task_with_full_fields(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={
            "title": "Ship",
            "status": "in_progress",
            "assignee": str(OWNER_1),
            "due_date": "2026-09-01",
            "description": "details",
        },
        headers=auth_header,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["assignee"] == str(OWNER_1)
    assert body["due_date"] == "2026-09-01"
    assert body["description"] == "details"


def test_create_task_unknown_assignee_returns_422(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "Ship", "assignee": str(uuid4()), "due_date": "2026-09-01"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_create_task_malformed_assignee_returns_422(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "Ship", "assignee": "not-a-uuid", "due_date": "2026-09-01"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_create_task_strips_title(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "  Ship  ", "due_date": "2026-09-01"},
        headers=auth_header,
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Ship"


def test_create_task_rejects_unknown_field(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "Ship", "due_date": "2026-09-01", "id": str(uuid4())},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_create_task_requires_auth():
    resp = client.post(
        f"/projects/{uuid4()}/tasks",
        json={"title": "Ship", "due_date": "2026-09-01"},
    )
    assert resp.status_code == 401


def test_create_task_blank_title(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "  ", "due_date": "2026-09-01"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_create_task_missing_due_date(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "Ship"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_create_task_invalid_status(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "Ship", "status": "paused", "due_date": "2026-09-01"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_create_task_forbidden_other_users_project(other_auth_header):
    pid = _create_project("Mine", owner_id=OWNER_1)
    resp = client.post(
        f"/projects/{pid}/tasks",
        json={"title": "Ship", "due_date": "2026-09-01"},
        headers=other_auth_header,
    )
    assert resp.status_code == 403


def test_create_task_missing_project_returns_404(auth_header):
    resp = client.post(
        f"/projects/{uuid4()}/tasks",
        json={"title": "Ship", "due_date": "2026-09-01"},
        headers=auth_header,
    )
    assert resp.status_code == 404


def test_update_task(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"status": "done", "due_date": "2026-10-01"},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["due_date"] == "2026-10-01"
    stored = tasks.get_task(tid)
    assert stored.status == "done"
    assert stored.due_date == date(2026, 10, 1)


def test_update_task_status_only(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"status": "in_progress"},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["due_date"] == "2026-09-01"


def test_update_task_due_date_only(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"due_date": "2026-11-01"},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "todo"
    assert body["due_date"] == "2026-11-01"


def test_update_task_assignee(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"assignee": str(OWNER_1)},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["assignee"] == str(OWNER_1)
    assert tasks.get_task(tid).assignee == str(OWNER_1)


def test_update_task_unknown_assignee_returns_422(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"assignee": str(uuid4())},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_update_task_malformed_assignee_returns_422(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"assignee": "not-a-uuid"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_update_task_clear_assignee(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", assignee="alice", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"assignee": None},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["assignee"] is None
    assert tasks.get_task(tid).assignee is None


def test_update_task_assignee_untouched_when_omitted(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", assignee="alice", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"status": "done"},
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["assignee"] == "alice"


def test_update_task_empty_payload(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(f"/projects/{pid}/tasks/{tid}", json={}, headers=auth_header)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "todo"
    assert body["due_date"] == "2026-09-01"


def test_update_task_invalid_status(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"status": "paused"},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_update_task_expired_due_date(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    past = datetime.now(UTC).date() - timedelta(days=1)
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"due_date": past.isoformat()},
        headers=auth_header,
    )
    assert resp.status_code == 422
    assert "already expired" in resp.json()["detail"][0]["msg"]


def test_update_task_rejects_unknown_field(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"status": "done", "bogus": 1},
        headers=auth_header,
    )
    assert resp.status_code == 422


def test_update_task_requires_auth():
    resp = client.put(
        f"/projects/{uuid4()}/tasks/{uuid4()}",
        json={"status": "done"},
    )
    assert resp.status_code == 401


def test_update_task_forbidden_other_users_project(other_auth_header):
    pid = _create_project("Mine", owner_id=OWNER_1)
    tid = tasks.create_task(pid, "Old", due_date=date(2026, 9, 1)).id
    resp = client.put(
        f"/projects/{pid}/tasks/{tid}",
        json={"status": "done"},
        headers=other_auth_header,
    )
    assert resp.status_code == 403


def test_update_task_missing_project_returns_404(auth_header):
    resp = client.put(
        f"/projects/{uuid4()}/tasks/{uuid4()}",
        json={"status": "done"},
        headers=auth_header,
    )
    assert resp.status_code == 404


def test_update_task_missing_task_returns_404(auth_header):
    pid = _create_project("Site", owner_id=OWNER_1)
    resp = client.put(
        f"/projects/{pid}/tasks/{uuid4()}",
        json={"status": "done"},
        headers=auth_header,
    )
    assert resp.status_code == 404
