"""Keep the restored-branch rehearsal pinned to the real Alembic head/schema."""

from __future__ import annotations

import ast
from pathlib import Path

from scripts.rehearse_restored_neon_branch import (
    EXPECTED_HEAD_REVISION,
    EXPECTED_START_REVISION,
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
