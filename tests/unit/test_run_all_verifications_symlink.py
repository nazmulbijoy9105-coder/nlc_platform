"""Regression tests for refusing symlinked verification report paths."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "run_all_verifications.py"
SPEC = importlib.util.spec_from_file_location("run_all_verifications", SCRIPT)
run_all_verifications = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_all_verifications)


def _unexpected_subprocess(*args, **kwargs):
    pytest.fail("A child process must not be launched for a symlinked report path")


def test_run_script_rejects_symlinked_report(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    victim = tmp_path / "victim.txt"
    victim.write_text("original", encoding="utf-8")
    (out / "verify_rls_report.json").symlink_to(victim)
    monkeypatch.setattr(run_all_verifications.subprocess, "run", _unexpected_subprocess)
    script = Path(run_all_verifications.__file__).parent / "verify_rls.py"

    result = run_all_verifications.run_script(script, tmp_path, out)

    assert result["ok"] is False
    assert "symlink" in result["stderr"].lower()
    assert victim.read_text(encoding="utf-8") == "original"


def test_run_script_rejects_dangling_report_symlink(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    target = tmp_path / "missing.txt"
    (out / "verify_rls_report.json").symlink_to(target)
    monkeypatch.setattr(run_all_verifications.subprocess, "run", _unexpected_subprocess)
    script = Path(run_all_verifications.__file__).parent / "verify_rls.py"

    result = run_all_verifications.run_script(script, tmp_path, out)

    assert result["ok"] is False
    assert "symlink" in result["stderr"].lower()
    assert not target.exists()


@pytest.mark.parametrize("report_name", ["all_findings.json", "all_findings_summary.txt"])
def test_main_rejects_symlinked_consolidated_report(tmp_path, monkeypatch, capsys, report_name):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    victim = tmp_path / "victim.txt"
    victim.write_text("original", encoding="utf-8")
    (out / report_name).symlink_to(victim)
    monkeypatch.setattr(
        sys, "argv", ["run_all_verifications.py", str(repo), "--output-dir", str(out)]
    )
    monkeypatch.setattr(run_all_verifications.subprocess, "run", _unexpected_subprocess)

    assert run_all_verifications.main() == 2

    assert "symlink" in capsys.readouterr().err.lower()
    assert victim.read_text(encoding="utf-8") == "original"


def test_run_script_writes_regular_report(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    script = Path(run_all_verifications.__file__).parent / "verify_tenant_isolation.py"

    def fake_run(args, **kwargs):
        output = Path(args[args.index("--output") + 1])
        output.write_text('{"findings": []}', encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(run_all_verifications.subprocess, "run", fake_run)

    result = run_all_verifications.run_script(script, tmp_path, out)

    assert result["ok"] is True
    assert result["report"] == {"findings": []}


def test_run_script_records_invalid_subprocess_text_as_failure(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    script = Path(run_all_verifications.__file__).parent / "verify_rls.py"

    def invalid_text_run(*args, **kwargs):
        raise UnicodeDecodeError("utf-8", bytes([255]), 0, 1, "invalid start byte")

    monkeypatch.setattr(run_all_verifications.subprocess, "run", invalid_text_run)

    result = run_all_verifications.run_script(script, tmp_path, out)

    assert result["ok"] is False
    assert "decode" in result["stderr"].lower()


def test_run_script_records_invalid_report_utf8_as_failure(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    script = Path(run_all_verifications.__file__).parent / "verify_rls.py"

    def invalid_report_run(args, **kwargs):
        output = Path(args[args.index("--output") + 1])
        output.write_bytes(b'{"findings": ["' + bytes([255]) + b'"]}')
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(run_all_verifications.subprocess, "run", invalid_report_run)

    result = run_all_verifications.run_script(script, tmp_path, out)

    assert result["ok"] is False
    assert "could not parse output json" in result["stderr"].lower()
    assert "utf-8" in result["stderr"].lower()


def test_normalize_rls_report_rejects_non_string_status():
    with pytest.raises(ValueError, match="unexpected result status"):
        run_all_verifications.normalize_rls_report({
            "results": [{"status": [], "check_id": "RLS-TEST"}]
        })


def test_failed_verifier_is_a_consolidated_failure_and_nonzero_exit(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(
        run_all_verifications,
        "SCRIPTS",
        ["verify_rls.py"],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_all_verifications.py", str(repo), "--output-dir", str(out)],
    )
    monkeypatch.setattr(
        run_all_verifications,
        "run_script",
        lambda *args, **kwargs: {
            "script": "verify_rls.py",
            "ok": False,
            "stderr": "malformed RLS report",
            "stdout_tail": "",
        },
    )

    assert run_all_verifications.main() == 1

    report = json.loads((out / "all_findings.json").read_text(encoding="utf-8"))
    assert report["fail_count"] == 1
    assert report["findings"][0]["check_id"] == "VERIFIER_EXECUTION"
    assert report["findings"][0]["severity"] == "FAIL"
    assert report["findings"][0]["detail"] == "malformed RLS report"
