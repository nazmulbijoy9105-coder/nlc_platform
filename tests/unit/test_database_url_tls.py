"""Unit tests for secure PostgreSQL asyncpg URL normalization."""
from __future__ import annotations

import ssl

import pytest

from app.db_url import is_render_runtime, normalize_asyncpg_url


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

@pytest.mark.parametrize(
    "raw_url",
    ["", "mysql://user:secret@db.example.com/nlc"],
)
def test_rejects_empty_or_non_postgresql_connection_urls(raw_url):
    with pytest.raises(ValueError):
        normalize_asyncpg_url(raw_url, require_tls=True)



def test_libpq_channel_binding_is_removed_but_verified_tls_is_preserved():
    url, context = normalize_asyncpg_url(
        "postgresql://nlc_app:secret@db.example.com/neondb"
        "?channel_binding=require&application_name=nlc",
        require_tls=True,
    )

    assert "channel_binding" not in url
    assert "application_name=nlc" in url
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize(
    "render_environment",
    [
        {"RENDER": "true"},
        {"RENDER_SERVICE_ID": "srv-example"},
        {"RENDER_INSTANCE_ID": "srv-example-instance"},
    ],
)
def test_render_environment_identifiers_enable_deployment_tls(render_environment):
    assert is_render_runtime(render_environment) is True


def test_non_render_environment_does_not_enable_render_detection():
    assert is_render_runtime({"ENVIRONMENT": "development"}) is False
