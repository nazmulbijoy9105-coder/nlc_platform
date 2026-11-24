import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY

import pytest
import sqlalchemy as sa

ROOT = Path(__file__).resolve().parents[2]


def _load_migration_with_fake_op(monkeypatch, scoreless_plans):
    spec = importlib.util.spec_from_file_location(
        "migration_0126",
        ROOT / "alembic" / "versions" / "0126_score_independent_rescue_workflow.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    bind = SimpleNamespace(
        execute=lambda statement: SimpleNamespace(scalar_one=lambda: scoreless_plans)
    )
    fake_op = SimpleNamespace(
        get_bind=lambda: bind,
        drop_column=lambda *args, **kwargs: calls.append(("drop_column", args, kwargs)),
        alter_column=lambda *args, **kwargs: calls.append(("alter_column", args, kwargs)),
        execute=lambda *args, **kwargs: calls.append(("execute", args, kwargs)),
    )
    monkeypatch.setattr(module, "op", fake_op)
    return module, calls


def test_score_independent_rescue_migration_makes_score_nullable_and_adds_authorization_mode():
    migration = (
        ROOT
        / "alembic"
        / "versions"
        / "0126_score_independent_rescue_workflow.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "0126_score_independent_rescue_workflow"' in migration
    assert 'down_revision = "0125_reconcile_agm001_statutory_basis"' in migration
    assert 'op.alter_column("rescue_plans", "initial_score"' in migration
    assert "nullable=True" in migration
    assert '"workflow_mode"' in migration
    assert 'server_default="STATUTORY_ACTION_AUTHORIZED"' in migration
    assert "server_default=None" not in migration
    assert "def downgrade() -> None:" in migration
    assert "SET initial_score = 0" not in migration


def test_workflow_mode_comment_matches_model_and_names_the_persisted_mode():
    from app.models.rescue import RescuePlan

    migration = ast.parse(
        (
            ROOT
            / "alembic"
            / "versions"
            / "0126_score_independent_rescue_workflow.py"
        ).read_text(encoding="utf-8")
    )
    upgrade = next(
        node for node in migration.body
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
    )
    column = next(
        node for node in ast.walk(upgrade)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Attribute) and node.func.attr == "Column")
            or (isinstance(node.func, ast.Name) and node.func.id == "Column")
        )
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "workflow_mode"
    )
    comment = next(keyword.value for keyword in column.keywords if keyword.arg == "comment")
    assert isinstance(comment, ast.Constant)
    workflow_mode = RescuePlan.__table__.c.workflow_mode
    assert workflow_mode.comment == comment.value
    assert workflow_mode.server_default.arg in comment.value
    assert "REVIEW_ONLY" not in comment.value


def test_downgrade_refuses_when_scoreless_rescue_plans_exist(monkeypatch):
    migration, calls = _load_migration_with_fake_op(monkeypatch, scoreless_plans=2)

    with pytest.raises(RuntimeError, match="0126 refuses to downgrade"):
        migration.downgrade()

    assert calls == []


def test_downgrade_restores_not_null_score_without_fabricating_values(monkeypatch):
    migration, calls = _load_migration_with_fake_op(monkeypatch, scoreless_plans=0)

    migration.downgrade()

    assert calls == [
        ("drop_column", ("rescue_plans", "workflow_mode"), {}),
        (
            "alter_column",
            ("rescue_plans", "initial_score"),
            {"existing_type": ANY, "nullable": False},
        ),
    ]
    assert isinstance(calls[1][2]["existing_type"], sa.Integer)


def test_rescue_plan_model_declares_the_retained_workflow_mode_server_default():
    from app.models.rescue import RescuePlan

    assert RescuePlan.__table__.c.workflow_mode.server_default.arg == "STATUTORY_ACTION_AUTHORIZED"
    assert RescuePlan.__table__.c.workflow_mode.nullable is False
