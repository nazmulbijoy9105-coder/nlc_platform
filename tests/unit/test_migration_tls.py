from __future__ import annotations

import ssl

import pytest
from sqlalchemy.engine import make_url

from app.db_url import normalize_asyncpg_url, prepare_asyncpg_connection


def test_neon_pooler_always_gets_verified_tls_and_libpq_flags_are_removed() -> None:
    raw_url = (
        "postgresql://migration_user:placeholder@"
        "ep-example-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )

    normalized_url, connect_args = prepare_asyncpg_connection(
        raw_url,
        require_tls=False,
    )

    parsed = make_url(normalized_url)
    assert parsed.drivername == "postgresql+asyncpg"
    assert parsed.host.endswith(".aws.neon.tech")
    assert "sslmode" not in parsed.query
    assert "channel_binding" not in parsed.query
    assert set(connect_args) == {"ssl"}
    assert isinstance(connect_args["ssl"], ssl.SSLContext)


def test_production_non_neon_connection_gets_verified_tls() -> None:
    normalized_url, connect_args = prepare_asyncpg_connection(
        "postgresql://migration_user:placeholder@db.example.test/neondb",
        require_tls=True,
    )

    assert make_url(normalized_url).drivername == "postgresql+asyncpg"
    assert isinstance(connect_args["ssl"], ssl.SSLContext)


def test_local_non_neon_connection_does_not_force_tls() -> None:
    normalized_url, connect_args = prepare_asyncpg_connection(
        "postgresql://local_user:placeholder@localhost/nlc_test",
        require_tls=False,
    )

    assert make_url(normalized_url).drivername == "postgresql+asyncpg"
    assert connect_args == {}


def test_neon_tls_cannot_be_disabled() -> None:
    with pytest.raises(ValueError, match="TLS cannot be disabled"):
        normalize_asyncpg_url(
            "postgresql://migration_user:placeholder@"
            "ep-example-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb"
            "?sslmode=disable",
            require_tls=False,
        )
