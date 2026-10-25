#!/usr/bin/env python3
"""Phase 1 — Quick wins fix script.

Applies 4 low-risk, high-signal fixes to the NLC platform repo:

Fix 1 (HIST-OR-TRUE): Remove `or True` from tests/unit/test_rule_engine.py:69
    Before:  assert hasattr(output.score_breakdown, "score_hash") or True  # hash in persistence layer
    After:   assert hasattr(output.score_breakdown, "score_hash")

Fix 2 (RULE-003a): Add VERIFIED_ABSENT to RuleState enum in two files:
    - app/rule_engine/engine.py
    - canonical_architecture/statutory_rules.py

Fix 3 (TR-007 / TR-011): Fix Form 117 None + bool() collapse in
    app/services/company_service.py around line 350-354.
    Replace bool(t.board_approval) with explicit 3-valued logic.
    Replace form_117_filed=None,  # TODO: with proper UNKNOWN handling.

Fix 4 (RJSC-005): Add VALID_TRANSITIONS map to app/models/filings.py.

Idempotent: running twice produces no further changes.

Run from repo root: python phase1_quick_wins.py
"""
from pathlib import Path
import re


# ---------- Fix 1: HIST-OR-TRUE ----------
def fix_1_hist_or_true():
    p = Path("tests/unit/test_rule_engine.py")
    if not p.exists():
        print("[SKIP] Fix 1: tests/unit/test_rule_engine.py not found")
        return False
    text = p.read_text(encoding="utf-8")
    original = text
    # Match: `or True  # hash in persistence layer` (with optional whitespace)
    pattern = r"\s+or\s+True\s*#\s*hash in persistence layer"
    new_text = re.sub(pattern, "", text)
    if new_text == original:
        # already fixed or pattern not found
        if "or True" in text and "score_hash" in text:
            print(f"[WARN] Fix 1: pattern not matched in {p.name}, but `or True` still present")
            return False
        print(f"[--] Fix 1: no change needed in {p.name}")
        return True
    p.write_text(new_text, encoding="utf-8")
    print(f"[OK ] Fix 1: removed `or True` from {p.name}:69")
    return True


# ---------- Fix 2: RULE-003a — add VERIFIED_ABSENT to RuleState enum ----------
def fix_2_rule_state_enum():
    targets = [
        Path("app/rule_engine/engine.py"),
        Path("canonical_architecture/statutory_rules.py"),
    ]
    success = True
    for p in targets:
        if not p.exists():
            print(f"[SKIP] Fix 2: {p} not found")
            success = False
            continue
        text = p.read_text(encoding="utf-8")
        if "VERIFIED_ABSENT" in text:
            print(f"[--] Fix 2: VERIFIED_ABSENT already present in {p.name}")
            continue
        # Find the RuleState class definition and add VERIFIED_ABSENT member
        # Pattern: class RuleState(...):\n    COMPLIANT = "COMPLIANT"\n    ...
        # Or:    class RuleState(Enum):\n    UNKNOWN = "UNKNOWN"\n    ...
        # We look for the class and add the new member after the last enum member.

        # Approach 1: insert VERIFIED_ABSENT right after NON_COMPLIANT line
        # Pattern: NON_COMPLIANT = "NON_COMPLIANT"  (possibly with comment)
        pattern = re.compile(
            r'^(\s*)(NON_COMPLIANT\s*=\s*["\']NON_COMPLIANT["\'])\s*(#[^\n]*)?$',
            re.MULTILINE,
        )
        m = pattern.search(text)
        if m:
            indent = m.group(1)
            new_line = f"\n{indent}VERIFIED_ABSENT = \"VERIFIED_ABSENT\"  # confirmed absence via verified external source"
            text = text[:m.end()] + new_line + text[m.end():]
            p.write_text(text, encoding="utf-8")
            print(f"[OK ] Fix 2: added VERIFIED_ABSENT to RuleState enum in {p.name}")
        else:
            # Fallback: try UNKNOWN
            pattern2 = re.compile(
                r'^(\s*)(UNKNOWN\s*=\s*["\']UNKNOWN["\'])\s*(#[^\n]*)?$',
                re.MULTILINE,
            )
            m = pattern2.search(text)
            if m:
                indent = m.group(1)
                new_line = f"\n{indent}VERIFIED_ABSENT = \"VERIFIED_ABSENT\"  # confirmed absence via verified external source"
                text = text[:m.end()] + new_line + text[m.end():]
                p.write_text(text, encoding="utf-8")
                print(f"[OK ] Fix 2: added VERIFIED_ABSENT after UNKNOWN in {p.name}")
            else:
                print(f"[WARN] Fix 2: could not find NON_COMPLIANT or UNKNOWN in RuleState enum in {p.name}")
                success = False
    return success


