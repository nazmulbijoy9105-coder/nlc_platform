"""
Service to generate branded PDF compliance reports using WeasyPrint.

Every value interpolated into the HTML goes through esc(), and rendering goes
through pdf_render.render_html_to_pdf_async, which only lets WeasyPrint load
files from app/static/brand.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import Response, HTTPException

from app.services.company_service import CompanyService
from app.services.compliance_service import ComplianceService
from app.models.compliance import ComplianceScoreHistory
from app.services.rescue_service import RescueService
from sqlalchemy import select
from app.rule_engine.engine import CATEGORY_CAPS
from app.services.pdf_render import (
    asset_uri,
    esc,
    render_html_to_pdf_async,
    safe_filename_part,
)

REPORT_TZ = ZoneInfo("Asia/Dhaka")
LOGO_FILE = "nlc_logo.png"

# Brand colours sampled from the Neum Lex Counsel logo.
NAVY = "#0f233c"
GOLD = "#9d793b"

# Plain string (not an f-string) so CSS braces never need doubling.
_CSS = """
@page {
    size: A4;
    margin: 1.8cm 2cm 2.2cm 2cm;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9px;
        color: #6c757d;
    }
}
body { font-family: 'Noto Sans Bengali', 'Noto Sans', 'Liberation Sans', sans-serif; color: #333; }
.header { text-align: center; border-bottom: 2px solid __GOLD__; padding-bottom: 12px; margin-bottom: 20px; }
.logo { height: 3cm; margin-bottom: 8px; }
.title { font-size: 22px; font-weight: bold; color: __NAVY__; }
.subtitle { font-size: 12px; color: __GOLD__; letter-spacing: 1px; text-transform: uppercase; margin-top: 2px; }
h2 { color: __NAVY__; }
.score-box { background: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; text-align: center; margin: 20px 0; }
.score-number { font-size: 48px; font-weight: bold; }
.score-good { color: #1a7a52; }
.score-warn { color: #D97706; }
.score-bad { color: #B91C1C; }
.band { font-size: 18px; font-weight: bold; text-transform: uppercase; }
.flags-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
.flags-table th, .flags-table td { border: 1px solid #dee2e6; padding: 8px; text-align: left; font-size: 12px; }
.flags-table th { background-color: __NAVY__; color: white; }
.footer { margin-top: 40px; font-size: 10px; color: #6c757d; text-align: center; border-top: 1px solid #dee2e6; padding-top: 10px; }

/* ── Rescue Plan section ────────────────────────────────────── */
.rescue-section { margin-top: 28px; page-break-inside: avoid; }
.rescue-section h3 { color: __NAVY__; border-bottom: 2px solid __GOLD__; padding-bottom: 6px; margin-bottom: 12px; }
.rescue-meta { font-size: 11px; color: #495057; margin-bottom: 12px; line-height: 1.5; }
.rescue-meta strong { color: __NAVY__; }
.progress-wrap { background: #e9ecef; border-radius: 4px; height: 18px; margin: 8px 0 14px; overflow: hidden; }
.progress-bar { background: __GOLD__; height: 100%; }
.progress-label { font-size: 11px; color: #495057; margin-bottom: 10px; }
.steps-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.steps-table th, .steps-table td { border: 1px solid #dee2e6; padding: 7px 8px; text-align: left; font-size: 11px; vertical-align: top; }
.steps-table th { background-color: __NAVY__; color: white; }
.steps-table td.step-num { text-align: center; font-weight: bold; color: __NAVY__; width: 32px; }
.status-badge { display: inline-block; padding: 2px 7px; border-radius: 3px; font-size: 9px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
.status-PENDING     { background: #e2e8f0; color: #475569; }
.status-IN_PROGRESS { background: #fef3c7; color: #92400e; }
.status-COMPLETE    { background: #dcfce7; color: #166534; }
.status-BLOCKED     { background: #fee2e2; color: #991b1b; }
.step-notes { color: #6b7280; font-style: italic; margin-top: 4px; }
.step-blocked { color: #991b1b; font-style: italic; margin-top: 4px; }
.no-rescue { font-size: 11px; color: #6c757d; font-style: italic; margin-top: 8px; }
""".replace("__NAVY__", NAVY).replace("__GOLD__", GOLD)


def _score_class(score: Any) -> str:
    if score >= 70:
        return "score-good"
    if score < 50:
        return "score-bad"
    return "score-warn"


def _render_rescue_section(rescue_plan: Any) -> str:
    """
    Render the Corporate Rescue Plan block.

    Returns an empty string when no active plan exists (GREEN/YELLOW companies
    never have one, and RED/BLACK companies may not yet have triggered rescue
    generation).
    """
    if rescue_plan is None:
        # Only emit a notice when the company is RED/BLACK — for those bands
        # a missing rescue plan is itself actionable information. For GREEN/
        # YELLOW we omit the section entirely so the report stays clean.
        return ""

    plan = rescue_plan
    steps = getattr(plan, "steps", None) or []

    started_at = getattr(plan, "started_at", None)
    started_str = started_at.strftime("%d %b %Y") if started_at else "—"
    target_str = getattr(plan, "target_completion_date", None) or "—"
    if target_str != "—" and hasattr(target_str, "strftime"):
        target_str = target_str.strftime("%d %b %Y")

    completed = int(getattr(plan, "completed_steps", 0) or 0)
    total = int(getattr(plan, "total_steps", 0) or 0)
    blocked = int(getattr(plan, "blocked_steps", 0) or 0)
    pct = int(getattr(plan, "completion_percentage", 0) or 0)
    if total == 0 and steps:
        total = len(steps)
    pct = min(max(pct, 0), 100)

    # Step rows
    if steps:
        rows_html = []
        for s in steps:
            status_val = getattr(s, "step_status", None)
            status_str = str(getattr(status_val, "value", status_val) or "PENDING")
            target_step_date = getattr(s, "target_completion_date", None)
            target_step_str = (
                target_step_date.strftime("%d %b %Y")
                if hasattr(target_step_date, "strftime")
                else (target_step_date or "—")
            )
            statutory = getattr(s, "statutory_basis", None) or ""
            complexity_val = getattr(s, "complexity", None)
            complexity_str = str(getattr(complexity_val, "value", complexity_val) or "")
            notes = getattr(s, "completion_notes", None) or ""
            blocked_reason = getattr(s, "blocked_reason", None) or ""

            notes_html = (
                f'<div class="step-notes">{esc(notes)}</div>'
                if notes
                else ""
            )
            blocked_html = (
                f'<div class="step-blocked">Blocked: {esc(blocked_reason)}</div>'
                if blocked_reason
                else ""
            )

            rows_html.append(
                f"<tr>"
                f'<td class="step-num">{esc(getattr(s, "step_number", ""))}</td>'
                f"<td><strong>{esc(getattr(s, 'step_title', ''))}</strong>"
                f"<div style=\"font-size:10px;color:#6b7280;margin-top:2px;\">{esc(getattr(s, 'step_description', ''))[:240]}</div>"
                f"{blocked_html}{notes_html}</td>"
                f"<td>{esc(statutory)}</td>"
                f"<td>{esc(complexity_str)}</td>"
                f'<td><span class="status-badge status-{esc(status_str)}">{esc(status_str.replace("_", " "))}</span></td>'
                f"<td>{esc(target_step_str)}</td>"
                f"</tr>"
            )
        rows = "".join(rows_html)
    else:
        rows = '<tr><td colspan="6">No rescue steps recorded.</td></tr>'

    return f"""
    <div class="rescue-section">
        <h3>Corporate Rescue Plan</h3>
        <div class="rescue-meta">
            <strong>Plan:</strong> {esc(getattr(plan, "plan_name", ""))}<br>
            <strong>Triggered by risk band:</strong> {esc(getattr(plan, "initial_risk_band", ""))}
            &nbsp;|&nbsp; <strong>Initial score:</strong> {esc(getattr(plan, "initial_score", ""))}/100<br>
            <strong>Started:</strong> {esc(started_str)}
            &nbsp;|&nbsp; <strong>Target completion:</strong> {esc(target_str)}
            &nbsp;|&nbsp; <strong>Steps:</strong> {esc(completed)}/{esc(total)} completed
            {"&nbsp;|&nbsp; <strong>Blocked:</strong> " + esc(str(blocked)) if blocked else ""}
        </div>
        <div class="progress-label">Progress: {esc(pct)}%</div>
        <div class="progress-wrap">
            <div class="progress-bar" style="width:{esc(pct)}%;"></div>
        </div>
        <table class="steps-table">
            <tr>
                <th>#</th>
                <th>Step</th>
                <th>Statutory Basis</th>
                <th>Complexity</th>
                <th>Status</th>
                <th>Target Date</th>
            </tr>
            {rows}
        </table>
    </div>
    """


def build_compliance_report_html(
    company: Any,
    flags: Any,
    generated_at: datetime,
    logo_uri: str | None = None,
    rescue_plan: Any = None,
) -> str:
    """Pure function: company + flags + rescue_plan -> report HTML. All dynamic values escaped.

    logo_uri must come from pdf_render.asset_uri(), never from user input.
    rescue_plan may be None (GREEN/YELLOW company, or RED/BLACK company that
    hasn't triggered rescue generation yet); in that case the rescue section
    is omitted entirely.
    """
    score = company.current_compliance_score or 0
    band = company.current_risk_band or "NOT_EVALUATED"

    if flags:
        rows = "".join(
            f"<tr><td>{esc(f.rule_id)}</td><td>{esc(f.severity)}</td>"
            f"<td>{esc(f.description)}</td><td>-{esc(f.score_impact or 0)} pts</td></tr>"
            for f in flags
        )
    else:
        rows = '<tr><td colspan="4">No active compliance flags.</td></tr>'
    # F1 reconciliation: per-flag impacts are raw (pre-cap). The engine applies
    # CATEGORY_CAPS per category inside _calculate_score; surface it so the
    # printed math reconciles with the score box.
    band_str = str(getattr(band, "value", band) or "NOT_EVALUATED")
    recon_html = ""
    if flags and band_str != "BLACK":
        cat_raw = {}
        for fl in flags:
            rid = str(getattr(fl, "rule_id", "") or "")
            imp = int(getattr(fl, "score_impact", 0) or 0)
            cat = "OTHER"
            for cat_name, (_cap, _prefixes) in CATEGORY_CAPS.items():
                if any(rid.startswith(p) for p in _prefixes):
                    cat = cat_name
                    break
            cat_raw[cat] = cat_raw.get(cat, 0) + imp
        total_eff = 0
        adjusted = []
        for cat_name in sorted(cat_raw):
            raw = cat_raw[cat_name]
            cap = 100 if cat_name == "OTHER" else CATEGORY_CAPS[cat_name][0]
            eff = min(raw, cap)
            total_eff += eff
            if eff < raw:
                adjusted.append(
                    f'<div>Category cap applied ({esc(cat_name)}): raw deduction {raw} pts '
                    f'capped to {eff} pts (cap {cap})</div>'
                )
        if total_eff > 0:
            implied = 100 - total_eff
            note = "" if implied == int(score) else " (final score clamped/overridden by engine)"
            cap_html = "".join(adjusted)
            recon_html = (
                '<div style="font-size:11px;color:#495057;margin-top:8px;">'
                f'<strong>Score reconciliation:</strong> raw deductions '
                f'-{sum(cat_raw.values())} pts; category caps '
                f'-{sum(cat_raw.values()) - total_eff} pts; effective deductions '
                f'-{total_eff} pts &rarr; indicated score {implied}/100{note}'
                f'{cap_html}</div>'
            )

    logo_html = (
        f'<img class="logo" src="{esc(logo_uri)}" alt="Neum Lex Counsel"><br>'
        if logo_uri
        else ""
    )

    rescue_html = _render_rescue_section(rescue_plan)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>RJSC Compliance Intelligence Report</title>
    <style>{_CSS}</style>
</head>
<body>
    <div class="header">
        {logo_html}
        <div class="title">RJSC Compliance Intelligence Report</div>
        <div class="subtitle">Generated by Neum Lex Counsel</div>
    </div>

    <h2>{esc(company.company_name or '[COMPANY NAME NOT ON FILE]')}</h2>
    <p><strong>Registration Number:</strong> {esc(company.registration_number)}<br>
       <strong>Date of Report:</strong> {esc(generated_at.strftime('%d %B %Y'))}</p>

        <div class="score-box">
        <div class="score-number {_score_class(score)}">{esc(score)} / 100</div>
        <div class="band">Risk Band: {esc(band)}</div>
        {('<div style="font-size:11px;color:#B91C1C;margin-top:8px;"><strong>Score Override:</strong> A BLACK-severity rule has been triggered. The compliance score is set to 0 regardless of accumulated deductions, as the company has a critical legal deficiency requiring immediate remediation.</div>') if band == 'BLACK' else ''}
    </div>

    <h3>Active Compliance Flags</h3>
    <table class="flags-table">
        <tr><th>Rule ID</th><th>Severity</th><th>Description</th><th>Score Impact</th></tr>
        {rows}
    </table>

    {recon_html}

    {rescue_html}

    <div class="footer">
        <p>This compliance intelligence output is subject to professional review under the Companies Act 1994 (Bangladesh).</p>
        <p>Automated compliance screening. Not legal advice. Consult your legal counsel.</p>
    </div>
</body>
</html>"""


class PDFReportService:
    def __init__(self, db):
        self.db = db

    async def generate_company_compliance_pdf(self, company_id: str) -> Response:
        company = await CompanyService(self.db).get_by_id_or_404(company_id)
        flags = await ComplianceService(self.db).get_active_flags(company_id)

        # Fetch the active rescue plan (if any) so the PDF includes the
        # 8-step recovery roadmap. GREEN/YELLOW companies have no plan;
        # RED/BLACK companies may not have triggered rescue generation yet.
        # Failure to load the plan must NOT break PDF generation — we degrade
        # gracefully to a flags-only report.
        rescue_plan = None
        try:
            rescue_plan = await RescueService(self.db).get_active_plan(company.id)
        except Exception:
            rescue_plan = None

        # COM-007: bind report to evidence snapshot + engine version
        score_snapshot = await self.db.execute(
            select(ComplianceScoreHistory)
            .where(ComplianceScoreHistory.company_id == company.id)
            .order_by(ComplianceScoreHistory.calculated_at.desc())
            .limit(1)
        )
        snapshot = score_snapshot.scalar_one_or_none()
        snapshot_hash = snapshot.score_hash if snapshot else "unknown"
        engine_version = snapshot.engine_version if snapshot else "unknown"

        html_content = build_compliance_report_html(
            company,
            flags,
            datetime.now(REPORT_TZ),
            logo_uri=asset_uri(LOGO_FILE),
            rescue_plan=rescue_plan,
        )
        pdf_bytes = await render_html_to_pdf_async(html_content)

        filename = f"compliance_report_{safe_filename_part(company.registration_number)}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Snapshot-Hash": snapshot_hash,  # COM-007
                "X-Engine-Version": engine_version,  # COM-007
            },
        )