from pathlib import Path

import pytest

from scripts import check_security_closure as closure

SECTION = closure.SECTION_TITLE
# Keep a stable reference so direct audit tests bypass the main()-only fixture stub.
_AUDIT_CURRENT_DEPENDENCIES = closure.audit_current_dependencies


def _write_doc(root: Path, items: str) -> None:
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "SECURITY_RISK_ACCEPTANCE.md").write_text(
        f"# Doc\n\n{SECTION}\n\n{items}\n\n## Next section\n", encoding="utf-8"
    )


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(closure, "audit_current_dependencies", lambda: (True, "test audit passed"))
    # Most tests use one synthetic item; completeness tests restore 1..5.
    monkeypatch.setattr(closure, "EXPECTED_FINDING_NUMBERS", frozenset({1}))
    return tmp_path


@pytest.mark.parametrize(
    "markup",
    [
        "[evidence](docs/evidence/report.md)",
        "[evidence](docs/evidence/report.md#section)",
        '[evidence](docs/evidence/report.md "Report title")',
        "[evidence](<docs/evidence/report.md>)",
        "[evidence](evidence/report.md)",
        "[evidence](./evidence/report.md)",
        "[evidence](/docs/evidence/report.md)",
        "![evidence](docs/evidence/report.md)",
        "[evidence][ref]\n\n[ref]: docs/evidence/report.md",
        "[evidence](docs/evidence/my%20report.md)",
    ],
)
def test_missing_linked_evidence_fails_closed(repo, capsys, markup):
    _write_doc(repo, f"1. Item: see {markup}\n   Status: CLOSED")

    assert closure.main() == 1
    assert "FAIL: missing evidence file: docs/evidence/" in capsys.readouterr().out


@pytest.mark.parametrize(
    "markup",
    [
        "[evidence](docs/evidence/report.md)",
        "[evidence](evidence/report.md#anchor)",
        "[evidence](/docs/evidence/report.md)",
        "[evidence][ref]\n\n[ref]: docs/evidence/report.md",
    ],
)
def test_existing_linked_evidence_passes(repo, markup):
    _write_doc(repo, f"1. Item: see {markup}\n   Status: CLOSED")
    (repo / "docs" / "evidence").mkdir()
    (repo / "docs" / "evidence" / "report.md").write_text("evidence", encoding="utf-8")

    assert closure.main() == 0


def test_url_decoded_link_destination_is_checked(repo):
    _write_doc(repo, "1. Item: see [evidence](docs/evidence/my%20report.md)\n   Status: CLOSED")
    (repo / "docs" / "evidence").mkdir()
    (repo / "docs" / "evidence" / "my report.md").write_text("evidence", encoding="utf-8")

    assert closure.main() == 0


def test_backticked_missing_evidence_still_fails(repo, capsys):
    _write_doc(repo, "1. Item: see `docs/evidence/report.md`\n   Status: CLOSED")

    assert closure.main() == 1
    assert "missing evidence file: docs/evidence/report.md" in capsys.readouterr().out


@pytest.mark.parametrize(
    "destination",
    [
        "https://example.com/docs/report.md",
        "mailto:security@example.com",
        "//example.com/docs/report.md",
        "#closure-notes",
        "../README.md",
        "docs/../README.md",
    ],
)
def test_external_anchor_and_non_docs_destinations_are_ignored(destination):
    assert closure.link_evidence_path(destination) is None


def test_same_missing_file_is_reported_once(repo, capsys):
    _write_doc(
        repo,
        "1. Item: `docs/evidence/report.md` and [same](docs/evidence/report.md)\n   Status: CLOSED",
    )

    assert closure.main() == 1
    out = capsys.readouterr().out
    assert out.count("missing evidence file: docs/evidence/report.md") == 1


@pytest.mark.parametrize(
    "status_line",
    [
        "Status: CLOSED",
        "- Status: CLOSED",
        "**Status:** CLOSED",
        "**Status: CLOSED**",
        "Status: **CLOSED**",
        "  status:   CLOSED  ",
    ],
)
def test_explicit_closed_status_passes(repo, status_line):
    _write_doc(repo, f"1. Item\n   {status_line}")

    assert closure.main() == 0


