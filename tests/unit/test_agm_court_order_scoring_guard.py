from datetime import date, datetime, timezone

import pytest

from app.compliance.agm_court_order import agm_court_order_scoring_guard


def _evidence(**overrides):
    value = {
        "court_name": "High Court Division",
        "case_number": "Company Matter 12 of 2026",
        "order_date": "2026-10-01",
        "operative_paragraphs": "Paragraph 4 directs the respondent to ...",
        "affected_event": "FIRST_AGM_2026",
        "statutory_power_claimed": "Companies Act 1994, section 85",
        "evidence_ref": "document:verified-order-001",
        "authenticated": True,
        "verified_by": "reviewer-uuid",
        "verified_at": "2026-10-02T10:00:00+06:00",
        "order_status": "IN_FORCE",
    }
    value.update(overrides)
    return value


def _decision(**overrides):
    value = {
        "reviewer_id": "counsel-uuid",
        "decided_at": "2026-10-03T12:00:00+06:00",
        "decision_reference": "legal-review:agm-001-2026-01",
        "reasoning": "The operative order applies only to this event.",
        "affected_event": "FIRST_AGM_2026",
        "outcome": "DEADLINE_MODIFIED",
        "court_name": "High Court Division",
        "case_number": "Company Matter 12 of 2026",
        "order_date": "2026-10-01",
        "evidence_ref": "document:verified-order-001",
        "effective_from": "2026-10-01",
        "effective_until": None,
        "reviewer_qualification_verified": True,
        "reviewer_qualification_evidence_ref": "counsel-register:verified-001",
        "reviewer_qualification_verified_by": "independent-credential-reviewer",
        "reviewer_qualification_verified_at": "2026-10-02T09:00:00+06:00",
    }
    value.update(overrides)
    return value


def test_absent_order_evidence_does_not_change_score():
    result = agm_court_order_scoring_guard(None, as_of=date(2026, 11, 28))
    assert result["state"] == "NO_ORDER_EVIDENCE"
    assert result["score_impact"] == 0
    assert result["score_uplift"] == 0
    assert result["automatic_clearance"] is False


@pytest.mark.parametrize(
    "override",
    [
        {"authenticated": False},
        {"verified_by": None},
        {"verified_at": None},
        {"order_status": "UNKNOWN"},
        {"evidence_ref": ""},
        {"operative_paragraphs": ""},
    ],
)
def test_incomplete_or_unverified_order_routes_to_lawyer_without_score_change(override):
    result = agm_court_order_scoring_guard(_evidence(**override), as_of=date(2026, 11, 28))
    assert result["requires_lawyer_judgment"] is True
    assert result["state"] == "REQUIRES_LAWYER_JUDGMENT"
    assert result["eval_state"] == "UNKNOWN"
    assert result["severity"] == "NOT_EVALUATED"
    assert result["score_impact"] == 0
    assert result["score_uplift"] == 0
    assert result["is_black_override"] is False
    assert result["automatic_clearance"] is False


def test_verified_order_without_lawyer_decision_never_clears_default():
    result = agm_court_order_scoring_guard(_evidence(), as_of=date(2026, 11, 28))
    assert result["evidence_verified"] is True
    assert result["requires_lawyer_judgment"] is True
    assert result["state"] == "REQUIRES_LAWYER_JUDGMENT"
    assert result["score_impact"] == 0
    assert result["score_uplift"] == 0
    assert result["automatic_clearance"] is False


def test_lawyer_decision_must_match_affected_agm_event():
    result = agm_court_order_scoring_guard(
        _evidence(), _decision(affected_event="ANOTHER_AGM"),
        as_of=date(2026, 11, 28),
    )
    assert result["requires_lawyer_judgment"] is True
    assert result["state"] == "REQUIRES_LAWYER_JUDGMENT"
    assert result["score_impact"] == 0
    assert result["score_uplift"] == 0
    assert result["automatic_clearance"] is False


def test_scoped_lawyer_decision_is_recorded_but_not_automatically_scored():
    result = agm_court_order_scoring_guard(
        _evidence(), _decision(), as_of=date(2026, 11, 28),
        qualified_counsel_ids=frozenset({"counsel-uuid"}),
    )
    assert result["requires_lawyer_judgment"] is False
    assert result["state"] == "LAWYER_DECISION_RECORDED"
    assert result["lawyer_decision"]["outcome"] == "DEADLINE_MODIFIED"
    assert result["score_impact"] == 0
    assert result["score_uplift"] == 0
    assert result["is_black_override"] is False
    assert result["automatic_clearance"] is False


def test_asserted_qualification_without_trusted_registry_keeps_review_open():
    result = agm_court_order_scoring_guard(
        _evidence(), _decision(), as_of=date(2026, 11, 28),
    )
    assert result["requires_lawyer_judgment"] is True
    assert result["state"] == "REQUIRES_LAWYER_JUDGMENT"
    assert result["score_impact"] == 0
    assert result["automatic_clearance"] is False


def test_unknown_or_unrecognized_order_status_is_rejected():
    with pytest.raises(ValueError, match="order_status"):
        from app.compliance.agm_court_order import AgmCourtOrderEvidence
        AgmCourtOrderEvidence.from_mapping(_evidence(order_status="CANCELLED"))


def test_order_date_is_not_inferred_from_today_or_upload_date():
    with pytest.raises(ValueError, match="order_date"):
        from app.compliance.agm_court_order import AgmCourtOrderEvidence
        AgmCourtOrderEvidence.from_mapping(_evidence(order_date=None))

@pytest.mark.parametrize("status", ["APPEALED", "STAYED", "SUPERSEDED"])
def test_order_status_with_pending_or_superseding_process_requires_reference(status):
    from app.compliance.agm_court_order import AgmCourtOrderEvidence

    with pytest.raises(ValueError, match="appeal_or_stay_reference"):
        AgmCourtOrderEvidence.from_mapping(_evidence(order_status=status))


def test_decision_without_independent_qualification_evidence_does_not_close_review():
    result = agm_court_order_scoring_guard(
        _evidence(),
        _decision(
            reviewer_qualification_verified=False,
            reviewer_qualification_evidence_ref="",
        ),
        as_of=date(2026, 11, 28),
    )
    assert result["requires_lawyer_judgment"] is True
    assert result["state"] == "REQUIRES_LAWYER_JUDGMENT"


def test_decision_for_another_order_cannot_close_this_order_review():
    result = agm_court_order_scoring_guard(
        _evidence(),
        _decision(case_number="Different Company Matter"),
        as_of=date(2026, 11, 28),
    )
    assert result["requires_lawyer_judgment"] is True
    assert result["state"] == "REQUIRES_LAWYER_JUDGMENT"


def test_expired_lawyer_decision_does_not_close_review():
    result = agm_court_order_scoring_guard(
        _evidence(),
        _decision(effective_until="2026-10-31"),
        as_of=date(2026, 11, 1),
    )
    assert result["requires_lawyer_judgment"] is True
    assert result["state"] == "REQUIRES_LAWYER_JUDGMENT"
    assert result["score_impact"] == 0
    assert result["automatic_clearance"] is False


def test_not_yet_effective_lawyer_decision_does_not_close_review():
    result = agm_court_order_scoring_guard(
        _evidence(),
        _decision(effective_from="2026-11-02"),
        as_of=date(2026, 11, 1),
    )
    assert result["requires_lawyer_judgment"] is True
    assert result["state"] == "REQUIRES_LAWYER_JUDGMENT"
    assert result["score_impact"] == 0
    assert result["automatic_clearance"] is False
