#!/usr/bin/env python3
"""Round-3: TL-001 expected -> 2009 Acts; engine count 85; seed OFF-001 dedup."""
import io, re, ast

def load(p): return io.open(p, encoding="utf-8", newline="").read()
def save(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)
OK, SKIP = [], []

# F1: audit EXPECTED TL-001 -> match the corrected statutory basis
A = "tools/legal_citation_audit.py"
t = load(A)
t2, n = re.subn(r'"TL-001":\s*\[[^\]]*\]',
                lambda m: '"TL-001": ["City Corporation", "Paurashava"],',
                t, count=1)
if n: save(A, t2)
(OK if n else SKIP).append("F1 audit EXPECTED TL-001: %d hit" % n)

# F2: integrity test engine count 86 -> 85 (INC-002 removed from engine)
T = "tests/unit/test_canonical_integrity.py"
t = load(T)
t2, n = re.subn(r'(EXPECTED[A-Za-z_]*\s*=\s*)86\b', lambda m: m.group(1) + "85", t, count=1)
if n == 0:
    t2, n = re.subn(r'(_engine_ids\(\)\s*==\s*)86\b', lambda m: m.group(1) + "85", t, count=1)
if n: save(T, t2)
(OK if n else SKIP).append("F2 test engine count 86->85: %d hit" % n)

# F3: seed dedup - drop the OFF-001 line still carrying INC-002 content
S = "scripts/seed_rules.py"
lines = load(S).splitlines(True)
print("--- OFF-001 seed lines seen ---")
for l in lines:
    if '"rule_id": "OFF-001"' in l: print("  ", l.strip()[:160])
bad = [l for l in lines if '"rule_id": "OFF-001"' in l
       and ('"check_fn": "check_inc_002"' in l or '"rule_name": "Form III Not Filed"' in l)]
if len(bad) == 1:
    keep = [l for l in lines if l not in bad]
    left = sum(1 for l in keep if '"rule_id": "OFF-001"' in l)
    save(S, "".join(keep))
    OK.append("F3 seed dup OFF-001 removed; %d OFF-001 line(s) remain" % left)
else:
    SKIP.append("F3 seed dup OFF-001: found %d candidate line(s)" % len(bad))

for f in (A, T, S): ast.parse(load(f))
print("AST OK on all 3 files")
for x in OK: print("  FIXED " + x)
for x in SKIP: print("  SKIP  " + x)
