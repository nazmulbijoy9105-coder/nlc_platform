from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


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
    assert "UPDATE rescue_plans SET initial_score = 0 WHERE initial_score IS NULL" in migration


def test_rescue_plan_model_declares_the_retained_workflow_mode_server_default():
    from app.models.rescue import RescuePlan

    assert RescuePlan.__table__.c.workflow_mode.server_default.arg == "STATUTORY_ACTION_AUTHORIZED"
    assert RescuePlan.__table__.c.workflow_mode.nullable is False
