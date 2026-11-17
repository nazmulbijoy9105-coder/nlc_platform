from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_render_web_service_starts_api_without_running_alembic():
    render_config = (ROOT / "render.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    deploy_workflow = (
        ROOT / ".github" / "workflows" / "deploy-vercel-backend.yml"
    ).read_text(encoding="utf-8")

    expected_api_command = (
        "uvicorn app.main:app --host 0.0.0.0 --port 8000"
    )
    assert f"dockerCommand: {expected_api_command}" in render_config
    assert f'CMD ["{expected_api_command.split()[0]}"' in dockerfile
    assert "alembic upgrade head" not in render_config
    assert "alembic upgrade head" not in dockerfile

    # Database migrations are a separate CI-gated release operation. The
    # Render deploy hook must remain after the successful migration step.
    migration_step = deploy_workflow.index(
        "- name: Apply production migrations before Render deploy"
    )
    deploy_step = deploy_workflow.index("- name: Trigger Render Deploy Hook")
    assert migration_step < deploy_step
    assert "NLC_MIGRATION_DATABASE_URL" in deploy_workflow
