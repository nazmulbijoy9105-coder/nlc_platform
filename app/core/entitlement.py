"""COM-005: Fail-closed server-side entitlement checks.

Premium customer features remain unavailable until the canonical subscription
and entitlement records are implemented and verified. Staff authorization is
handled separately by explicit role checks; it must never be inferred from a
missing company identifier.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user

# Only platform administrators may bypass a customer subscription check.
# Legal staff still require the route's explicit role authorization and do not
# receive an implicit subscription bypass.
_PRIVILEGED_BYPASS_ROLES = frozenset({"SUPER_ADMIN", "ADMIN_STAFF"})


def require_entitlement(feature_name: str):
    """Require a verified entitlement for a premium feature.

    Until a canonical subscription model and company-membership resolution
    exist, customer access fails closed with 503. Returning 403 would falsely
    imply that a subscription was checked and found inactive.
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
