from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.entitlement import require_entitlement


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["SUPER_ADMIN", "ADMIN_STAFF"])
async def test_platform_admin_can_bypass_customer_entitlement(role):
    dependency = require_entitlement("advanced_compliance")
    result = await dependency(SimpleNamespace(role=role))
    assert result is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role", ["CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY", "LEGAL_STAFF"]
)
async def test_unverified_entitlement_fails_closed_for_non_admin_roles(role):
    dependency = require_entitlement("advanced_compliance")

    with pytest.raises(HTTPException) as exc:
        await dependency(SimpleNamespace(role=role))

    assert exc.value.status_code == 503
    assert "entitlement verification is not configured" in exc.value.detail
    assert exc.value.headers["Retry-After"] == "3600"


@pytest.mark.asyncio
async def test_missing_role_does_not_grant_entitlement():
    dependency = require_entitlement("advanced_compliance")

    with pytest.raises(HTTPException) as exc:
        await dependency(SimpleNamespace())

    assert exc.value.status_code == 503
