"""Unit tests for secure PostgreSQL asyncpg URL normalization."""
from __future__ import annotations

import ssl

import pytest

from app.core.db_url import normalize_asyncpg_url


def test_production_url_without_sslmode_still_uses_verified_tls():
    url, context = normalize_asyncpg_url(
        "postgresql://nlc_app:secret@db.example.com/neondb?application_name=nlc",
        require_tls=True,
    )

    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url
    assert "application_name=nlc" in url
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("parameter", ["sslmode=require", "ssl=require"])
def test_libpq_tls_parameters_are_translated_to_asyncpg_context(parameter):
    url, context = normalize_asyncpg_url(
        f"postgresql://nlc_app:secret@db.example.com/neondb?{parameter}",
        require_tls=False,
    )

    assert "sslmode" not in url
    assert "ssl=" not in url
    assert isinstance(context, ssl.SSLContext)


def test_production_refuses_explicit_tls_disable():
    with pytest.raises(ValueError, match="cannot be disabled"):
        normalize_asyncpg_url(
            "postgresql://nlc_app:secret@db.example.com/neondb?sslmode=disable",
            require_tls=True,
        )


def test_development_can_keep_tls_disabled_without_ssl_connect_argument():
    url, context = normalize_asyncpg_url(
        "postgresql://nlc_app:secret@localhost/neondb?sslmode=disable",
        require_tls=False,
    )

    assert "sslmode" not in url
    assert context is None
