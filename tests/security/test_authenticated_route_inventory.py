"""Fail CI when a new API route is accidentally exposed without authentication."""
from __future__ import annotations

from fastapi.routing import APIRoute

from app.api import auth as auth_api
from app.core.dependencies import get_current_user, verify_access_token
from app.main import app


PUBLIC_API_ROUTES = frozenset({
    ("GET", "/api/v1/health"),
    ("HEAD", "/api/v1/health"),
    ("GET", "/api/v1/health/live"),
    ("HEAD", "/api/v1/health/live"),
    ("GET", "/api/v1/health/ready"),
    ("HEAD", "/api/v1/health/ready"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/verify-2fa"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/signup"),
    # Read-only public statutory catalogue metadata; no tenant/user data.
    ("GET", "/api/v1/rules"),
})


def _dependency_calls(dependant):
    calls = set()
    pending = [dependant]
    while pending:
        current = pending.pop()
        call = getattr(current, "call", None)
        if call is not None:
            calls.add(call)
        pending.extend(getattr(current, "dependencies", ()))
    return calls


def test_every_api_route_is_authenticated_or_explicitly_public():
    """Every protected router route must transitively verify a JWT/database user."""
    missing = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1/"):
            continue
        calls = _dependency_calls(route.dependant)
        has_auth = (
            verify_access_token in calls
            or get_current_user in calls
            or auth_api.get_current_user in calls
        )
        for method in sorted(route.methods - {"OPTIONS"}):
            if (method, route.path) in PUBLIC_API_ROUTES:
                continue
            if not has_auth:
                missing.append(f"{method} {route.path}")

    assert not missing, (
        "API routes without a verified authentication dependency must be "
        "explicitly allowlisted as public or given an authentication dependency:\n"
        + "\n".join(sorted(missing))
    )


def test_public_api_allowlist_contains_only_registered_routes():
    registered = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods - {"OPTIONS"}
    }
    stale_allowlist = PUBLIC_API_ROUTES - registered
    assert not stale_allowlist, (
        "Remove stale public API allowlist entries; the allowlist must match "
        f"real route methods exactly: {sorted(stale_allowlist)!r}"
    )
