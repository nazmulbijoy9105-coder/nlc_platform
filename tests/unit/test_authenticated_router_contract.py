"""Structural authentication certification for every protected API router."""
from __future__ import annotations

from fastapi.routing import APIRoute

from app.core.dependencies import verify_access_token
from app.main import create_app


def _dependency_calls(dependant):
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _dependency_calls(dependency)


def test_every_route_in_each_protected_router_has_verified_jwt_dependency():
    protected_modules = (
        "companies",
        "portfolio_compliance",
        "filings",
        "rescue",
        "documents",
        "commercial",
        "finance",
        "subscriptions",
        "rjsc_forms",
        "calendar",
        "legal_provenance",
        "rules",
        "admin",
        "notifications",
        "webhooks",
    )
    import importlib

    app = create_app()
    registered = {
        route.path: route
        for route in app.routes
        if isinstance(route, APIRoute)
    }

    checked = 0
    for module_name in protected_modules:
        module = importlib.import_module(f"app.api.{module_name}")
        assert module.router.routes, f"{module_name} router unexpectedly has no routes"
        for router_route in module.router.routes:
            if not isinstance(router_route, APIRoute):
                continue
            app_route = next(
                (
                    candidate for candidate in registered.values()
                    if candidate.endpoint is router_route.endpoint
                ),
                None,
            )
            assert app_route is not None, (
                f"{module_name} route is not mounted: {router_route.path}"
            )
            calls = set(_dependency_calls(app_route.dependant))
            assert verify_access_token in calls, (
                f"Protected route lacks verified JWT dependency: "
                f"{module_name} {sorted(app_route.methods or [])} {full_path}"
            )
            checked += 1

    assert checked >= len(protected_modules), "No authenticated endpoints were inspected"


def test_company_live_coverage_endpoint_is_company_scoped_and_authenticated():
    app = create_app()
    route = next(
        route for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == "/api/v1/companies/{company_id}/rule-coverage"
    )
    calls = set(_dependency_calls(route.dependant))
    assert verify_access_token in calls
    assert any(
        getattr(call, "__name__", "") == "_check_access"
        for call in calls
    ), "Company coverage must enforce live company membership/assignment"
