from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _assert_gate_before(workflow: str, production_step: str) -> None:
    gate = "python scripts/check_security_closure.py"
    assert gate in workflow
    assert workflow.index(gate) < workflow.index(production_step)
    gate_block = workflow[workflow.rfind("- name:", 0, workflow.index(gate)):workflow.index(gate)]
    assert "continue-on-error: true" not in gate_block


def test_controlled_production_release_checks_security_closure_before_operations():
    workflow = (ROOT / ".github/workflows/production-release.yml").read_text(
        encoding="utf-8"
    )
    _assert_gate_before(workflow, "Obtain direct migration")


def test_ci_triggered_render_deploy_checks_security_closure_before_migrations():
    workflow = (ROOT / ".github/workflows/deploy-vercel-backend.yml").read_text(
        encoding="utf-8"
    )
    _assert_gate_before(workflow, "Apply production migrations")
