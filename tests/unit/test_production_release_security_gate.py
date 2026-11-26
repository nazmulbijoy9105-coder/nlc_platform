"""The controlled production release must run the security-closure gate first (audit F-12)."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "production-release.yml"
GATE_COMMAND = "python scripts/check_security_closure.py"


def _steps() -> list[dict]:
    workflow = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["release"]["steps"]


def test_security_closure_gate_runs_before_any_production_step():
    steps = _steps()
    gate_index = next(
        i for i, step in enumerate(steps) if step.get("run", "").strip() == GATE_COMMAND
    )

    assert any(step.get("uses", "").startswith("actions/checkout") for step in steps[:gate_index])
    names = [step.get("name", "") for step in steps]
    for production_step in (
        "Verify production branch, preserved backup and Render target",
        "Obtain direct migration, runtime, audit and backup connection URIs",
        "Apply and verify production migrations 0112 through 0127",
        "Deploy exact main SHA and verify Render deployment",
    ):
        assert gate_index < names.index(production_step), production_step


def test_security_closure_gate_failure_blocks_the_release():
    gate = next(step for step in _steps() if step.get("run", "").strip() == GATE_COMMAND)

    assert not gate.get("continue-on-error")
    assert "if" not in gate
