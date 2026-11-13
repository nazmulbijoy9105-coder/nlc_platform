"""
Service to generate branded PDF compliance reports using WeasyPrint.

Every value interpolated into the HTML goes through esc(), and rendering goes
through pdf_render.render_html_to_pdf_async, which only lets WeasyPrint load
files from app/static/brand.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Response
from sqlalchemy import select

from app.models.compliance import ComplianceEvaluationRun

# Import CATEGORY_CAPS for score reconciliation (cap adjustment display)
from app.rule_engine.engine import (
    AUTHORIZED_BLACK_OVERRIDE_RULE_IDS,
    CATEGORY_CAPS,
    LEGAL_SCORE_RELEASED,
    PRODUCT_SCORING_RULE_IDS,
    VERIFIED_RULE_IDS,
    RuleState,
)
from app.services.company_service import CompanyService
from app.services.pdf_render import (
    asset_uri,
    esc,
    render_html_to_pdf_async,
    safe_filename_part,
)
from app.services.rescue_service import RescueService
from canonical_architecture.scoring_spec import allocate_flag_deductions
from canonical_architecture.scoring_spec import SCORING_SPEC_VERSION

REPORT_TZ = ZoneInfo("Asia/Dhaka")
LOGO_FILE = "nlc_logo.svg"


class ScoreReconciliationError(ValueError):
    """Raised when a PDF cannot prove that its displayed score reconciles."""

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
.unsigned-banner { background:#991b1b; color:#fff; border:2px solid #7f1d1d; padding:12px; margin:14px 0; text-align:center; font-size:14px; font-weight:bold; letter-spacing:.3px; }
.liability-box { border:2px solid #991b1b; background:#fff7f7; padding:12px; margin:14px 0; font-size:10px; line-height:1.5; }
.signature-box { border:1px solid #64748b; padding:12px; margin:18px 0; page-break-inside:avoid; font-size:10px; line-height:1.8; }
.footer { margin-top: 40px; font-size: 10px; color: #6c757d; text-align: center; border-top: 1px solid #dee2e6; padding-top: 10px; }

/* ── Risk band legend ───────────────────────────────────── */
.band-legend { display: flex; gap: 8px; margin: 12px 0 4px; font-size: 9px; }
.band-item { flex: 1; padding: 6px 4px; text-align: center; border-radius: 3px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
.band-GREEN  { background: #dcfce7; color: #166534; }
.band-YELLOW { background: #fef3c7; color: #92400e; }
.band-RED    { background: #fee2e2; color: #991b1b; }
.band-BLACK  { background: #1f2937; color: #f9fafb; }
.band-NOT_EVALUATED { background: #e5e7eb; color: #6b7280; }
.band-current { border: 2px solid __GOLD__; }

/* ── Executive summary ─────────────────────────────────── */
.exec-summary { background: #f8f9fa; border-left: 3px solid __GOLD__; padding: 10px 14px; margin: 16px 0; font-size: 11px; line-height: 1.6; color: #374151; }
.exec-summary strong { color: __NAVY__; }

/* ── Audit metadata in footer ──────────────────────────── */
.audit-meta { font-size: 9px; color: #9ca3af; margin-top: 6px; font-family: monospace; }

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


def _render_band_legend(current_band: str) -> str:
    """Render the 5-band risk legend with the current band highlighted.

    Includes NOT_EVALUATED for companies with insufficient data (coverage < 0.5).
    """
    # Risk band is the worst product-released, evidence-supported finding severity,
    # not a numeric score range. Product scoring does not imply legal certification.
    bands = [
        ("GREEN", "No active adverse finding", "Routine monitoring"),
        ("YELLOW", "Active monitoring finding", "Review"),
        ("RED", "Active material finding", "Action required"),
        ("BLACK", "Active critical override", "Critical"),
        ("NOT_EVALUATED", "Insufficient evidence or scoring disabled", "No score released"),
    ]
    items = []
    for band_name, score_range, label in bands:
        cls = f"band-item band-{band_name}"
        if band_name == current_band:
            cls += " band-current"
        items.append(
            f'<div class="{cls}">{esc(band_name)}<br><span style="font-weight:normal;text-transform:none;letter-spacing:0;">{esc(score_range)} · {esc(label)}</span></div>'
        )
    return f'<div class="band-legend">{"".join(items)}</div>'


def _render_exec_summary(company: Any, flags: Any, band: str, score: int, rescue_plan: Any) -> str:
    """Generate a brief executive summary paragraph based on the company's status."""
    flag_count = len(flags) if flags else 0
    def verified_severity(flag):
        if getattr(flag, "rule_id", "") not in PRODUCT_SCORING_RULE_IDS:
            return None
        return getattr(
            getattr(flag, "severity", None),
            "value",
            getattr(flag, "severity", None),
        )

    black_count = sum(1 for f in (flags or []) if verified_severity(f) == "BLACK")
    red_count = sum(1 for f in (flags or []) if verified_severity(f) == "RED")
    yellow_count = sum(1 for f in (flags or []) if verified_severity(f) == "YELLOW")

    if band == "BLACK":
        urgency = "<strong>Critical product-risk indicator detected.</strong> A product-allowlisted BLACK-severity finding requires urgent professional review and remediation. The compliance score has been overridden to 0 pending resolution of the critical flag(s)."
    elif band == "RED":
        urgency = "<strong>Significant product-risk findings detected.</strong> Review the active RED-severity product findings and determine appropriate remediation with qualified counsel."
    elif band == "YELLOW":
        urgency = "<strong>Product-risk monitoring recommended.</strong> The company has product findings that should be reviewed and addressed where appropriate."
    elif band == "NOT_EVALUATED":
        urgency = "<strong>Not evaluated: no customer-facing score is available.</strong> Product scoring may be disabled, or the company facts and evidence may be insufficient for evaluation. This report is not a compliance certification."
    else:
        urgency = "<strong>No adverse product-risk findings detected.</strong> This is not a compliance certification. Continue evidence-based monitoring."

    parts = [urgency]
    score_summary = "NOT EVALUATED" if band == "NOT_EVALUATED" else f"{score}/100"
    parts.append(
        f"Active flags: <strong>{flag_count}</strong> "
        f"({black_count} BLACK, {red_count} RED, {yellow_count} YELLOW). "
        f"Product risk score: <strong>{esc(score_summary)}</strong>."
    )

    if rescue_plan is not None:
        completed = int(getattr(rescue_plan, "completed_steps", 0) or 0)
        total = int(getattr(rescue_plan, "total_steps", 0) or 0)
        parts.append(
            f"A <strong>Corporate Rescue Plan</strong> has been initiated with "
            f"{total} remediation step(s), {completed} completed."
        )
    elif band in ("RED", "BLACK"):
        parts.append("No rescue plan has been generated yet. Consider triggering compliance evaluation to generate a remediation roadmap.")

    return f'<div class="exec-summary">{" ".join(parts)}</div>'


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
                if target_step_date is not None
                and callable(getattr(target_step_date, "strftime", None))
                else (str(target_step_date) if target_step_date is not None else "—")
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


