import asyncio

import pytest
from fastapi import HTTPException

import app.core.token_blacklist as tb
from app.api import auth
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import verify_access_token
from app.core.security import create_access_token, create_refresh_token, create_temp_token


def _tok():
    return create_access_token({"sub": "u1", "user_id": "u1"})


def test_get_current_user_rejects_revoked_token(monkeypatch):
    monkeypatch.setattr(tb, "is_revoked", lambda jti: True)
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.get_current_user(_tok()))
    assert e.value.status_code == 401


def test_get_current_user_accepts_valid_token(monkeypatch):
    monkeypatch.setattr(tb, "is_revoked", lambda jti: False)
    assert asyncio.run(auth.get_current_user(_tok()))["sub"] == "u1"


def test_auth_route_rejects_refresh_token(monkeypatch):
    monkeypatch.setattr(tb, "is_revoked", lambda jti: False)
    token = create_refresh_token({"sub": "u1", "user_id": "u1", "email": "u1@example.test", "role": "CLIENT_VIEW_ONLY"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.get_current_user(token))
    assert exc.value.status_code == 401


def test_auth_route_rejects_temp_token(monkeypatch):
    token = create_temp_token({"sub": "u1"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.get_current_user(token))
    assert exc.value.status_code == 401


def test_core_access_dependency_rejects_refresh_token(monkeypatch):
    monkeypatch.setattr("app.core.dependencies._check_token_blacklist", lambda jti: False)
    token = create_refresh_token({"sub": "u1", "user_id": "u1", "email": "u1@example.test", "role": "CLIENT_VIEW_ONLY"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        verify_access_token(credentials)
    assert exc.value.status_code == 401


def test_core_access_dependency_rejects_temp_token(monkeypatch):
    monkeypatch.setattr("app.core.dependencies._check_token_blacklist", lambda jti: False)
    token = create_temp_token({"sub": "u1"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        verify_access_token(credentials)
    assert exc.value.status_code == 401
