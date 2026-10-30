"""
Regression pins for 64d9259-class engine rewrites — NLC compliance platform.

Incident: commit 64d9259 rewrote app/rule_engine/engine.py from a pre-F-29
snapshot, silently dropping the eval_state UNKNOWN guards (F-29 x3 sites,
F-30 black_count filter, 39b4b9d severity floor) and corrupting the D16 F3
comment. Restored in 26ea991. These tests make any future silent rewrite
fail loudly in CI instead of being discovered in the next audit.

Layers:
  1. Source pins  — pure text/regex on engine.py, immune to import breakage.
  2. Structure pins — loads engine.py as a standalone module (stdlib-only
     by design) and checks the guard-relevant surface.

Run with pytest:      python -m pytest tests/test_engine_guards.py -v
Or standalone:        python tests/test_engine_guards.py
"""
from __future__ import annotations

import dataclasses
import importlib.util
import re
import sys
from pathlib import Path

ENGINE_PATH = Path(__file__).resolve().parents[1] / "app" / "rule_engine" / "engine.py"

EXPECTED_GUARD_SITES = 5          # F-29 x3 + F-30 black_count + 39b4b9d severity floor
EXPECTED_VERIFIED_COUNT = 41      # D15-verified register (post 64d9259 trim, confirmed 2026-10-30)
FORBIDDEN_RULE_IDS = ("AR-001", "SH-002", "ESC-003")   # unscored: AR/SH informational, ESC-003 is the surcharge itself
LIFECYCLE_ALLOWED = 1             # one lifecycle site is un-gated by design

GUARD = 'f.eval_state != "UNKNOWN"'
F30_TAIL = "not f.resolved and f.conditional_applies and f.rule_id not in self._ESC_RULE_IDS])"
F30_RESIDUE = "Severity.BLACK and f.rule_id not in"
F3_RESIDUE = ") != 'UNKNOWN'] # F3"
F3_CLEAN = "# F3: exclude UNKNOWN from rescue"
UNGUARDED_PATTERN = "is_black_override and f.state == RuleState.NON_COMPLIANT"


def _source() -> str:
    return ENGINE_PATH.read_text(encoding="utf-8", errors="replace")


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

def test_guard_site_count_is_five():
    n = _source().count(GUARD)
    assert n == EXPECTED_GUARD_SITES, (
        f"expected {EXPECTED_GUARD_SITES} eval_state UNKNOWN guard sites, found {n}. "
        "A snapshot rewrite likely dropped guards again (see 64d9259 incident, restored in 26ea991)."
    )


def test_f30_black_count_full_filter():
    src = _source()
    assert src.count(F30_TAIL) == 1, (
        "F-30 black_count full filter missing or duplicated — pure data gaps "
        "(eval_state UNKNOWN) would count toward the ESC-003 surcharge."
    )
    assert F30_RESIDUE not in src, "unguarded black_count residue present"


def test_d16_f3_comment_cleaned():
    src = _source()
    assert src.count(F3_CLEAN) == 1, "cleaned F3 comment missing or duplicated"
    assert F3_RESIDUE not in src, "F3 comment residue (duplicated fragment) is back"


def test_unguarded_override_sites_bounded():
    lines = [ln for ln in _source().splitlines()
             if UNGUARDED_PATTERN in ln and "eval_state" not in ln]
    assert len(lines) <= LIFECYCLE_ALLOWED, (
        f"{len(lines)} unguarded is_black_override+NON_COMPLIANT sites "
        f"(allowed: {LIFECYCLE_ALLOWED} lifecycle site):\n" + "\n".join(lines)
    )


def test_verified_rule_ids_pin():
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
    bad = [r for r in FORBIDDEN_RULE_IDS if r in uniq]
    assert not bad, f"forbidden members in VERIFIED_RULE_IDS: {bad}"


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
    forbidden = uniq & set(FORBIDDEN_RULE_IDS)
    assert not forbidden, f"forbidden members in VERIFIED_RULE_IDS: {sorted(forbidden)}"


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
