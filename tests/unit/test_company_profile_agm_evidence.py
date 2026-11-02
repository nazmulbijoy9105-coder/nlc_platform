from datetime import date
from types import SimpleNamespace

from app.services.company_service import _agm_profile_evidence
from app.rule_engine.engine import CompanyProfile, NLCRuleEngine


def test_missing_agm_record_keeps_attendance_and_auditor_status_unknown():
    evidence = _agm_profile_evidence(None)

    assert evidence == {
        "members_present_at_agm": None,
        "auditor_reappointed_at_agm": None,
        "agm_minutes_prepared": None,
        "notice_sent_date": None,
    }


def test_agm_profile_evidence_comes_from_the_latest_agm_record():
    meeting = SimpleNamespace(
        members_present=3,
        auditor_reappointed=False,
        minutes_prepared=True,
        notice_sent_date=date(2026, 1, 1),
    )

    evidence = _agm_profile_evidence(meeting)

    assert evidence["members_present_at_agm"] == 3
    assert evidence["auditor_reappointed_at_agm"] is False
    assert evidence["agm_minutes_prepared"] is True
    assert evidence["notice_sent_date"] == date(2026, 1, 1)


def test_default_zero_attendance_is_not_treated_as_verified_quorum_breach():
    meeting = SimpleNamespace(
        members_present=0,
        auditor_reappointed=True,
        minutes_prepared=False,
        notice_sent_date=None,
    )

    evidence = _agm_profile_evidence(meeting)

    assert evidence["members_present_at_agm"] is None
    assert evidence["auditor_reappointed_at_agm"] is True
    assert evidence["agm_minutes_prepared"] is None



def test_missing_agm_evidence_does_not_create_quorum_or_reappointment_flags():
    today = date.today()
    profile = CompanyProfile(
        company_id="agm-evidence-test",
        company_name="AGM Evidence Test Ltd",
        incorporation_date=date(today.year - 3, 1, 1),
        agm_count=1,
        last_agm_date=today.replace(day=1),
        agm_held_this_cycle=True,
        members_present_at_agm=None,
        auditor_reappointed_at_agm=None,
        agm_minutes_prepared=None,
        first_auditor_appointed=True,
        audit_complete=True,
        annual_return_filed=True,
    )

    result = NLCRuleEngine().evaluate(profile)
    fired_rule_ids = {flag.rule_id for flag in result.flags}

    assert "AGM-005" not in fired_rule_ids
    assert "AGM-006" not in fired_rule_ids
    assert "AUD-004" not in fired_rule_ids


def test_director_count_from_local_records_is_not_rjsc_verified():
    today = date.today()
    profile = CompanyProfile(
        company_id="director-verification-test",
        company_name="Director Verification Test Ltd",
        incorporation_date=date(today.year - 2, 1, 1),
        current_director_count=0,
        directors_verified=False,
        agm_count=1,
        annual_return_filed=True,
        first_auditor_appointed=True,
        audit_complete=True,
    )

    result = NLCRuleEngine().evaluate(profile)
    assert "INC-003" not in {flag.rule_id for flag in result.flags}


def test_verified_zero_directors_triggers_minimum_director_rule():
    today = date.today()
    profile = CompanyProfile(
        company_id="verified-director-test",
        company_name="Verified Director Test Ltd",
        incorporation_date=date(today.year - 2, 1, 1),
        current_director_count=0,
        directors_verified=True,
        agm_count=1,
        annual_return_filed=True,
        first_auditor_appointed=True,
        audit_complete=True,
    )

    result = NLCRuleEngine().evaluate(profile)
    assert "INC-003" in {flag.rule_id for flag in result.flags}
