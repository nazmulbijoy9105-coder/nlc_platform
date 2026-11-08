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

    asyncpg does not accept several libpq-only URL parameters. Remove
    sslmode/ssl and channel_binding from the URL; express TLS policy through
    asyncpg's ssl connect argument. Production callers always require TLS.
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
    if require_tls and explicitly_disabled:
        raise ValueError(
            "PostgreSQL TLS cannot be disabled in production or on Render"
        )

    tls_required = require_tls or sslmode in {
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
