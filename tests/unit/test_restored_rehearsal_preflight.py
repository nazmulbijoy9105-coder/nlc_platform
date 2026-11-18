import json

import pytest

from scripts import rehearse_restored_neon_branch as rehearsal


class _FakeConnection:
    async def close(self):
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "preflight",
    [
        {
            "missing_tables": ["webhook_endpoints", "webhook_deliveries", "rescue_audit_log"],
            "missing_columns_by_table": {},
        },
        {
            "missing_tables": [],
            "missing_columns_by_table": {"rescue_audit_log": ["actor_user_id"]},
        },
    ],
)
async def test_restored_rehearsal_blocks_before_alembic_on_pre_0042_schema_drift(
    monkeypatch, tmp_path, preflight
):
    """A 0042 branch with missing 0037/0038 schema must not reach Alembic 0044."""
    async def fake_connect(_url, *, assume_migration_owner=False):
        assert assume_migration_owner is True
        return _FakeConnection()

    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("migration or post-migration query must not run")

    monkeypatch.setattr(
        rehearsal,
        "_database_url",
        lambda name: f"postgresql://redacted/{name}",
    )
    monkeypatch.setattr(rehearsal, "_connect", fake_connect)
    monkeypatch.setattr(
        rehearsal,
        "_identity",
        lambda _conn: _async_value(
            {
                "project_id": rehearsal.EXPECTED_PROJECT_ID,
                "branch_id": rehearsal.EXPECTED_BRANCH_ID,
                "database_name": rehearsal.EXPECTED_DATABASE,
                "current_user": "nlc_migration_owner",
                "session_user": "nlc_migration_user",
                "alembic_versions": [rehearsal.EXPECTED_START_REVISION],
            }
        ),
    )
    monkeypatch.setattr(
        rehearsal, "_preflight_pre_0042_tables", lambda _conn: _async_value(preflight)
    )
    def fail_sync_if_called(*_args, **_kwargs):
        raise AssertionError("Alembic command must not run")

    monkeypatch.setattr(rehearsal, "_table_row_counts", fail_if_called)
    monkeypatch.setattr(rehearsal, "_run_command", fail_sync_if_called)
    report_path = tmp_path / "neon-restored-branch-rehearsal.json"
    monkeypatch.setattr(rehearsal, "REPORT_PATH", report_path)

    exit_code = await rehearsal.main()

    assert exit_code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "BLOCKED_SCHEMA_DRIFT"
    assert report["migration_applied"] is False
    assert report["pre_0042_schema_preflight"] == preflight
    assert "blocked before Alembic" in report["error"]


async def _async_value(value):
    return value


@pytest.mark.asyncio
async def test_0115_preflight_blocks_missing_legal_rule_schema_columns():
    class Connection:
        async def fetch(self, query, *args):
            assert "information_schema.columns" in query
            return [{"column_name": "rule_id"}, {"column_name": "rule_name"}]

    report = await rehearsal._preflight_legacy_rule_identities(Connection())

    assert report["status"] == "BLOCKED_SCHEMA_DRIFT"
    assert "verification_status" in report["missing_columns"]
    assert "verification_notes" in report["missing_columns"]


@pytest.mark.asyncio
async def test_0115_preflight_accepts_observed_legacy_rows_for_quarantine_only():
    class Connection:
        async def fetch(self, query, *args):
            if "information_schema.columns" in query:
                return [{"column_name": name} for name in rehearsal.LEGACY_RULE_REQUIRED_COLUMNS]
            assert "rule_condition ->> 'trigger'" in query
            return [
                {
                    "rule_id": "INC-001",
                    "rule_name": "Certificate of Incorporation Not Obtained",
                    "statutory_basis": "Section 9, Companies Act 1994 (Bangladesh)",
                    "trigger": "certificate_obtained == False",
                },
                {
                    "rule_id": "INC-002",
                    "rule_name": "Memorandum and Articles Not Filed",
                    "statutory_basis": "Section 11, Companies Act 1994 (Bangladesh)",
                    "trigger": "moa_filed == False OR aoa_filed == False",
                },
            ]

    report = await rehearsal._preflight_legacy_rule_identities(Connection())

    assert report["status"] == "PASS"
    assert report["fingerprint_mismatches"] == []


@pytest.mark.asyncio
async def test_0115_preflight_still_blocks_unrecognised_identity_drift():
    class Connection:
        async def fetch(self, query, *args):
            if "information_schema.columns" in query:
                return [{"column_name": name} for name in rehearsal.LEGACY_RULE_REQUIRED_COLUMNS]
            return [
                {
                    "rule_id": "INC-001",
                    "rule_name": "Unexpected renamed obligation",
                    "statutory_basis": "Section 9, Companies Act 1994 (Bangladesh)",
                    "trigger": "certificate_obtained == False",
                },
                {
                    "rule_id": "INC-002",
                    "rule_name": "Memorandum and Articles Not Filed",
                    "statutory_basis": "Section 11, Companies Act 1994 (Bangladesh)",
                    "trigger": "moa_filed == False OR aoa_filed == False",
                },
            ]

    report = await rehearsal._preflight_legacy_rule_identities(Connection())

    assert report["status"] == "BLOCKED_LEGACY_IDENTITY_DRIFT"
    assert [item["rule_id"] for item in report["fingerprint_mismatches"]] == ["INC-001"]
