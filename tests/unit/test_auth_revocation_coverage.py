import asyncio

import pytest
from fastapi import HTTPException

import app.core.token_blacklist as tb
from app.api import auth
from app.core.security import create_access_token


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
