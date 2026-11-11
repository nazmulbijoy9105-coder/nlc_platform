"""Production safety guards for the legacy rule bootstrap utility."""

import pytest

from scripts.seed_rules import assert_seed_write_allowed


def _clear_deployment_markers(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)


def test_seed_write_requires_explicit_development_opt_in(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    _clear_deployment_markers(monkeypatch)
    monkeypatch.delenv("NLC_ALLOW_DEVELOPMENT_RULE_SEED", raising=False)

    with pytest.raises(RuntimeError, match="explicit local development opt-in"):
        assert_seed_write_allowed('postgresql+asyncpg://test:test@localhost:5432/nlc_dev')


@pytest.mark.parametrize("environment", ["production", "prod"])
def test_seed_write_is_blocked_in_production_even_with_opt_in(monkeypatch, environment):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("NLC_ALLOW_DEVELOPMENT_RULE_SEED", "true")
    _clear_deployment_markers(monkeypatch)

    with pytest.raises(RuntimeError, match="disabled in production/Render"):
        assert_seed_write_allowed("postgresql+asyncpg://test:test@localhost:5432/nlc_dev")


def test_seed_write_is_blocked_on_render_even_if_environment_is_misconfigured(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("NLC_ALLOW_DEVELOPMENT_RULE_SEED", "true")

    with pytest.raises(RuntimeError, match="disabled in production/Render"):
        assert_seed_write_allowed("postgresql+asyncpg://test:test@localhost:5432/nlc_dev")


def test_seed_write_can_be_enabled_for_local_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("NLC_ALLOW_DEVELOPMENT_RULE_SEED", "true")
    _clear_deployment_markers(monkeypatch)

    assert_seed_write_allowed("postgresql+asyncpg://test:test@localhost:5432/nlc_dev")

 
def test_seed_write_rejects_remote_neon_database_even_with_opt_in(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("NLC_ALLOW_DEVELOPMENT_RULE_SEED", "true")
    _clear_deployment_markers(monkeypatch)

    with pytest.raises(RuntimeError, match="restricted to local PostgreSQL hosts"):
        assert_seed_write_allowed(
            "postgresql+asyncpg://user:password@ep-example.ap-southeast-1.aws.neon.tech/neondb"
        )
