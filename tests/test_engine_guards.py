"""
Regression pins for engine rewrites — NLC compliance platform.

Incident 1 (2026-10-30): commit 64d9259 rewrote app/rule_engine/engine.py from
a pre-F-29 snapshot, silently dropping the eval_state UNKNOWN guards (F-29 x3
sites, F-30 black_count filter, 39b4b9d severity floor) and corrupting the D16
F3 comment. Restored in 26ea991.

Incident 2 (2026-11-15 → 2026-11-19): this tripwire itself drifted. The source
pins were written against a ~2026-10-30 snapshot but the file was committed on
2026-11-15 after two weeks of legitimate scoring-gate evolution (the pins were
born red: 9 guard sites, reformatted F-30 filter, relocated F-3 comment). The
4th pin also encoded the pre-#370 release semantics. Because the file was
wired into no CI workflow and no Makefile target, the failures were never
seen. This rewrite re-points every pin to the verified 2026-11-19 surface,
adds per-protection anchors (so dropping ANY single protection fails even
when the total count is preserved), and the file is now wired into ci.yml.

Maintenance protocol: any engine change that adds, removes or reformats a
confirmed-violation (eval_state == "VIOLATION") gate MUST update
EXPECTED_GUARD_SITES and the PROTECTION_ANCHORS in the same PR, stating the
PR that justifies the change. Adding a gate without bumping the count fails
CI; dropping a gate fails CI both via the count and via its anchor.

Layers:
  1. Source pins  — pure text/regex on engine.py, immune to import breakage.
  2. Structure pins — loads engine.py as a standalone module (stdlib-only
     by design) and checks the guard-relevant surface.

Run with pytest:      python -m pytest tests/test_engine_guards.py -v
Or standalone:        python tests/test_engine_guards.py
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    # Standalone mode needs the repo root importable for canonical_architecture.
    sys.path.insert(0, str(REPO_ROOT))

ENGINE_PATH = REPO_ROOT / "app" / "rule_engine" / "engine.py"

# 2026-11-19 verified inventory (9 sites, variable `f`):
#   1. has_black_override           — ESC-003 trigger gate (F-29)
#   2. black_count (ESC-003)        — F-29 gate + F-30 ESC-exclusion filter
#   3. _calculate_score critical    — final-score BLACK override gate (F-29)
#   4. band max_flag_severity loop  — 39b4b9d severity floor, positive form
#   5-8. score-breakdown            — black/red/yellow/green_flag_count gates
#   9. rescue actionable filter     — F-3 confirmed-violation rescue gate
# The central eligibility filter (_eligible_scoring_flags) uses the variable
# name `flag` and is pinned separately by PROTECTION_ANCHORS.
EXPECTED_GUARD_SITES = 9
EXPECTED_VERIFIED_COUNT = 0       # independent counsel verification only; no signed approvals recorded
SPECIAL_ACTIVE_RULE_IDS = ("AR-001", "SH-002", "ESC-003")   # specifically retained in the 85-rule product scoring set
LIFECYCLE_ALLOWED = 1             # one lifecycle site is un-gated by design

GUARD = 'f.eval_state == "VIOLATION"'
F30_RESIDUE = "Severity.BLACK and f.rule_id not in"
F3_RESIDUE = ") != 'UNKNOWN'] # F3"
F3_CURRENT_COMMENT = "# F3 UNKNOWN policy: unknown facts are indeterminate, not violations"
UNGUARDED_PATTERN = "is_black_override and f.state == RuleState.NON_COMPLIANT"

# Per-protection anchors. Each entry keys on a semantic anchor line; the
# helper then requires a confirmed-violation gate within a small line window
# AFTER the anchor. The window is smaller than the distance to any unrelated
# gate, so a dropped protection cannot "borrow" the next block's gate, while
# pure reformatting inside the block keeps passing.
PROTECTION_ANCHORS: dict[str, tuple[str, int]] = {
    # Central scoring eligibility: only confirmed violations are score-eligible.
    "eligible_scoring_flags_gate": (r"def _eligible_scoring_flags\(", 14),
    # F-29: ESC-003 trigger requires a confirmed violation.
    "esc003_trigger_gate": (r"has_black_override\s*=\s*any\(", 14),
    # F-29: the final-score BLACK override requires a confirmed violation.
    "score_black_override_gate": (r"critical\s*=\s*\[", 14),
    # 39b4b9d severity floor: band elevation requires a confirmed violation.
    "band_severity_floor_gate": (r"max_flag_severity\s*=\s*Severity\.GREEN", 16),
    # F-3: rescue steps originate only from confirmed violations.
    "rescue_actionable_gate": (r"actionable\s*=\s*\[", 14),
}

GATE_RE = r"\w*\.eval_state\s*==\s*[\"']VIOLATION[\"']"
ESC_EXCLUSION_RE = r"f\.rule_id\s+not\s+in\s+self\._ESC_RULE_IDS"


def _source() -> str:
    return ENGINE_PATH.read_text(encoding="utf-8", errors="replace")


def _gate_within_window(src: str, anchor: str, window: int, gate_re: str = GATE_RE) -> bool:
    """True if a gate matching gate_re appears within `window` lines after an anchor match.

    The window is bounded so the check cannot leak into a neighbouring block
    whose own gate would otherwise mask a dropped protection.
    """
    lines = src.splitlines()
    for m in re.finditer(anchor, src):
        start = src[:m.start()].count("\n")
        chunk = lines[start:start + window + 1]
        if any(re.search(gate_re, ln) for ln in chunk):
            return True
    return False


def _load_module():
    """Load engine.py standalone — it is stdlib-only by design (LAYER C)."""
    spec = importlib.util.spec_from_file_location("nlc_engine_under_test", ENGINE_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec: dataclass processing resolves the module via
    # sys.modules[cls.__module__]; without registration this raises
    # AttributeError: 'NoneType' object has no attribute '__dict__' (py3.12).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # raises loudly if the module is broken — that IS the test
    return mod


# ═══════════════ source-level pins (no import needed) ═══════════════

def test_guard_site_count_matches_inventory():
    n = _source().count(GUARD)
    assert n == EXPECTED_GUARD_SITES, (
        f"expected {EXPECTED_GUARD_SITES} eval_state VIOLATION guard sites, found {n}. "
        "If a gate was added or removed, update EXPECTED_GUARD_SITES, the site "
        "inventory in the module docstring and PROTECTION_ANCHORS in the same PR. "
        "If nothing changed intentionally, a snapshot rewrite likely dropped or "
        "duplicated guards (see 64d9259 incident, restored in 26ea991; and the "
        "2026-11-15 born-red drift documented in the docstring)."
    )


def test_every_protection_anchor_is_present():
    """Each confirmed-violation protection must exist at its anchor site.

    This catches the incident class 'one protection dropped while a new,
    unrelated gate kept the total count unchanged' — the windowed search
    cannot borrow a neighbouring block's gate.
    """
    src = _source()
    missing = [name for name, (anchor, window) in PROTECTION_ANCHORS.items()
               if not _gate_within_window(src, anchor, window)]
    assert not missing, (
        f"protection anchor(s) missing from engine.py: {missing}. "
        "A confirmed-violation gate was dropped or semantically weakened."
    )


def test_score_breakdown_band_counts_are_individually_gated():
    """Each band count (black/red/yellow/green) must gate on confirmed violations.

    Pinned per severity with a tempered span (may not cross the count's own
    closing `])`), so dropping a single count's gate fails even though the
    other three keep matching and the total guard count is preserved.
    """
    src = _source()
    for sev in ("BLACK", "RED", "YELLOW", "GREEN"):
        pattern = (
            rf"{sev.lower()}_flag_count=len\(\[(?:(?!\]\)).)*?"
            rf"\w*\.eval_state\s*==\s*[\"']VIOLATION[\"']"
        )
        assert re.search(pattern, src, re.DOTALL), (
            f"{sev} flag-count gate missing or unguarded — band counts must "
            "only count confirmed violations."
        )


def test_f30_black_count_full_filter():
    src = _source()
    # The F-30 ESC-exclusion and its confirmed-violation gate live inside the
    # black_count block, within the anchor window (no borrowing from neighbours).
    assert _gate_within_window(src, r"black_count\s*=\s*len\(", 14), (
        "F-30 black_count confirmed-violation gate missing — pure data gaps "
        "(eval_state UNKNOWN) would count toward the ESC-003 surcharge."
    )
    exclusion = re.search(
        r"black_count\s*=\s*len\(", src
    )
    assert exclusion, "ESC-003 black_count block missing entirely"
    lines = src.splitlines()
    start = src[:exclusion.start()].count("\n")
    window_chunk = "\n".join(lines[start:start + 15])
    assert re.search(ESC_EXCLUSION_RE, window_chunk), (
        "F-30 black_count ESC-exclusion filter missing — ESC-family rows "
        "would count toward the ESC-003 surcharge."
    )
    assert F30_RESIDUE not in src, "unguarded black_count residue present"


def test_d16_f3_comment_cleaned():
    src = _source()
    assert src.count(F3_CURRENT_COMMENT) == 1, (
        "current F3 UNKNOWN-policy comment missing or duplicated"
    )
    assert F3_RESIDUE not in src, "F3 comment residue (duplicated fragment) is back"


def test_unguarded_override_sites_bounded():
    lines = [ln for ln in _source().splitlines()
             if UNGUARDED_PATTERN in ln and "eval_state" not in ln]
    assert len(lines) <= LIFECYCLE_ALLOWED, (
        f"{len(lines)} unguarded is_black_override+NON_COMPLIANT sites "
        f"(allowed: {LIFECYCLE_ALLOWED} lifecycle site):\n" + "\n".join(lines)
    )


def test_legal_approval_gate_pin():
    src = _source()
    m = re.search(r"\bVERIFIED_RULE_IDS\b[^\n]*=", src)
    assert m, "VERIFIED_RULE_IDS definition not found in source"
    hint = src[m.start():m.start() + 120]
    rest = src[m.end():]
    # tolerate wrapper calls:  = frozenset({...})  /  = set({...})
    rest = re.sub(r"^\s*(?:frozenset|set)\s*\(", "(", rest, count=1)
    ob = re.search(r"[\{\[\(]", rest)
    assert ob, f"no literal after VERIFIED_RULE_IDS assignment near: {hint!r}"
    open_ch = rest[ob.start()]
    close_ch = {"{": "}", "[": "]", "(": ")"}[open_ch]
    depth, i = 1, ob.start() + 1
    while i < len(rest) and depth:
        ch = rest[i]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
        i += 1
    assert depth == 0, f"unbalanced brackets in VERIFIED_RULE_IDS literal near: {hint!r}"
    body = rest[ob.start() + 1:i - 1]
    ids = re.findall(r'["\']([A-Z][A-Z0-9]*-[0-9A-Z]+)["\']', body)
    uniq = set(ids)
    assert len(ids) == len(uniq), (
        f"duplicate entries in VERIFIED_RULE_IDS ({len(ids)} raw vs {len(uniq)} unique) near: {hint!r}"
    )
    assert len(uniq) == EXPECTED_VERIFIED_COUNT, (
        f"expected {EXPECTED_VERIFIED_COUNT} verified rules, found {len(uniq)} — "
        f"definition form near: {hint!r} (register pin moved without a register update?)"
    )


def test_f3_unknown_constants():
    src = _source()
    assert re.search(r"^UNKNOWN_COVERAGE_CAP\s*=\s*5\b", src, re.M), "UNKNOWN_COVERAGE_CAP changed"
    assert re.search(r"^UNKNOWN_COVERAGE_PER\s*=\s*1\b", src, re.M), "UNKNOWN_COVERAGE_PER changed"


# ═══════════════ structure-level pins (loads the module) ═══════════════

def test_engine_module_imports():
    _load_module()


def test_compliance_flag_guard_surface():
    mod = _load_module()
    flag = mod.ComplianceFlag(
        rule_id="T-001",
        flag_code="TEST",
        severity=mod.Severity.BLACK,
        score_impact=0,
        revenue_tier=mod.RevenueTier.COMPLIANCE_PACKAGE,
        description="structure probe",
        statutory_basis="test",
    )
    # Guards use f.state / f.eval_state / f.conditional_applies — must exist
    # (as dataclass fields or properties; hasattr covers both).
    for attr in ("state", "eval_state", "conditional_applies", "resolved", "is_black_override"):
        assert hasattr(flag, attr), f"ComplianceFlag.{attr} missing — guard logic cannot work"
    assert flag.resolved is False
    assert flag.is_black_override is False


def test_enums_have_guard_members():
    mod = _load_module()
    assert mod.RuleState.NON_COMPLIANT is not None
    assert mod.Severity.BLACK is not None
    assert mod.Severity.NOT_EVALUATED is not None
    assert mod.RevenueTier.COMPLIANCE_PACKAGE is not None


def test_verified_rule_ids_module_attr():
    mod = _load_module()
    ids = getattr(mod, "VERIFIED_RULE_IDS", None)
    assert ids is not None, "VERIFIED_RULE_IDS is not module-level anymore"
    uniq = set(ids)
    assert len(uniq) == EXPECTED_VERIFIED_COUNT, (
        f"expected {EXPECTED_VERIFIED_COUNT} verified rules, found {len(uniq)}"
    )


def test_product_scoring_allowlist_is_full_and_separate_from_legal_verification():
    """Pin the #370 explicit-counsel-separation release contract.

    Product release depends on the product-owner allowlist only and must NOT
    depend on counsel verification: scripts/check_rule_verification.py fails
    closed if legal_score_is_released() references VERIFIED_RULE_IDS or uses
    issubset. Counsel verification remains a separate, currently empty register.
    """
    mod = _load_module()
    product_ids = set(mod.PRODUCT_SCORING_RULE_IDS)
    deduction_ids = set(mod.SCORE_DEDUCTION_RULE_IDS)
    assert len(product_ids) == 85
    assert set(SPECIAL_ACTIVE_RULE_IDS) <= product_ids
    assert len(deduction_ids) == 85
    assert product_ids == deduction_ids
    assert mod.VERIFIED_RULE_IDS == frozenset()
    assert mod.legal_score_is_released() is (
        mod.LEGAL_SCORE_RELEASED is True
        and bool(product_ids)
    )


# ═══════════════ standalone runner ═══════════════

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"{'ALL-PASS' if failed == 0 else 'FAILED'} ({len(fns) - failed}/{len(fns)})")
    sys.exit(1 if failed else 0)
