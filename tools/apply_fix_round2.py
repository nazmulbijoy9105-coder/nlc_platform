#!/usr/bin/env python3
"""Round-2 fixes: audit repair + seed INC-002 removal (2026-10-30)."""
import io, ast

def load(p): return io.open(p, encoding="utf-8", newline="").read()
def save(p, t): io.open(p, "w", encoding="utf-8", newline="").write(t)
OK, SKIP = [], []

def rep(path, old, new, label):
    t = load(path)
    n = t.count(old)
    if n: save(path, t.replace(old, new, 1))
    (OK if n else SKIP).append("%s: %d hit(s)" % (label, n))

A = "tools/legal_citation_audit.py"

# R1: repair double comma from batch-3 EXPECTED replacement
rep(A, '"CAP-002": ["Section 159", "Section 159(1)"],,',
       '"CAP-002": ["Section 159", "Section 159(1)"],',
       "R1 double-comma repaired")

# R2: fixtures are not legal sources - drop tests/ from citation scan
rep(A, 'SCAN_DIRS = ["app", "canonical_architecture", "tests"]',
       'SCAN_DIRS = ["app", "canonical_architecture"]',
       "R2 tests/ dropped from scan")

# R3: docstring sync (cosmetic)
rep(A, "Scans live declarations in app/, canonical_architecture/, tests/. alembic/ = historical, excluded.",
       "Scans live declarations in app/, canonical_architecture/. tests/ (fixtures) and alembic/ (history) excluded.",
       "R3 docstring")

# R4: remove seed INC-002 entry (robust line filter)
p = "scripts/seed_rules.py"
lines = load(p).splitlines(True)
keep = [l for l in lines if '"rule_id": "INC-002"' not in l]
if len(keep) != len(lines):
    save(p, "".join(keep))
    OK.append("R4 seed INC-002 removed (%d line)" % (len(lines) - len(keep)))
else:
    SKIP.append("R4 seed INC-002 not found")

for f in (A, p): ast.parse(load(f))
print("AST OK on both files")
for x in OK: print("  FIXED " + x)
for x in SKIP: print("  SKIP  " + x)
