"""Fail CI when a new API route is accidentally exposed without authentication."""
from __future__ import annotations

from fastapi.routing import APIRoute
from starlette.routing import Mount

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


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/")
    return path


def _iter_api_routes(routes):
    """Yield APIRoute objects from a route list, descending into Mount routers."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif isinstance(route, Mount) and hasattr(route, "routes"):
            yield from _iter_api_routes(route.routes)


def _registered_api_methods_and_paths():
    """Return {(METHOD, normalized_path)} for every mounted APIRoute."""
    registered: set[tuple[str, str]] = set()
    route_lists = []
    router = getattr(app, "router", None)
    if router is not None and getattr(router, "routes", None) is not None:
        route_lists.append(router.routes)
    route_lists.append(getattr(app, "routes", []) or [])

    seen_ids: set[int] = set()
    for route_list in route_lists:
        for route in _iter_api_routes(route_list):
            if id(route) in seen_ids:
                continue
            seen_ids.add(id(route))
            methods = set(route.methods or ())
            path = _normalize_path(route.path)
            for method in methods - {"OPTIONS"}:
                registered.add((method, path))
    return registered


def test_every_api_route_is_authenticated_or_explicitly_public():
    """Every protected router route must transitively verify a JWT/database user."""
    missing = []
    for route in _iter_api_routes(getattr(app.router, "routes", app.routes)):
        path = _normalize_path(route.path)
        if not path.startswith("/api/v1/"):
            continue
        calls = _dependency_calls(route.dependant)
        has_auth = (
            verify_access_token in calls
            or get_current_user in calls
            or auth_api.get_current_user in calls
        )
        for method in sorted(set(route.methods or ()) - {"OPTIONS"}):
            if (method, path) in PUBLIC_API_ROUTES:
                continue
            if not has_auth:
                missing.append(f"{method} {path}")

    assert not missing, (
        "API routes without a verified authentication dependency must be "
        "explicitly allowlisted as public or given an authentication dependency:\n"
        + "\n".join(sorted(missing))
    )


def test_public_api_allowlist_contains_only_registered_routes():
    registered = _registered_api_methods_and_paths()
    assert registered, (
        "No APIRoute entries were discovered on app.router; cannot validate "
        "the public allowlist. Check that app.main:app mounts /api/v1 routers."
    )
    stale_allowlist = PUBLIC_API_ROUTES - registered
    assert not stale_allowlist, (
        "Remove stale public API allowlist entries; the allowlist must match "
        f"real route methods exactly: {sorted(stale_allowlist)!r}. "
        f"Sample registered API routes: {sorted(registered)[:40]!r}"
    )
