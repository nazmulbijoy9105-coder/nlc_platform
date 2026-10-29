#!/usr/bin/env python3
"""Round-4: repair audit double-comma, map TL-002, self-heal round-3 saves."""
import io, ast

def load(p): return io.open(p, encoding="utf-8", newline="").read()
def save(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)

A = "tools/legal_citation_audit.py"
t = load(A)

# G1: repair the double comma from round-3 F1
n = t.count('"Paurashava"],,')
if n:
    t = t.replace('"Paurashava"],,', '"Paurashava"],')
    save(A, t)
    print("G1 FIXED double comma (%d)" % n)
else:
    print("G1 SKIP (no double comma)")

# G2: map TL-002 (engine line 632 cites the same 2009 Acts)
if '"TL-002"' not in t:
    anchor = '"TL-001": ["City Corporation", "Paurashava"],'
    if anchor in t:
        t = t.replace(anchor, anchor + '\n    "TL-002": ["City Corporation", "Paurashava"],')
        save(A, t)
        print("G2 FIXED TL-002 mapped")
    else:
        print("G2 SKIP (TL-001 anchor not found)")
else:
    print("G2 SKIP (TL-002 already mapped)")

ast.parse(load(A))
print("AUDIT AST OK")

# G3: self-heal the integrity test count (in case round-3 F2 did not save)
T = "tests/unit/test_canonical_integrity.py"
t = load(T)
if "EXPECTED = 85" in t:
    print("G3 test count 85 OK")
elif "EXPECTED = 86" in t:
    save(T, t.replace("EXPECTED = 86", "EXPECTED = 85"))
    print("G3 FIXED EXPECTED 86->85")
else:
    print("G3 UNKNOWN count constant - paste: git grep -n EXPECTED -- tests/unit/test_canonical_integrity.py")

# G4: self-heal the seed dedup (in case round-3 F3 did not save)
S = "scripts/seed_rules.py"
s = load(S)
cnt = s.count('"rule_id": "OFF-001"')
if cnt == 1:
    print("G4 seed OFF-001 lines: 1 OK")
else:
    print("G4 seed OFF-001 lines:", cnt, "- removing remnant")
    lines = s.splitlines(True)
    bad = [l for l in lines if '"rule_id": "OFF-001"' in l
           and ('"check_fn": "check_inc_002"' in l or '"rule_name": "Form III Not Filed"' in l)]
    if len(bad) == 1:
        save(S, "".join(l for l in lines if l not in bad))
        print("G4 FIXED dup removed, 1 remains")
    else:
        print("G4 CANNOT AUTO-FIX - paste OFF-001 lines back")