@pytest.mark.parametrize(
    "status_lines",
    [
        "Status: NOT CLOSED",
        "Status: UNCLOSED",
        "Status: OPEN",
        "Status: closed",
        "Status: CLOSED pending review",
        "Status:",
        "Status: CLOSED\n   Status: OPEN",
        "Not closed yet.",
        "This was CLOSED in an earlier review but reopened.",
    ],
)
def test_item_without_exact_closed_status_fails_closed(repo, capsys, status_lines):
    _write_doc(repo, f"1. Item\n   {status_lines}")

    assert closure.main() == 1
    assert "FAIL:" in capsys.readouterr().out


def test_one_unresolved_item_fails_even_when_others_are_closed(repo, capsys):
    _write_doc(repo, "1. First\n   Status: CLOSED\n2. Second\n   Status: NOT CLOSED")

    assert closure.main() == 1
    out = capsys.readouterr().out
    assert "2. Second" in out
    assert "1. First" not in out


def test_reference_definition_outside_closure_section_is_resolved(repo, capsys):
    _write_doc(repo, "1. Item: see [evidence][report]\n   Status: CLOSED")
    document = repo / "docs" / "SECURITY_RISK_ACCEPTANCE.md"
    document.write_text(
        document.read_text(encoding="utf-8")
        + "\n[report]: docs/evidence/report.md\n",
        encoding="utf-8",
    )

    assert closure.main() == 1
    assert "missing evidence file: docs/evidence/report.md" in capsys.readouterr().out


def test_collapsed_reference_link_definition_outside_section_passes(repo):
    _write_doc(repo, "1. Item: see [report][]\n   Status: CLOSED")
    evidence = repo / "docs" / "evidence"
    evidence.mkdir()
    (evidence / "report.md").write_text("evidence", encoding="utf-8")
    document = repo / "docs" / "SECURITY_RISK_ACCEPTANCE.md"
    document.write_text(
        document.read_text(encoding="utf-8")
        + "\n[report]: docs/evidence/report.md\n",
        encoding="utf-8",
    )

    assert closure.main() == 0



def test_live_dependency_audit_writes_fresh_report_and_passes(repo, monkeypatch):
    import json
    from types import SimpleNamespace

    requirements = repo / "requirements.txt"
    requirements.write_text("example==1.0", encoding="utf-8")
    report_path = repo / "artifacts" / "security" / "pip-audit-current.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("stale report", encoding="utf-8")
    report = {"dependencies": [{"name": "example", "version": "1.0", "vulns": []}], "fixes": []}
    monkeypatch.setattr(closure, "REQUIREMENTS_PATH", requirements)
    monkeypatch.setattr(closure, "CURRENT_AUDIT_REPORT", report_path)
    monkeypatch.setattr(
        closure.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(report), stderr=""),
    )

    ok, message = _AUDIT_CURRENT_DEPENDENCIES()

    assert ok is True
    assert "packages=1" in message
    assert json.loads(report_path.read_text(encoding="utf-8")) == report


def test_live_dependency_audit_fails_on_vulnerability(repo, monkeypatch):
    import json
    from types import SimpleNamespace

    requirements = repo / "requirements.txt"
    requirements.write_text("example==1.0", encoding="utf-8")
    report_path = repo / "artifacts" / "security" / "pip-audit-current.json"
    report = {
        "dependencies": [
            {"name": "example", "version": "1.0", "vulns": [{"id": "PYSEC-TEST"}]}
        ],
        "fixes": [],
    }
    monkeypatch.setattr(closure, "REQUIREMENTS_PATH", requirements)
    monkeypatch.setattr(closure, "CURRENT_AUDIT_REPORT", report_path)
    monkeypatch.setattr(
        closure.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=json.dumps(report), stderr=""),
    )

    ok, message = _AUDIT_CURRENT_DEPENDENCIES()

    assert ok is False
    assert "vulnerabilities=1" in message
    assert report_path.is_file()


def test_live_dependency_audit_fails_on_invalid_json(repo, monkeypatch):
    from types import SimpleNamespace

    requirements = repo / "requirements.txt"
    requirements.write_text("example==1.0", encoding="utf-8")
    monkeypatch.setattr(closure, "REQUIREMENTS_PATH", requirements)
    monkeypatch.setattr(
        closure.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="not-json", stderr=""),
    )

    ok, message = _AUDIT_CURRENT_DEPENDENCIES()

    assert ok is False
    assert "valid JSON" in message


def test_live_dependency_audit_fails_when_requirements_are_missing(repo, monkeypatch):
    monkeypatch.setattr(closure, "REQUIREMENTS_PATH", repo / "missing-requirements.txt")

    ok, message = _AUDIT_CURRENT_DEPENDENCIES()

    assert ok is False
    assert "requirements file is missing" in message


