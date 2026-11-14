from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.rule_engine.engine import CompanyProfile, NLCRuleEngine, RuleState, Severity
from app.services.company_service import _agm_profile_evidence


TODAY = date(2026, 7, 22)


def _flags(profile: CompanyProfile, today: date = TODAY):
    return NLCRuleEngine(today=today).evaluate(profile).flags


def _by_rule(flags, rule_id):
    return [flag for flag in flags if flag.rule_id == rule_id]


def test_sample_a_seven_member_private_company_without_verified_articles_is_unknown():
    profile = CompanyProfile(
        company_id="sample-a-7-members",
        company_name="Sample A Ltd",
        company_type="PRIVATE_LIMITED",
        member_count=7,
        agm_held_this_cycle=True,
        members_present_at_agm=2,
        agm_attendance_verified=True,
        agm_attendance_evidence_ref="fixture://agm-attendance",
        agm_quorum_basis_verified=False,
    )
    finding = _by_rule(_flags(profile), "AGM-005")
    assert len(finding) == 1
    assert finding[0].state == RuleState.UNKNOWN
    assert finding[0].severity == Severity.NOT_EVALUATED
    assert finding[0].score_impact == 0


def test_sample_a_verified_three_member_quorum_is_not_flagged():
    profile = CompanyProfile(
        company_id="sample-a-verified-quorum",
        company_name="Sample A Verified Ltd",
        company_type="PRIVATE_LIMITED",
        member_count=7,
        agm_held_this_cycle=True,
        members_present_at_agm=3,
        agm_attendance_verified=True,
        agm_attendance_evidence_ref="fixture://agm-attendance",
        agm_quorum_required=3,
        agm_quorum_basis_verified=True,
        agm_quorum_evidence_ref="fixture://certified-articles-review",
    )
    assert _by_rule(_flags(profile), "AGM-005") == []


def test_sample_b_unanimous_verified_short_notice_consent_is_not_defective():
    profile = CompanyProfile(
        company_id="sample-b-short-notice",
        company_name="Sample B Ltd",
        agm_scheduled_date=date(2026, 6, 30),
        notice_sent_date=date(2026, 6, 20),
        short_notice_consent_obtained=True,
        short_notice_consent_verified=True,
        short_notice_consent_evidence_ref="fixture://all-member-consents",
    )
    assert _by_rule(_flags(profile), "AGM-003") == []


def test_sample_c_verified_accidental_omission_does_not_create_notice_default():
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    reviewer = uuid4()
    served = SimpleNamespace(
        is_active=True,
        entitled_member_verified=True,
        entitlement_evidence_ref="fixture://member-register-1",
        entitlement_verified_at=now,
        entitlement_verified_by=reviewer,
        notice_delivery_status="SERVED",
        notice_sent_date=date(2026, 6, 1),
        notice_evidence_ref="fixture://notice-1",
        notice_verified=True,
        notice_verified_at=now,
        notice_verified_by=reviewer,
        consent_given=None,
        consent_evidence_ref=None,
        consent_verified=False,
        consent_verified_at=None,
        consent_verified_by=None,
        omission_accidental=None,
        omission_evidence_ref=None,
        omission_verified=False,
        omission_verified_at=None,
        omission_verified_by=None,
    )
    omitted = SimpleNamespace(
        **{
            **vars(served),
            "notice_delivery_status": "NOT_SERVED",
            "notice_sent_date": None,
            "notice_evidence_ref": "fixture://delivery-attempt",
            "omission_accidental": True,
            "omission_evidence_ref": "fixture://accidental-omission-record",
            "omission_verified": True,
            "omission_verified_at": now,
            "omission_verified_by": reviewer,
        }
    )
    meeting = SimpleNamespace(
        member_register_snapshot_verified=True,
        member_register_evidence_ref="fixture://member-register",
        member_register_verified_at=now,
        member_register_verified_by=reviewer,
        entitled_members_count=2,
        notice_evidence=[served, omitted],
    )
    evidence = _agm_profile_evidence(meeting)
    assert evidence["agm_notice_verified_absent"] is False
    assert evidence["notice_sent_date"] == date(2026, 6, 1)

    profile = CompanyProfile(
        company_id="sample-c-accidental-omission",
        company_name="Sample C Ltd",
        agm_scheduled_date=date(2026, 6, 30),
        **{
            key: value for key, value in evidence.items()
            if key in CompanyProfile.__dataclass_fields__
        },
    )
    assert _by_rule(_flags(profile), "AGM-003") == []
    assert _by_rule(_flags(profile), "AGM-004") == []