def _legal_score_is_released() -> bool:
    """Mirror the engine product-release gate using testable inputs."""
    return (
        LEGAL_SCORE_RELEASED is True
        and bool(PRODUCT_SCORING_RULE_IDS)
    )


def _verified_flag_score(flags: Any) -> tuple[int, bool]:
    """Mirror the engine's release, eligibility, category-cap and override gates."""
    if not _legal_score_is_released():
        return (0, False)

    remaining = {name: cap[0] for name, cap in CATEGORY_CAPS.items()}
    total_applied = 0
    has_black_override = False
    for flag in flags:
        rule_id = getattr(flag, "rule_id", "")
        state = getattr(flag, "state", RuleState.NON_COMPLIANT)
        eval_state = getattr(flag, "eval_state", "VIOLATION")
        active = (
            not getattr(flag, "resolved", False)
            and getattr(flag, "conditional_applies", True)
        )
        if (
            not active
            or state not in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            or eval_state != "VIOLATION"
            or rule_id not in PRODUCT_SCORING_RULE_IDS
            ):
            continue

        severity = getattr(
            getattr(flag, "severity", None),
            "value",
            getattr(flag, "severity", None),
        )
        if (
            rule_id in AUTHORIZED_BLACK_OVERRIDE_RULE_IDS
            and getattr(flag, "is_black_override", False) is True
            and severity == "BLACK"
        ):
            has_black_override = True
            continue

        category = next(
            (
                name
                for name, (_, prefixes) in CATEGORY_CAPS.items()
                if rule_id.startswith(prefixes)
            ),
            None,
        )
        if category is None:
            continue
        applied = min(
            max(0, int(getattr(flag, "score_impact", 0) or 0)),
            remaining[category],
        )
        remaining[category] -= applied
        total_applied += applied

    return (0 if has_black_override else max(0, 100 - total_applied), has_black_override)


