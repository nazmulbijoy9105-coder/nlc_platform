from datetime import date
from types import SimpleNamespace

from app.services.company_service import _agm_profile_evidence


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
    assert evidence["agm_minutes_prepared"] is False
