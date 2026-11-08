"""Server-side company-scoped subscription entitlement dependency."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_for_user
from app.models.company import CompanyUserAccess
from app.models.user import User
from app.services.subscription_service import SubscriptionService

_PRIVILEGED_BYPASS_ROLES = frozenset({"SUPER_ADMIN", "ADMIN_STAFF", "LEGAL_STAFF"})
_CUSTOMER_ROLES = frozenset({"CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY"})


async def _company_contexts(
    request: Request,
    db: AsyncSession,
    current_user: User,
) -> list[uuid.UUID]:
    raw_company_id = request.path_params.get("company_id") or request.query_params.get("company_id")
    if raw_company_id:
        try:
            company_id = uuid.UUID(str(raw_company_id))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid company context") from exc
        membership = await db.execute(
            select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.company_id == company_id,
                CompanyUserAccess.user_id == current_user.id,
                CompanyUserAccess.is_active.is_(True),
                CompanyUserAccess.can_view_financials.is_(True),
            ).limit(1)
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Active company financial access is required.")
        return [company_id]

    raw_document_id = request.path_params.get("document_id")
    if raw_document_id:
        try:
            document_id = uuid.UUID(str(raw_document_id))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid document context") from exc
        from app.models.documents import Document

        result = await db.execute(
            select(Document.company_id).where(Document.id == document_id).limit(1)
        )
        company_id = result.scalar_one_or_none()
        if company_id is None:
            raise HTTPException(status_code=404, detail="Document not found")
        membership = await db.execute(
            select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.company_id == company_id,
                CompanyUserAccess.user_id == current_user.id,
                CompanyUserAccess.is_active.is_(True),
                CompanyUserAccess.can_view_financials.is_(True),
            ).limit(1)
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Active company financial access is required.")
        return [company_id]

"""COM-005: Fail-closed, server-side company-scoped subscription entitlement checks.

Premium customer features require an active company membership and a current
server-verified subscription entitlement. Staff authorization is handled by
explicit role checks; it is never inferred from a missing company identifier.
"""COM-005: Fail-closed server-side entitlement checks.

Premium customer features remain unavailable until the canonical subscription
and entitlement records are implemented and verified. Staff authorization is
handled separately by explicit role checks; it must never be inferred from a
missing company identifier.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_for_user
from app.models.company import Company, CompanyUserAccess
from app.models.user import User
from app.services.subscription_service import SubscriptionService

_PRIVILEGED_BYPASS_ROLES = frozenset({"SUPER_ADMIN", "ADMIN_STAFF"})
_CUSTOMER_ROLES = frozenset({"CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY", "LEGAL_STAFF"})

async def _company_contexts(
    request: Request,
    db: AsyncSession,
    current_user: User,
) -> list[uuid.UUID]:
    role_value = str(getattr(current_user.role, "value", current_user.role))
    raw_company_id = (
        request.path_params.get("company_id")
        or request.query_params.get("company_id")
    )
    if raw_company_id is None and request.method not in {"GET", "HEAD"}:
        try:
            payload = await request.json()
        except (ValueError, TypeError):
            payload = None
        if isinstance(payload, dict):
            raw_company_id = payload.get("company_id")

    if raw_company_id:
        try:
            company_id = uuid.UUID(str(raw_company_id))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid company context") from exc
        if role_value == "LEGAL_STAFF":
            from app.core.company_authorization import ensure_staff_company_scope

            await ensure_staff_company_scope(company_id, current_user, db)
            return [company_id]
        membership = await db.execute(
            select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.company_id == company_id,
                CompanyUserAccess.user_id == current_user.id,
                CompanyUserAccess.is_active.is_(True),
            ).limit(1)
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Active company membership is required.")
        return [company_id]

    raw_document_id = request.path_params.get("document_id")
    if raw_document_id:
        try:
            document_id = uuid.UUID(str(raw_document_id))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid document context") from exc
        from app.models.documents import Document

        result = await db.execute(
            select(Document.company_id).where(Document.id == document_id).limit(1)
        )
        document_company_id = result.scalar_one_or_none()
        if document_company_id is None:
            raise HTTPException(status_code=404, detail="Document not found")
        company_id = document_company_id
        if role_value == "LEGAL_STAFF":
            from app.core.company_authorization import ensure_staff_company_scope

            await ensure_staff_company_scope(company_id, current_user, db)
            return [company_id]
        membership = await db.execute(
            select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.company_id == company_id,
                CompanyUserAccess.user_id == current_user.id,
                CompanyUserAccess.is_active.is_(True),
            ).limit(1)
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Active company membership is required.")
        return [company_id]

    if role_value == "LEGAL_STAFF":
        assigned = await db.execute(
            select(Company.id).where(Company.assigned_staff_id == current_user.id)
        )
        memberships = await db.execute(
            select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.user_id == current_user.id,
                CompanyUserAccess.is_active.is_(True),
            )
        )
        return list(dict.fromkeys([*assigned.scalars().all(), *memberships.scalars().all()]))

    result = await db.execute(
        select(CompanyUserAccess.company_id).where(
            CompanyUserAccess.user_id == current_user.id,
            CompanyUserAccess.is_active.is_(True),
            CompanyUserAccess.can_view_financials.is_(True),
        )
    )
    return list(result.scalars().all())


def require_entitlement(feature_name: str):
    """Require a paid feature on the exact tenant being accessed.

    The dependency resolves company context from a company path/query parameter,
    a document resource ID, or the caller's live financial company memberships.
    It never trusts a client-supplied JWT company_ids claim.
        )
    )
    return list(dict.fromkeys(result.scalars().all()))