def _render_score_reconciliation(flags: Any, score: int, band: str) -> str:
    """Render and strictly reconcile persisted per-finding score allocations.

    A category cap alone is not enough to validate a snapshot: the global
    100-point budget and explicit shared-event suppression can also reduce an
    individual finding. Recompute the exact allocation using the same
    versioned scoring specification used by the evaluation pipeline.
    """
    if not _legal_score_is_released() or band in ("BLACK", "NOT_EVALUATED"):
        return ""

    cat_deductions: dict[str, dict] = {}
    duplicate_rows: list[str] = []
    allocation_rows: list[tuple[str, int, str | None, bool, int]] = []

    for f in (flags or []):
        rule_id = getattr(f, "rule_id", "") or ""
        if (
            rule_id not in PRODUCT_SCORING_RULE_IDS
        ):
            continue

        scoring_status = getattr(f, "scoring_status", None)
        if scoring_status is not None and scoring_status not in (
            "APPLIED",
            "CATEGORY_CAP_REACHED",
            "DUPLICATE_EVENT_SUPPRESSED",
        ):
            continue

        raw_impact = max(0, int(getattr(f, "score_impact", 0) or 0))
        has_applied_metadata = hasattr(f, "score_impact_applied")
        applied_impact = (
            int(getattr(f, "score_impact_applied", 0) or 0)
            if has_applied_metadata
            else raw_impact
        )
        detail = getattr(f, "detail", None)
        event_key = (
            detail.get("scoring_event_key")
            if isinstance(detail, dict)
            else None
        )
        allocation_rows.append((
            rule_id, raw_impact, event_key, has_applied_metadata, applied_impact
        ))

        if scoring_status == "DUPLICATE_EVENT_SUPPRESSED":
            duplicate_rows.append(
                f'<div style="font-size:10px;color:#555;padding:2px 0;">'
                f'Duplicate finding suppressed from scoring: {esc(rule_id)}'
                f'</div>'
            )
            continue

        if raw_impact == 0 and applied_impact == 0:
            continue

        category = next(
            (
                name
                for name, (_, prefixes) in CATEGORY_CAPS.items()
                if any(rule_id.startswith(prefix) for prefix in prefixes)
            ),
            None,
        )
        if category is None:
            continue

        if category not in cat_deductions:
            cap = CATEGORY_CAPS[category][0]
            cat_deductions[category] = {
                "raw": 0,
                "applied": 0,
                "cap": cap,
                "has_complete_applied_metadata": True,
            }

        data = cat_deductions[category]
        data["raw"] += raw_impact
        data["applied"] += applied_impact
        data["has_complete_applied_metadata"] = (
            data["has_complete_applied_metadata"] and has_applied_metadata
        )

    if not cat_deductions and not duplicate_rows:
        return ""

    # New snapshots carry applied-impact metadata for every eligible finding.
    # Recompute each allocation, including global-budget and duplicate-event
    # effects, then reject any persisted per-finding disagreement.
    metadata_presence = [row[3] for row in allocation_rows]
    if any(metadata_presence) and not all(metadata_presence):
        raise ScoreReconciliationError(
            "PDF snapshot contains incomplete per-finding applied-impact metadata"
        )
    if allocation_rows and all(metadata_presence):
        expected = allocate_flag_deductions([
            (rule_id, raw_impact, event_key)
            for rule_id, raw_impact, event_key, _, _ in allocation_rows
        ])
        for row, expected_applied in zip(allocation_rows, expected):
            rule_id, _, _, _, persisted_applied = row
            if persisted_applied != expected_applied:
                raise ScoreReconciliationError(
                    f"PDF finding reconciliation mismatch for {rule_id}: "
                    f"persisted_applied={persisted_applied}, "
                    f"expected_applied={expected_applied}"
                )

    cap_rows = list(duplicate_rows)
    effective_total = 0
    for cat_name, data in sorted(cat_deductions.items()):
        raw = data["raw"]
        cap = data["cap"]
        maximum_allowed = min(raw, cap)

        if data["has_complete_applied_metadata"]:
            effective = data["applied"]
            if effective < 0 or effective > maximum_allowed:
                raise ScoreReconciliationError(
                    f"PDF category reconciliation mismatch for {cat_name}: "
                    f"raw={raw}, cap={cap}, persisted_applied={effective}, "
                    f"maximum_allowed={maximum_allowed}"
                )
        else:
            # Compatibility for older snapshots that predate applied-impact
            # metadata. New evaluation snapshots always carry this value.
            effective = maximum_allowed

        effective_total += effective
        if raw > cap:
            cap_rows.append(
                f'<div style="font-size:10px;color:#555;padding:2px 0;">'
                f'Category cap applied ({esc(cat_name)}): '
                f'raw deduction {raw} pts capped to {effective} pts'
                f'</div>'
            )

    if effective_total > 100:
        raise ScoreReconciliationError(
            f"PDF applied category deductions exceed global score budget: {effective_total}"
        )
    indicated_score = 100 - effective_total
    if indicated_score != score:
        raise ScoreReconciliationError(
            f"PDF score reconciliation mismatch: displayed={score}, indicated={indicated_score}"
        )

    return f"""
    <div class="score-reconciliation" style="margin:8px 0;padding:8px;background:#F8F9FA;border:1px solid #E0E0E0;border-radius:4px;">
        <div style="font-size:11px;font-weight:bold;margin-bottom:4px;">Score reconciliation</div>
        {"".join(cap_rows)}
        <div style="font-size:10px;color:#555;margin-top:4px;">
            effective deductions -{effective_total} pts · indicated score {indicated_score}/100
        </div>
    </div>
    """

