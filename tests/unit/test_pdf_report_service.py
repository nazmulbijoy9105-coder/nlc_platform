"""Unit tests for the compliance report PDF service (no database required)."""
import asyncio
import re
import zlib
from datetime import datetime
from enum import Enum
from types import SimpleNamespace

import pytest
from fastapi import Response

from app.services import pdf_render
from app.services import pdf_report_service as report_module
from app.services.pdf_report_service import (
    LOGO_FILE,
    PDFReportService,
    build_compliance_report_html,
)


class Severity(Enum):
    RED = "RED"


MALICIOUS_NAME = (
    '<img src="file:///etc/hostname">'
    '<link rel="attachment" href="file:///etc/passwd">Acme & Sons "Ltd"'
)
COMPANY = SimpleNamespace(
    company_name=MALICIOUS_NAME,
    registration_number="C-1\r\nX-Evil: 1/2020",
    current_compliance_score=62,
    current_risk_band="AMBER",
)
FLAGS = [
    SimpleNamespace(
        rule_id="AGM-001",
        severity=Severity.RED,
        description="<script>alert(1)</script> AGM overdue",
        score_impact=15,
    )
]
WHEN = datetime(2026, 10, 20, 1, 0)


def _require_weasyprint():
    try:
        import weasyprint  # noqa: F401
    except Exception as exc:  # OSError when Pango/Cairo are missing
        pytest.skip(f"WeasyPrint not usable here: {exc}")


def _require_logo():
    if pdf_render.asset_uri(LOGO_FILE) is None:
        pytest.skip(f"app/static/brand/{LOGO_FILE} is not present")


def _pdf_contains(pdf: bytes, marker: bytes) -> bool:
    """True if marker appears in the raw PDF or in any zlib-compressed stream."""
    if marker in pdf:
        return True
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S):
        try:
            if marker in zlib.decompress(match.group(1)):
                return True
        except zlib.error:
            continue
    return False


def _patch_services(monkeypatch, company=COMPANY, flags=FLAGS):
    class FakeCompanyService:
        def __init__(self, db):
            pass

        async def get_by_id_or_404(self, company_id):
            return company

    class FakeComplianceService:
        def __init__(self, db):
            pass

        async def get_active_flags(self, company_id):
            return flags

    monkeypatch.setattr(report_module, "CompanyService", FakeCompanyService)
    monkeypatch.setattr(report_module, "ComplianceService", FakeComplianceService)


# --------------------------------------------------------------------------- endpoint


def test_endpoint_returns_pdf_response_with_safe_headers_and_escaped_html(monkeypatch):
    _patch_services(monkeypatch)
    captured = {}

    async def fake_render(html_content):
        captured["html"] = html_content
        return b"%PDF-1.7 stub"

    monkeypatch.setattr(report_module, "render_html_to_pdf_async", fake_render)

    # Mock the COM-007 snapshot lookup: this test does not need a real database.
    snapshot = SimpleNamespace(
        score_hash="test-snapshot-hash",
        engine_version="test-engine-v1",
    )

    class FakeDB:
        async def execute(self, statement):
            return SimpleNamespace(scalar_one_or_none=lambda: snapshot)

    response = asyncio.run(
        PDFReportService(db=FakeDB()).generate_company_compliance_pdf("any-id")
    )

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.media_type == "application/pdf"
    assert response.body == b"%PDF-1.7 stub"
    assert response.headers["x-snapshot-hash"] == "test-snapshot-hash"
    assert response.headers["x-engine-version"] == "test-engine-v1"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="compliance_report_C-1_X-Evil_1_2020.pdf"'
    )

    page = captured["html"]
    assert 'src="file:///etc/hostname"' not in page  # injected <img> was escaped
    assert "<link" not in page
    assert "<script" not in page
    assert "&lt;img" in page
    assert "Acme &amp; Sons &quot;Ltd&quot;" in page
    assert "AGM-001" in page and "RED" in page and "-15 pts" in page


# --------------------------------------------------------------------------- HTML builder


def test_html_builder_handles_empty_flags_and_missing_values():
    company = SimpleNamespace(
        company_name="Acme",
        registration_number=None,
        current_compliance_score=None,
        current_risk_band=None,
    )
    page = build_compliance_report_html(company, [], WHEN)
    assert "No active compliance flags." in page
    assert "0 / 100" in page
    assert "NOT_EVALUATED" in page
    assert "20 October 2026" in page
    assert "score-bad" in page
    assert "<img" not in page  # no logo_uri given -> no logo markup


