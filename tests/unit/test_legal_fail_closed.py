"""Regression tests for unresolved tax and labour applicability.

These tests ensure profile booleans cannot become statutory violations before
identity, legal applicability and primary evidence are verified.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
ENGINE = (ROOT / "app" / "rule_engine" / "engine.py").read_text(encoding="utf-8")
SEED = (ROOT / "scripts" / "seed_rules.py").read_text(encoding="utf-8")


def _block(pattern: str, next_pattern: str) -> str:
    match = re.search(pattern + r"(.*?)" + next_pattern, ENGINE, re.S)
    assert match, f"could not locate guarded block: {pattern}"
    return match.group(1)


def test_tin_profile_boolean_is_review_only():
    block = _block(r"if c\.tin_obtained is False:", r"\n        if c\.vat_registered is False")
    assert "severity=Severity.NOT_EVALUATED" in block
    assert "score_impact=0" in block
    assert 'state=RuleState.UNKNOWN' in block
    assert 'eval_state="UNKNOWN"' in block
    assert "sections 166, 261 and 264" in block
    assert "severity=Severity.RED" not in block


def test_advance_tax_remains_review_only_and_uses_2026_threshold():
    block = _block(r"if c\.tin_obtained:", r"\n        if c\.vat_registered is True")
    assert "severity=Severity.NOT_EVALUATED" in block
    assert "score_impact=0" in block
    assert 'eval_state="UNKNOWN"' in block
    assert "Finance Act 2026" in block
    assert "BDT 10 lakh" in block
    assert "BDT 6 lakh" in block


def test_labour_licence_findings_remain_review_only():
    start = ENGINE.index('rule_id="LBR-001"')
    end = ENGINE.index("MODULE 14", start)
    block = ENGINE[start:end]
    assert block.count("severity=Severity.NOT_EVALUATED") >= 2
    assert block.count("score_impact=0") >= 2
    assert "Government direction" in block
    assert "Section 326" in block


def test_labour_court_order_boolean_is_review_only():
    block = _block(r"if c\.labour_court_order_pending:", r"\n\n    # MODULE 14")
    assert "severity=Severity.NOT_EVALUATED" in block
    assert "score_impact=0" in block
    assert 'state=RuleState.UNKNOWN' in block
    assert 'eval_state="UNKNOWN"' in block
    assert "certified order" in block


def test_seed_defaults_match_fail_closed_tax_and_labour_states():
    for rule_id in ("TAX-001", "TAX-004", "LBR-001", "LBR-002", "LBR-003", "VAT-002", "VAT-003"):
        line = next(x for x in SEED.splitlines() if f'"rule_id": "{rule_id}"' in x)
        assert '"default_severity": "NOT_EVALUATED"' in line, rule_id
        assert '"score_impact": 0' in line, rule_id


def test_legal_scoring_allowlist_stays_empty():
    assert re.search(r"VERIFIED_RULE_IDS:\s*frozenset\[str\]\s*=\s*frozenset\(\)", ENGINE)
    assert re.search(r"LEGAL_SCORE_RELEASED:\s*bool\s*=\s*False", ENGINE)