def test_sample_d_missing_minutes_upload_is_unknown_not_a_breach():
    profile = CompanyProfile(
        company_id="sample-d-minutes",
        company_name="Sample D Ltd",
        agm_held_this_cycle=True,
        agm_minutes_prepared=False,
    )
    finding = _by_rule(_flags(profile), "AGM-006")
    assert len(finding) == 1
    assert finding[0].state == RuleState.UNKNOWN
    assert finding[0].severity == Severity.NOT_EVALUATED
    assert finding[0].score_impact == 0


def test_sample_e_unverified_non_filing_is_unknown_not_a_default():
    profile = CompanyProfile(
        company_id="sample-e-unverified-return",
        company_name="Sample E Ltd",
        last_agm_date=date(2026, 6, 30),
        annual_return_filed=False,
    )
    finding = _by_rule(_flags(profile), "AR-001")
    assert len(finding) == 1
    assert finding[0].state == RuleState.UNKNOWN
    assert finding[0].severity == Severity.NOT_EVALUATED
    assert finding[0].score_impact == 0


def test_sample_e_verified_rjsc_filing_after_21_days_retains_late_default():
    profile = CompanyProfile(
        company_id="sample-e-late-filed-return",
        company_name="Sample E Late Filed Ltd",
        last_agm_date=date(2026, 6, 1),
        annual_return_filed=True,
        annual_return_filed_date=date(2026, 7, 1),
        annual_return_filing_status_verified=True,
        annual_return_filing_status_evidence_ref="fixture://rjsc-certified-filing-receipt",
        annual_return_filing_status_verified_at=date(2026, 7, 22),
        annual_return_filing_status_verified_by="fixture-reviewer",
    )
    finding = _by_rule(_flags(profile), "AR-001")
    assert len(finding) == 1
    assert finding[0].flag_code == "ANNUAL_RETURN_FILED_LATE"
    assert finding[0].state == RuleState.NON_COMPLIANT
    assert finding[0].eval_state == "VIOLATION"
    assert finding[0].detail["delay_days"] == 9


def test_sample_e_verified_rjsc_non_filing_after_21_days_is_a_candidate_default():
    profile = CompanyProfile(
        company_id="sample-e-verified-return",
        company_name="Sample E Verified Ltd",
        last_agm_date=date(2026, 6, 30),
        annual_return_filed=False,
        annual_return_filing_status_verified=True,
        annual_return_filing_status_evidence_ref="fixture://rjsc-certified-search",
        annual_return_filing_status_verified_at=date(2026, 7, 22),
        annual_return_filing_status_verified_by="fixture-reviewer",
    )
    finding = _by_rule(_flags(profile), "AR-001")
    assert len(finding) == 1
    assert finding[0].flag_code == "ANNUAL_RETURN_DEFAULT"
    assert finding[0].state == RuleState.NON_COMPLIANT
    assert finding[0].eval_state == "VIOLATION"


def test_sample_f_verified_first_auditor_appointment_after_one_calendar_month():
    profile = CompanyProfile(
        company_id="sample-f-first-auditor",
        company_name="Sample F Ltd",
        incorporation_date=date(2026, 1, 31),
        first_auditor_appointed=True,
        first_auditor_appointment_date=date(2026, 3, 2),
        first_auditor_appointment_verified=True,
        first_auditor_appointment_evidence_ref="fixture://board-appointment-resolution",
        first_auditor_appointment_verified_at=date(2026, 3, 3),
        first_auditor_appointment_verified_by="fixture-reviewer",
    )
    finding = _by_rule(_flags(profile, date(2026, 3, 10)), "AUD-001")
    assert len(finding) == 1
    assert finding[0].flag_code == "FIRST_AUDITOR_APPOINTED_LATE"
    assert finding[0].state == RuleState.NON_COMPLIANT
    assert finding[0].detail["deadline"] == "2026-02-28"
    assert finding[0].detail["calculation_method"] == "calendar_month"
