"""Company-scoped authorization helpers for staff operations.

Platform admins retain portfolio-wide access. Legal staff must be explicitly
assigned to the target company either through companies.assigned_staff_id or
an active company_user_access row. Client access remains governed by the
existing live-membership dependency and is not granted here.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyUserAccess


_PLATFORM_WIDE_ROLES = frozenset({"SUPER_ADMIN", "ADMIN_STAFF"})


async def ensure_staff_company_scope(
    company_id: uuid.UUID,
    current_user,
    db: AsyncSession,
    *,
    additional_staff_id: uuid.UUID | None = None,
) -> None:
    """Require a staff actor to be assigned to the company being operated on."""
    role = getattr(current_user, "role", None)
    role_value = str(getattr(role, "value", role))

    if role_value in _PLATFORM_WIDE_ROLES:
        return
    if role_value != "LEGAL_STAFF":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff authorization is required for this company operation.",
        )

    active_membership = (
        select(CompanyUserAccess.company_id)
        .where(
            CompanyUserAccess.company_id == Company.id,
            CompanyUserAccess.user_id == current_user.id,
            CompanyUserAccess.is_active.is_(True),
        )
        .exists()
    )
    result = await db.execute(
        select(Company.id).where(
            Company.id == company_id,
            or_(
                Company.assigned_staff_id == current_user.id,
                active_membership,
                *([additional_staff_id == current_user.id] if additional_staff_id is not None else []),
            ),
        ).limit(1)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this company.",
        )
