"""Authentication and self-service authorization tests with tenant RLS enabled."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.database import set_rls_context

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_signup_login_me_and_password_change_work_with_user_rls(api_client):
    email = f"rls-{uuid.uuid4().hex}@example.com"
    original_password = "Nlc!StrongPassword2026"
    replacement_password = "Nlc!DifferentPassword2026"

    signup = await api_client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": "RLS Signup Test",
            "password": original_password,
            # Public signup must ignore any requested privilege escalation.
            "role": "SUPER_ADMIN",
        },
    )
    assert signup.status_code == 200, signup.text
    created = signup.json()
    assert created["user"]["role"] in ("CLIENT_VIEW_ONLY", "UserRole.CLIENT_VIEW_ONLY")
    assert created["user"]["is_active"] is True
    access_token = created["access_token"]
    assert access_token

    me = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email
    assert me.json()["role"] in ("CLIENT_VIEW_ONLY", "UserRole.CLIENT_VIEW_ONLY")

    changed = await api_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": original_password,
            "new_password": replacement_password,
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "password_changed"

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": replacement_password},
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]


@pytest.mark.asyncio
async def test_client_cannot_promote_or_reactivate_own_account(db, db_client_user):
    """The database trigger protects authorization fields even for table owners."""
    await set_rls_context(db, str(db_client_user.id))

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text("UPDATE users SET role = 'SUPER_ADMIN' WHERE id = :uid"),
                {"uid": db_client_user.id},
            )

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text("UPDATE users SET is_active = FALSE WHERE id = :uid"),
                {"uid": db_client_user.id},
            )