def test_duplicate_closure_item_fails_closed(repo, capsys):
    # Regression guard for PR #432: a superseded block left in place made the
    # gate see two item-1 blocks. The fail-closed gate must reject duplicates.
    _write_doc(
        repo,
        "1. First\n   Status: CLOSED\n1. Duplicate first\n   Status: CLOSED",
    )

    assert closure.main([]) == 1
    assert "duplicate closure item 1" in capsys.readouterr().out


def test_structure_only_passes_with_an_open_item(repo, monkeypatch, capsys):
    monkeypatch.setattr(closure, "EXPECTED_FINDING_NUMBERS", frozenset({1, 2}))
    # The PR-level structural job must not force every item CLOSED; an OPEN
    # item is reported as info, not a failure (the production gate still blocks).
    _write_doc(repo, "1. Closed\n   Status: CLOSED\n2. Pending\n   Status: OPEN")

    assert closure.main(["--structure-only"]) == 0
    out = capsys.readouterr().out
    assert "OPEN: 2. Pending" in out
    assert "1 OPEN item(s)" in out


def test_structure_only_fails_on_duplicate_item(repo, capsys):
    _write_doc(
        repo,
        "1. First\n   Status: CLOSED\n1. Duplicate\n   Status: CLOSED",
    )

    assert closure.main(["--structure-only"]) == 1
    assert "duplicate closure item 1" in capsys.readouterr().out


def test_structure_only_fails_on_missing_status(repo, capsys):
    _write_doc(repo, "1. Item with no status line\n   some prose only")

    assert closure.main(["--structure-only"]) == 1
    assert "exactly one Status: OPEN or Status: CLOSED" in capsys.readouterr().out


def test_structure_only_fails_on_missing_evidence(repo, capsys):
    _write_doc(repo, "1. Item: see `docs/evidence/report.md`\n   Status: CLOSED")

    assert closure.main(["--structure-only"]) == 1
    assert "missing evidence file: docs/evidence/report.md" in capsys.readouterr().out


def test_structure_only_does_not_run_live_audit(tmp_path, monkeypatch):
    # The structural job must not depend on pip-audit or requirements.txt.
    monkeypatch.chdir(tmp_path)
    _write_doc(tmp_path, "1. Closed\n   Status: CLOSED")

    calls = {"count": 0}

    def boom() -> tuple[bool, str]:
        calls["count"] += 1
        return False, "audit must not run in structure-only mode"

    monkeypatch.setattr(closure, "audit_current_dependencies", boom)

    assert closure.main(["--structure-only"]) == 0
    assert calls["count"] == 0


def test_leading_zero_duplicate_numbers_are_normalized(repo, capsys):
    _write_doc(repo, "1. First\n   Status: CLOSED\n01. Duplicate with leading zero\n   Status: CLOSED")

    assert closure.main(["--structure-only"]) == 1
    assert "duplicate closure item 1" in capsys.readouterr().out


def test_indented_markdown_item_is_split_and_duplicate_detected(repo, capsys):
    _write_doc(repo, "1. First\n   Status: CLOSED\n   1. Indented duplicate\n   Status: CLOSED")

    assert closure.main(["--structure-only"]) == 1
    assert "duplicate closure item 1" in capsys.readouterr().out


def test_required_findings_cannot_be_removed(repo, monkeypatch, capsys):
    monkeypatch.setattr(closure, "EXPECTED_FINDING_NUMBERS", frozenset({1, 2, 3, 4, 5}))
    _write_doc(
        repo,
        "1. First\n   Status: CLOSED\n2. Second\n   Status: CLOSED\n"
        "3. Third\n   Status: CLOSED\n5. Fifth\n   Status: CLOSED",
    )

    assert closure.main(["--structure-only"]) == 1
    assert "missing required closure item(s): 4" in capsys.readouterr().out


@pytest.mark.parametrize(
    "status_lines",
    [
        "Status:",
        "Status: PENDING",
        "Status: CLOSED\n   Status: OPEN",
        "Status: closed",
        "Status: OPEN pending",
    ],
)
def test_structure_only_rejects_malformed_or_conflicting_statuses(repo, capsys, status_lines):
    _write_doc(repo, f"1. Item\n   {status_lines}")

    assert closure.main(["--structure-only"]) == 1
    assert "exactly one Status: OPEN or Status: CLOSED" in capsys.readouterr().out
