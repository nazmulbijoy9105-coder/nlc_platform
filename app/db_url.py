"""PostgreSQL asyncpg URL normalization with explicit TLS enforcement."""
from __future__ import annotations

import os
import ssl
from collections.abc import Mapping

from sqlalchemy.engine import make_url


def is_render_runtime(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether the process is running inside a Render service.

    Render service/instance identifiers are stronger deployment signals than
    relying only on the optional convenience RENDER flag. Keep this helper
    shared by Alembic and the API so TLS and runtime-role policy agree.
    """
    source = os.environ if environ is None else environ
    return (
        source.get("RENDER", "").strip().lower() == "true"
        or bool(source.get("RENDER_SERVICE_ID", "").strip())
        or bool(source.get("RENDER_INSTANCE_ID", "").strip())
    )


def normalize_asyncpg_url(
    raw_url: str,
    *,
    require_tls: bool,
) -> tuple[str, ssl.SSLContext | None]:
    """Return an asyncpg URL and a verified TLS context when required.

    Neon endpoints always require TLS, independently of deployment-environment
    detection. Other production callers can require TLS explicitly. Remove
    libpq-only URL parameters and express TLS through asyncpg's ssl argument.
    """
    if not raw_url or not raw_url.strip():
        raise ValueError("PostgreSQL connection URL must not be empty")

    url = make_url(raw_url.strip())
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")
    elif url.drivername != "postgresql+asyncpg":
        raise ValueError(
            "Database URL must use PostgreSQL with the asyncpg driver"
        )

    host = (url.host or "").strip().lower().rstrip(".")
    is_neon_endpoint = host == "neon.tech" or host.endswith(".neon.tech")
    tls_required_by_policy = require_tls or is_neon_endpoint

    query = dict(url.query)
    sslmode = str(query.pop("sslmode", "")).strip().lower()
    ssl_option = str(query.pop("ssl", "")).strip().lower()
    # channel_binding is a libpq option, not an asyncpg.connect() argument.
    query.pop("channel_binding", None)

    explicitly_disabled = sslmode in {"disable", "false", "0"} or ssl_option in {
        "disable",
        "false",
        "0",
    }
    if tls_required_by_policy and explicitly_disabled:
        raise ValueError(
            "PostgreSQL TLS cannot be disabled for Neon, production, or Render"
        )

    tls_required = tls_required_by_policy or sslmode in {
        "require",
        "verify-ca",
        "verify-full",
        "prefer",
        "allow",
    } or ssl_option in {"require", "verify-ca", "verify-full", "true", "1"}

    normalized = url.set(query=query).render_as_string(hide_password=False)
    if not tls_required:
        return normalized, None

    # Default context verifies the certificate chain and hostname. Never
    # disable certificate validation to make a deployment connect.
    return normalized, ssl.create_default_context()


def prepare_asyncpg_connection(
    raw_url: str,
    *,
    require_tls: bool,
) -> tuple[str, dict[str, ssl.SSLContext]]:
    """Prepare a sanitized asyncpg URL and fail-closed TLS connect arguments.

    Neon always requires TLS, even if deployment detection is unavailable.
    Production callers can require TLS for non-Neon PostgreSQL endpoints too.
    """
    normalized_url, ssl_context = normalize_asyncpg_url(
        raw_url,
        require_tls=require_tls,
    )
    host = (make_url(normalized_url).host or "").strip().lower().rstrip(".")
    is_neon_endpoint = host == "neon.tech" or host.endswith(".neon.tech")

    if (require_tls or is_neon_endpoint) and not isinstance(
        ssl_context, ssl.SSLContext
    ):
        # Never allow a future URL-normalization regression to silently turn
        # a production/Neon migration connection into plaintext.
        raise RuntimeError(
            "TLS is required for this migration database, but no verified "
            "SSLContext was prepared."
        )

    return normalized_url, ({"ssl": ssl_context} if ssl_context is not None else {})
