"""Three-channel rule-change separation — structural contract tests.

The legal-rule corpus is governed by exactly three mutation channels. Each
channel has a distinct authority, scope and audit mechanism, and blurring
them is a governance defect even when the individual change looks harmless:

  CHANNEL 1 — Seeder (dev bootstrap only)
      Inserts MISSING canonical rule IDs into a local development database.
      Never changes existing rows: definitions AND the operator-controlled
      activation state (is_active) of existing rows are immutable here.
      Refuses writes outside explicit local-development opt-in; production
      registry changes must use Alembic. Enforced additionally by
      tests/unit/test_rule_seed_activation_preservation.py and
      tests/unit/test_rule_seed_write_guard.py.

  CHANNEL 2 — Canonical update migration (definition changes)
      Rule DEFINITIONS (name, statutory basis, severity, scoring, conditions)
      change only through reviewed, forward-only Alembic migrations run as
      the database-owner migration principal. The DB guard installed by
      0084 lets only that principal bypass the version-snapshot requirement
      and refuses any runtime role that owns the database. The append-only
      legal_rule_versions ledger (0050: UPDATE/DELETE/TRUNCATE rejected,
      app role holds SELECT+INSERT only) is the audit record.

  CHANNEL 3 — Operator workflow (activation changes)
      is_active (and other operator-facing fields) change only through
      PATCH /api/v1/rules/{rule_id}: SUPER_ADMIN role gate, mandatory
      change_reason (>= 10 chars), optimistic expected_version locking,
      LegalRuleVersion snapshot written BEFORE the row update, activity-log
      and structured-log audit. The 0084 DB trigger independently enforces
      the snapshot + active SUPER_ADMIN identity for every runtime UPDATE.

  VERIFICATION STATUS is deliberately NOT operator-mutable: counsel
  verification transitions belong to the canonical channel (source-controlled
  legal_approval_register.yaml + migration), never to PATCH or the provenance
  workflow. The engine's VERIFIED_RULE_IDS allowlist stays empty until a
  reviewed register change records counsel approval
  (scripts/check_rule_verification.py fails closed on this).

Any refactor that moves a mutation between channels, widens a channel's
scope, or drops its audit mechanism must update these pins in the same PR,
stating the PR that justifies the change.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SEED_PATH = ROOT / "scripts" / "seed_rules.py"
SERVICE_PATH = ROOT / "app" / "services" / "rules_service.py"
API_PATH = ROOT / "app" / "api" / "rules.py"
PROVENANCE_PATH = ROOT / "app" / "api" / "legal_provenance.py"
GUARD_0084 = ROOT / "alembic" / "versions" / "0084_install_legal_rule_version_guard.py"
HARDENING_0050 = ROOT / "alembic" / "versions" / "0050_signed_rls_identity_hardening.py"
AUDIT_VIEW_0093 = ROOT / "alembic" / "versions" / "0093_verified_rule_audit_view.py"
QUARANTINE_0090 = ROOT / "alembic" / "versions" / "0090_rule_registry_drift_quarantine.py"


def _src(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ════════════ CHANNEL 1 — Seeder: insert-only dev bootstrap ════════════

def test_seeder_channel_is_insert_only():
    src = _src(SEED_PATH)
    assert "UPDATE legal_rules" not in src, (
        "Channel 1 violation: the seeder must never change existing legal_rules rows"
    )
    assert "DELETE FROM legal_rules" not in src, (
        "Channel 1 violation: the seeder must never delete legal_rules rows"
    )
    # New-row bootstrap remains the only write, with a local-dev write guard.
    assert "INSERT INTO legal_rules" in src
    assert "assert_seed_write_allowed" in src
    assert "NLC_ALLOW_DEVELOPMENT_RULE_SEED" in src


def test_seeder_write_guard_rejects_remote_and_production():
    from scripts.seed_rules import assert_seed_write_allowed  # noqa: F401

    src = _src(SEED_PATH)
    assert "local_hosts" in src, "seeder write guard must restrict to local hosts"
    assert "Use Alembic" in src, "seeder must point production changes at Alembic"


# ════════════ CHANNEL 2 — Canonical migration: versioned definitions ════════════

def test_version_snapshot_trigger_gates_every_runtime_update():
    src = _src(GUARD_0084)
    assert "BEFORE UPDATE ON public.legal_rules" in src, (
        "Channel 2 guard missing: every runtime UPDATE of legal_rules must "
        "require a version snapshot"
    )
    assert "Only an active SUPER_ADMIN may modify legal rules" in src
    assert "matching legal_rule_versions snapshot is required" in src
    assert "legal_rules.rule_id is immutable" in src


def test_migration_owner_is_the_only_trigger_bypass_principal():
    src = _src(GUARD_0084)
    # Owner bypass exists, but is symmetrically bounded: the runtime role must
    # NOT own the database, and the migration principal MUST own it.
    assert "pg_has_role(session_user, 'pg_database_owner', 'USAGE')" in src
    assert "nlc_app_role must not own the database" in src
    assert "must run under the database-owner migration principal" in src


def test_version_ledger_is_append_only():
    src = _src(HARDENING_0050)
    assert "legal_rule_versions is append-only" in src
    assert "BEFORE UPDATE OR DELETE ON public.legal_rule_versions" in src
    assert "BEFORE TRUNCATE ON public.legal_rule_versions" in src
    assert (
        "REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE "
        "public.legal_rule_versions FROM nlc_app_role"
    ) in src
    assert "GRANT SELECT, INSERT ON TABLE public.legal_rule_versions TO nlc_app_role" in src


def test_audit_view_is_fail_closed_on_verification_and_activation():
    src = _src(AUDIT_VIEW_0093)
    assert "is_active IS TRUE" in src and "verification_status = 'VERIFIED'" in src, (
        "The audit candidate view must require BOTH activation and explicit "
        "citation verification — no default-true semantics"
    )


def test_verification_transitions_belong_to_the_canonical_channel():
    src = _src(QUARANTINE_0090)
    assert "verification_status = 'PENDING'" in src, (
        "verification_status transitions (including quarantine resets) are "
        "canonical-channel changes and must occur in reviewed migrations"
    )


# ════════════ CHANNEL 3 — Operator workflow: activation with audit ════════════

def _update_rule_node(service_src: str):
    tree = ast.parse(service_src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "update_rule":
            return node
    raise AssertionError("RulesService.update_rule not found")


def test_operator_channel_requires_authorization_reason_and_locking():
    src = _src(SERVICE_PATH)
    node = _update_rule_node(src)
    params = {a.arg for a in node.args.args + node.args.kwonlyargs}
    assert {"change_reason", "changed_by"} <= params, (
        "Operator channel must carry explicit actor and reason parameters"
    )
    assert "change_reason must contain at least 10 non-whitespace characters" in src
    assert "changed_by is required for every legal-rule change" in src
    assert "with_for_update()" in src, "concurrent operator edits must serialize"
    assert "expected_version" in src, "optimistic locking against stale edits required"

    # Snapshot BEFORE the row update, inside the same transaction, and as an
    # UNCONDITIONAL top-level statement — wrapping it in `if`/`try` would let
    # some updates bypass the version ledger (and then fail the 0084 trigger).
    segment = ast.get_source_segment(src, node) or ""
    assert "_create_version_snapshot(" in segment
    assert segment.index("_create_version_snapshot(") < segment.index("updates.items()"), (
        "version snapshot must be written before the rule row is mutated"
    )
    direct_snapshot = any(
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Await)
        and isinstance(stmt.value.value, ast.Call)
        and getattr(stmt.value.value.func, "attr", "") == "_create_version_snapshot"
        for stmt in node.body
    )
    assert direct_snapshot, (
        "_create_version_snapshot must be called unconditionally at the top "
        "level of update_rule — conditional snapshotting breaks the audit ledger"
    )


def test_operator_patch_endpoint_is_super_admin_only_and_audited():
    src = _src(API_PATH)
    m = re.search(r"@router\.patch\(\s*\n\s*\"/\{rule_id\}\"(.*?)async def update_rule", src, re.S)
    assert m, "PATCH /rules/{rule_id} endpoint not found"
    assert 'require_roles("SUPER_ADMIN")' in m.group(1), (
        "Operator channel must be gated to SUPER_ADMIN at the API boundary"
    )
    assert '"LEGAL_RULE_UPDATED"' in src, "operator changes must emit an activity-log event"


def test_verification_status_is_not_operator_mutable():
    """Counsel verification is a canonical-channel register change, not a PATCH field."""
    src = _src(SERVICE_PATH)
    node = _update_rule_node(src)
    params = {a.arg for a in node.args.args + node.args.kwonlyargs}
    forbidden = {"verification_status", "verified_by", "verified_at", "verification_notes"}
    leaked = sorted(forbidden & params)
    assert not leaked, (
        f"Operator update path must not accept {leaked}: verification status "
        "changes belong to the canonical migration channel"
    )
    # The snapshot records verification state for audit, but no operator field mutates it.
    assert '"verification_status"' in src, "snapshot should record verification state"


def test_provenance_workflow_never_mutates_rule_verification():
    src = _src(PROVENANCE_PATH)
    assert "without changing the statutory\nverification_status on legal_rules" in src, (
        "provenance workflow must document its non-mutation contract"
    )
    # Fail-closed responses: provenance operations report no verification change.
    assert '"legal_verification_status_changed": False' in src
    assert '"legal_verification_status": "UNCHANGED"' in src
