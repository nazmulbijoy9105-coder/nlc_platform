"""Keep the restored-branch rehearsal pinned to the real Alembic head/schema."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from scripts.rehearse_restored_neon_branch import (
    EXPECTED_HEAD_REVISION,
    EXPECTED_PRE_IDENTITY_REVISION,
    EXPECTED_PROVIDER_MEMBERSHIPS,
    EXPECTED_START_REVISION,
    _preflight_restricted_role_security,
    POST_MIGRATION_REQUIRED_COLUMNS,
    PRE_0042_REQUIRED_COLUMNS,
)

ROOT = Path(__file__).resolve().parents[2]


def _assignment_literal(tree: ast.AST, name: str):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in targets
            ):
                return ast.literal_eval(node.value)
    raise AssertionError(f"Missing literal assignment: {name}")


def test_rehearsal_head_tracks_the_single_repository_alembic_head():
    revisions: set[str] = set()
    referenced: set[str] = set()
    for path in (ROOT / "alembic/versions").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        revision = _assignment_literal(tree, "revision")
        down_revision = _assignment_literal(tree, "down_revision")
        revisions.add(revision)
        if isinstance(down_revision, str):
            referenced.add(down_revision)
        elif isinstance(down_revision, (tuple, list)):
            referenced.update(
                item for item in down_revision if isinstance(item, str)
            )

    heads = revisions - referenced
    assert heads == {EXPECTED_HEAD_REVISION}
    assert EXPECTED_HEAD_REVISION == "0127_one_active_rescue_plan_per_company"
    assert EXPECTED_START_REVISION == "0042_dedup_key"


def test_rehearsal_pre_0042_schema_matches_alembic_env_guard():
    env_tree = ast.parse(
        (ROOT / "alembic/env.py").read_text(encoding="utf-8"),
        filename="alembic/env.py",
    )
    guard = next(
        node for node in ast.walk(env_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "preflight_historical_evidence_schema"
    )
    expected_columns = next(
        ast.literal_eval(node.value)
        for node in ast.walk(guard)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "expected_columns"
            for target in node.targets
        )
    )
    assert PRE_0042_REQUIRED_COLUMNS == expected_columns


def test_webhook_deliveries_preflight_uses_original_0037_shape():
    assert "updated_at" not in PRE_0042_REQUIRED_COLUMNS["webhook_deliveries"]
    assert "updated_at" in PRE_0042_REQUIRED_COLUMNS["webhook_endpoints"]
    assert "updated_at" in PRE_0042_REQUIRED_COLUMNS["rescue_audit_log"]
    assert "updated_at" in POST_MIGRATION_REQUIRED_COLUMNS["webhook_deliveries"]


def test_0115_identity_preflight_runs_after_upgrade_to_0114_and_before_head():
    source = (ROOT / "scripts/rehearse_restored_neon_branch.py").read_text(
        encoding="utf-8"
    )
    upgrade_0114 = source.index('["alembic", "upgrade", EXPECTED_PRE_IDENTITY_REVISION]')
    identity_preflight = source.index(
        "_preflight_legacy_rule_identities(conn)", upgrade_0114
    )
    upgrade_head = source.index('["alembic", "upgrade", "head"]', identity_preflight)

    assert EXPECTED_PRE_IDENTITY_REVISION == "0114_annual_return_filing_status_provenance"
    assert upgrade_0114 < identity_preflight < upgrade_head


def test_rehearsal_requires_finding_binding_schema_and_forced_rls_audit():
    assert POST_MIGRATION_REQUIRED_COLUMNS["compliance_finding_bindings"] >= {
        "company_id", "compliance_flag_id", "evaluation_run_id",
        "canonical_rule_id", "revision_id", "finding_snapshot_hash",
        "finding_snapshot_canonical", "evidence_manifest_canonical",
    }
    assert POST_MIGRATION_REQUIRED_COLUMNS["compliance_finding_evidence"] >= {
        "company_id", "company_fact_id", "fact_value_snapshot",
        "document_sha256", "evidence_hash",
        "fact_value_canonical", "evidence_canonical",
    }


def test_rehearsal_rejects_any_membership_involving_app_or_audit_roles():
    assert EXPECTED_PROVIDER_MEMBERSHIPS == set()

def test_role_security_preflight_runs_before_any_alembic_migration():
    source = (ROOT / "scripts/rehearse_restored_neon_branch.py").read_text(
        encoding="utf-8"
    )
    role_preflight = source.index("_preflight_restricted_role_security(conn)")
    upgrade_0114 = source.index(
        '["alembic", "upgrade", EXPECTED_PRE_IDENTITY_REVISION]'
    )
    upgrade_head = source.index('["alembic", "upgrade", "head"]')

    assert role_preflight < upgrade_0114 < upgrade_head
    assert 'report["migration_applied"] = False' in source[role_preflight:upgrade_0114]
    assert '"BLOCKED_ROLE_SECURITY"' in source

class _FakeRoleConnection:
    def __init__(self, roles, memberships):
        self.roles = roles
        self.memberships = memberships

    async def fetch(self, query):
        if "FROM pg_auth_members membership" in query:
            return self.memberships
        return self.roles


def _role_row(name, *, inherit=False):
    return {
        "rolname": name,
        "rolcanlogin": True,
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolinherit": inherit,
        "rolreplication": False,
        "rolbypassrls": False,
    }


def test_role_preflight_blocks_inherit_and_owner_membership_before_migration():
    conn = _FakeRoleConnection(
        [_role_row("nlc_app_role", inherit=True), _role_row("nlc_ci_audit_role")],
        [{
            "member_role": "neondb_owner",
            "granted_role": "nlc_app_role",
            "grantor_role": "cloud_admin",
            "admin_option": True,
            "inherit_option": False,
            "set_option": False,
        }],
    )

    result = asyncio.run(_preflight_restricted_role_security(conn))

    assert result["status"] == "BLOCKED_ROLE_SECURITY"
    assert result["unsafe_roles"] == ["nlc_app_role"]
    assert result["restricted_memberships"][0]["granted_role"] == "nlc_app_role"


def test_role_preflight_passes_only_noinherit_roles_without_memberships():
    conn = _FakeRoleConnection(
        [_role_row("nlc_app_role"), _role_row("nlc_ci_audit_role")],
        [],
    )

    result = asyncio.run(_preflight_restricted_role_security(conn))

    assert result["status"] == "PASS"
    assert result["restricted_memberships"] == []

def test_0125_agm001_migration_records_prior_definition_and_advances_version():
    migration = (
        ROOT / "alembic/versions/0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")

    history_insert = migration.index(
        "INSERT INTO public.legal_rule_versions"
    )
    catalogue_update = migration.index(
        "UPDATE public.legal_rules"
    )
    assert history_insert < catalogue_update
    assert "to_jsonb(rule) AS previous_definition" in migration
    assert "previous_version" in migration
    assert "changed_by" in migration
    assert "actor_type" in migration
    assert "'MIGRATION'" in migration
    assert "migration_revision" in migration
    assert "op.alter_column(" in migration
    assert 'nullable=True' in migration
    assert "rule_version = :next_version" in migration
    assert "last_modified_at = now()" in migration
    assert "last_modified_by = :changed_by" not in migration


def test_0125_migration_actor_does_not_require_a_bootstrap_user():
    migration = (
        ROOT / "alembic/versions/0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")
    model = (ROOT / "app/models/rules.py").read_text(encoding="utf-8")

    assert "changed_by, changed_at" in migration
    assert "VALUES" in migration
    assert "'MIGRATION', :migration_revision" in migration
    assert "COALESCE(" not in migration
    assert "active SUPER_ADMIN user is available" not in migration
    assert "changed_by IS NULL" in migration
    assert "migration_revision IS NOT NULL" in migration
    assert "changed_by: Mapped[uuid.UUID | None]" in model
    assert 'server_default="USER"' in model
    assert "ck_legal_rule_versions_actor_provenance" in model


def test_production_rehearsal_active_catalogue_guard_names_0125():
    source = (
        ROOT / "scripts/rehearse_production_0112_to_0122.py"
    ).read_text(encoding="utf-8")
    assert '"0125 requires exactly 85 active catalogue rows "' in source
    assert '"0124 requires exactly 85 active catalogue rows "' not in source
