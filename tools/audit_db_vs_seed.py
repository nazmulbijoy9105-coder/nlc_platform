#!/usr/bin/env python3
"""Read-only audit: DB-after-migrations vs scripts/seed_rules.py, plus two engine checks.

Usage (repo root):
  python tools/audit_db_vs_seed.py db_rules.txt

db_rules.txt = psql -At -F '|' dump of:
  rule_id|rule_name|statutory_basis|default_severity|score_impact|is_black_override|is_active

Checks
  1. every seed rule exists in the migrated DB with the same section numbers,
     severity, score_impact, is_black_override, active flag, and name
  2. DB rules that are not in the seed (orphans)
  3. engine.BLACK_OVERRIDE_RULES vs seed is_black_override
  4. engine/service functions annotated -> int/bool/str/float/date that can fall
     through without a return (returns None at runtime)
Exit code 1 on any finding.
"""
import ast
import glob
import re
import sys

RID = r"[A-Z]+-\d+"
bad = 0


def out(rid, msg):
    global bad
    bad += 1
    print(f"{rid:10s} {msg}")


def nums(text):
    found = set()
    for m in re.finditer(r"Sections?\s+([0-9][0-9(),\sand\u2013\-]*)", text or ""):
        found.update(n.split("(")[0] for n in re.findall(r"\d+(?:\(\d+\))?", m.group(1)))
    return found


def field(line, key):
    m = re.search(rf'"{key}":\s*"([^"]*)"', line)
    return m.group(1) if m else None


seed = {}
with open("scripts/seed_rules.py", encoding="utf-8") as f:
    for line in f:
        a = re.search(rf'"rule_id":\s*"({RID})"', line)
        if not a:
            continue
        score = re.search(r'"score_impact":\s*(\d+)', line)
        blk = re.search(r'"is_black_override":\s*(True|False)', line)
        sev, basis = field(line, "default_severity"), field(line, "statutory_basis")
        if sev and basis and score and blk:
            seed[a.group(1)] = dict(
                name=field(line, "rule_name") or "",
                basis=basis,
                sev=sev,
                score=int(score.group(1)),
                black=blk.group(1) == "True",
            )

db = {}
if len(sys.argv) > 1:
    with open(sys.argv[1], encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("|")
            if len(p) < 7:
                continue
            truthy = ("t", "true", "True")
            db[p[0]] = dict(
                name=p[1], basis=p[2], sev=p[3], score=int(p[4]),
                black=p[5] in truthy, active=p[6] in truthy,
            )

print(f"seed rules: {len(seed)}   db rules: {len(db)}\n")

if db:
    for rid, s in sorted(seed.items()):
        d = db.get(rid)
        if not d:
            out(rid, "MISSING in migrated DB")
            continue
        if nums(s["basis"]) != nums(d["basis"]):
            out(rid, f"sections DB {sorted(nums(d['basis']), key=int)} != seed {sorted(nums(s['basis']), key=int)}")
        if s["sev"] != d["sev"]:
            out(rid, f"severity DB {d['sev']} != seed {s['sev']}")
        if s["score"] != d["score"]:
            out(rid, f"score_impact DB {d['score']} != seed {s['score']}")
        if s["black"] != d["black"]:
            out(rid, f"is_black_override DB {d['black']} != seed {s['black']}")
        if not d["active"]:
            out(rid, "inactive in DB")
        if s["name"].strip().lower() != d["name"].strip().lower():
            out(rid, f"name DB '{d['name'][:45]}' != seed '{s['name'][:45]}'")
    for rid in sorted(set(db) - set(seed)):
        out(rid, f"in DB, not in seed: '{db[rid]['name'][:50]}'")
else:
    print("[skip] no DB dump given; checks 1-2 not run\n")

try:
    with open("app/rule_engine/engine.py", encoding="utf-8") as f:
        src = f.read()
except FileNotFoundError:
    src = ""

m = re.search(r"BLACK_OVERRIDE_RULES\s*=\s*\{([^}]*)\}", src)
if m:
    eng = set(re.findall(rf'"({RID})"', m.group(1)))
    sb = {r for r, s in seed.items() if s["black"]}
    for r in sorted(eng - sb):
        out(r, "in engine BLACK_OVERRIDE_RULES but seed is_black_override=False")
    for r in sorted(sb - eng):
        out(r, "seed is_black_override=True but NOT in engine BLACK_OVERRIDE_RULES")


def always_returns(stmts):
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, (ast.Return, ast.Raise)):
        return True
    if isinstance(last, ast.If):
        return bool(last.orelse) and always_returns(last.body) and always_returns(last.orelse)
    if isinstance(last, (ast.Try, ast.With, ast.While, ast.For)):
        return True  # not analysed; do not flag
    return False


for path in ["app/rule_engine/engine.py"] + sorted(glob.glob("app/services/*.py")):
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError):
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.returns is not None:
            if ast.unparse(node.returns) in ("int", "bool", "str", "float", "date") and not always_returns(node.body):
                out(node.name, f"{path}:{node.lineno} annotated '-> {ast.unparse(node.returns)}' but can fall through (returns None)")

print(f"\nFINDINGS: {bad}")
sys.exit(1 if bad else 0)
