from datetime import date

import pytest

from app.compliance.obligation_state import (
    Applicability, ApplicabilityResolutionTask, EvidenceState, FactProvenance,
    FactTrustLevel, LegalRuleSnapshot, ObligationFinding, ObligationState,
    ObligationStatus,
)


def test_applicability_evidence_and_status_are_orthogonal():
    state = ObligationState(
        Applicability.APPLIES, EvidenceState.NOT_PROVIDED, ObligationStatus.OVERDUE,
        statutory_deadline=date(2026, 10, 31),
    )
    assert state.applicability is Applicability.APPLIES
    assert state.evidence is EvidenceState.NOT_PROVIDED
    assert state.status is ObligationStatus.OVERDUE


def test_filed_late_is_distinct_and_requires_verified_receipt():
    state = ObligationState(
        Applicability.APPLIES, EvidenceState.VERIFIED_PRESENT, ObligationStatus.FILED_LATE,
        statutory_deadline=date(2026, 10, 31), filed_on=date(2026, 11, 5),
    )
    assert state.status is ObligationStatus.FILED_LATE
    with pytest.raises(ValueError, match="after the statutory deadline"):
        ObligationState(
            Applicability.APPLIES, EvidenceState.VERIFIED_PRESENT, ObligationStatus.FILED_LATE,
            statutory_deadline=date(2026, 10, 31), filed_on=date(2026, 10, 30),
        )
    with pytest.raises(ValueError, match="verified filing evidence"):
        ObligationState(
            Applicability.APPLIES, EvidenceState.NOT_PROVIDED, ObligationStatus.FILED_LATE,
            statutory_deadline=date(2026, 10, 31), filed_on=date(2026, 11, 5),
        )


def test_verified_absence_requires_named_source_and_check_date():
    with pytest.raises(ValueError, match="named source"):
        ObligationState(
            Applicability.APPLIES, EvidenceState.VERIFIED_ABSENT, ObligationStatus.OVERDUE,
            evidence_checked_on=date(2026, 11, 1),
        )
    with pytest.raises(ValueError, match="verification date"):
        ObligationState(
            Applicability.APPLIES, EvidenceState.VERIFIED_ABSENT, ObligationStatus.OVERDUE,
            evidence_source="RJSC filing receipt search",
        )


def test_unknown_applicability_has_owned_expiring_resolution_task():
    task = ApplicabilityResolutionTask(
        "tax-return-2026", "company-admin-1", date(2026, 11, 20),
        "tax_profile", "tin_and_return_receipts", 14,
    )
    assert task.owner_id == "company-admin-1"
    assert task.escalation_after_days == 14


def test_legal_rule_reuses_verification_gate_and_effective_dates():
    rule = LegalRuleSnapshot(
        "AGM-001", "2.1", "bd-company-law-2026.11",
        date(2024, 7, 1), date(2026, 7, 1), "Companies Act 1994, s.81",
        "VERIFIED", "legal-reviewer-1", date(2026, 6, 1),
    )
    assert rule.may_generate_findings
    assert rule.is_in_force_on(date(2025, 12, 31))
    assert not rule.is_in_force_on(date(2026, 7, 1))


def test_pending_rule_cannot_generate_findings():
    rule = LegalRuleSnapshot(
        "AR-001", "1.0", "bd-company-law-2026.11",
        date(1994, 1, 1), None, "Companies Act 1994, s.36",
        "PENDING", None, None,
    )
    assert not rule.may_generate_findings


def test_finding_pins_versions_legal_date_and_fact_provenance():
    fact = FactProvenance(
        "financial_year_end", FactTrustLevel.DOCUMENT_BACKED,
        "uploaded:audited-accounts-2025.pdf", date(2026, 3, 1),
    )
    finding = ObligationFinding(
        "annual-return-2025", "AR-001", "1.0", "bd-company-law-2026.11",
        date(2025, 12, 31), (fact,),
        ObligationState(
            Applicability.APPLIES, EvidenceState.NOT_PROVIDED, ObligationStatus.OVERDUE,
            statutory_deadline=date(2026, 1, 21),
        ),
    )
    assert finding.catalogue_version == "bd-company-law-2026.11"
    assert not finding.contains_unverified_facts


def test_user_asserted_fact_is_flagged_on_finding():
    fact = FactProvenance(
        "has_employees", FactTrustLevel.USER_ASSERTED,
        "company-onboarding-questionnaire", date(2026, 11, 11),
    )
    finding = ObligationFinding(
        "labour-registration", "LBR-001", "1.0", "bd-company-law-2026.11",
        date(2026, 11, 11), (fact,),
        ObligationState(
            Applicability.UNKNOWN, EvidenceState.NOT_PROVIDED, ObligationStatus.NOT_YET_DUE,
        ),
    )
    assert finding.contains_unverified_facts
