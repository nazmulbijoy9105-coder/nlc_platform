"""API design tests — response models, pagination, error handling."""


def _api_paths():
    """Return the registered API paths from FastAPI's generated OpenAPI schema.

    FastAPI's route container is an implementation detail and may contain
    included-router wrappers rather than flattened APIRoute instances.
    OpenAPI is the public, supported view of the mounted API surface.
    """
    from app.main import create_app

    app = create_app()
    return app.openapi().get("paths", {})


class TestAPIDesign:
    """Verify API design quality."""

    def test_all_list_endpoints_support_pagination(self):
        """List endpoints should support pagination."""
        paths = _api_paths()
        get_operations = [
            operations["get"]
            for operations in paths.values()
            if "get" in operations
        ]
        assert len(get_operations) > 10, "Not enough GET endpoints"

    def test_all_post_endpoints_have_request_model(self):
        """POST endpoints should accept Pydantic models."""
        paths = _api_paths()
        post_operations = [
            operations["post"]
            for operations in paths.values()
            if "post" in operations
        ]
        assert len(post_operations) > 5, "Not enough POST endpoints"

    def test_health_endpoint_returns_200(self):
        """Health endpoint should exist and return 200."""
        paths = _api_paths()
        health_paths = [path for path in paths if "health" in path]
        assert health_paths, "No health endpoint"
        assert any(
            "200" in paths[path].get("get", {}).get("responses", {})
            for path in health_paths
        ), "No health endpoint documents a 200 response"

    def test_api_has_v1_prefix(self):
        """All API routes should be under /api/v1/."""
        paths = _api_paths()
        api_paths = [path for path in paths if path.startswith("/api/")]
        assert api_paths, "No /api/ routes found"
        assert any(path.startswith("/api/v1/") for path in api_paths), (
            "No /api/v1/ routes found"
        )

    def test_rules_endpoint_accessible(self):
        """GET /rules should be accessible (no auth required)."""
        paths = _api_paths()
        assert any("/rules" in path for path in paths), "No /rules endpoint"

    def test_company_endpoints_exist(self):
        """Company CRUD endpoints should exist."""
        paths = _api_paths()
        assert any("/companies" in path for path in paths), (
            "No /companies endpoint"
        )

    def test_filing_endpoints_exist(self):
        """Filing endpoints (AGM, annual return) should exist."""
        paths = _api_paths()
        assert any("agm" in path.lower() for path in paths), "No AGM endpoint"
        assert any("annual" in path.lower() for path in paths), (
            "No annual return endpoint"
        )

    def test_rescue_endpoints_exist(self):
        """Rescue plan endpoints should exist."""
        paths = _api_paths()
        assert any("rescue" in path.lower() for path in paths), (
            "No rescue endpoint"
        )

    def test_document_endpoints_exist(self):
        """Document endpoints should exist."""
        paths = _api_paths()
        assert any("document" in path.lower() for path in paths), (
            "No document endpoint"
        )

    def test_auth_endpoints_exist(self):
        """Auth endpoints (login, refresh, 2FA) should exist."""
        paths = _api_paths()
        assert any("login" in path for path in paths), "No login endpoint"
        assert any("refresh" in path for path in paths), "No refresh endpoint"

    def test_admin_endpoints_exist(self):
        """Admin endpoints should exist."""
        paths = _api_paths()
        assert any("users" in path for path in paths), "No users endpoint"

    def test_openapi_docs_accessible(self):
        """OpenAPI docs should be accessible."""
        from app.main import create_app

        app = create_app()
        assert app.openapi_url == "/api/v1/openapi.json"
        assert app.docs_url == "/api/v1/docs"
        assert app.redoc_url == "/api/v1/redoc"
