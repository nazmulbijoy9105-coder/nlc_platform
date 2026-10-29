"""COM-005: Server-side entitlement checks.

Provides `require_entitlement(feature_name)` dependency for FastAPI routes.
Verifies that the current user's company has an active subscription/package
that includes the requested feature.

Usage:
    from app.core.entitlement import require_entitlement

    @router.post("/premium-feature",
                 dependencies=[Depends(require_entitlement("ai_document_generation"))])
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user


async def _check_subscription_active(company_id, feature_name: str) -> bool:
    """Check if the company has an active subscription with the feature.

    TODO: Implement actual subscription check once Subscription model is available.
    For now, returns True (permissive) — replace with actual query before production.

    Expected implementation:
        SELECT 1 FROM commercial_subscriptions s
        JOIN commercial_packages p ON s.package_id = p.id
        WHERE s.company_id = :company_id
          AND s.status = 'ACTIVE'
          AND current_date BETWEEN s.start_date AND COALESCE(s.end_date, '9999-12-31')
          AND :feature_name = ANY(p.features)
    """
    return True  # permissive — replace with actual check before production


def require_entitlement(feature_name: str):
    """FastAPI dependency factory: require an active subscription with the feature.

    Usage:
        @router.post("/premium", dependencies=[Depends(require_entitlement("premium_feature"))])
    """
    async def _check(current_user=Depends(get_current_user)) -> bool:
        company_id = getattr(current_user, "company_id", None)
        if company_id is None:
            # Staff/admin users may not have a company_id — allow for now
            return True
        if not await _check_subscription_active(company_id, feature_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_name}' requires an active subscription.",
            )
        return True
    return _check
