#!/usr/bin/env python3
"""Read-only citation-anchor audit for NLC's Bangladesh Companies Act rule declarations.

This checks that selected runtime rule IDs cite the current candidate section
anchors recorded in the maintained legal-basis inventory. It is a technical
consistency check, NOT independent legal verification or counsel approval.
Run: python tools/legal_citation_audit.py (exit 1 = anchor mismatch)
Scans runtime declarations in app/ and canonical_architecture/.
Historical migrations and tool fixtures are excluded.
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
    "AGM-005": ["Section 85(2)(b)"],
    "AGM-006": ["Section 89"],
    "AR-001": ["Section 36"],
    "AUD-001": ["Section 210(6)"],
    "AUD-002": ["Section 183"],
    "AUD-005": ["Section 210(3)"],
    "ACC-002": ["Section 190"],
    "DIR-001": ["Section 115"],
    "DIR-002": ["Section 115"],
    "DIR-004": ["Section 115"],
    "DIR-007": ["Section 93(2)", "Section 92"],
    "REG-002": ["Sections 34, 89, 174"],
    "SH-001": ["Section 151", "Form XV"],
    "SH-002": ["Section 158"],
    "CAP-001": ["Sections 53, 54 and 56"],
    "CAP-002": ["Section 159", "Section 159(1)"],
    "CAP-003": ["Sections 59-60"],
    "CHG-001": ["Section 172"],
    "DEF-001": ["Section 94"],
    "MEM-001": ["Section 222"],
    "TR-001": ["Section 38"],
    "TL-001": ["City Corporation", "Paurashava"],
    "TL-002": ["City Corporation", "Paurashava"],
    "INC-003": ["Sections 90(1) and 90(2)"],
    "INC-004": ["Section 56"],
    "INC-007": ["Section 150(1)", "Section 150(6)"],
    "AUD-003": ["Sections 183 and 210"],
    "AUD-004": ["Section 210(3)"],
    "AGM-003": ["Section 85(1)(a)"],
    "AGM-004": ["Section 85(1)(a)"],
    "AR-002": ["Section 36"],
    "AR-003": ["Section 36", "Section 346"],
    "AR-004": ["Section 36", "Schedule X"],
    "DIR-003": ["Section 115(2)"],
    "SH-003": ["Section 56"],
    "TR-003": ["Section 38(7)"],
    "TR-004": ["Section 38(4)"],
    "TR-005": ["Section 38(7)"],
    "TR-006": ["Sections 34 and 38"],
    "CAP-004": ["Section 88(1)"],
    "STR-001": ["Sections 11 and 88(1)"],
    "STR-002": ["Sections 12, 15-16", "Section 88(1)"],
    "STR-003": ["Sections 20 and 88(1)"],
    "DIR-008": ["Section 104"],
    "DIR-010": ["Section 110"],
    "BOD-001": ["Section 96"],
    "BOD-002": ["Section 95"],
    "BOD-003": ["Section 89"],
    "ACC-001": ["Section 183"],
    "ACC-003": ["Section 181"],
    "ESC-001": ["Section 346"],
    "ESC-002": ["Section 346"],
    "ESC-004": ["Section 286"],
    "ESC-005": ["Sections 195 and 197"],
}
# These rule families are outside the Companies Act anchor audit. They remain
# subject to their own primary-source and counsel review; SKIP is not PASS.
OUT_OF_SCOPE = {
    "INC-005": "foreign investment / Bangladesh Bank requirements",
    "INC-006": "BIDA / foreign investment requirements",
    "TR-002": "Stamp Act 1899",
    "TAX-001": "Income Tax Act and current tax rules",
    "TAX-002": "VAT / withholding tax legislation",
    "TAX-003": "Income Tax Act and current tax rules",
    "TAX-004": "Income Tax Act and current tax rules",
    "VAT-002": "VAT and Supplementary Duty Act 2012",
    "VAT-003": "VAT and Supplementary Duty Act 2012",
    "LBR-001": "Bangladesh Labour Act 2006 and Rules",
    "LBR-002": "Bangladesh Labour Act 2006 and Rules",
    "LBR-003": "Bangladesh Labour Act 2006 and Rules",
    "FX-001": "Foreign Exchange Regulation Act 1947 / Bangladesh Bank circulars",
    "BSEC-001": "BSEC rules and Corporate Governance Code",
    "BSEC-002": "BSEC rules and Corporate Governance Code",
    "BSEC-003": "BSEC rules and Corporate Governance Code",
    "BSEC-004": "BSEC rules and Corporate Governance Code",
}

# A mapped candidate is not necessarily a legally resolved proposition.
# These declarations have an explicit reason to remain review-only.
REVIEW_ONLY = {
    "REG-001": ("Companies Act 1994 (Bangladesh) and applicable Articles",
                "Generic register-completeness signal must be split by register type."),
    "REG-003": ("Unresolved location proposition",
                "Section 34(2) is not accepted as location authority; no breach is inferred."),
    "DEF-002": ("Case-specific enabling provision required",
                "A penalty notice requires the issuing authority and exact enabling provision."),
    "BNK-001": ("Companies Act 1994 (Bangladesh), Part V",
                "Exact petition ground and procedural route require case-specific review."),
    "BNK-002": ("Companies Act 1994 (Bangladesh), Part V",
                "Voluntary and court-appointed liquidator routes require separate mapping."),
    "BNK-003": ("Companies Act 1994 (Bangladesh), Part V",
                "Authenticated operative court order and exact provision require review."),
    "AGM-007": ("Section 85 and the company Articles",
                "Adjournment notice depends on the Articles and exact procedural facts."),
    "DIR-005": ("Section 130",
                "Section 130 concerns director-interest disclosure, not a generic register duty."),
    "DIR-006": ("exact register obligation requires counsel verification",
                "No universal register provision has been established."),
    "ESC-003": ("NLC internal risk policy",
                "Internal rescue policy, not a statutory breach or Companies Act consequence."),
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
    fails = warns = passes = scopes = 0
    print("=" * 78)
    print(" DEEP LEGAL CITATION AUDIT v2 - NLC RULE ENGINE")
    print(" Statute: Companies Act 1994 (Bangladesh) - candidate anchors; legal approval separate")
    print("=" * 78)
    for p in iter_py():
        text = p.read_text(encoding="utf-8", errors="replace")
        for rid, decls in blocks(text).items():
            for anchor, blob in decls:
                loc = "%s:%d" % (p.relative_to(ROOT), anchor + 1)
                if rid in FORBIDDEN_IDS:
                    print("FAIL  %-9s forbidden rule id at %s - %s" % (rid, loc, FORBIDDEN_IDS[rid])); fails += 1
                    continue
                if rid in REVIEW_ONLY:
                    anchor_text, rationale = REVIEW_ONLY[rid]
                    if anchor_text.lower() in blob.lower():
                        print("REVIEW %-9s documented hold at %s - %s" % (rid, loc, rationale)); scopes += 1
                    else:
                        print("FAIL  %-9s review-only anchor %r missing at %s" % (rid, anchor_text, loc)); fails += 1
                    continue
                if rid in OUT_OF_SCOPE:
                    print("SCOPE %-9s separate statute audit required at %s - %s" % (rid, loc, OUT_OF_SCOPE[rid])); scopes += 1
                    continue
                if rid not in EXPECTED:
                    print("WARN  %-9s unmapped Companies Act proposition at %s" % (rid, loc)); warns += 1
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
    print(" REVIEW / OUT OF SCOPE: %d (source and counsel review remain open)" % scopes)
    print(" VERDICT: %d FAIL / %d UNMAPPED / %d CANDIDATE-ANCHOR MATCH" % (fails, warns, passes))
    print(" LEGAL STATUS: candidate-anchor consistency is not source authentication or counsel approval.")
    print(" VERIFIED_RULE_IDS and the independent counsel register remain fail-closed.")
    print("=" * 78)
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
