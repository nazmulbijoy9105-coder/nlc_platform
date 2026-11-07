"""COM-005: Fail-closed server-side entitlement checks.

Premium customer features remain unavailable until the canonical subscription
and entitlement records are implemented and verified. Staff authorization is
handled separately by explicit role checks; it must never be inferred from a
missing company identifier.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user


# Keep this allowlist narrow and subject to route-level authorization. This
# dependency is not a substitute for require_admin/require_staff.
_PRIVILEGED_BYPASS_ROLES = frozenset({"SUPER_ADMIN", "ADMIN_STAFF", "LEGAL_STAFF"})


def require_entitlement(feature_name: str):
    """Require verified entitlement for a premium customer feature.

    Until subscription records and company-membership resolution are available,
    customer-role access fails closed with 503. Explicit staff roles remain subject
    to each route's independent RBAC and company-access controls. A 503 accurately reports
    that entitlement verification is unavailable; it does not assert that a
    subscription was checked and found inactive.
    """
    async def _check(current_user=Depends(get_current_user)) -> bool:
        role = getattr(current_user, "role", None)
        role_value = str(getattr(role, "value", role))

        if role_value in _PRIVILEGED_BYPASS_ROLES:
            return True

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Feature '{feature_name}' is temporarily unavailable because "
                "subscription entitlement verification is not configured."
            ),
            headers={"Retry-After": "3600"},
        )

    return _check
