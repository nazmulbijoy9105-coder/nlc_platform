from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "Dockerfile"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-vercel-backend.yml"


def test_api_container_does_not_run_privileged_alembic_migrations():
    source = DOCKERFILE.read_text(encoding="utf-8")

    assert 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]' in source
    assert "alembic upgrade head" not in source


def test_production_migrations_run_before_render_deploy_hook():
    source = DEPLOY_WORKFLOW.read_text(encoding="utf-8")

    migration_step = source.index("Apply production migrations before Render deploy")
    deploy_step = source.index("Trigger Render Deploy Hook")
    assert migration_step < deploy_step
    assert "secrets.NLC_MIGRATION_DATABASE_URL" in source
    assert "MIGRATION_DATABASE_URL is not configured" in source
    assert "docker run --rm" in source
    assert "alembic upgrade head" in source


def test_missing_migration_secret_fails_before_any_render_deploy():
    source = DEPLOY_WORKFLOW.read_text(encoding="utf-8")

    guard = source.index("MIGRATION_DATABASE_URL is not configured")
    hook = source.index("Trigger Render Deploy Hook")
    assert guard < hook
    assert "No Render deployment will be triggered" in source
