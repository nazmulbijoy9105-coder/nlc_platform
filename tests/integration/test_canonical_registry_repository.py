"""Integration-suite coverage for the SQLAlchemy registry adapter.

The adapter is exercised as a repository-to-resolver boundary here. Real
PostgreSQL role/RLS enforcement is covered independently by test_rls_hardening.
"""
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import DBAPIError

from app.rule_engine.canonical_identity import canonical_definition_hash
from app.rule_engine.canonical_registry_repository import resolve_from_registry

pytestmark = pytest.mark.integration

NS = "engine-build:integration"
LEGACY = "INC-001"
CANONICAL = "00000000-0000-0000-0000-000000000001"
REVISION = "00000000-0000-0000-0000-000000000002"
DEFINITION = {"provision": "Companies Act 1994, s. 81", "obligation": "hold_agm"}


def _registry_rows():
    alias = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000003",
        source_namespace=NS,
        historical_rule_id=LEGACY,
        canonical_rule_id=CANONICAL,
        resolution_status="RESOLVED",
        valid_from=date(2020, 1, 1),
        valid_to=None,
    )
    identity = SimpleNamespace(
        id=CANONICAL,
        identity_status="ACTIVE",
        jurisdiction="BD",
    )
    revision = SimpleNamespace(
        id=REVISION,
        canonical_rule_id=CANONICAL,
        revision_number=1,
        effective_from=date(2020, 1, 1),
        effective_to=None,
        definition_json=DEFINITION,
        definition_hash=canonical_definition_hash(DEFINITION),
        approval_state="REVIEW_REQUIRED",
        evaluator_name="agm_evaluator",
        evaluator_version="2.1.0",
        evaluator_artifact_hash="a" * 64,\n        evaluator_name="agm_evaluator",\n        evaluator_version="2.1.0",\n        evaluator_artifact_hash="a" * 64,
    )
    return alias, identity, revision


def _session_for(*rowsets):
    session = MagicMock()
    results = []
    for rows in rowsets:
        result = MagicMock()
        result.scalars.return_value.all.return_value = list(rows)
        results.append(result)
    session.execute = AsyncMock(side_effect=results)
    return session


@pytest.mark.asyncio
async def test_registry_adapter_composes_database_rows_with_deterministic_resolver():
    alias, identity, revision = _registry_rows()
    session = _session_for([alias], [identity], [revision])

    result = await resolve_from_registry(
        session,
        source_namespace=NS,
        historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1),
        jurisdiction="BD",
    )

    assert result.status == "RESOLVED"
    assert result.canonical_rule_id == CANONICAL
    assert result.revision_id == REVISION
    assert result.alias_id == "00000000-0000-0000-0000-000000000003"
    assert result.evaluator_name == "agm_evaluator"
    assert result.evaluator_version == "2.1.0"
    assert result.evaluator_artifact_hash == "a" * 64
    assert result.approval_state == "REVIEW_REQUIRED"
    assert session.execute.await_count == 3
    assert not session.commit.called
    assert not session.add.called


@pytest.mark.asyncio
async def test_registry_adapter_short_circuits_when_exact_alias_is_absent():
    session = _session_for([])

    result = await resolve_from_registry(
        session,
        source_namespace=NS,
        historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1),
        jurisdiction="BD",
    )

    assert result.status == "UNRESOLVED"
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_registry_adapter_sanitizes_database_permission_failures():
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=DBAPIError("SELECT", {}, Exception("permission denied"))
    )

    result = await resolve_from_registry(
        session,
        source_namespace=NS,
        historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1),
        jurisdiction="BD",
    )

    assert result.status == "REGISTRY_UNAVAILABLE"
    assert "permission denied" not in result.detail


@pytest.mark.asyncio
async def test_registry_adapter_rejects_missing_jurisdiction_without_query():
    session = MagicMock()
    session.execute = AsyncMock()

    result = await resolve_from_registry(
        session,
        source_namespace=NS,
        historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1),
        jurisdiction="",
    )

    assert result.status == "INVALID_LOOKUP_KEY"
    assert not session.execute.called
