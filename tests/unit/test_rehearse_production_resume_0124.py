"""Regression coverage for resuming the production rehearsal from revision 0124."""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "rehearse_production_0112_to_0122.py"
SPEC = importlib.util.spec_from_file_location("rehearsal_resume_0124_tests", SCRIPT)
rehearsal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rehearsal)


def test_script_parses_and_imports():
    ast.parse(SCRIPT.read_text(encoding="utf-8"))
    assert callable(rehearsal.main)


class FakeConn:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True

    def is_closed(self):
        return self.closed

    async def fetchrow(self, sql):
        assert "session_user" in sql
        return {"session_user": "nlc_migration_user", "branch_id": "test-branch"}


def _main_harness(monkeypatch, tmp_path, starting_revision):
    commands = []
    archive_reads = []
    revision_calls = 0
    current_revision = starting_revision
    report = tmp_path / "rehearsal.json"

    async def connect():
        return FakeConn()

    async def alembic_revision(conn):
        nonlocal revision_calls
        revision_calls += 1
        if revision_calls == 1:
            return [starting_revision]
        return [rehearsal.HEAD_REVISION]

    async def rows_digest(conn, table):
        return {"rows": 0, "sha256": "unchanged"}

    async def legacy_payloads(conn, *, from_archive=False):
        archive_reads.append(from_archive)
        return {"AGM-001": {"rule_version": "1.0.0"}}

    async def rule_payload(conn, rule_id):
        assert rule_id == "AGM-001"
        return {
            "statutory_basis": "Section 81, Companies Act 1994 (Bangladesh)",
            "rule_version": "1.0.0",
        }

    async def postflight(conn, before_tables, before_rules, agm001_before_0125):
        assert set(before_tables) == set(rehearsal.HISTORICAL_TABLES)
        assert "AGM-001" in before_rules
        assert agm001_before_0125["rule_version"] == "1.0.0"
        return {}

    async def audit_view_parity():
        return {}

    def run(args, **kwargs):
        nonlocal current_revision
        commands.append(args)
        assert kwargs["check"] is True
        assert kwargs["env"]["ENVIRONMENT"] == "production"
        if args[3] == "upgrade":
            current_revision = args[4]
        return subprocess.CompletedProcess(args, 0, current_revision, "")

    monkeypatch.setattr(rehearsal, "_connect", connect)
    monkeypatch.setattr(rehearsal, "_alembic_revision", alembic_revision)
    monkeypatch.setattr(rehearsal, "_rows_digest", rows_digest)
    monkeypatch.setattr(rehearsal, "_legacy_payloads", legacy_payloads)
    monkeypatch.setattr(rehearsal, "_rule_payload", rule_payload)
    monkeypatch.setattr(rehearsal, "_postflight", postflight)
    monkeypatch.setattr(rehearsal, "_audit_view_parity", audit_view_parity)
    monkeypatch.setattr(rehearsal.subprocess, "run", run)
    monkeypatch.setattr(rehearsal, "REPORT", report)
    return commands, archive_reads, report


def test_main_resumes_from_0124(monkeypatch, tmp_path):
    commands, archive_reads, report_path = _main_harness(
        monkeypatch, tmp_path, rehearsal.AGM_PRE_0125_REVISION
    )

    asyncio.run(rehearsal.main())

    assert commands == [
        ["python", "-m", "alembic", "upgrade", rehearsal.HEAD_REVISION],
        ["python", "-m", "alembic", "current"],
    ]
    assert archive_reads == [True]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["starting_revision"] == rehearsal.AGM_PRE_0125_REVISION
    assert report["mode"] == "resumed_from_0124"
    assert report["legacy_before_image_source"] == "legal_rule_identity_archive"
    assert report["final_revision"] == [rehearsal.HEAD_REVISION]


