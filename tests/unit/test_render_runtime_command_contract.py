from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_render_web_service_starts_api_without_running_alembic():
    render_config = (ROOT / "render.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    deploy_workflow = (
        ROOT / ".github" / "workflows" / "deploy-vercel-backend.yml"
    ).read_text(encoding="utf-8")

    assert (
        'dockerCommand: sh -c \'exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"'
        ' --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"\'' in render_config
    )
    assert "ENV PORT=10000" in dockerfile
    assert "EXPOSE 10000" in dockerfile
    assert 'CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port' in dockerfile
    assert "--proxy-headers" in dockerfile
    for source in (dockerfile, render_config):
        assert ":-*" not in source
    assert "ENV FORWARDED_ALLOW_IPS=*" not in dockerfile
    assert 'ENV FORWARDED_ALLOW_IPS="*"' not in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "CMD curl -fsS" in dockerfile
    assert "alembic upgrade head" not in render_config
    assert "alembic upgrade head" not in dockerfile

    # Migrations are a separate CI-gated release operation.
    migration_step = deploy_workflow.index(
        "- name: Apply production migrations before Render deploy"
    )
    deploy_step = deploy_workflow.index("- name: Trigger Render Deploy Hook")
    assert migration_step < deploy_step
    assert "NLC_MIGRATION_DATABASE_URL" in deploy_workflow
