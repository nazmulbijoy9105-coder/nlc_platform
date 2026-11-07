"""Security/evidence migrations must never undo controls or erase provenance."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORWARD_ONLY_MIGRATIONS = (
    "alembic/versions/0037_add_webhook_tables.py",
    "alembic/versions/0038_add_rescue_audit_log.py",
    "alembic/versions/0044_webhook_schema_reconcile.py",
    "alembic/versions/0046_legal_evidence_provenance.py",
    "alembic/versions/0050_signed_rls_identity_hardening.py",
    "alembic/versions/0053_agm_minutes_unknown_default.py",
    "alembic/versions/0058_suppress_unreleased_rule_notifications.py",
    "alembic/versions/0059_finance_role_separation.py",
    "alembic/versions/0060_financial_billing_core.py",
)


def test_sensitive_migration_downgrades_are_noop_and_data_preserving():
    for relative_path in FORWARD_ONLY_MIGRATIONS:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative_path)
        downgrade = next(
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "downgrade"
        )
        statements = [
            node for node in downgrade.body
            if not (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            )
        ]
        assert len(statements) == 1, f"{relative_path} downgrade must remain a no-op"
        assert isinstance(statements[0], ast.Pass), (
            f"{relative_path} downgrade must not remove security controls "
            "or destroy legal evidence"
        )
