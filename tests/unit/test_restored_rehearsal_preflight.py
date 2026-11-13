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