def test_html_builder_includes_logo_only_when_given():
    page = build_compliance_report_html(COMPANY, FLAGS, WHEN, logo_uri="file:///x/logo.png")
    assert '<img class="logo" src="file:///x/logo.png"' in page


def test_asset_uri_rejects_missing_and_traversal():
    assert pdf_render.asset_uri("does-not-exist.png") is None
    assert pdf_render.asset_uri("../services/pdf_render.py") is None


# --------------------------------------------------------------------------- fetcher


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "file:///proc/self/environ",
        f"{pdf_render.ASSET_DIR.as_uri()}/../../../etc/passwd",
        f"{pdf_render.ASSET_DIR.as_uri()}/sub/x.png",
        "file://evil-host/share/logo.png",
        "http://169.254.169.254/latest/meta-data/",
        "https://example.com/logo.png",
        "data:text/plain,hi",
    ],
)
def test_safe_fetcher_refuses_everything_outside_brand_dir(url):
    _require_weasyprint()
    fetcher = pdf_render.make_safe_fetcher()
    with pytest.raises(ValueError):
        fetcher(url)


def test_safe_fetcher_serves_the_logo():
    _require_weasyprint()
    _require_logo()
    fetcher = pdf_render.make_safe_fetcher()
    response = fetcher(pdf_render.asset_uri(LOGO_FILE))
    try:
        assert response.read(8) == b"\x89PNG\r\n\x1a\n"
    finally:
        response.close()


def test_renderer_uses_the_safe_fetcher(monkeypatch):
    _require_weasyprint()
    import weasyprint

    seen = {}

    class FakeHTML:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def write_pdf(self):
            return b"%PDF-fake"

    monkeypatch.setattr(weasyprint, "HTML", FakeHTML)

    assert pdf_render.render_html_to_pdf("<p>x</p>") == b"%PDF-fake"
    assert seen["string"] == "<p>x</p>"
    with pytest.raises(ValueError):
        seen["url_fetcher"]("file:///etc/passwd")


# --------------------------------------------------------------------------- real renders


def test_real_render_does_not_embed_local_files(tmp_path):
    _require_weasyprint()
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET-MARKER-12345")
    uri = secret.as_uri()
    html_doc = (
        f'<html><body><p>hello</p><img src="{uri}">'
        f'<link rel="attachment" href="{uri}"></body></html>'
    )

    pdf = pdf_render.render_html_to_pdf(html_doc)

    assert pdf.startswith(b"%PDF")
    assert b"EmbeddedFile" not in pdf
    assert not _pdf_contains(pdf, b"TOP-SECRET-MARKER-12345")
    assert b"/Subtype /Image" not in pdf


def test_real_render_of_branded_report_includes_the_logo():
    _require_weasyprint()
    _require_logo()
    page = build_compliance_report_html(
        COMPANY, FLAGS, WHEN, logo_uri=pdf_render.asset_uri(LOGO_FILE)
    )
    pdf = pdf_render.render_html_to_pdf(page)
    assert pdf.startswith(b"%PDF")
    assert b"/Subtype /Image" in pdf
    assert b"EmbeddedFile" not in pdf


def test_real_render_with_logo_still_blocks_injected_markup(tmp_path):
    _require_weasyprint()
    _require_logo()
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET-MARKER-12345")
    company = SimpleNamespace(
        company_name=f'<link rel="attachment" href="{secret.as_uri()}">',
        registration_number="X-1",
        current_compliance_score=50,
        current_risk_band="AMBER",
    )
    page = build_compliance_report_html(
        company, FLAGS, WHEN, logo_uri=pdf_render.asset_uri(LOGO_FILE)
    )
    pdf = pdf_render.render_html_to_pdf(page)
    assert b"EmbeddedFile" not in pdf
    assert not _pdf_contains(pdf, b"TOP-SECRET-MARKER-12345")


def test_real_render_of_report_with_bengali_text():
    _require_weasyprint()
    company = SimpleNamespace(
        company_name="নিউম লেক্স কাউন্সেল লিমিটেড",
        registration_number="C-123456/2020",
        current_compliance_score=82,
        current_risk_band="GREEN",
    )
    pdf = pdf_render.render_html_to_pdf(build_compliance_report_html(company, FLAGS, WHEN))
    assert pdf.startswith(b"%PDF")