def require_entitlement(feature_name: str):
    """Require an active paid feature for the exact company being accessed.

    Tenant identity comes from the route/resource and live database membership,
    never from JWT company claims. Platform administrators retain their explicit
    staff bypass; legal staff must be assigned to each company and still respect
    that company's paid entitlement.
    """
    async def _check(
        request: Request,
        db: AsyncSession = Depends(get_db_for_user),
        current_user: User = Depends(get_current_user),
    ) -> bool:
        role = getattr(current_user, "role", None)
        role_value = str(getattr(role, "value", role))
        if role_value in _PRIVILEGED_BYPASS_ROLES:
            return True
        if role_value == "LEGAL_STAFF":
            # Internal staff are authorized by the route's role/company-access
            # dependencies, not by a customer's subscription. Still bind
            # resource-specific requests to the staff member's assigned scope.
            raw_company_id = request.path_params.get("company_id") or request.query_params.get("company_id")
            raw_document_id = request.path_params.get("document_id")
            if raw_company_id:
                try:
                    company_id = uuid.UUID(str(raw_company_id))
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=400, detail="Invalid company context") from exc
                from app.core.company_authorization import ensure_staff_company_scope
                await ensure_staff_company_scope(company_id, current_user, db)
            elif raw_document_id:
                try:
                    document_id = uuid.UUID(str(raw_document_id))
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=400, detail="Invalid document context") from exc
                from app.models.documents import Document
                result = await db.execute(
                    select(Document.company_id).where(Document.id == document_id).limit(1)
                )
                company_id = result.scalar_one_or_none()
                if company_id is None:
                    raise HTTPException(status_code=404, detail="Document not found")
                from app.core.company_authorization import ensure_staff_company_scope
                await ensure_staff_company_scope(company_id, current_user, db)
            elif not (
                request.url.path.rstrip("/").endswith("/documents")
                or request.url.path.rstrip("/").endswith("/documents/templates")
            ):
                raise HTTPException(status_code=403, detail="An assigned company context is required.")
            return True
        if role_value not in _CUSTOMER_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This feature is not available to this account role.",
            )

        company_ids = await _company_contexts(request, db, current_user)
        if not company_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="An active company financial access membership is required.",
            )
        service = SubscriptionService(db)
        entitled_company_ids = []
        for company_id in company_ids:
            if await service.has_entitlement(
                company_id=company_id,
                feature_code=feature_name,
            ):
                entitled_company_ids.append(company_id)
        if not entitled_company_ids:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Company subscription does not include the '{feature_name}' feature or its paid term has expired.",
            )
        request.state.entitled_company_ids = [str(item) for item in entitled_company_ids]
        return True
        role_value = str(getattr(current_user.role, "value", current_user.role))
        if role_value in _PRIVILEGED_BYPASS_ROLES:
            return True
        if role_value not in _CUSTOMER_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This feature is not available to this account role.",
            )

        company_ids = await _company_contexts(request, db, current_user)
        if not company_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="An active company membership or assigned company is required.",
            )
        service = SubscriptionService(db)
        entitled_company_ids: list[uuid.UUID] = []
        for company_id in company_ids:
            if await service.has_entitlement(
                company_id=company_id,
                feature_code=feature_name,
            ):
                entitled_company_ids.append(company_id)
        if not entitled_company_ids:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Company subscription does not include the '{feature_name}' feature or its paid term has expired.",
            )
        request.state.entitled_company_ids = [str(item) for item in entitled_company_ids]
        return True
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