def _render_review_queue(flags: Any) -> str:
    """Show unverified rule IDs as neutral review prompts, never as breaches."""
    if not flags:
        return ""
    items = "".join(
        f"<li>{esc(getattr(flag, 'rule_id', 'Unknown rule'))}: "
        "Independent Bangladesh-counsel/source verification remains pending. "
        "Product scoring release is not legal approval or certification.</li>"
        for flag in flags
    )
    return (
        '<section class="review-queue"><h3>Items pending legal/source review</h3>'
        f"<ul>{items}</ul></section>"
    )


def _flag_impact_label(flag: Any) -> str:
    rule_id = getattr(flag, "rule_id", "") or ""
    if (
        not _legal_score_is_released()
        or rule_id not in PRODUCT_SCORING_RULE_IDS
    ):
        return "Not scored — excluded from product scoring"
    applied = getattr(
        flag,
        "score_impact_applied",
        getattr(flag, "score_impact", 0),
    ) or 0
    return f"-{int(applied)} pts" if applied else "Not applied"



def _render_rule_outcome_ledger(items: list[dict] | None) -> str:
    """Render the immutable rule ledger without treating missing findings as passes."""
    if not items:
        return (
            '<section><h3>Statutory Rule Outcome Ledger</h3>'
            '<p>Unavailable for this historical evaluation. No rule-level pass count is inferred.</p></section>'
        )
    counts: dict[str, int] = {}
    rows: list[str] = []
    for item in items:
        state = str(item.get("outcome_state") or "UNKNOWN")
        counts[state] = counts.get(state, 0) + 1
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('rule_id', ''))}</td>"
            f"<td>{esc(item.get('rule_version', ''))}</td>"
            f"<td>{esc(state)}</td>"
            f"<td>{esc(item.get('verification_status', 'PENDING'))}</td>"
            f"<td>{esc(item.get('assessment_source', ''))}</td>"
            f"<td>{esc(item.get('statutory_basis', ''))}</td>"
            "</tr>"
        )
    summary = " · ".join(
        f"{esc(state)}: {count}" for state, count in sorted(counts.items())
    )
    return (
        '<section class="rule-outcome-ledger"><h3>Statutory Rule Outcome Ledger</h3>'
        f'<p><strong>Catalogue rows:</strong> {len(items)} · {summary}</p>'
        '<p>NOT_EVALUATED means no engine finding was emitted for that catalogue rule; '
        'it is not a finding of compliance. Catalogue verification status is shown separately.</p>'
        '<table class="flags-table"><tr><th>Rule ID</th><th>Rule Version</th>'
        '<th>Outcome</th><th>Legal Source Verification</th><th>Assessment Basis</th>'
        f'<th>Statutory Basis</th></tr>{"".join(rows)}</table></section>'
    )


