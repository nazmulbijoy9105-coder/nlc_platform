"""Fail-closed logout tests for Redis-backed token revocation."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api import auth
from app.core import token_blacklist


@pytest.mark.asyncio
async def test_logout_does_not_claim_success_when_access_revocation_fails(monkeypatch):
    monkeypatch.setattr(
        auth,
        "decode_token",
        lambda token, expected_type: {
            "jti": "access-jti",
            "exp": 1_900_000_000,
            "sub": "user-1",
        },
    )
    monkeypatch.setattr(token_blacklist, "revoke", lambda jti, exp: False)

    with pytest.raises(HTTPException) as exc:
        await auth.logout(
            body=auth.LogoutRequest(),
            current_user={"sub": "user-1"},
            token="access-token",
        )

    assert exc.value.status_code == 503
    assert "may remain active" in exc.value.detail


@pytest.mark.asyncio
async def test_logout_reports_failure_when_refresh_revocation_fails(monkeypatch):
    calls: list[str] = []

    def decode(token: str, expected_type: str):
        if expected_type == "access":
            return {"jti": "access-jti", "exp": 1_900_000_000, "sub": "user-1"}
        return {"jti": "refresh-jti", "exp": 1_900_000_000, "sub": "user-1"}

    def revoke(jti: str, exp: int) -> bool:
        calls.append(jti)
        return jti == "access-jti"

    monkeypatch.setattr(auth, "decode_token", decode)
    monkeypatch.setattr(token_blacklist, "revoke", revoke)

    with pytest.raises(HTTPException) as exc:
        await auth.logout(
            body=auth.LogoutRequest(refresh_token="refresh-token"),
            current_user={"sub": "user-1"},
            token="access-token",
        )

    assert calls == ["access-jti", "refresh-jti"]
    assert exc.value.status_code == 503
    assert "refresh-token revocation failed" in exc.value.detail


@pytest.mark.asyncio
async def test_logout_succeeds_only_after_access_and_matching_refresh_are_revoked(
    monkeypatch,
):
    calls: list[str] = []

    def decode(token: str, expected_type: str):
        if expected_type == "access":
            return {"jti": "access-jti", "exp": 1_900_000_000, "sub": "user-1"}
        return {"jti": "refresh-jti", "exp": 1_900_000_000, "sub": "user-1"}

    def revoke(jti: str, exp: int) -> bool:
        calls.append(jti)
        return True

    monkeypatch.setattr(auth, "decode_token", decode)
    monkeypatch.setattr(token_blacklist, "revoke", revoke)

    result = await auth.logout(
        body=auth.LogoutRequest(refresh_token="refresh-token"),
        current_user={"sub": "user-1"},
        token="access-token",
    )

    assert calls == ["access-jti", "refresh-jti"]
    assert result == {
        "status": "logged_out",
        "access_revoked": True,
        "refresh_revoked": True,
        "user_id": "user-1",
    }


def test_access_token_is_rejected_when_redis_blacklist_is_unavailable(monkeypatch):
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    from app.core import dependencies

    def unavailable(*args, **kwargs):
        raise token_blacklist.BlacklistUnavailable("redis unavailable")

    monkeypatch.setattr(
        dependencies,
        "decode_token",
        lambda token, expected_type: {
            "jti": "access-jti",
            "sub": "user-1",
            "user_id": "user-1",
            "email": "user-1@nlctest.com",
            "role": "CLIENT_DIRECTOR",
            "exp": 1_900_000_000,
        },
    )
    monkeypatch.setattr(token_blacklist, "is_revoked", unavailable)

    with pytest.raises(HTTPException) as exc:
        dependencies.verify_access_token(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")
        )
    assert exc.value.status_code == 401
    assert "temporarily unavailable" in exc.value.detail
