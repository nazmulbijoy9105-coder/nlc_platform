#!/usr/bin/env python3
"""Deep legal citation audit v2 - NLC rule engine vs Companies Act 1994 (BD).
Ground truth: rule-map v1.0 + user-verified mappings (migrations 0007/0010/0029/0030, cb306ac).
Run: python tools/legal_citation_audit.py   (exit 1 = violations found)
Scans live declarations in app/, canonical_architecture/. tests/ (fixtures) and alembic/ (history) excluded.
Citations matched as plain substrings over the FULL declaration block (description + statutory_basis).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "app" / "rule_engine" / "engine.py"
SCAN_DIRS = ["app", "canonical_architecture"]
EXCLUDE = ("alembic", "tools", "legal_audit")

EXPECTED = {
    "INC-001": ["Section 23"],
    "OFF-001": ["Section 77"],
    "AGM-001": ["Section 81"],
    "AGM-002": ["Section 81"],
    "AR-001":  ["Section 36"],
    "AUD-001": ["Section 210(6)"],
    "AUD-002": ["Section 183"],
    "AUD-005": ["Section 210(3)"],
    "ACC-002": ["Section 190"],
    "DIR-001": ["Section 90"],
    "DIR-002": ["Section 93"],
    "DIR-004": ["Section 109", "Section 110"],
    "REG-001": ["Section 34"],
    "REG-002": ["Sections 34-36", "Section 89"],
    "SH-001":  ["Section 151", "Form XV"],
    "SH-002":  ["Section 158"],
    "CAP-001": ["Section 53", "Section 56"],
    "CAP-002": ["Section 159", "Section 159(1)"],
    "CAP-003": ["Section 150"],
    "CHG-001": ["Section 159"],
    "DEF-001": ["Section 118(6)", "Section 182(9)"],
    "MEM-001": ["Section 222"],
    "TR-001":  ["Section 38"],
    "TL-001": ["City Corporation", "Paurashava"],
    "TL-002": ["City Corporation", "Paurashava"],
}
FORBIDDEN_IDS = {"INC-002": "duplicate of INC-001; split into OFF-001 (D2)"}
FORBIDDEN_TEXT = ["210(2A)", "120 days of incorporation",
                  "Directors (Sec 90)", "Charges (Sec 87)", "AGM Minutes (Sec 83)"]

def iter_py():
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(x in p.parts for x in EXCLUDE):
                continue
            yield p

def blocks(text):
    lines = text.split("\n")
    out = {}
    for i, l in enumerate(lines):
        if 'rule_id="' in l:
            rid = l.split('rule_id="')[1].split('"')[0]
            start = i
            while start > 0 and "_add_flag(ComplianceFlag(" not in lines[start] and "ComplianceFlag(" not in lines[start]:
                start -= 1
            end = i
            while end < len(lines) - 1 and lines[end].strip() != "))":
                end += 1
            out.setdefault(rid, []).append((start, "\n".join(lines[start:end + 1])))
    return out

def main():
    fails = warns = passes = 0
    print("=" * 78)
    print(" DEEP LEGAL CITATION AUDIT v2 - NLC RULE ENGINE")
    print(" Statute: Companies Act 1994 (Bangladesh) - ground truth v1.0 (synced)")
    print("=" * 78)
    for p in iter_py():
        text = p.read_text(encoding="utf-8", errors="replace")
        for rid, decls in blocks(text).items():
            for anchor, blob in decls:
                loc = "%s:%d" % (p.relative_to(ROOT), anchor + 1)
                if rid in FORBIDDEN_IDS:
                    print("FAIL  %-9s forbidden rule id at %s - %s" % (rid, loc, FORBIDDEN_IDS[rid])); fails += 1
                    continue
                if rid not in EXPECTED:
                    print("WARN  %-9s unmapped rule at %s" % (rid, loc)); warns += 1
                    continue
                if any(f.lower() in blob.lower() for f in FORBIDDEN_TEXT):
                    hit = [f for f in FORBIDDEN_TEXT if f.lower() in blob.lower()]
                    print("FAIL  %-9s forbidden citation %s at %s" % (rid, hit, loc)); fails += 1
                    continue
                if any(c in blob for c in EXPECTED[rid]):
                    print("PASS  %-9s citation OK  [%s]" % (rid, loc)); passes += 1
                else:
                    print("FAIL  %-9s expected any of %s at %s" % (rid, EXPECTED[rid], loc)); fails += 1

    eng = ENGINE.read_text(encoding="utf-8", errors="replace")
    print("-" * 78)
    for token, msg in [("210(2A)", "stale AUD-001 citation"), ("120 days of incorporation", "stale AUD-001 text"),
                       ("Directors (Sec 90)", "stale REG-002 text"), ("Charges (Sec 87)", "stale REG-002 text"),
                       ("AGM Minutes (Sec 83)", "stale REG-002 text")]:
        if token.lower() in eng.lower():
            print("FAIL  [E] engine.py contains forbidden %r (%s)" % (token, msg)); fails += 1
        else:
            print("PASS  [E] %r absent" % token); passes += 1
    print("-" * 78)
    for token, note in [("CATEGORY_CAPS", "100-cap score model not merged yet"),
                        ("eval_state", "UNKNOWN policy (F3)"),
                        ("BLACK_OVERRIDE_RULES", "black-override set"),
                        ("UNKNOWN_COVERAGE_CAP", "coverage penalty constants")]:
        print(("PASS  " if token in eng else "WARN  ") + "[F] %s %s" % (token, "" if token in eng else "- " + note))
        if token not in eng: warns += 1
    print("=" * 78)
    print(" VERDICT: %d FAIL / %d WARN / %d PASS" % (fails, warns, passes))
    print("=" * 78)
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
