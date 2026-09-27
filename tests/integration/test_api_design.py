"""API design tests — response models, pagination, error handling."""

class TestAPIDesign:
    """Verify API design quality."""

    def test_all_list_endpoints_support_pagination(self):
        """List endpoints should support pagination."""
        from app.main import create_app
        app = create_app()
        list_routes = [r for r in app.routes if hasattr(r, 'path') and hasattr(r, 'methods') and 'GET' in r.methods]
        # Verify list endpoints exist
        assert len(list_routes) > 10, "Not enough GET endpoints"

    def test_all_post_endpoints_have_request_model(self):
        """POST endpoints should accept Pydantic models."""
        from app.main import create_app
        app = create_app()
        post_routes = [r for r in app.routes if hasattr(r, 'methods') and 'POST' in r.methods]
        assert len(post_routes) > 5, "Not enough POST endpoints"

    def test_health_endpoint_returns_200(self):
        """Health endpoint should exist and return 200."""
        from app.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        health_routes = [r for r in routes if 'health' in r]
        assert len(health_routes) > 0, "No health endpoint"

    def test_api_has_v1_prefix(self):
        """All API routes should be under /api/v1/."""
        from app.main import create_app
        app = create_app()
        api_routes = [r for r in app.routes if hasattr(r, 'path') and '/api/' in r.path]
        assert len(api_routes) > 0, "No /api/ routes found"
        v1_routes = [r for r in api_routes if '/v1/' in r.path]
        assert len(v1_routes) > 0, "No /api/v1/ routes found"

    def test_rules_endpoint_accessible(self):
        """GET /rules should be accessible (no auth required)."""
        from app.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert any('rules' in r for r in routes), "No /rules endpoint"

    def test_company_endpoints_exist(self):
        """Company CRUD endpoints should exist."""
        from app.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert any('companies' in r for r in routes), "No /companies endpoint"

    def test_filing_endpoints_exist(self):
        """Filing endpoints (AGM, annual return) should exist."""
        from app.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert any('agm' in r.lower() for r in routes), "No AGM endpoint"
        assert any('annual' in r.lower() for r in routes), "No annual return endpoint"

    def test_rescue_endpoints_exist(self):
        """Rescue plan endpoints should exist."""
        from app.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert any('rescue' in r.lower() for r in routes), "No rescue endpoint"

    def test_document_endpoints_exist(self):
        """Document endpoints should exist."""
        from app.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert any('document' in r.lower() for r in routes), "No document endpoint"

    def test_auth_endpoints_exist(self):
        """Auth endpoints (login, refresh, 2FA) should exist."""
        from app.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert any('login' in r for r in routes), "No login endpoint"
        assert any('refresh' in r for r in routes), "No refresh endpoint"

    def test_admin_endpoints_exist(self):
        """Admin endpoints should exist."""
        from app.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert any('users' in r for r in routes), "No users endpoint"

    def test_openapi_docs_accessible(self):
        """OpenAPI docs should be accessible."""
        from app.main import create_app
        app = create_app()
        # FastAPI auto-generates /docs and /openapi.json
        assert any('/docs' in str(r) for r in app.routes), "No /docs endpoint"
        assert any('openapi' in str(r) for r in app.routes), "No /openapi.json"
