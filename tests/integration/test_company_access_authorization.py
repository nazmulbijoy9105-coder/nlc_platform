"""Direct regression tests for company-level authorization and IDOR prevention."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

pytestmark = [pytest.mark.integration]


# =============================================================================
# COMPANY ACCESS DEPENDENCY — IDOR REGRESSION COVERAGE
# =============================================================================

class TestCompanyAccessDependency:

    @pytest.mark.asyncio
    async def test_super_admin_bypasses_company_membership_lookup(self):
        from starlette.requests import Request
        from app.core.company_access import require_company_access

        dependency = require_company_access()
        request = Request({
            "type": "http", "http_version": "1.1", "method": "GET",
            "scheme": "http", "path": "/companies/any/documents",
            "raw_path": b"/companies/any/documents", "query_string": b"",
            "headers": [], "server": ("test", 80), "client": ("test", 1),
            "root_path": "", "path_params": {"company_id": "not-a-uuid"},
        })
        db = SimpleNamespace(execute=AsyncMock())
        user = SimpleNamespace(role="SUPER_ADMIN", id=uuid.uuid4())

        assert await dependency(request, current_user=user, db=db) is user
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_company_path_parameter_is_rejected(self):
        from fastapi import HTTPException
        from starlette.requests import Request
        from app.core.company_access import require_company_access

        dependency = require_company_access()
        request = Request({
            "type": "http", "http_version": "1.1", "method": "GET",
            "scheme": "http", "path": "/companies", "raw_path": b"/companies",
            "query_string": b"", "headers": [], "server": ("test", 80),
            "client": ("test", 1), "root_path": "", "path_params": {},
        })
        user = SimpleNamespace(role="CLIENT_VIEW_ONLY", id=uuid.uuid4())

        with pytest.raises(HTTPException) as exc:
            await dependency(request, current_user=user, db=SimpleNamespace(execute=AsyncMock()))
        assert exc.value.status_code == 400
        assert "Missing path parameter" in exc.value.detail

    @pytest.mark.asyncio
    async def test_malformed_company_id_is_rejected_before_database_lookup(self):
        from fastapi import HTTPException
        from starlette.requests import Request
        from app.core.company_access import require_company_access

        dependency = require_company_access()
        request = Request({
            "type": "http", "http_version": "1.1", "method": "GET",
            "scheme": "http", "path": "/companies/not-a-uuid",
            "raw_path": b"/companies/not-a-uuid", "query_string": b"",
            "headers": [], "server": ("test", 80), "client": ("test", 1),
            "root_path": "", "path_params": {"company_id": "not-a-uuid"},
        })
        db = SimpleNamespace(execute=AsyncMock())
        user = SimpleNamespace(role="CLIENT_VIEW_ONLY", id=uuid.uuid4())

        with pytest.raises(HTTPException) as exc:
            await dependency(request, current_user=user, db=db)
        assert exc.value.status_code == 400
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_active_company_membership_grants_access(self):
        from starlette.requests import Request
        from app.core.company_access import require_company_access

        company_id = uuid.uuid4()
        dependency = require_company_access()
        request = Request({
            "type": "http", "http_version": "1.1", "method": "GET",
            "scheme": "http", "path": f"/companies/{company_id}",
            "raw_path": f"/companies/{company_id}".encode(), "query_string": b"",
            "headers": [], "server": ("test", 80), "client": ("test", 1),
            "root_path": "", "path_params": {"company_id": str(company_id)},
        })
        user = SimpleNamespace(role="CLIENT_VIEW_ONLY", id=uuid.uuid4())
        membership = SimpleNamespace(company_id=company_id, user_id=user.id, is_active=True)
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: membership))
        )

        assert await dependency(request, current_user=user, db=db) is user
        db.execute.assert_awaited_once()
        statement = db.execute.await_args.args[0]
        rendered_query = str(statement)
        assert "company_user_access.user_id" in rendered_query
        assert "company_user_access.company_id" in rendered_query
        assert "company_user_access.is_active" in rendered_query

    @pytest.mark.asyncio
    async def test_missing_company_membership_is_forbidden(self):
        from fastapi import HTTPException
        from starlette.requests import Request
        from app.core.company_access import require_company_access

        company_id = uuid.uuid4()
        dependency = require_company_access()
        request = Request({
            "type": "http", "http_version": "1.1", "method": "GET",
            "scheme": "http", "path": f"/companies/{company_id}",
            "raw_path": f"/companies/{company_id}".encode(), "query_string": b"",
            "headers": [], "server": ("test", 80), "client": ("test", 1),
            "root_path": "", "path_params": {"company_id": str(company_id)},
        })
        user = SimpleNamespace(role="CLIENT_VIEW_ONLY", id=uuid.uuid4())
        db = SimpleNamespace(
            execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
        )

        with pytest.raises(HTTPException) as exc:
            await dependency(request, current_user=user, db=db)
        assert exc.value.status_code == 403
        assert "do not have access" in exc.value.detail
        db.execute.assert_awaited_once()

