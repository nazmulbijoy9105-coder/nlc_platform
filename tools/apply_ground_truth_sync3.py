#!/usr/bin/env python3
"""Ground-truth sync batch 3 - final polish (2026-10-30).

F1  engine: CHARGE deadline 30 -> 21 days, citation -> Section 159(1)
F2  engine: CAP-002 statutory_basis -> Section 159(1) (windowed rewrite)
F3  engine: TL-001 basis -> Local Government (City Corporation) Act 2009
F4  api:    drop stale INC-002 from black-override docstring
F5  seed:   remove INC-002 entry; sync CAP-002 -> s.159(1) / 21 days
F6  models: FORM_VIII -> Section 159(1), deadline_days 21
F7  audit:  EXPECTED CAP-002 -> Section 159
F8  tests:  OFF-001 -> s.77, AGM-001 -> s.81 (windowed statutory_basis rewrite)
Run: python tools/apply_ground_truth_sync3.py
"""
import io, re, ast

OK, SKIP = [], []

def load(p): return io.open(p, encoding="utf-8", newline="").read()
def save(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)

def subx(path, old, new, label):
    t = load(path)
    n = t.count(old)
    if n:
        save(path, t.replace(old, new))
    (OK if n else SKIP).append("%s: %d hit(s) [%s]" % (label, n, path))

def rex(path, pattern, repl, label, count=1):
    t = load(path)
    t2, n = re.subn(pattern, lambda m: repl, t, count=count)
    if n:
        save(path, t2)
    (OK if n else SKIP).append("%s: %d hit(s) [%s]" % (label, n, path))

def windowed_basis(path, rid, basis, span=1000):
    t = load(path)
    pat = re.compile(r'(rule_id="%s".{0,%d}?)statutory_basis="[^"]*"' % (re.escape(rid), span), re.S)
    t2, n = pat.subn(lambda m: m.group(1) + 'statutory_basis="%s"' % basis, t)
    if n:
        save(path, t2)
    (OK if n else SKIP).append("%s -> %s: %d block(s) [%s]" % (rid, basis, n, path))

def sync_line(path, anchor, pairs, label):
    t = load(path)
    rx = re.compile(r"^.*" + re.escape(anchor) + r".*$", re.M)
    hits = [0]
    def repl(m):
        line = m.group(0)
        for old, new in pairs:
            if old in line:
                line = line.replace(old, new)
                hits[0] += 1
        return line
    save(path, rx.sub(repl, t))
    (OK if hits[0] else SKIP).append("%s: %d change(s) [%s]" % (label, hits[0], path))

E = "app/rule_engine/engine.py"

# F1a: constant + verify comment -> final value
rex(E, r"CHARGE_REGISTRATION_DEADLINE_DAYS = 30\s*#[^\n]*",
    "CHARGE_REGISTRATION_DEADLINE_DAYS = 21  # Section 159(1): charge registration within 21 days of creation",
    "F1a charge constant 30->21")

# F1b: CAP-002 description (s.174 -> s.159(1), state the 21-day window)
subx(E,
    "not registered. Section 174: registration deadline. Unregistered charge void against creditors and liquidator.",
    "not registered within 21 days of creation. Section 159(1): unregistered charge void against creditors and liquidator.",
    "F1b CAP-002 description")

# F2: CAP-002 statutory_basis (current value unknown -> windowed rewrite)
windowed_basis(E, "CAP-002", "Section 159(1), Companies Act 1994 (Bangladesh)")

# F3: TL-001 basis - the 1983 Ordinance was replaced by the 2009 Acts
subx(E,
    "City Corporation Ordinance 1983 / Pourashava Act 2009",
    "Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
    "F3 TL-001 statutory basis")

# F4: stale INC-002 in API docstring
subx("app/api/rules.py",
    "CAP-003, INC-002, INC-004)",
    "CAP-003, INC-004)",
    "F4 api docstring INC-002 removed")

# F5a: seed_rules - delete INC-002 entry line
rex("scripts/seed_rules.py", r'^[ \t]*\{"rule_id": "INC-002".*\r?\n', "",
    "F5a seed INC-002 entry removed", count=0)

# F5b: seed_rules - sync CAP-002 entry (line-scoped)
sync_line("scripts/seed_rules.py", '"rule_id": "CAP-002"', [
    ("Charge Not Registered With RJSC Within 30 Days",
     "Charge Not Registered With RJSC Within 21 Days"),
    ("not registered via Form VIII within 30 days. Section 87:",
     "not registered via Form VIII within 21 days. Section 159(1):"),
    ("days_since_charge_creation > 30",
     "days_since_charge_creation > 21"),
    ('"statutory_basis": "Section 87, Companies Act 1994 (Bangladesh)"',
     '"statutory_basis": "Section 159(1), Companies Act 1994 (Bangladesh)"'),
], "F5b seed CAP-002 sync")

# F6: models/rjsc_forms.py - FORM_VIII entry (line-scoped)
sync_line("app/models/rjsc_forms.py", '"FORM_VIII"', [
    ('"section": "Section 87"', '"section": "Section 159(1)"'),
    ('"deadline_days": 30', '"deadline_days": 21'),
], "F6 FORM_VIII sync")

# F7: audit EXPECTED - CAP-002 -> Section 159
rex("tools/legal_citation_audit.py", r'"CAP-002": \[[^\]]*\]',
    '"CAP-002": ["Section 159", "Section 159(1)"],',
    "F7 audit EXPECTED CAP-002")

# F8: test citations (the 2 remaining audit FAILs)
windowed_basis("tests/integration/test_services.py", "OFF-001",
               "Section 77, Companies Act 1994 (Bangladesh)")
windowed_basis("tests/unit/test_pdf_report_service.py", "AGM-001",
               "Section 81, Companies Act 1994 (Bangladesh)")

# Syntax gate on every touched file
FILES = [E, "app/api/rules.py", "scripts/seed_rules.py", "app/models/rjsc_forms.py",
         "tools/legal_citation_audit.py",
         "tests/integration/test_services.py", "tests/unit/test_pdf_report_service.py"]
for f in FILES:
    ast.parse(load(f))
print("AST OK on %d files" % len(FILES))

print("\n--- APPLIED ---")
for x in OK: print("  FIXED " + x)
print("\n--- SKIPPED (pattern not found - usually means already fixed, or paste window back) ---")
for x in SKIP: print("  SKIP  " + x)
