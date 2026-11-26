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
    _write_doc(repo, f"1. CLOSED: see {markup}")

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
    _write_doc(repo, f"1. CLOSED: see {markup}")
    (repo / "docs" / "evidence").mkdir()
    (repo / "docs" / "evidence" / "report.md").write_text("evidence", encoding="utf-8")

    assert closure.main() == 0


def test_url_decoded_link_destination_is_checked(repo):
    _write_doc(repo, "1. CLOSED: see [evidence](docs/evidence/my%20report.md)")
    (repo / "docs" / "evidence").mkdir()
    (repo / "docs" / "evidence" / "my report.md").write_text("evidence", encoding="utf-8")

    assert closure.main() == 0


def test_backticked_missing_evidence_still_fails(repo, capsys):
    _write_doc(repo, "1. CLOSED: see `docs/evidence/report.md`")

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
        "1. CLOSED: `docs/evidence/report.md` and [same](docs/evidence/report.md)",
    )

    assert closure.main() == 1
    out = capsys.readouterr().out
    assert out.count("missing evidence file: docs/evidence/report.md") == 1
