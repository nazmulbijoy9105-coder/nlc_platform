"""The counsel register is the sole release source for statutory rule findings."""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

import app.rule_engine.engine as engine_module
from app.rule_engine.engine import CompanyProfile, NLCRuleEngine, RuleState, Severity

ROOT = Path(__file__).resolve().parents[2]


def test_85_rule_catalogue_matches_counsel_register_and_engine_allowlist():
    with (ROOT / "docs/legal/NLC_BD_COMPANIES_LAW_RULES_v1.0.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        catalogue_ids = {
            row["rule_id"].strip()
            for row in csv.DictReader(handle)
            if row.get("rule_id")
        }

    register_text = (
        ROOT / "docs/legal/legal_approval_register.yaml"
    ).read_text(encoding="utf-8")
    register_rows = re.findall(
        r"(?m)^\s+- rule_id:\s*([A-Z][A-Z0-9]*-[0-9]+)\s*\n"
        r"\s+status:\s*([A-Z_]+)\s*\n"
        r"\s+score_eligible:\s*(true|false)\s*$",
        register_text,
    )
    register_ids = {rule_id for rule_id, _status, _eligible in register_rows}

    approved_match = re.search(
        r"(?m)^approved_rule_ids:\s*\[([^\]]*)\]\s*$", register_text
    )
    assert approved_match is not None, "approved_rule_ids must be explicit"
    approved_ids = set(
        re.findall(r"[A-Z][A-Z0-9]*-[0-9]+", approved_match.group(1))
    )

    assert len(catalogue_ids) == 85
    assert catalogue_ids == register_ids
    assert set(engine_module.PRODUCT_SCORING_RULE_IDS) == catalogue_ids
    assert set(engine_module.VERIFIED_RULE_IDS) == approved_ids

    for rule_id, status, eligible in register_rows:
        if rule_id in approved_ids:
            assert status == "VERIFIED"
            assert eligible == "true"
        else:
            assert status == "REVIEW_REQUIRED"
            assert eligible == "false"


def test_unverified_statutory_candidate_is_downgraded_before_api_score_or_rescue(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AUD-001"}))
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())

    profile = CompanyProfile(
        company_id="counsel-gate-test",
        company_name="Counsel Gate Test Ltd",
        incorporation_date=date(2020, 1, 1),
        first_auditor_appointed=False,
        first_auditor_appointment_verified=True,
        first_auditor_appointment_evidence_ref="AUDITOR-SEARCH-001",
        first_auditor_appointment_verified_at=date(2026, 11, 1),
        first_auditor_appointment_verified_by="reviewer-1",
    )
    output = NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)
    matches = [flag for flag in output.flags if flag.rule_id == "AUD-001"]
    assert len(matches) == 1

    finding = matches[0]
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.state is RuleState.UNKNOWN
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0
    assert finding.detail["legal_validation_status"] == "PENDING_COUNSEL_APPROVAL"
    assert finding.detail["statutory_finding_authorized"] is False
    assert finding.detail["candidate_state"] == RuleState.NON_COMPLIANT.value
    assert output.score_breakdown.risk_band is Severity.NOT_EVALUATED
