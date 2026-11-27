from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
GATE_COMMAND = "python scripts/check_security_closure.py"


def _workflow_steps(path: str, job_name: str) -> list[dict]:
    workflow = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    return workflow["jobs"][job_name]["steps"]


def _gate_index(steps: list[dict]) -> int:
    matches = [
        index
        for index, step in enumerate(steps)
        if step.get("run", "").strip() == GATE_COMMAND
    ]
    assert len(matches) == 1, f"expected exactly one security gate, found {len(matches)}"
    return matches[0]


def test_controlled_production_release_checks_security_closure_before_operations():
    steps = _workflow_steps(".github/workflows/production-release.yml", "release")
    gate_index = _gate_index(steps)

    assert any(
        step.get("uses", "").startswith("actions/checkout")
        for step in steps[:gate_index]
    )
    names = [step.get("name", "") for step in steps]
    for production_step in (
        "Verify production branch, preserved backup and Render target",
        "Obtain direct migration, runtime, audit and backup connection URIs",
        "Apply and verify production migrations 0112 through 0128",
        "Deploy exact main SHA and verify Render deployment",
    ):
        assert gate_index < names.index(production_step), production_step

    gate = steps[gate_index]
    assert not gate.get("continue-on-error")
    assert "if" not in gate
    assert any(
        step.get("name") == "Install pinned pip-audit release-gate tool"
        and index < gate_index
        for index, step in enumerate(steps)
    )
    assert any(
        step.get("uses") == "actions/upload-artifact@v4"
        and step.get("with", {}).get("path") == "artifacts/security/pip-audit-current.json"
        and index > gate_index
        for index, step in enumerate(steps)
    )


def test_ci_triggered_render_deploy_checks_security_closure_before_migrations():
    steps = _workflow_steps(".github/workflows/deploy-vercel-backend.yml", "deploy-render")
    gate_index = _gate_index(steps)
    names = [step.get("name", "") for step in steps]

    assert gate_index < names.index("Apply production migrations before Render deploy")
    gate = steps[gate_index]
    assert gate.get("if") == "steps.freshness.outputs.current == 'true'"
    assert not gate.get("continue-on-error")
    assert any(
        step.get("name") == "Install pinned pip-audit release-gate tool"
        and index < gate_index
        and step.get("if") == "steps.freshness.outputs.current == 'true'"
        for index, step in enumerate(steps)
    )
    assert any(
        step.get("uses") == "actions/upload-artifact@v4"
        and step.get("with", {}).get("path") == "artifacts/security/pip-audit-current.json"
        and index > gate_index
        for index, step in enumerate(steps)
    )
