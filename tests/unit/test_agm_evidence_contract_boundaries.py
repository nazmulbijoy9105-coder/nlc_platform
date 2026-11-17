from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.rule_engine.engine import ComplianceFlag, RevenueTier, RuleState, Severity, NLCRuleEngine
from app.services.company_service import _agm_profile_evidence


def _notice_row(**overrides):
    values = {
        "is_active": True,
        "entitled_member_verified": True,
        "entitlement_evidence_ref": "register://member",
        "entitlement_verified_at": datetime.now(timezone.utc),
        "entitlement_verified_by": uuid4(),
        "notice_delivery_status": "SERVED",
        "notice_sent_date": date(2026, 1, 1),
        "notice_evidence_ref": "dispatch://notice",
        "notice_verified": True,
        "notice_verified_at": datetime.now(timezone.utc),
        "notice_verified_by": uuid4(),
        "consent_given": True,
        "consent_received_date": date(2025, 12, 20),
        "consent_evidence_ref": "consent://written",
        "consent_verified": True,
        "consent_verified_at": datetime.now(timezone.utc),
        "consent_verified_by": uuid4(),
        "omission_accidental": None,
        "omission_evidence_ref": None,
        "omission_verified": False,
        "omission_verified_at": None,
        "omission_verified_by": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _agm(**overrides):
    values = {
        "agm_held": True,
        "agm_held_verified": False,
        "agm_held_evidence_ref": None,
        "agm_held_verified_at": None,
        "agm_held_verified_by": None,
        "members_present_verified": False,
        "members_present_evidence_ref": None,
        "members_present_verified_at": None,
        "members_present_verified_by": None,
        "quorum_required_verified": False,
        "quorum_evidence_ref": None,
        "quorum_verified_at": None,
        "quorum_verified_by": None,
        "quorum_required": None,
        "quorum_met": None,
        "auditor_reappointment_verified": False,
        "auditor_reappointment_evidence_ref": None,
        "auditor_reappointment_verified_at": None,
        "auditor_reappointment_verified_by": None,
        "member_register_snapshot_verified": False,
        "member_register_evidence_ref": None,
        "member_register_verified_at": None,
        "member_register_verified_by": None,
        "entitled_members_count": None,
        "notice_evidence": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _verified_roster(rows, count):
    return _agm(
        member_register_snapshot_verified=True,
        member_register_evidence_ref="register://snapshot",
        member_register_verified_at=datetime.now(timezone.utc),
        member_register_verified_by=uuid4(),
        entitled_members_count=count,
        notice_evidence=rows,
    )


def test_calendar_month_arithmetic_clamps_month_end_and_leap_year():
    assert NLCRuleEngine._add_months(date(2024, 1, 31), 18) == date(2025, 7, 31)
    assert NLCRuleEngine._add_months(date(2023, 8, 31), 18) == date(2025, 2, 28)
    assert NLCRuleEngine._add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)


def test_short_notice_requires_written_consent_from_every_entitled_member():
    rows = [
        _notice_row(consent_evidence_ref="consent://member-1"),
        _notice_row(consent_evidence_ref="consent://member-2"),
    ]
    evidence = _agm_profile_evidence(_verified_roster(rows, 2))
    assert evidence["short_notice_consent_verified"] is True
    assert evidence["short_notice_consent_obtained"] is True

    rows[1] = _notice_row(consent_given=False, consent_evidence_ref="consent://member-2")
    evidence = _agm_profile_evidence(_verified_roster(rows, 2))
    assert evidence["short_notice_consent_verified"] is True
    assert evidence["short_notice_consent_obtained"] is False


def test_partial_roster_or_unverified_consent_remains_unknown_not_false():
    rows = [
        _notice_row(),
        _notice_row(consent_verified=False, consent_evidence_ref=None),
    ]
    evidence = _agm_profile_evidence(_verified_roster(rows, 3))
    assert evidence["short_notice_consent_verified"] is False
    assert evidence["short_notice_consent_obtained"] is None


def test_verified_accidental_omission_is_member_specific_exception():
    served = _notice_row(notice_sent_date=date(2026, 1, 2))
    omitted = _notice_row(
        notice_delivery_status="NOT_SERVED",
        notice_sent_date=None,
        omission_accidental=True,
        omission_evidence_ref="minutes://recorded-omission",
        omission_verified=True,
        omission_verified_at=datetime.now(timezone.utc),
        omission_verified_by=uuid4(),
    )
    evidence = _agm_profile_evidence(_verified_roster([served, omitted], 2))
    assert evidence["notice_sent_date"] == date(2026, 1, 2)
    assert evidence["agm_notice_verified_absent"] is False


def test_unverified_accidental_omission_does_not_create_exception():
    served = _notice_row(notice_sent_date=date(2026, 1, 2))
    omitted = _notice_row(
        notice_delivery_status="NOT_SERVED",
        notice_sent_date=None,
        omission_accidental=True,
        omission_evidence_ref="minutes://unverified",
        omission_verified=False,
        omission_verified_at=None,
        omission_verified_by=None,
    )
    evidence = _agm_profile_evidence(_verified_roster([served, omitted], 2))
    assert evidence["notice_sent_date"] is None
    assert evidence["agm_notice_verified_absent"] is True


def test_articles_quorum_requires_verified_clause_and_provenance():
    agm = _agm(
        quorum_required=3,
        quorum_required_verified=True,
        quorum_evidence_ref=None,
        quorum_verified_at=datetime.now(timezone.utc),
        quorum_verified_by=uuid4(),
    )
    evidence = _agm_profile_evidence(agm)
    assert evidence["agm_quorum_required"] is None
    assert evidence["agm_quorum_basis_verified"] is False

    agm.quorum_evidence_ref = "articles://certified-current-articles#quorum"
    evidence = _agm_profile_evidence(agm)
    assert evidence["agm_quorum_required"] == 3
    assert evidence["agm_quorum_basis_verified"] is True


def test_unknown_rule_state_cannot_create_score_impact():
    flag = ComplianceFlag(
        rule_id="AGM-005",
        flag_code="AGM_QUORUM_BASIS_UNKNOWN",
        severity=Severity.NOT_EVALUATED,
        score_impact=15,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="Quorum basis is unknown",
        statutory_basis="Section 85(2)(b), Companies Act 1994",
        state=RuleState.UNKNOWN,
        eval_state="UNKNOWN",
    )
    assert flag.score_impact == 0