# ---------- Fix 3: TR-007 / TR-011 — Form 117 + bool() collapse ----------
def fix_3_company_service():
    p = Path("app/services/company_service.py")
    if not p.exists():
        print("[SKIP] Fix 3: app/services/company_service.py not found")
        return False
    text = p.read_text(encoding="utf-8")
    original = text
    changes_made = []

    # Replace bool(t.board_approval) with 3-valued logic helper
    # The verifier found `bool(t.board_approval)` on lines 350, 351
    # Replace with: None if t.board_approval is None else bool(t.board_approval)
    # But better: just use the value directly — the field is already Optional[bool]
    # Actually, the issue is that the engine reads board_approval as truthy.
    # The right fix is to keep the value as Optional[bool] (None/True/False) and
    # have the engine treat None as UNKNOWN.
    # In the service layer, just don't collapse to bool():
    old_pattern = r"bool\(\s*t\.board_approval\s*\)"
    new_text = re.sub(old_pattern, "t.board_approval", text)
    if new_text != text:
        changes_made.append("replaced bool(t.board_approval) with t.board_approval (preserves None)")
        text = new_text

    # Replace form_117_filed=None,  # TODO: ... with proper UNKNOWN handling.
    # The actual code uses dict-style: "form_117_filed": None,  # TODO: ...
    # Or variable-style: form_117_filed = None,  # TODO: ...
    # Handle both forms.
    old_pattern_117a = r'"form_117_filed"\s*:\s*None\s*,\s*#\s*TODO:\s*separate from instrument field'
    new_117a = (
        '"form_117_filed": getattr(t, "form_117_filed", None),  # UNKNOWN until RJSC filings table lookup implemented (TR-007)'
    )
    new_text = re.sub(old_pattern_117a, new_117a, text)
    if new_text != text:
        changes_made.append("replaced form_117_filed=None TODO with getattr lookup + UNKNOWN marker (dict form)")
        text = new_text

    old_pattern_117b = r'form_117_filed\s*=\s*None\s*,\s*#\s*TODO:\s*separate from instrument field'
    new_117b = (
        'form_117_filed=getattr(t, "form_117_filed", None),  # UNKNOWN until RJSC filings table lookup implemented (TR-007)'
    )
    new_text = re.sub(old_pattern_117b, new_117b, text)
    if new_text != text:
        changes_made.append("replaced form_117_filed=None TODO with getattr lookup + UNKNOWN marker (variable form)")
        text = new_text

    if text == original:
        print(f"[--] Fix 3: no change needed in {p.name}")
        return True

    p.write_text(text, encoding="utf-8")
    for c in changes_made:
        print(f"[OK ] Fix 3: {c}")
    return True


# ---------- Fix 4: RJSC-005 — VALID_TRANSITIONS map ----------
def fix_4_valid_transitions():
    p = Path("app/models/filings.py")
    if not p.exists():
        print("[SKIP] Fix 4: app/models/filings.py not found")
        return False
    text = p.read_text(encoding="utf-8")
    if "VALID_TRANSITIONS" in text:
        print(f"[--] Fix 4: VALID_TRANSITIONS already present in {p.name}")
        return True

    # Find a good place to insert — after the AGM-001 / AGM-002 default flags comment block
    # or at module level after imports
    # Look for `# AGM-001 / AGM-002:` comment (per earlier paste)
    insert_marker = "# AGM-001 / AGM-002: default flags"
    new_block = '''

# RJSC-005: Filing lifecycle state transition validation.
# Every PATCH handler must validate `next_status` against this map.
# Invalid transitions (e.g. FILED -> PENDING) must be rejected with 409 Conflict.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING":     {"FILED", "CANCELLED"},
    "FILED":       {"REJECTED", "SUPERSEDED"},
    "REJECTED":    {"PENDING"},  # allow re-submission after rejection
    "SUPERSEDED":  set(),         # terminal
    "CANCELLED":   set(),         # terminal
    "OVERDUE":     {"FILED", "CANCELLED"},  # overdue can still be filed or cancelled
    "HELD":        {"MINUTES_FILED", "CANCELLED"},  # AGM held, awaiting minutes
    "MINUTES_FILED": set(),       # terminal
    "COMPLETED":   set(),         # terminal (audit complete, etc.)
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
}


def validate_filing_transition(current_status: str, next_status: str) -> bool:
    """Return True if the transition is allowed, False otherwise."""
    allowed = VALID_TRANSITIONS.get(current_status, set())
    return next_status in allowed


class InvalidFilingTransitionError(ValueError):
    """Raised when a filing lifecycle transition is not allowed."""
    def __init__(self, current: str, next_: str):
        super().__init__(
            f"Invalid filing transition: {current} -> {next_}. "
            f"Allowed from {current}: {VALID_TRANSITIONS.get(current, set())}"
        )

'''
    if insert_marker in text:
        # insert before the marker
        idx = text.index(insert_marker)
        new_text = text[:idx] + new_block + text[idx:]
    else:
        # Fallback: append at end of file
        new_text = text + new_block

    p.write_text(new_text, encoding="utf-8")
    print(f"[OK ] Fix 4: added VALID_TRANSITIONS map + validate_filing_transition() + InvalidFilingTransitionError to {p.name}")
    return True


def main():
    print("=== Phase 1: Quick Wins Fix Script ===")
    print()
    fix_1_hist_or_true()
    fix_2_rule_state_enum()
    fix_3_company_service()
    fix_4_valid_transitions()
    print()
    print("=== Phase 1 complete ===")
    print()
    print("Next steps:")
    print("  1. Review the changes with: git diff --stat")
    print("  2. Run the affected tests:")
    print("     pytest tests/unit/test_rule_engine.py -x  # verify Fix 1 doesn't break")
    print("  3. Verify the new enum member is exported:")
    print("     python -c 'from app.rule_engine.engine import RuleState; print(list(RuleState))'")
    print("  4. Once verified, commit: git add -A && git commit -m 'Phase 1: quick wins (HIST-OR-TRUE, RULE-003a, TR-007/TR-011, RJSC-005)'")


if __name__ == "__main__":
    main()