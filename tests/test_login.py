import pytest
from fastapi.testclient import TestClient

from taskflow.controllers import users
from taskflow.main import app
from taskflow.utils import auth, passwords

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    users.clear_users()


def test_login_new_user_creates_user_and_returns_token():
    resp = client.post("/auth/login", json={"username": "alice", "password": "secret"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    uid = auth.decode_token(token)
    user = users.get_user_by_username("alice")
    assert user is not None
    assert user.id == str(uid)


def test_login_existing_user_returns_token():
    client.post("/auth/login", json={"username": "alice", "password": "secret"})
    resp = client.post("/auth/login", json={"username": "alice", "password": "secret"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password_rejected():
    client.post("/auth/login", json={"username": "alice", "password": "secret"})
    resp = client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_password_stored_hashed_not_plaintext():
    client.post("/auth/login", json={"username": "alice", "password": "secret"})
    user = users.get_user_by_username("alice")
    assert user.password_hash != "secret"
    assert passwords.verify_password("secret", user.password_hash)


def test_login_does_not_duplicate_user():
    client.post("/auth/login", json={"username": "alice", "password": "secret"})
    client.post("/auth/login", json={"username": "alice", "password": "secret"})
    rows = users.list_users()
    assert len(rows) == 1