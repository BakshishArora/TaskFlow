from uuid import uuid4

import pytest
from fastapi import HTTPException

from taskflow.utils import auth


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


def test_get_current_user_from_request():
    from fastapi import Request

    uid = uuid4()
    token = auth.create_token(user_id=uid)
    req = Request(
        {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
    )
    assert auth.get_current_user(req) == uid


def test_get_current_user_missing_header_raises():
    from fastapi import Request

    req = Request({"type": "http", "headers": []})
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(req)
    assert exc.value.status_code == 401