def test_main_from_start_preserves_both_upgrade_boundaries(monkeypatch, tmp_path):
    commands, archive_reads, report_path = _main_harness(
        monkeypatch, tmp_path, rehearsal.START_REVISION
    )

    asyncio.run(rehearsal.main())

    assert commands == [
        ["python", "-m", "alembic", "upgrade", rehearsal.AGM_PRE_0125_REVISION],
        ["python", "-m", "alembic", "current"],
        ["python", "-m", "alembic", "upgrade", rehearsal.HEAD_REVISION],
        ["python", "-m", "alembic", "current"],
    ]
    assert archive_reads == [False]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["starting_revision"] == rehearsal.START_REVISION
    assert report["final_revision"] == [rehearsal.HEAD_REVISION]
    assert "mode" not in report


def test_main_rejects_unknown_revision(monkeypatch, tmp_path):
    commands, archive_reads, report_path = _main_harness(monkeypatch, tmp_path, "0100_unknown")

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(rehearsal.main())

    for revision in (
        rehearsal.START_REVISION,
        rehearsal.AGM_PRE_0125_REVISION,
        rehearsal.HEAD_REVISION,
    ):
        assert revision in str(exc_info.value)
    assert commands == []
    assert archive_reads == []
    assert not report_path.exists()


def test_main_verifies_existing_head_without_subprocess(monkeypatch, tmp_path):
    commands, archive_reads, report_path = _main_harness(
        monkeypatch, tmp_path, rehearsal.HEAD_REVISION
    )

    asyncio.run(rehearsal.main())

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["mode"] == "verified_existing_rehearsal"
    assert report["final_revision"] == [rehearsal.HEAD_REVISION]
    assert report["restricted_audit_view_parity"] == {}
    assert commands == []
    assert archive_reads == []


class LegacyConn:
    def __init__(self):
        self.calls = []
        self.rows = {}
        for rule_id, fingerprints in rehearsal.LEGACY_FINGERPRINTS.items():
            rule_name, statutory_basis, trigger = next(iter(fingerprints))
            self.rows[rule_id] = {
                "payload": {"rule_id": rule_id, "rule_name": rule_name},
                "rule_name": rule_name,
                "statutory_basis": statutory_basis,
                "trigger": trigger,
            }

    async def fetchrow(self, sql, rule_id):
        self.calls.append((sql, rule_id))
        return self.rows.get(rule_id)


@pytest.mark.parametrize("from_archive", [True, False])
def test_legacy_payloads_selects_archive_only_for_inc_rules(from_archive):
    conn = LegacyConn()

    result = asyncio.run(rehearsal._legacy_payloads(conn, from_archive=from_archive))

    assert result == {rule_id: row["payload"] for rule_id, row in conn.rows.items()}
    assert len(conn.calls) == 3
    for sql, rule_id in conn.calls:
        if from_archive and rule_id in {"INC-001", "INC-002"}:
            assert "legal_rule_identity_archive" in sql
            assert "ORDER BY captured_at, legacy_identity_key LIMIT 1" in sql
        else:
            assert "public.legal_rules" in sql


def test_legacy_payloads_allows_missing_inc002_in_archive():
    conn = LegacyConn()
    del conn.rows["INC-002"]

    result = asyncio.run(rehearsal._legacy_payloads(conn, from_archive=True))

    assert set(result) == {"INC-001", "AGM-001"}
    assert "INC-002" not in result


def test_legacy_payloads_rejects_missing_inc001_in_archive():
    conn = LegacyConn()
    del conn.rows["INC-001"]

    with pytest.raises(RuntimeError, match="INC-001 is missing"):
        asyncio.run(rehearsal._legacy_payloads(conn, from_archive=True))


def test_legacy_payloads_rejects_unknown_fingerprint_in_archive():
    conn = LegacyConn()
    conn.rows["INC-001"]["rule_name"] = "Unknown legacy identity"

    with pytest.raises(RuntimeError, match="INC-001 does not match a known legacy"):
        asyncio.run(rehearsal._legacy_payloads(conn, from_archive=True))