def build_compliance_report_html(
    company: Any,
    flags: Any,
    generated_at: datetime,
    logo_uri: str | None = None,
    rescue_plan: Any = None,
    engine_version: str = "unknown",
    snapshot_hash: str = "unknown",
    evaluation_at: datetime | None = None,
    rule_outcomes_snapshot: list[dict] | None = None,
) -> str:
    """Pure function: company + flags + rescue_plan -> report HTML. All dynamic values escaped.

    logo_uri must come from pdf_render.asset_uri(), never from user input.
    rescue_plan may be None (GREEN/YELLOW company, or RED/BLACK company that
    hasn't triggered rescue generation yet); in that case the rescue section
    is omitted entirely.
    engine_version and snapshot_hash are included in the footer for audit trail.
    """
    # The HTML builder is also called directly by tests and internal jobs.
    # Enforce the release boundary here, not only in the HTTP endpoint:
    # stale cached scores, flags and rescue plans must never leak into a report.
    review_flags = []
    if not _legal_score_is_released():
        flags = ()
        rescue_plan = None
        score = 0
        band = "NOT_EVALUATED"
    else:
        score = company.current_compliance_score or 0
        band = company.current_risk_band or "NOT_EVALUATED"
        review_flags = [
            flag for flag in (flags or [])
            if getattr(flag, "rule_id", "") not in VERIFIED_RULE_IDS
        ]
        flags = [
            flag for flag in (flags or [])
            if getattr(flag, "rule_id", "") in PRODUCT_SCORING_RULE_IDS
        ]
    company_name = company.company_name or "[COMPANY NAME NOT ON FILE]"
    score_display = "NOT EVALUATED" if band == "NOT_EVALUATED" else f"{score} / 100"
    score_css_class = "score-warn" if band == "NOT_EVALUATED" else _score_class(score)

    if flags:
        rows = "".join(
            f"<tr><td>{esc(f.rule_id)}</td><td>{esc(f.severity)}</td>"
            f"<td>{esc(f.description)}</td><td>{esc(_flag_impact_label(f))}</td></tr>"
            for f in flags
        )
    else:
        rows = '<tr><td colspan="4">No active compliance flags.</td></tr>'

    logo_html = (
        f'<img class="logo" src="{esc(logo_uri)}" alt="Neum Lex Counsel"><br>'
        if logo_uri
        else ""
    )

    legend_html = _render_band_legend(band)
    summary_html = _render_exec_summary(company, flags, band, score, rescue_plan)
    rescue_html = _render_rescue_section(rescue_plan)
    reconciliation_html = _render_score_reconciliation(flags, score, band)
    review_html = _render_review_queue(review_flags)
    rule_outcomes_html = _render_rule_outcome_ledger(rule_outcomes_snapshot)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>RJSC Compliance Intelligence Report</title>
    <style>{_CSS}</style>
