"""Server-side company-scoped subscription entitlement dependency."""
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
_CUSTOMER_ROLES = frozenset({"CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY"})


async def _company_contexts(
    request: Request,
    db: AsyncSession,
    current_user: User,
) -> list[uuid.UUID]:
    """Resolve tenant scope from a route resource or live DB membership."""
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
        company_id = result.scalar_one_or_none()
        if company_id is None:
            raise HTTPException(status_code=404, detail="Document not found")
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

    resource_models = {}
    from app.models.filings import AGM, AnnualReturn, Audit
    from app.models.infrastructure import StatutoryRegister
    resource_models.update({
        "agm_id": AGM,
        "audit_id": Audit,
        "return_id": AnnualReturn,
        "register_id": StatutoryRegister,
    })
    for parameter, model in resource_models.items():
        raw_resource_id = request.path_params.get(parameter)
        if not raw_resource_id:
            continue
        try:
            resource_id = uuid.UUID(str(raw_resource_id))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid filing resource context") from exc
        result = await db.execute(
            select(model.company_id).where(model.id == resource_id).limit(1)
        )
        company_id = result.scalar_one_or_none()
        if company_id is None:
            raise HTTPException(status_code=404, detail="Filing record not found")
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
        )
    )
    return list(dict.fromkeys(result.scalars().all()))


def require_entitlement(feature_name: str):
    """Require a current subscription for customer tenants; staff need scope."""
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
            company_context = (
                request.path_params.get("company_id")
                or request.query_params.get("company_id")
                or request.path_params.get("document_id")
                or request.path_params.get("agm_id")
                or request.path_params.get("audit_id")
                or request.path_params.get("return_id")
                or request.path_params.get("register_id")
            )
            if company_context:
                await _company_contexts(request, db, current_user)
            elif not (
                request.url.path.rstrip("/").endswith("/documents")
                or request.url.path.rstrip("/").endswith("/documents/templates")
                or request.url.path.rstrip("/").endswith("/filings")
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="An assigned company context is required.",
                )
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
                detail="An active company membership is required.",
            )

        service = SubscriptionService(db)
        entitled_company_ids: list[uuid.UUID] = []
        for company_id in company_ids:
            if await service.has_entitlement(company_id=company_id, feature_code=feature_name):
                entitled_company_ids.append(company_id)
        if not entitled_company_ids:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Company subscription does not include '{feature_name}' or its paid term has expired.",
            )
        request.state.entitled_company_ids = [str(item) for item in entitled_company_ids]
        return True

    return _check
