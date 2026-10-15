"""
Company access authorization dependency.

Checks that the authenticated user has been granted access to the
specified company via the CompanyUserAccess table.  This prevents
IDOR (Insecure Direct Object Reference) attacks where a user of one
tenant reads/writes another tenant's data.

Usage in routes:

    @router.post("/{company_id}/documents")
    async def create_document(
        company_id: str,
        _: TokenData = Depends(require_company_access("company_id")),
        ...
    ):
"""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.commercial import CompanyUserAccess  # adjust import path


async def require_company_access(
    company_id_param: str = "company_id",
):
    """
    Factory that returns a dependency checking CompanyUserAccess.
    Prevents IDOR (Insecure Direct Object Reference) attacks.
    """
    from fastapi import Request as FastAPIRequest

    async def _check_access(
        request: FastAPIRequest,
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # SUPER_ADMIN bypasses company-level checks
        if str(current_user.role) == "SUPER_ADMIN":
            return current_user

        # Extract company_id from path params
        company_id = request.path_params.get(company_id_param)
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing path parameter: {company_id_param}",
            )

        try:
            cid = uuid.UUID(str(company_id))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid company ID format.",
            )

        # Check CompanyUserAccess — just check the record exists
        result = await db.execute(
            select(CompanyUserAccess).where(
                CompanyUserAccess.user_id == current_user.id,
                CompanyUserAccess.company_id == cid,
            )
        )
        access = result.scalar_one_or_none()

        if access is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this company.",
            )

        return current_user

    return _check_access