</head>
<body>
    <div class="unsigned-banner">UNSIGNED — FOR COUNSEL REVIEW ONLY — NO NLC LIABILITY WITHOUT SIGNATURE</div>
    <div class="header">
        {logo_html}
        <div class="title">RJSC Compliance Intelligence Report</div>
        <div class="subtitle">Generated by Neum Lex Counsel</div>
    </div>

    <h2>{esc(company_name)}</h2>
    <table class="meta-table" style="width:100%;font-size:11px;margin-bottom:12px;">
        <tr>
            <td style="width:25%;"><strong>Registration Number:</strong> {esc(company.registration_number)}</td>
            <td style="width:25%;"><strong>Company Type:</strong> {esc(getattr(company, 'company_type', 'N/A'))}</td>
            <td style="width:25%;"><strong>Date of Report:</strong> {esc(generated_at.strftime('%d %B %Y'))}</td>
            <td style="width:25%;"><strong>Assessment ID:</strong> {esc(snapshot_hash[:12] if snapshot_hash and snapshot_hash != 'unknown' else 'N/A')}</td>
        </tr>
        <tr>
            <td><strong>Incorporated:</strong> {esc(getattr(company, 'incorporation_date', 'N/A') or 'N/A')}</td>
            <td><strong>Financial Year End:</strong> {esc(getattr(company, 'financial_year_end', 'N/A') or 'N/A')}</td>
            <td><strong>Status:</strong> {esc(getattr(company, 'status', 'N/A'))}</td>
            <td><strong>Engine Version:</strong> {esc(engine_version)}</td>
        </tr>
        <tr>
            <td colspan="4"><strong>Evaluation Snapshot Time:</strong> {esc(evaluation_at.isoformat() if evaluation_at else 'N/A')}</td>
        </tr>
    </table>

        <div class="score-box">
        <div class="score-number {score_css_class}">{esc(score_display)}</div>
        <div class="band">Risk Band: {esc(band)}</div>
        {('<div style="font-size:11px;color:#B91C1C;margin-top:8px;"><strong>Score Override:</strong> A BLACK-severity rule has been triggered. The product risk score is set to 0 under the configured critical-override policy, as the company has a critical legal deficiency requiring immediate remediation.</div>') if band == 'BLACK' else ''}
    </div>
    {('<div style="font-size:10px;color:#8B6914;background:#FFF8E1;border:1px solid #FFD54F;padding:6px;margin:8px 0;border-radius:4px;"><strong>TEST ASSESSMENT:</strong> This report was generated for a test company. Do not use for legal or regulatory purposes.</div>') if 'TEST' in (company.registration_number or '').upper() else ''}
    {legend_html}
    {summary_html}
    {reconciliation_html}
    {review_html}

    <div class="liability-box">
        <strong>LIABILITY AND RELIANCE NOTICE</strong><br>
        This is an unsigned, automated product output prepared for preliminary information and review only.
        It is not legal advice, a legal opinion, a statutory certificate, an RJSC determination, or confirmation
        that any company is compliant or non-compliant. No NLC legal opinion, professional certification,
        or liability for legal conclusions is assumed or represented by this unsigned report. NLC accepts no
        liability for reliance on legal conclusions in this report unless and until an independent Bangladesh
        company-law counsel has reviewed the relevant facts and sources and signed the approval block below.
        Product scoring release is a product-owner setting and does not constitute independent legal verification.
    </div>

    <div class="signature-box">
        <h3>Lawyer Review &amp; Signature</h3>
        <p><strong>Reviewing Bangladesh Company-Law Counsel:</strong> __________________________________</p>
        <p><strong>Date:</strong> ____________________ &nbsp; <strong>Comments / qualifications:</strong> ______________________________</p>
        <p>☐ I have independently reviewed the relevant company facts, evidence, statutory sources, rule application and score reconciliation.</p>
        <p>☐ I approve the legal conclusions stated in this report, subject to the comments or qualifications recorded above.</p>
        <p><strong>Signature:</strong> _________________________________________________________________</p>
        <p><strong>Approval status:</strong> UNSIGNED — no counsel approval is represented until completed and signed.</p>
    </div>

    {rule_outcomes_html}

    <h3>Active Compliance Flags</h3>
    <table class="flags-table">
        <tr><th>Rule ID</th><th>Severity</th><th>Description</th><th>Score Impact</th></tr>
        {rows}
    </table>

    {rescue_html}

    <div class="footer">
        <p>This compliance intelligence output is subject to professional review under the Companies Act 1994 (Bangladesh).</p>
        <p><strong>Status: UNSIGNED</strong></p>
        <p>Automated compliance screening. Not legal advice. For counsel review only.</p>
        <div class="audit-meta">Engine: {esc(engine_version)} | Snapshot: {esc(snapshot_hash[:16]) if snapshot_hash else 'unknown'} | Generated: {esc(generated_at.isoformat())}</div>
    </div>
