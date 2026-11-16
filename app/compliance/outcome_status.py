"""Fail-closed customer-facing compliance outcome derivation.

Flag lifecycle (ACTIVE/RESOLVED/ACKNOWLEDGED) is deliberately separate from
legal evaluation outcome. An open finding is not a positive compliance result.
"""
from __future__ import annotations


def _value(value) -> str:
    return str(getattr(value, "value", value) or "").strip().upper()


def derive_compliance_outcome(flag, *, counsel_verified_rule: bool) -> str:
    """Return a conservative outcome; never infer PASS from lifecycle status.

    Positive COMPLIANT requires an explicit engine COMPLIANT state, an explicit
    passing evaluation state, applicable/unresolved finding context, and an
    independently counsel-verified rule identifier.
    """
    state = _value(getattr(flag, "state", None))
    evaluation = _value(getattr(flag, "eval_state", None))

    if getattr(flag, "resolved", False):
        return "RESOLVED"
    applicability = getattr(flag, "conditional_applies", True)
    if applicability is False:
        return "NOT_APPLICABLE"
    if applicability is None:
        return "REVIEW_REQUIRED"

    tokens = {state, evaluation}
    if tokens & {"NOT_AUTHORISED", "NOT_AUTHORIZED", "UNAUTHORISED", "UNAUTHORIZED"}:
        return "NOT_AUTHORISED"
    if tokens & {"FAILED", "FAIL"}:
        return "FAILED"
    if tokens & {"NOT_PASS", "NOT_PASSED"}:
        return "NOT_PASS"
    if state == "NON_COMPLIANT" and evaluation in {"VIOLATION", "NON_COMPLIANT", "FAILED", "FAIL"}:
        return "NON_COMPLIANT"
    if state == "VERIFIED_ABSENT" and evaluation in {"VIOLATION", "NON_COMPLIANT", "FAILED", "FAIL"}:
        return "NON_COMPLIANT"
    if state == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if state == "COMPLIANT" and evaluation in {"COMPLIANT", "PASS", "PASSED"}:
        return "COMPLIANT" if counsel_verified_rule else "REVIEW_REQUIRED"
    if state in {"UNKNOWN", "CONTRADICTORY", "DISPUTED", "REQUIRES_LAWYER_JUDGMENT"}:
        return "REVIEW_REQUIRED"
    if evaluation in {"UNKNOWN", "NOT_EVALUATED", "PENDING", "REVIEW_REQUIRED"}:
        return "REVIEW_REQUIRED"
    return "REVIEW_REQUIRED"
