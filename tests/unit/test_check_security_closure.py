from pathlib import Path

import pytest

from scripts import check_security_closure as closure

SECTION = closure.SECTION_TITLE


def _write_doc(root: Path, items: str) -> None:
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "SECURITY_RISK_ACCEPTANCE.md").write_text(
        f"# Doc\n\n{SECTION}\n\n{items}\n\n## Next section\n", encoding="utf-8"
    )


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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
    assert "FAIL: item not CLOSED" in capsys.readouterr().out


def test_one_unresolved_item_fails_even_when_others_are_closed(repo, capsys):
    _write_doc(repo, "1. First\n   Status: CLOSED\n2. Second\n   Status: NOT CLOSED")

    assert closure.main() == 1
    out = capsys.readouterr().out
    assert "2. Second" in out
    assert "1. First" not in out


def test_reference_definition_outside_closure_section_is_resolved(repo, capsys):
    _write_doc(repo, "1. Item: see [evidence][report]\\n   Status: CLOSED")
    document = repo / "docs" / "SECURITY_RISK_ACCEPTANCE.md"
    document.write_text(
        document.read_text(encoding="utf-8")
        + "\\n[report]: docs/evidence/report.md\\n",
        encoding="utf-8",
    )

    assert closure.main() == 1
    assert "missing evidence file: docs/evidence/report.md" in capsys.readouterr().out


def test_collapsed_reference_link_definition_outside_section_passes(repo):
    _write_doc(repo, "1. Item: see [report][]\\n   Status: CLOSED")
    evidence = repo / "docs" / "evidence"
    evidence.mkdir()
    (evidence / "report.md").write_text("evidence", encoding="utf-8")
    document = repo / "docs" / "SECURITY_RISK_ACCEPTANCE.md"
    document.write_text(
        document.read_text(encoding="utf-8")
        + "\\n[report]: docs/evidence/report.md\\n",
        encoding="utf-8",
    )

    assert closure.main() == 0
