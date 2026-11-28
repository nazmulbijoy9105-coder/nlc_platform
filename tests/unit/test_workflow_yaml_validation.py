from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_workflow_yaml.py"
SPEC = importlib.util.spec_from_file_location("check_workflow_yaml", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "workflow.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_valid_workflow_with_jobs_mapping_passes(tmp_path: Path) -> None:
    path = _write(tmp_path, "name: CI\non:\n  pull_request:\njobs:\n  test:\n    runs-on: ubuntu-latest\n")
    assert MODULE.validate_workflow(path) == []


def test_duplicate_top_level_yaml_key_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, "name: CI\nname: Shadowed\njobs:\n  test: {}\n")
    errors = MODULE.validate_workflow(path)
    assert len(errors) == 1
    assert "duplicate key" in errors[0]


def test_duplicate_nested_yaml_key_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, "jobs:\n  test:\n    runs-on: ubuntu-latest\n    runs-on: windows-latest\n")
    errors = MODULE.validate_workflow(path)
    assert len(errors) == 1
    assert "duplicate key" in errors[0]


def test_non_mapping_jobs_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, "name: CI\njobs: []\n")
    assert "must be a mapping" in MODULE.validate_workflow(path)[0]


def test_empty_jobs_mapping_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, "name: CI\njobs: {}\n")
    assert "must not be empty" in MODULE.validate_workflow(path)[0]
