"""BSEC Corporate Governance Code review taxonomy.

The Code is not reduced to binary profile booleans. This taxonomy separates
documentary existence/authenticity checks from legal/professional judgments.
It is a review-workflow catalogue only: no item produces a statutory breach,
score deduction or certification.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GovernanceReviewClass(StrEnum):
    DOCUMENTARY = "DOCUMENTARY"
    JUDGMENT = "JUDGMENT"


@dataclass(frozen=True)
class GovernanceReviewRule:
    rule_id: str
    condition: str
    review_class: GovernanceReviewClass
    question: str
    minimum_evidence: tuple[str, ...]
    decision_boundary: str


GOVERNANCE_CODE_REVIEW_RULES: tuple[GovernanceReviewRule, ...] = (
    GovernanceReviewRule(
        "BSEC-DOC-001", "Condition 1(1), 1(2)(c)-(e)",
        GovernanceReviewClass.DOCUMENTARY,
        "Verify Board size, appointment dates, shareholder approval and vacancy timeline.",
        ("RJSC director list", "Board appointment resolutions", "AGM minutes", "effective-date history"),
        "Document existence and dates can be checked; director eligibility and legal effect remain separate judgment questions.",
    ),
    GovernanceReviewRule(
        "BSEC-JDG-001", "Condition 1(2)-(3)",
        GovernanceReviewClass.JUDGMENT,
        "Determine independent-director status, eligibility, independence, experience and ratio.",
        ("director declarations", "shareholding and related-party records", "employment history", "qualification and experience evidence"),
        "Do not infer independence from a database flag; legal criteria and connected-person facts require professional assessment.",
    ),
    GovernanceReviewRule(
        "BSEC-DOC-002", "Condition 2",
        GovernanceReviewClass.DOCUMENTARY,
        "Verify the holding/subsidiary relationship and required cross-board records.",
        ("certified group structure", "holding-company and subsidiary Board minutes", "subsidiary director appointment records"),
        "The relationship and record trail must be effective-dated; applicability is not inferred from a company name.",
    ),
    GovernanceReviewRule(
        "BSEC-JDG-002", "Condition 2",
        GovernanceReviewClass.JUDGMENT,
        "Assess whether holding-company governance requirements attach to the subsidiary and whether the prescribed oversight occurred.",
        ("verified group relationship", "relevant Articles", "holding-company committee records"),
        "Requires scope interpretation and review of actual governance substance; not a mechanical boolean.",
    ),
    GovernanceReviewRule(
        "BSEC-DOC-003", "Conditions 4 and 5(1)-(4)",
        GovernanceReviewClass.DOCUMENTARY,
        "Verify Audit Committee constitution, written terms, member appointments, vacancy dates and meeting minutes.",
        ("Board resolutions", "committee terms of reference", "member register", "meeting notices and signed minutes"),
        "The presence of documents is verifiable; their legal sufficiency and the committee's actual performance are not established by presence alone.",
    ),
    GovernanceReviewRule(
        "BSEC-JDG-003", "Condition 5(2)-(4)",
        GovernanceReviewClass.JUDGMENT,
        "Assess member independence, financial literacy, expertise, chairperson eligibility and quorum.",
        ("member profiles", "qualification evidence", "experience records", "attendance and quorum records"),
        "Eligibility and quorum must be assessed against the operative Code version and actual meeting facts.",
    ),
    GovernanceReviewRule(
        "BSEC-DOC-004", "Condition 5(5)-(7)",
        GovernanceReviewClass.DOCUMENTARY,
        "Verify audit committee reporting, annual report disclosure and review records for annual, quarterly and half-yearly statements.",
        ("committee activity report", "annual report", "financial statement versions", "Board submission dates", "auditor meeting minutes"),
        "Record provenance and sequence; missing upload is not proof that a record was never created.",
    ),
    GovernanceReviewRule(
        "BSEC-JDG-004", "Condition 5(5)-(7)",
        GovernanceReviewClass.JUDGMENT,
        "Assess whether financial reporting oversight, audit challenge and escalation were substantively adequate.",
        ("financial statements", "audit findings", "management responses", "committee minutes", "Board actions"),
        "Requires professional evaluation of substance, materiality and adequacy; do not automate a legal conclusion.",
    ),
    GovernanceReviewRule(
        "BSEC-DOC-005", "Condition 9",
        GovernanceReviewClass.DOCUMENTARY,
        "Verify annual compliance certificate, eligible certifier, AGM appointment and annual-report disclosure.",
        ("signed compliance certificate", "certifier credentials", "AGM appointment record", "annual report"),
        "Authenticity, date and appointment evidence are document checks; legal eligibility and exceptions still require review.",
    ),
)


def governance_review_rules(
    *,
    bsec_listed: bool | None,
    listing_verified: bool,
    subsidiary_of_listed_issuer: bool | None = None,
    subsidiary_scope_verified: bool = False,
) -> tuple[GovernanceReviewRule, ...]:
    """Return review tasks only when issuer or subsidiary scope is established."""
    if bsec_listed is True and listing_verified:
        return GOVERNANCE_CODE_REVIEW_RULES
    if (
        subsidiary_of_listed_issuer is True
        and subsidiary_scope_verified
    ):
        return tuple(
            rule for rule in GOVERNANCE_CODE_REVIEW_RULES
            if rule.condition.startswith("Condition 2")
        )
    return ()
