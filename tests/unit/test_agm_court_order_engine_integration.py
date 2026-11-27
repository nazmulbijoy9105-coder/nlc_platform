from datetime import date

from app.compliance.fact_provenance import coerce_company_profile_fact_value
from app.rule_engine.engine import CompanyProfile, NLCRuleEngine, RuleState, Severity


def _profile_with_order(*, verified=True, decision=None, affected_event="FIRST_AGM_2026"):
    evidence = {
        "court_name": "High Court Division",
        "case_number": "Company Matter 12 of 2026",
        "order_date": "2026-10-01",
        "operative_paragraphs": "Paragraph 4 directs the respondent to ...",
        "affected_event": affected_event,
        "statutory_power_claimed": "Companies Act 1994, section 85",
        "evidence_ref": "document:verified-order-001",
        "authenticated": True,
        "verified_by": "reviewer-uuid",
        "verified_at": "2026-10-02T10:00:00+06:00",
        "order_status": "IN_FORCE",
    }
    keys = {"agm_history_verified"}
    if verified:
        keys.add("agm_court_order_evidence")
    if decision is not None:
        keys.add("agm_court_order_lawyer_decision")
    return CompanyProfile(
        company_id="agm-court-order-integration",
        company_name="AGM Court Order Integration Ltd",
        incorporation_date=date(2024, 1, 1),
        agm_count=0,
        agm_history_verified=True,
        agm_history_evidence_ref="agm-history:verified",
        agm_history_verified_at=date(2026, 1, 1),
        agm_history_verified_by="agm-reviewer",
        agm_court_order_evidence=evidence,
        agm_court_order_lawyer_decision=decision,
        verified_fact_keys=frozenset(keys),
        verified_fact_context={
            "agm_court_order_evidence": {
                "document_id": "order-document-001",
                "source_reference": "court-order:case-12-2026",
            }
        } if verified else {},
    )


def _run_agm(profile):
    engine = NLCRuleEngine(today=date(2026, 11, 27))
    engine._flags = []
    engine._rule_versions = {}
    engine._rule_active = {}
    engine._rule_bases = {}
    engine._catalogue_binding_required = False
    engine._run_agm_rules(profile)
    return engine


def test_verified_court_order_routes_first_agm_to_review_and_blocks_default_score():
    profile = _profile_with_order()
    engine = _run_agm(profile)

    assert len(engine._flags) == 1
    flag = engine._flags[0]
    assert flag.rule_id == "AGM-001"
    assert flag.flag_code == "AGM_COURT_ORDER_REQUIRES_REVIEW"
    assert flag.state is RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.eval_state == "UNKNOWN"
    assert flag.severity is Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.is_black_override is False
    assert flag.detail["court_order_review"]["automatic_clearance"] is False
    assert flag.detail["court_order_review"]["score_uplift"] == 0
    score = engine._calculate_score(engine._flags, profile)
    assert score.final_score == 100
    assert score.risk_band is Severity.NOT_EVALUATED


def test_unverified_company_fact_cannot_authenticate_court_order():
    profile = _profile_with_order(verified=False)
    engine = _run_agm(profile)

    flag = engine._flags[0]
    assert flag.state is RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.detail["court_order_review"]["evidence_verified"] is False
    assert flag.score_impact == 0
    assert flag.is_black_override is False


def test_scoped_lawyer_decision_still_withholds_scoring_until_rule_logic_is_implemented():
    decision = {
        "reviewer_id": "counsel-uuid",
        "decided_at": "2026-10-03T12:00:00+06:00",
        "decision_reference": "legal-review:agm-001-2026-01",
        "reasoning": "The operative order applies only to this event.",
        "affected_event": "FIRST_AGM_2026",
        "outcome": "DEADLINE_MODIFIED",
    }
    profile = _profile_with_order(decision=decision)
    engine = _run_agm(profile)

    flag = engine._flags[0]
    assert flag.state is RuleState.UNKNOWN
    assert flag.eval_state == "UNKNOWN"
    assert flag.severity is Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.is_black_override is False
    assert flag.detail["court_order_review"]["state"] == "LAWYER_DECISION_RECORDED"
    assert flag.detail["court_order_review"]["automatic_clearance"] is False


def test_subsequent_agm_order_does_not_suppress_first_agm_rule_when_count_is_zero():
    profile = _profile_with_order(affected_event="SUBSEQUENT_AGM_2026")
    engine = _run_agm(profile)
    # A subsequent-AGM order is not applied to an unheld first AGM.
    assert len(engine._flags) == 1
    assert engine._flags[0].rule_id == "AGM-001"
    assert engine._flags[0].flag_code == "FIRST_AGM_DEFAULT"

def test_ambiguous_order_is_scoped_to_first_agm_when_verified_count_is_zero():
    profile = _profile_with_order(affected_event="UNSCOPED_ORDER")
    engine = _run_agm(profile)
    assert len(engine._flags) == 1
    assert engine._flags[0].rule_id == "AGM-001"
    assert engine._flags[0].flag_code == "AGM_COURT_ORDER_REQUIRES_REVIEW"


def test_subsequent_agm_order_routes_only_subsequent_rule_after_first_agm():
    profile = _profile_with_order(affected_event="SUBSEQUENT_AGM_2026")
    profile.agm_count = 1
    profile.last_agm_date = date(2025, 6, 1)
    engine = _run_agm(profile)
    assert len(engine._flags) == 1
    assert engine._flags[0].rule_id == "AGM-002"
    assert engine._flags[0].flag_code == "AGM_COURT_ORDER_REQUIRES_REVIEW"

def test_court_order_and_lawyer_decision_are_supported_company_fact_payloads():
    order = {
        "court_name": "High Court Division",
        "case_number": "Company Matter 12 of 2026",
        "order_date": "2026-10-01",
        "operative_paragraphs": "Paragraph 4 ...",
        "affected_event": "FIRST_AGM_2026",
        "statutory_power_claimed": "Companies Act 1994, section 85",
        "evidence_ref": "document:order-001",
        "authenticated": True,
        "verified_by": "reviewer-uuid",
        "verified_at": "2026-10-02T10:00:00+06:00",
        "order_status": "IN_FORCE",
    }
    decision = {
        "reviewer_id": "counsel-uuid",
        "decided_at": "2026-10-03T12:00:00+06:00",
        "decision_reference": "legal-review:agm-001-2026-01",
        "reasoning": "Scoped interpretation recorded.",
        "affected_event": "FIRST_AGM_2026",
        "outcome": "NO_EFFECT",
    }

    assert coerce_company_profile_fact_value("agm_court_order_evidence", order) == order
    assert (
        coerce_company_profile_fact_value("agm_court_order_lawyer_decision", decision)
        == decision
    )

def test_malformed_non_object_order_fact_fails_closed_in_engine():
    profile = _profile_with_order()
    profile.agm_court_order_evidence = ["not", "an", "object"]
    engine = _run_agm(profile)

    assert len(engine._flags) == 1
    flag = engine._flags[0]
    assert flag.rule_id == "AGM-001"
    assert flag.state is RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.eval_state == "UNKNOWN"
    assert flag.severity is Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.is_black_override is False
    assert flag.detail["court_order_review"]["reason"].startswith(
        "INVALID_OR_INCOMPLETE_ORDER_EVIDENCE:"
    )
