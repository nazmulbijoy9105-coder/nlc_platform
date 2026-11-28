"""Fail-closed evidence and review contract for AGM-related court orders.

A court order is evidence, not an automatic waiver, extension, or finding of
compliance. This module deliberately does not alter AGM deadlines or scores.
A separately recorded, scoped lawyer decision is required before downstream
rule logic may interpret the order.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping


ORDER_STATUSES = frozenset({"IN_FORCE", "APPEALED", "STAYED", "SUPERSEDED", "UNKNOWN"})
LAWYER_OUTCOMES = frozenset({
    "NO_EFFECT",
    "DEADLINE_MODIFIED",
    "RELIEF_GRANTED",
    "OTHER",
})


@dataclass(frozen=True)
class AgmCourtOrderEvidence:
    court_name: str
    case_number: str
    order_date: date
    operative_paragraphs: str
    affected_event: str
    statutory_power_claimed: str
    evidence_ref: str
    authenticated: bool
    verified_by: str | None
    verified_at: datetime | None
    order_status: str = "UNKNOWN"
    appeal_or_stay_reference: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AgmCourtOrderEvidence":
        """Parse a structured evidence payload without trusting truthy flags."""
        if not isinstance(value, Mapping):
            raise ValueError("court-order evidence must be an object")

        def required_text(key: str) -> str:
            raw = value.get(key)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"{key} is required")
            return raw.strip()

        raw_date = value.get("order_date")
        if isinstance(raw_date, datetime):
            raw_date = raw_date.date()
        if isinstance(raw_date, str):
            try:
                raw_date = date.fromisoformat(raw_date)
            except ValueError as exc:
                raise ValueError("order_date must be an ISO date") from exc
        if not isinstance(raw_date, date):
            raise ValueError("order_date is required")

        raw_verified_at = value.get("verified_at")
        if isinstance(raw_verified_at, str):
            try:
                raw_verified_at = datetime.fromisoformat(raw_verified_at)
            except ValueError as exc:
                raise ValueError("verified_at must be an ISO datetime") from exc
        if raw_verified_at is not None and not isinstance(raw_verified_at, datetime):
            raise ValueError("verified_at must be a datetime")

        status = value.get("order_status", "UNKNOWN")
        if status not in ORDER_STATUSES:
            raise ValueError("order_status is not recognized")
        appeal_or_stay_reference = value.get("appeal_or_stay_reference")
        appeal_or_stay_reference = (
            appeal_or_stay_reference.strip()
            if isinstance(appeal_or_stay_reference, str) else None
        )
        if status in {"APPEALED", "STAYED", "SUPERSEDED"} and not appeal_or_stay_reference:
            raise ValueError(
                "appeal_or_stay_reference is required for appealed, stayed or superseded orders"
            )

        authenticated = value.get("authenticated") is True
        verified_by = value.get("verified_by")
        verified_by = verified_by.strip() if isinstance(verified_by, str) else None
        return cls(
            court_name=required_text("court_name"),
            case_number=required_text("case_number"),
            order_date=raw_date,
            operative_paragraphs=required_text("operative_paragraphs"),
            affected_event=required_text("affected_event"),
            statutory_power_claimed=required_text("statutory_power_claimed"),
            evidence_ref=required_text("evidence_ref"),
            authenticated=authenticated,
            verified_by=verified_by or None,
            verified_at=raw_verified_at,
            order_status=status,
            appeal_or_stay_reference=appeal_or_stay_reference or None,
        )

    @property
    def evidence_verified(self) -> bool:
        return bool(
            self.authenticated
            and self.verified_by
            and self.verified_at
            and self.order_status != "UNKNOWN"
        )


@dataclass(frozen=True)
class AgmLawyerDecision:
    reviewer_id: str
    decided_at: datetime
    decision_reference: str
    reasoning: str
    affected_event: str
    outcome: str
    court_name: str
    case_number: str
    order_date: date
    evidence_ref: str
    effective_from: date
    effective_until: date | None
    reviewer_qualification_verified: bool
    reviewer_qualification_evidence_ref: str
    reviewer_qualification_verified_by: str
    reviewer_qualification_verified_at: datetime

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AgmLawyerDecision":
        if not isinstance(value, Mapping):
            raise ValueError("lawyer decision must be an object")
        text_fields = (
            "reviewer_id", "decision_reference", "reasoning",
            "affected_event", "outcome", "court_name", "case_number",
            "evidence_ref", "reviewer_qualification_evidence_ref",
            "reviewer_qualification_verified_by",
        )
        parsed: dict[str, str] = {}
        for key in text_fields:
            item = value.get(key)
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{key} is required")
            parsed[key] = item.strip()
        decided_at = value.get("decided_at")
        if isinstance(decided_at, str):
            try:
                decided_at = datetime.fromisoformat(decided_at)
            except ValueError as exc:
                raise ValueError("decided_at must be an ISO datetime") from exc
        if not isinstance(decided_at, datetime):
            raise ValueError("decided_at is required")
        if parsed["outcome"] not in LAWYER_OUTCOMES:
            raise ValueError("outcome is not recognized")

        def parse_date(key: str, *, optional: bool = False) -> date | None:
            raw = value.get(key)
            if raw is None and optional:
                return None
            if isinstance(raw, datetime):
                raw = raw.date()
            if isinstance(raw, str):
                try:
                    raw = date.fromisoformat(raw)
                except ValueError as exc:
                    raise ValueError(f"{key} must be an ISO date") from exc
            if not isinstance(raw, date):
                raise ValueError(f"{key} is required")
            return raw

        order_date = parse_date("order_date")
        effective_from = parse_date("effective_from")
        effective_until = parse_date("effective_until", optional=True)
        qualification_verified_at = value.get("reviewer_qualification_verified_at")
        if isinstance(qualification_verified_at, str):
            try:
                qualification_verified_at = datetime.fromisoformat(
                    qualification_verified_at
                )
            except ValueError as exc:
                raise ValueError(
                    "reviewer_qualification_verified_at must be an ISO datetime"
                ) from exc
        if not isinstance(qualification_verified_at, datetime):
            raise ValueError("reviewer_qualification_verified_at is required")
        if value.get("reviewer_qualification_verified") is not True:
            raise ValueError("qualified counsel verification is required")
        if effective_until is not None and effective_until < effective_from:
            raise ValueError("effective_until cannot precede effective_from")
        return cls(
            decided_at=decided_at,
            order_date=order_date,
            effective_from=effective_from,
            effective_until=effective_until,
            reviewer_qualification_verified=True,
            reviewer_qualification_verified_at=qualification_verified_at,
            **parsed,
        )


def agm_court_order_scoring_guard(
    evidence_payload: Mapping[str, Any] | None,
    lawyer_decision_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a safe routing disposition; never clear or score an AGM by itself.

    A valid lawyer decision only closes the *routing* requirement. The
    evaluator must still implement the decision's exact event scope and
    effective period in a separately reviewed change before changing score.
    """
    if evidence_payload is None:
        return {
            "present": False,
            "evidence_verified": False,
            "requires_lawyer_judgment": False,
            "state": "NO_ORDER_EVIDENCE",
            "eval_state": "UNKNOWN",
            "severity": "NOT_EVALUATED",
            "score_impact": 0,
            "is_black_override": False,
            "score_uplift": 0,
            "automatic_clearance": False,
        }

    try:
        evidence = AgmCourtOrderEvidence.from_mapping(evidence_payload)
    except (TypeError, ValueError) as exc:
        return {
            "present": True,
            "evidence_verified": False,
            "requires_lawyer_judgment": True,
            "state": "REQUIRES_LAWYER_JUDGMENT",
            "eval_state": "UNKNOWN",
            "severity": "NOT_EVALUATED",
            "score_impact": 0,
            "is_black_override": False,
            "score_uplift": 0,
            "automatic_clearance": False,
            "reason": f"INVALID_OR_INCOMPLETE_ORDER_EVIDENCE:{exc}",
        }

    decision: AgmLawyerDecision | None = None
    decision_error: str | None = None
    if lawyer_decision_payload is not None:
        try:
            decision = AgmLawyerDecision.from_mapping(lawyer_decision_payload)
        except (TypeError, ValueError) as exc:
            decision_error = str(exc)

    decision_matches_order = bool(
        decision is not None
        and decision.affected_event == evidence.affected_event
        and decision.court_name == evidence.court_name
        and decision.case_number == evidence.case_number
        and decision.order_date == evidence.order_date
        and decision.evidence_ref == evidence.evidence_ref
        and decision.effective_from <= decision.decided_at.date()
        and (
            decision.effective_until is None
            or decision.decided_at.date() <= decision.effective_until
        )
        and decision.reviewer_qualification_verified
        and decision.reviewer_qualification_evidence_ref
        and decision.reviewer_qualification_verified_by != decision.reviewer_id
    )
    if (
        not evidence.evidence_verified
        or decision is None
        or not decision_matches_order
    ):
        reason = (
            "ORDER_EVIDENCE_NOT_VERIFIED"
            if not evidence.evidence_verified
            else "SCOPED_LAWYER_DECISION_REQUIRED"
        )
        if decision_error:
            reason = f"INVALID_LAWYER_DECISION:{decision_error}"
        return {
            "present": True,
            "evidence_verified": evidence.evidence_verified,
            "requires_lawyer_judgment": True,
            "state": "REQUIRES_LAWYER_JUDGMENT",
            "eval_state": "UNKNOWN",
            "severity": "NOT_EVALUATED",
            "score_impact": 0,
            "is_black_override": False,
            "score_uplift": 0,
            "automatic_clearance": False,
            "reason": reason,
        }

    return {
        "present": True,
        "evidence_verified": True,
        "requires_lawyer_judgment": False,
        "state": "LAWYER_DECISION_RECORDED",
        "eval_state": "UNKNOWN",
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "is_black_override": False,
        "score_uplift": 0,
        "automatic_clearance": False,
        "lawyer_decision": {
            "reviewer_id": decision.reviewer_id,
            "decided_at": decision.decided_at.isoformat(),
            "decision_reference": decision.decision_reference,
            "reasoning": decision.reasoning,
            "affected_event": decision.affected_event,
            "outcome": decision.outcome,
            "court_name": decision.court_name,
            "case_number": decision.case_number,
            "order_date": decision.order_date.isoformat(),
            "evidence_ref": decision.evidence_ref,
            "effective_from": decision.effective_from.isoformat(),
            "effective_until": (
                decision.effective_until.isoformat()
                if decision.effective_until else None
            ),
            "reviewer_qualification_verified": decision.reviewer_qualification_verified,
            "reviewer_qualification_evidence_ref": decision.reviewer_qualification_evidence_ref,
            "reviewer_qualification_verified_by": decision.reviewer_qualification_verified_by,
            "reviewer_qualification_verified_at": decision.reviewer_qualification_verified_at.isoformat(),
        },
        "reason": "DECISION_RECORDED_REQUIRES_RULE_SPECIFIC_IMPLEMENTATION",
    }
