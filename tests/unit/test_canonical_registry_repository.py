from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import DBAPIError

from app.rule_engine.canonical_registry_repository import resolve_from_registry
from app.rule_engine.canonical_identity import canonical_definition_hash


NS = "engine-build:abc123"
LEGACY = "INC-001"
CANONICAL = "00000000-0000-0000-0000-000000000001"
REVISION = "00000000-0000-0000-0000-000000000002"
DEFINITION = {"provision": "Companies Act 1994, s. 81", "obligation": "hold_agm"}


def _models():
    alias = SimpleNamespace(
        source_namespace=NS, historical_rule_id=LEGACY,
        canonical_rule_id=CANONICAL, resolution_status="RESOLVED",
        valid_from=date(2020, 1, 1), valid_to=None,
    )
    identity = SimpleNamespace(
        id=CANONICAL, identity_status="ACTIVE", jurisdiction="BD",
    )
    revision = SimpleNamespace(
        id=REVISION, canonical_rule_id=CANONICAL, revision_number=1,
        effective_from=date(2020, 1, 1), effective_to=None,
        definition_json=DEFINITION,
        definition_hash=canonical_definition_hash(DEFINITION),
        approval_state="REVIEW_REQUIRED",
    )
    return alias, identity, revision


def _session_with_results(*rows):
    session = MagicMock()
    results = []
    for rowset in rows:
        result = MagicMock()
        result.scalars.return_value.all.return_value = list(rowset)
        results.append(result)
    session.execute = AsyncMock(side_effect=results)
    return session


@pytest.mark.asyncio
async def test_repository_resolves_exact_registry_rows_without_writes():
    alias, identity, revision = _models()
    session = _session_with_results([alias], [identity], [revision])

    result = await resolve_from_registry(
        session, source_namespace=NS, historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1), jurisdiction="BD",
    )

    assert result.status == "RESOLVED"
    assert result.canonical_rule_id == CANONICAL
    assert result.revision_id == REVISION
    assert result.approval_state == "REVIEW_REQUIRED"
    assert session.execute.await_count == 3
    assert not session.commit.called
    assert not session.add.called


@pytest.mark.asyncio
async def test_repository_does_not_query_identity_or_revision_when_alias_missing():
    session = _session_with_results([])

    result = await resolve_from_registry(
        session, source_namespace=NS, historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1), jurisdiction="BD",
    )

    assert result.status == "UNRESOLVED"
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_repository_rejects_cross_jurisdiction_identity():
    alias, identity, revision = _models()
    identity.jurisdiction = "LK"
    session = _session_with_results([alias], [identity], [revision])

    result = await resolve_from_registry(
        session, source_namespace=NS, historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1), jurisdiction="BD",
    )

    assert result.status == "JURISDICTION_MISMATCH"


@pytest.mark.asyncio
async def test_repository_treats_rls_hidden_identity_as_registry_unavailable():
    alias, _, _ = _models()
    session = _session_with_results([alias], [], [])

    result = await resolve_from_registry(
        session, source_namespace=NS, historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1), jurisdiction="BD",
    )

    assert result.status == "REGISTRY_UNAVAILABLE"
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_repository_fails_closed_on_database_permission_error():
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=DBAPIError("SELECT", {}, Exception("permission denied"))
    )

    result = await resolve_from_registry(
        session, source_namespace=NS, historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1), jurisdiction="BD",
    )

    assert result.status == "REGISTRY_UNAVAILABLE"
    assert "permission denied" not in result.detail


@pytest.mark.asyncio
async def test_repository_rejects_missing_jurisdiction_before_database_access():
    session = MagicMock()
    session.execute = AsyncMock()

    result = await resolve_from_registry(
        session, source_namespace=NS, historical_rule_id=LEGACY,
        effective_date=date(2026, 1, 1), jurisdiction="",
    )

    assert result.status == "INVALID_LOOKUP_KEY"
    assert not session.execute.called
