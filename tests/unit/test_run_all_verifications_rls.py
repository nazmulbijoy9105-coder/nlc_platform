"""Regression tests for RLS verifier invocation and report aggregation."""

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

DATABASE_URL = "postgresql://u:secret@db.example/nlc"


def _record_report(monkeypatch, report):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        output = Path(args[args.index("--output") + 1])
        output.write_text(json.dumps(report), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(run_all_verifications.subprocess, "run", fake_run)
    return calls


def test_run_script_normalizes_rls_report_and_passes_database_url(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    report = {
        "results": [
            {
                "check_id": "RLS_PASS",
                "table": "public.passed",
                "status": "PASS",
                "detail": "Policy exists",
                "evidence": "not included",
            },
            {
                "check_id": "RLS_FAIL",
                "table": "public.failed",
                "status": "FAIL",
                "detail": "Policy missing",
                "evidence": "No policies found",
            },
            {
                "check_id": "RLS_WARN",
                "table": "public.warned",
                "status": "WARN",
                "detail": "Review policy",
                "evidence": "",
            },
            {
                "check_id": "RLS_SKIP",
                "table": "public.skipped",
                "status": "SKIP",
                "detail": "Table unavailable",
            },
        ]
    }
    calls = _record_report(monkeypatch, report)

    result = run_all_verifications.run_script(
        SCRIPT.parent / "verify_rls.py", repo, out, DATABASE_URL
    )

    assert result["ok"] is True
    assert result["report"]["results"] == report["results"]
    assert result["report"]["findings"] == [
        {
            "check_id": "RLS_FAIL",
            "file": "db:public.failed",
            "line": 0,
            "severity": "FAIL",
            "detail": "Policy missing",
            "evidence": "No policies found",
        },
        {
            "check_id": "RLS_WARN",
            "file": "db:public.warned",
            "line": 0,
            "severity": "WARN",
            "detail": "Review policy",
        },
        {
            "check_id": "RLS_SKIP",
            "file": "db:public.skipped",
            "line": 0,
            "severity": "INFO",
            "detail": "Table unavailable",
        },
    ]
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert str(repo.resolve()) not in args
    assert all("secret" not in arg for arg in args)
    assert kwargs["env"]["APP_DATABASE_URL"] == DATABASE_URL
    assert args[-2:] == ["--output", str(out / "verify_rls_report.json")]


def test_run_script_rls_inherits_environment_without_database_url(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    calls = _record_report(monkeypatch, {"results": []})

    result = run_all_verifications.run_script(SCRIPT.parent / "verify_rls.py", repo, out)

    assert result["ok"] is True
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert str(repo.resolve()) not in args
    assert kwargs["env"] is None


def test_run_script_other_verifier_keeps_repo_argument_and_report(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    report = {"findings": [{"check_id": "TENANT", "severity": "WARN"}]}
    calls = _record_report(monkeypatch, report)

    result = run_all_verifications.run_script(
        SCRIPT.parent / "verify_tenant_isolation.py", repo, out, DATABASE_URL
    )

    assert result["ok"] is True
    assert result["report"] == report
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert str(repo.resolve()) in args
    assert kwargs["env"] is None


@pytest.mark.parametrize(
    "report",
    [
        [],
        {},
        {"results": "x"},
        {"results": [{"status": "BOGUS"}]},
        {"results": [{"status": []}]},
        {"results": [{"status": {}}]},
    ],
)
def test_run_script_rejects_malformed_rls_report(tmp_path, monkeypatch, report):
    out = tmp_path / "out"
    out.mkdir()
    calls = _record_report(monkeypatch, report)

    result = run_all_verifications.run_script(SCRIPT.parent / "verify_rls.py", tmp_path, out)

    assert len(calls) == 1
    assert result["ok"] is False
    assert "normalize" in result["stderr"]


def test_main_aggregates_rls_failure_and_limits_database_environment(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if Path(args[1]).name == "verify_rls.py":
            report = {
                "results": [
                    {
                        "check_id": "RLS_MAIN_FAIL",
                        "table": "public.failed",
                        "status": "FAIL",
                        "detail": "Policy missing",
                    }
                ]
            }
        else:
            report = {"findings": []}
        output = Path(args[args.index("--output") + 1])
        output.write_text(json.dumps(report), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(run_all_verifications.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all_verifications.py",
            str(repo),
            "--output-dir",
            str(out),
            "--database-url",
            DATABASE_URL,
        ],
    )

    assert run_all_verifications.main() == 1

    assert {Path(args[1]).name for args, _ in calls} == set(run_all_verifications.SCRIPTS)
    for args, kwargs in calls:
        if Path(args[1]).name == "verify_rls.py":
            assert kwargs["env"]["APP_DATABASE_URL"] == DATABASE_URL
        else:
            assert kwargs["env"] is None
    consolidated = json.loads((out / "all_findings.json").read_text(encoding="utf-8"))
    assert consolidated["fail_count"] == 1
    assert any(
        finding["_source_script"] == "verify_rls.py" and finding["check_id"] == "RLS_MAIN_FAIL"
        for finding in consolidated["findings"]
    )


def test_main_fails_closed_when_rls_verifier_returns_non_string_status(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if Path(args[1]).name == "verify_rls.py":
            report = {"results": [{"check_id": "RLS_BAD_STATUS", "status": []}]}
        else:
            report = {"findings": []}
        output = Path(args[args.index("--output") + 1])
        output.write_text(json.dumps(report), encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(run_all_verifications.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_all_verifications.py",
            str(repo),
            "--output-dir",
            str(out),
            "--database-url",
            DATABASE_URL,
        ],
    )

    assert run_all_verifications.main() == 1

    consolidated = json.loads((out / "all_findings.json").read_text(encoding="utf-8"))
    failures = [
        finding
        for finding in consolidated["findings"]
        if finding["_source_script"] == "verify_rls.py"
    ]
    assert len(failures) == 1
    assert failures[0]["check_id"] == "VERIFIER_EXECUTION"
    assert failures[0]["severity"] == "FAIL"
    assert "unexpected result status" in failures[0]["detail"]

