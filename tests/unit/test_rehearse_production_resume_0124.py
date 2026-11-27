"""Contract tests for the strict 0112-to-0128 production migration rehearsal."""

from __future__ import annotations

import ast
import asyncio
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "rehearse_production_0112_to_0128.py"
SPEC = importlib.util.spec_from_file_location("rehearsal_0112_to_0128_contract_tests", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
rehearsal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rehearsal)


def test_0112_to_0128_script_exists_parses_and_imports():
    assert SCRIPT.is_file()
    ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
    assert callable(rehearsal.main)


def test_rehearsal_revision_constants_are_pinned_to_the_full_path():
    assert rehearsal.START_REVISION == "0112_runtime_acl_and_alembic_rls"
    assert rehearsal.HEAD_REVISION == "0128_agm001_calendar_month_definition"
    assert rehearsal.AGM_PRE_0125_REVISION == "0124_restore_85_rule_catalogue_parity"
    assert rehearsal.AGM_POST_0125_REVISION == "0125_reconcile_agm001_statutory_basis"
    assert rehearsal.AGM_POST_0126_REVISION == "0126_score_independent_rescue_workflow"


class FakeConn:
    """Minimal asyncpg-like connection for early-reject main() paths.

    asyncpg.Connection exposes is_closed() as a method (not a bool property).
    """

    def __init__(self):
        self._closed = False

    def is_closed(self) -> bool:
        return self._closed

    @property
    def closed(self) -> bool:
        return self._closed

    async def fetchrow(self, _sql):
        return {
            "session_user": "nlc_migration_user",
            "current_user": "nlc_migration_user",
            "current_database": rehearsal.DATABASE,
            "project_id": rehearsal.PROJECT_ID,
            "branch_id": "isolated-test-branch",
        }

    async def close(self):
        self._closed = True


@pytest.mark.parametrize(
    "starting_revision",
    [
        rehearsal.PREVIOUS_REVISION,
        rehearsal.AGM_PRE_0125_REVISION,
        rehearsal.AGM_POST_0125_REVISION,
        rehearsal.AGM_POST_0126_REVISION,
        rehearsal.HEAD_REVISION,
        "0100_unknown",
    ],
)
def test_main_rejects_any_non_0112_baseline_before_migration(
    monkeypatch, tmp_path, starting_revision
):
    conn = FakeConn()
    monkeypatch.setattr(rehearsal, "REPORT", tmp_path / "rehearsal.json")
    monkeypatch.setattr(rehearsal, "_connect", lambda: _return_conn(conn))

    async def revision(_conn):
        return [starting_revision]

    monkeypatch.setattr(rehearsal, "_alembic_revision", revision)
    monkeypatch.setattr(rehearsal, "_source_provenance", lambda: {"commit_sha": "test"})

    with pytest.raises(RuntimeError, match="Fresh disposable rehearsal must start at exactly"):
        asyncio.run(rehearsal.main())

    assert conn.closed
    assert conn.is_closed() is True
    assert not (tmp_path / "rehearsal.json").exists()


async def _return_conn(conn):
    return conn


def test_rehearsal_source_provenance_and_schema_inventory_are_in_report_contract():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "NLC_EXPECTED_SOURCE_SHA" in source
    assert '"input_sha256": hashes' in source
    assert '"schema_inventory_before": schema_before' in source
    assert '"schema_inventory_after": schema_after' in source
    assert "async def _application_role_parity()" in source
    assert "async def _audit_view_parity()" in source