</body>
</html>"""


class PDFReportService:
    def __init__(self, db):
        self.db = db

    async def generate_company_compliance_pdf(self, company_id: str) -> Response:
        if not _legal_score_is_released():
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: statutory score release is disabled; no score-bearing compliance report may be issued.",
            )
        company = await CompanyService(self.db).get_by_id_or_404(UUID(company_id))

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
            select(ComplianceEvaluationRun)
            .where(
                ComplianceEvaluationRun.company_id == company.id,
                ComplianceEvaluationRun.calculated_at == company.last_evaluated_at,
            )
            .limit(1)
        )
        snapshot = score_snapshot.scalar_one_or_none()
        if snapshot is None:
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: no authoritative evaluation snapshot exists for this company.",
            )
        if (
            getattr(snapshot, "evaluation_status", None) != "COMPLETED"
            or not getattr(snapshot, "score_hash", None)
            or not getattr(snapshot, "engine_version", None)
            or not isinstance(getattr(snapshot, "flags_snapshot", None), list)
        ):
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: the latest evaluation run is incomplete or lacks audit identity.",
            )
        outcomes = getattr(snapshot, "rule_outcomes_snapshot", None)
        if (
            not isinstance(outcomes, list)
            or not outcomes
            or getattr(snapshot, "rule_catalogue_count", None) != len(outcomes)
            or not getattr(snapshot, "rule_outcomes_hash", None)
        ):
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: the authoritative run has no complete statutory rule outcome ledger.",
            )
        outcomes_hash = hashlib.sha256(json.dumps(
            outcomes, sort_keys=True, separators=(",", ":"), default=str
        ).encode()).hexdigest()
        if outcomes_hash != getattr(snapshot, "rule_outcomes_hash", None):
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: statutory rule outcome ledger hash mismatch.",
            )

        score_snapshot_data = snapshot.score_breakdown_snapshot
        if (
            not isinstance(score_snapshot_data, dict)
            or score_snapshot_data.get("scoring_spec_version") != SCORING_SPEC_VERSION
            or score_snapshot_data.get("score_reconciles") is not True
            or score_snapshot_data.get("final_score") != snapshot.score
        ):
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: the authoritative run does not contain a reconciled score under the current scoring specification.",
            )
        if (
            snapshot.score != company.current_compliance_score
            or snapshot.risk_band != company.current_risk_band
            or company.last_evaluated_at is None
            or snapshot.calculated_at != company.last_evaluated_at
        ):
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: company state does not match its authoritative per-evaluation record.",
            )

        flags = [SimpleNamespace(**item) for item in snapshot.flags_snapshot if isinstance(item, dict)]
        if len(flags) != len(snapshot.flags_snapshot):
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: evaluation flag evidence is malformed.",
            )

        snapshot_hash = snapshot.score_hash
        engine_version = snapshot.engine_version

        try:
            html_content = build_compliance_report_html(
                company,
                flags,
                datetime.now(REPORT_TZ),
                logo_uri=asset_uri(LOGO_FILE),
                rescue_plan=rescue_plan,
                engine_version=engine_version,
                snapshot_hash=snapshot_hash,
                evaluation_at=snapshot.calculated_at,
                rule_outcomes_snapshot=outcomes,
            )
        except ScoreReconciliationError as exc:
            raise HTTPException(
                status_code=409,
                detail="PDF withheld: score reconciliation does not match the authoritative evaluation.",
            ) from exc
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
