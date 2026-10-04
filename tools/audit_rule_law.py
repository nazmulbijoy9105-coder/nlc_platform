#!/usr/bin/env python3
"""Read-only consistency audit: rule_id -> statutory section across every layer.

Run from repo root:  python tools/audit_rule_law.py
Exit code 1 if any mismatch is found (usable in pre-commit / CI).

Layers compared (section NUMBERS only, subsection parens stripped):
  seed      scripts/seed_rules.py                       "statutory_basis"
  canon     canonical_architecture/statutory_rules.py   "law"
  engine    app/rule_engine/engine.py                   statutory_basis=
  forms     app/models/rjsc_forms.py                    "section" per rule_id
  alembic   alembic/versions/*.py                       UPDATE legal_rules SET statutory_basis
"""
import glob
import re
import sys
from collections import defaultdict

RID = r"[A-Z]+-\d+"


def secs(text):
    out = set()
    for m in re.finditer(r"Sections?\s+([0-9][0-9(),\sand\u2013\-]*)", text or ""):
        for n in re.findall(r"\d+(?:\(\d+\))?", m.group(1)):
            out.add(n.split("(")[0])
    return out


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        print(f"[warn] missing {path}")
        return []


seed, canon = {}, {}
engine = defaultdict(list)
forms = defaultdict(list)
mig = []  # (file, rule_id, text)

for line in read("scripts/seed_rules.py"):
    a = re.search(rf'"rule_id":\s*"({RID})"', line)
    b = re.search(r'"statutory_basis":\s*"([^"]*)"', line)
    if a and b:
        seed[a.group(1)] = b.group(1)

cur = None
for line in read("canonical_architecture/statutory_rules.py"):
    a = re.search(rf'"rule_id":\s*"({RID})"', line)
    if a:
        cur = a.group(1)
    b = re.search(r'"law":\s*"([^"]*)"', line)
    if b and cur:
        canon[cur] = b.group(1)

cur = None
for line in read("app/rule_engine/engine.py"):
    a = re.search(rf'rule_id="({RID})"', line)
    if a:
        cur = a.group(1)
    b = re.search(r'statutory_basis="([^"]*)"', line)
    if b and cur:
        engine[cur].append(b.group(1))
        cur = None

for line in read("app/models/rjsc_forms.py"):
    m = re.search(rf'"section":\s*"([^"]*)",\s*"rule_id":\s*"({RID})"', line)
    if m:
        forms[m.group(2)].append(m.group(1))

for path in sorted(glob.glob("alembic/versions/*.py")):
    txt = "\n".join(read(path))
    for m in re.finditer(
        r"UPDATE legal_rules SET statutory_basis\s*=\s*'([^']*)'\s*WHERE rule_id\s*(?:=|IN)\s*\(?([^;]*?)\)?\s*;",
        txt,
    ):
        for rid in re.findall(rf"'({RID})'", m.group(2)):
            mig.append((path, rid, m.group(1)))

bad = 0


def report(rid, label, base, other_text):
    global bad
    s_other = secs(other_text)
    if base and s_other and base != s_other:
        bad += 1
        print(f"{rid:9s} {label:8s} {sorted(s_other, key=int)}  != seed {sorted(base, key=int)}   <- {other_text[:70]}")


for rid, text in seed.items():
    base = secs(text)
    if rid in canon:
        report(rid, "canon", base, canon[rid])
    for t in engine.get(rid, []):
        report(rid, "engine", base, t)
    for t in forms.get(rid, []):
        report(rid, "forms", base, t)
for path, rid, text in mig:
    if rid in seed:
        report(rid, path.split("/")[-1][:8], secs(seed[rid]), text)

only_canon = sorted(set(canon) - set(seed))
only_seed = sorted(set(seed) - set(canon))
print(f"\nrules: seed={len(seed)} canon={len(canon)} engine={len(engine)}")
print("in canon not seed:", only_canon or "-")
print("in seed not canon:", only_seed or "-")
print(f"\nMISMATCHES: {bad}")
sys.exit(1 if bad else 0)
