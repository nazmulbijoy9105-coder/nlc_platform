"""Keep every canonical rule explicitly classified in the citation audit.

This is a technical inventory guard only. Candidate anchors, out-of-scope
statutes and review-only dispositions are not independent counsel approval.
"""
from __future__ import annotations

import runpy
from pathlib import Path

from app.rule_engine.engine import VERIFIED_RULE_IDS
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY


def test_all_85_canonical_ids_have_exactly_one_citation_audit_disposition() -> None:
    audit = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "tools" / "legal_citation_audit.py")
    )
    canonical = set(STATUTORY_RULE_REGISTRY)
    expected = set(audit["EXPECTED"])
    out_of_scope = set(audit["OUT_OF_SCOPE"])
    review_only = set(audit["REVIEW_ONLY"])

    assert len(canonical) == 85
    assert expected.isdisjoint(out_of_scope)
    assert expected.isdisjoint(review_only)
    assert out_of_scope.isdisjoint(review_only)
    assert expected | out_of_scope | review_only == canonical


def test_non_candidate_dispositions_include_explicit_review_rationales() -> None:
    audit = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "tools" / "legal_citation_audit.py")
    )
    assert audit["OUT_OF_SCOPE"]
    assert all(
        isinstance(scope, str) and scope.strip()
        for scope in audit["OUT_OF_SCOPE"].values()
    )
    assert audit["REVIEW_ONLY"]
    assert all(
        isinstance(item, tuple)
        and len(item) == 2
        and all(isinstance(value, str) and value.strip() for value in item)
        for item in audit["REVIEW_ONLY"].values()
    )


def test_citation_audit_dispositions_never_grant_independent_counsel_approval() -> None:
    # Technical candidate-anchor matches must not populate the counsel allowlist.
    assert VERIFIED_RULE_IDS == frozenset()
