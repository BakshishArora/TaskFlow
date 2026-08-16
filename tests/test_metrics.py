from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from taskflow.controllers import metrics, users
from taskflow.main import app
from taskflow.utils import auth

client = TestClient(app)


def _token_for(user_id: UUID) -> str:
    return auth.create_token(user_id=user_id)


@pytest.fixture(autouse=True)
def reset_store():
    users.clear_users()
    metrics.clear_metrics()


def test_authenticated_request_is_recorded():
    user_id = uuid4()
    users.create_user("alice", "pw12345", user_id=user_id)
    token = _token_for(user_id)

    resp = client.get("/projects", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    rows = metrics.list_metrics(str(user_id))
    assert len(rows) == 1
    row = rows[0]
    assert row["endpoint"] == "/projects"
    assert row["status_code"] == 200
    assert row["user_id"] == str(user_id)
    assert row["timestamp"] is not None


def test_unauthenticated_request_is_not_recorded():
    client.get("/health")

    assert metrics.list_all() == []


def test_invalid_token_request_is_not_recorded():
    users.create_user("alice", "pw12345")
    client.get("/projects", headers={"Authorization": "Bearer garbage"})

    assert metrics.list_all() == []


def test_metrics_endpoint_is_public():
    resp = client.get("/metrics")
    assert resp.status_code == 200


def test_metrics_endpoint_returns_all_rows():
    alice_id = uuid4()
    bob_id = uuid4()
    users.create_user("alice", "pw12345", user_id=alice_id)
    users.create_user("bob", "pw12345", user_id=bob_id)

    client.get("/projects", headers={"Authorization": f"Bearer {_token_for(alice_id)}"})
    client.get("/projects", headers={"Authorization": f"Bearer {_token_for(bob_id)}"})

    rows = client.get("/metrics").json()

    assert len(rows) == 2
    assert {row["user_id"] for row in rows} == {str(alice_id), str(bob_id)}
