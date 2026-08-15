from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from taskflow.controllers import tasks
from taskflow.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    tasks.clear_tasks()


def test_create_task():
    resp = client.post("/tasks", json={"title": "Buy groceries"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Buy groceries"
    assert body["completed"] is False
    UUID(body["id"])


def test_create_task_blank_title_returns_422():
    resp = client.post("/tasks", json={"title": "  "})
    assert resp.status_code == 422


def test_list_tasks():
    client.post("/tasks", json={"title": "One"})
    client.post("/tasks", json={"title": "Two"})
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()] == ["One", "Two"]


def test_get_task():
    created = client.post("/tasks", json={"title": "Get me"}).json()
    resp = client.get(f"/tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get me"


def test_get_missing_task_returns_404():
    resp = client.get(f"/tasks/{uuid4()}")
    assert resp.status_code == 404


def test_get_invalid_task_id_returns_422():
    resp = client.get("/tasks/not-a-uuid")
    assert resp.status_code == 422


def test_update_task():
    created = client.post("/tasks", json={"title": "Old"}).json()
    resp = client.put(
        f"/tasks/{created['id']}", json={"title": "New", "completed": True}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New"
    assert body["completed"] is True


def test_update_task_null_title_rejected():
    created = client.post("/tasks", json={"title": "Old"}).json()
    resp = client.put(f"/tasks/{created['id']}", json={"title": None})
    assert resp.status_code == 422


def test_update_task_null_description_rejected():
    created = client.post("/tasks", json={"title": "Old"}).json()
    resp = client.put(f"/tasks/{created['id']}", json={"description": None})
    assert resp.status_code == 422


def test_delete_task():
    created = client.post("/tasks", json={"title": "Gone"}).json()
    resp = client.delete(f"/tasks/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404
