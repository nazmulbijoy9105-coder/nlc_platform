from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.company_service import _agm_profile_evidence


def _verified_row(**overrides):
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
        "short_notice_consent_verified": False,
        "short_notice_consent_evidence_ref": None,
        "short_notice_consent_verified_at": None,
        "short_notice_consent_verified_by": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_raw_agm_held_boolean_is_not_a_verified_current_cycle_fact():
    evidence = _agm_profile_evidence(_agm(agm_held=True))
    assert evidence["agm_held_this_cycle"] is None
    assert evidence["agm_held_this_cycle_verified"] is False


def test_verified_held_status_requires_evidence_actor_and_timestamp():
    evidence = _agm_profile_evidence(_agm(
        agm_held=True,
        agm_held_verified=True,
        agm_held_evidence_ref="minutes://agm-2026",
        agm_held_verified_at=datetime.now(timezone.utc),
        agm_held_verified_by=uuid4(),
    ))
    assert evidence["agm_held_this_cycle"] is True
    assert evidence["agm_held_this_cycle_verified"] is True


def test_notice_and_short_notice_consent_require_complete_entitled_member_roster():
    first = _verified_row(notice_sent_date=date(2026, 1, 1))
    second = _verified_row(notice_sent_date=date(2026, 1, 3))
    agm = _agm(
        member_register_snapshot_verified=True,
        member_register_evidence_ref="register://snapshot",
        member_register_verified_at=datetime.now(timezone.utc),
        member_register_verified_by=uuid4(),
        entitled_members_count=2,
        notice_evidence=[first, second],
    )
    evidence = _agm_profile_evidence(agm)
    assert evidence["notice_sent_date"] == date(2026, 1, 3)
    assert evidence["short_notice_consent_verified"] is True
    assert evidence["short_notice_consent_obtained"] is True

    agm.entitled_members_count = 3
    incomplete = _agm_profile_evidence(agm)
    assert incomplete["notice_sent_date"] is None
    assert incomplete["short_notice_consent_verified"] is False
    assert incomplete["short_notice_consent_obtained"] is None


def test_section_85_accidental_omission_is_not_treated_as_notice_default():
    served = _verified_row(notice_sent_date=date(2026, 1, 2))
    accidental = _verified_row(
        recipient_key="member-2",
        notice_delivery_status="NOT_SERVED",
        notice_sent_date=None,
        omission_accidental=True,
        omission_evidence_ref="minutes://accidental-omission",
        omission_verified=True,
        omission_verified_at=datetime.now(timezone.utc),
        omission_verified_by=uuid4(),
    )
    agm = _agm(
        member_register_snapshot_verified=True,
        member_register_evidence_ref="register://snapshot",
        member_register_verified_at=datetime.now(timezone.utc),
        member_register_verified_by=uuid4(),
        entitled_members_count=2,
        notice_evidence=[served, accidental],
    )
    evidence = _agm_profile_evidence(agm)
    assert evidence["notice_sent_date"] == date(2026, 1, 2)
    assert evidence["agm_notice_verified_absent"] is False
